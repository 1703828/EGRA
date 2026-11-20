"""
Vegetacio mesurada dibuixada amb un geometry shader (tasca 45.3 del pla; acta 05, §2.1; F53: es prepara sola i aspecte).

D'on surt: la superficie dels obstacles de cada cel·la de 3 x 3 km (dades/alcaries.preparar_superficie: terra +
alcaria del LiDAR, a 2 m amb l'ICGC o 2,5 m amb l'IGN) i les capes 'ulls' (el terra fora dels edificis) i 'edifici'
(contorns del Catastro). Cada cel·la amb un objecte de mes de MIN_M fora dels edificis es un punt: posicio del terra
i alcaria. El geometry shader (shaders/vegetacio.geom) en fa una columna de la mida de la cel·la.

Preparacio (F53, 20/11/2026): en activar la casella, les cel·les a menys de RADI_KM del punt de detall que encara no
tenen la superficie la preparen en un proces (la mateixa feina i els mateixos fitxers que el mapa de visibilitat de
detall, basecode/mapes.py: si un dels dos ja l'ha feta, l'altre la llegeix). Cal el relleu de 5 m del lloc (el
prepara basecode/detall.py) i el LiDAR (dades/alcaries.alcaria_cel, compartit amb les altures dels edificis: sovint ja
es al disc). motiu() diu per que no se'n veu: preparant-se, sense cobertura LiDAR, sense relleu, camera massa lluny.

Per que columnes i no arbres: l'estudi de dades (scripts/estudi_vegetacio.py, 45.1-45.2) troba capcades a la UAB,
pero el 78 % de la vegetacio forma masses continues, i substituir-la per un con per capcada canvia l'horitzo de la
posta una mediana d'1,8 graus (fins a 27): el que es veuria no seria el que calcula el mapa. Les columnes son
exactament la superficie del calcul (nivell N3 dels mapes): el Sol queda tapat a la imatge on el calcul diu que ho
esta (D94). Limitacions: el model d'alcaries es 2,5D (sense espai sota les capcades: un arbre es una massa fins a
terra) i l'ICGC no separa la vegetacio d'altres objectes (pals, tanques, cotxes).

Aspecte (F53; nomes il·luminacio i color, la geometria no canvia): cada punt porta la normal de la superficie suavitzada
(gaussiana de SIGMA_NORMAL_M, terra inclos: les vores de cada massa s'arrodoneixen a la llum), que el fragment shader fa
servir a la coberta i barreja amb la de cada cara lateral; color amb variacio natural (soroll a l'escala d'una capcada
i de les fulles, en coordenades del lloc: no rellisca en moure's), mes fosc cap a baix (oclusio aproximada), llum
filtrada entre les fulles i les ombres del relleu i dels edificis (ombres.glsl). Il·lustratiu: el LiDAR no diu l'especie.

Mode alternatiu (didactic, nomes des dels scripts: scripts/estudi_vegetacio_gpu.py): instancing
(shaders/vegetacio_inst.vert), amb les mateixes dades i el mateix descart de cares. Es mes lent que el geometry shader
(15-17 ms contra 6-7 ms de GPU per al milio de columnes de la UAB, 16/11).

Es dibuixen les cel·les a menys de RADI_KM del punt de detall, i nomes els punts a menys de DIST_MAX_KM de la camera (el
shader no emet la resta).
"""
import math
import os

import glm
import moderngl as mgl
import numpy as np
from pyproj import Transformer

from .programes import carregar_programa
from dades import alcaries, atmosfera, geodesia
from dades.feines import Feina, FeinaProces
from dades.model_eclipsi import area_tapada, angle_entre
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM

MIN_M = 1.5          # alcaria minima d'un objecte per dibuixar-lo (m)
RADI_KM = 2.0        # cel·les a aquesta distancia del punt de detall
DIST_MAX_KM = 1.5
MAX_CEL_LES = 4
SIGMA_NORMAL_M = 3.0  # suavitzat de la superficie per a la normal de la llum (m; ~ mitja capcada)
_A_LATLON = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
_A_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True)
TROS_M = 500.0        # els punts s'agrupen en trossos de 500 x 500 m: nomes es dibuixen els que son a prop de la camera
SIGMA_TO_M = 3.0      # mida de les taques de color (m; ~ una capcada)
# per punt, 20 bytes (com abans de la F53: cada byte de mes es llegeix per a cada punt a cada fotograma): terra (km),
# alcaria (km) i 4 bytes: cares, normal (est, nord) de la superficie suavitzada i to de verd, de 0 a 255 (la GPU els
# rep de 0 a 1: 'f1', unsigned byte normalitzat)
FORMAT = '3f 1f 4f1'
ATRIBUTS = ('in_base', 'in_alt', 'in_dades')


def normals_superficie(sup, res):
    """Components est i nord de la normal de la superficie (terra + objectes) suavitzada amb una gaussiana de
    SIGMA_NORMAL_M. Les files van cap al sud (GeoTIFF): d/dnord = -d/dfila."""
    from scipy.ndimage import gaussian_filter
    s = np.where(np.isfinite(sup), sup, np.nanmin(sup) if np.isfinite(sup).any() else 0.0).astype('f4')
    s = gaussian_filter(s, SIGMA_NORMAL_M / res)
    dz_dfila, dz_dcol = np.gradient(s, res)
    nx, ny = -dz_dcol, dz_dfila            # (-dz/dest, -dz/dnord, 1) sense normalitzar
    m = np.sqrt(nx * nx + ny * ny + 1.0)
    return nx / m, ny / m


def tons_verd(forma, res, llavor):
    """To de verd (0..1) de cada cel·la: soroll blanc suavitzat amb una gaussiana de SIGMA_TO_M i passat a una
    distribucio uniforme. La llavor surt de la clau de la cel·la: el mateix color cada vegada. Nomes estetic."""
    from math import sqrt
    from scipy.ndimage import gaussian_filter
    from scipy.special import erf
    soroll = gaussian_filter(np.random.default_rng(llavor).standard_normal(forma).astype('f4'), SIGMA_TO_M / res)
    z = soroll / max(float(soroll.std()), 1e-6)
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def punts_cel(clau_cel, avis=None):
    """Punts de vegetacio d'una cel·la (sense OpenGL): (origen ECEF, vertexs (n; FORMAT): terra (km, relatiu a
    l'origen), alcaria (km), cares exposades (bits: est, oest, nord, sud; 16 a tocar d'un edifici) i la normal (est,
    nord) de la superficie suavitzada i el to de verd (tons_verd)), res (m), trossos), o None. Els punts van ordenats
    per trossos de TROS_M: (primer, quants, centre, radi) de cada un."""
    import rasterio
    capes = {}
    for capa in ('superficie', 'ulls', 'edifici'):
        cami = alcaries.cami_superficie(clau_cel, capa)
        if not os.path.exists(cami):
            return None
        with rasterio.open(cami) as f:
            capes[capa], tr = f.read(1), f.transform
    alt = capes['superficie'] - capes['ulls']
    ok = np.isfinite(alt) & (alt > MIN_M) & (capes['edifici'] == 0)
    # cares exposades: on la cel·la del costat (est, oest, nord, sud) no te una columna de vegetacio tan alta (en un
    # bosc dens, la majoria de cares queden tapades per les del costat i no cal emetre-les)
    sup = np.where(ok, capes['superficie'], -1e9)
    p = np.pad(sup, 1, constant_values=-1e9)
    veina = [p[1:-1, 2:], p[1:-1, :-2], p[:-2, 1:-1], p[2:, 1:-1]]
    mascara = sum((1 << i) * (veina[i] < sup - 0.3) for i in range(4))
    # a menys de 2 cel·les d'un contorn del Catastro, l'objecte mesurat sol ser part de l'edifici (rafecs, porxos o
    # el desplacament entre el contorn i el LiDAR), no un arbre: es pinta gris (bit 4). Compta igual com a obstacle
    from scipy.ndimage import binary_dilation
    prop = binary_dilation(capes['edifici'] > 0, iterations=2)
    mascara = mascara + 16 * prop
    nx, ny = normals_superficie(capes['superficie'], tr.a)
    import zlib
    to = tons_verd(alt.shape, tr.a, zlib.crc32(clau_cel.encode()))
    files, cols = np.nonzero(ok)
    x, y = tr * (cols + 0.5, files + 0.5)
    lon, lat = _A_LATLON.transform(np.asarray(x), np.asarray(y))
    _, cx, cy = clau_cel.split('_')
    lo0, la0 = _A_LATLON.transform(float(cx), float(cy))
    origen = geodesia.ecef(la0, lo0, 0.0)
    base = geodesia.ecef(np.asarray(lat), np.asarray(lon), capes['ulls'][files, cols] / 1000.0) - origen
    # baixos (matolls, < 3 m): cap als verds clars (estetic)
    to = np.where(alt < 3.0, 0.45 * to + 0.4, to)
    # ordenats per trossos de TROS_M: (primer, quants, centre (km, relatiu a l'origen), radi (km)) de cada tros
    n_tros = int(round(TROS_M / tr.a))
    tros = (files // n_tros) * 10000 + cols // n_tros
    ordre = np.argsort(tros, kind='stable')
    files, cols, tros, base = files[ordre], cols[ordre], tros[ordre], base[ordre]
    inici = np.flatnonzero(np.r_[True, tros[1:] != tros[:-1]])
    quants = np.diff(np.r_[inici, len(tros)])
    trossos = []
    for i, k in zip(inici, quants):
        c = base[i:i + k].mean(axis=0)
        trossos.append((int(i), int(k), c, float(np.sqrt(((base[i:i + k] - c) ** 2).sum(axis=1)).max())))
    a = np.column_stack([base, alt[files, cols] / 1000.0]).astype('f4')
    b = np.column_stack([mascara[files, cols], np.round(127.5 + 127.5 * nx[files, cols]),
                         np.round(127.5 + 127.5 * ny[files, cols]), np.round(255 * to[files, cols])]).astype('u1')
    v = np.empty(len(a), dtype=[('a', 'f4', 4), ('b', 'u1', 4)])
    v['a'], v['b'] = a, b
    return origen, v, tr.a, trossos


def _preparar_superficie(cel, cami_mdt, parts_zona, avis):
    """La superficie dels obstacles d'una cel·la (FeinaProces): la mateixa funcio que el mapa de detall."""
    from .detall import _preparar_superficie as preparar
    return preparar(cel, cami_mdt, parts_zona, avis)


UNITAT_SOROLL = 0     # (cada programa lliga les seves textures abans de dibuixar)
MIDA_SOROLL_M = 4.0   # la textura de soroll de les fulles es repeteix cada 4 m (i una segona lectura, cada 1,45 m)


def textura_soroll(n=256, sigma_px=6.0, llavor=53):
    """Soroll de les fulles (RGBA8, n x n, es pot repetir: filtre gaussia amb vores circulars): R, clapes de llum i
    ombra; G i B, inclinacio de la normal; A, una segona clapa. Amb mipmaps, de lluny es fa la mitjana (sense
    parpelleig) i el detall no cal apagar-lo a ma."""
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(llavor).standard_normal((n, n, 4)).astype('f4')
    for k in range(4):
        r[..., k] = gaussian_filter(r[..., k], sigma_px, mode='wrap')
        r[..., k] = 0.5 + 0.5 * r[..., k] / (2.0 * r[..., k].std())
    return (np.clip(r, 0.0, 1.0) * 255).astype('u1')


def _cub():
    """Cub de la columna per al mode d'instancing: 36 vertexs (x, y, z, cara)."""
    cares = [(((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), 0), (((1, -1, 0), (1, 1, 0), (1, 1, 1), (1, -1, 1)), 1),
             (((-1, 1, 0), (-1, -1, 0), (-1, -1, 1), (-1, 1, 1)), 2), (((1, 1, 0), (-1, 1, 0), (-1, 1, 1), (1, 1, 1)), 3),
             (((-1, -1, 0), (1, -1, 0), (1, -1, 1), (-1, -1, 1)), 4), (((-1, -1, 0), (-1, 1, 0), (1, 1, 0), (1, -1, 0)), 5)]
    return np.array([(*q, k) for (a, b, c, d), k in cares for q in (a, b, c, a, c, d)], 'f4')


class Vegetacio:
    def __init__(self, app):
        self.app, self.ctx = app, app.ctx
        self.actiu = False
        self.programa = carregar_programa(self.ctx, 'vegetacio')
        self.instancing = False           # mode alternatiu (scripts): instancing en lloc del geometry shader
        self.programa_inst = carregar_programa(self.ctx, 'vegetacio', vertex='vegetacio_inst', geometry=False)
        self.cub = self.ctx.buffer(_cub().tobytes())
        self.soroll = self.ctx.texture((256, 256), 4, textura_soroll().tobytes())
        self.soroll.build_mipmaps()
        self.soroll.repeat_x = self.soroll.repeat_y = True
        self.soroll.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.soroll.anisotropy = 8.0
        self.cel_les = {}      # clau de la cel·la -> dict(vbo, vao, n, origen, res)
        self.feines = {}       # ('punts' | 'superficie', clau de la cel·la) -> Feina
        self.fallades = {}     # (tipus, clau) -> error
        self.n_punts = 0
        self.volgudes = []
        self.esperant = {}     # clau -> per que encara no es prepara (relleu, edificis)

    # ------------------------------------------------------------------ preparar

    def _recollir(self):
        for k, f in list(self.feines.items()):
            if not f.fet:
                continue
            del self.feines[k]
            tipus, c = k
            if tipus == 'superficie':
                if f.resultat is None:
                    self.fallades[k] = f.error or 'cap model d\'alcaries (LiDAR) no cobreix aquest lloc'
                continue
            if f.resultat is None:
                self.fallades[k] = f.error or 'sense dades'
                continue
            origen, v, res, trossos = f.resultat
            vbo = self.ctx.buffer(v.tobytes()) if len(v) else None
            vao = self.ctx.vertex_array(self.programa, [(vbo, FORMAT, *ATRIBUTS)]) if vbo else None
            vao_i = self.ctx.vertex_array(self.programa_inst, [(self.cub, '3f 1f', 'in_cub', 'in_cara'),
                                                               (vbo, FORMAT + '/i', *ATRIBUTS)]) if vbo else None
            self.cel_les[c] = dict(vbo=vbo, vao=vao, vao_i=vao_i, n=len(v), origen=origen, res=res, trossos=trossos)

    def _preparar_superficie(self, c, cx, cy):
        """Engega la superficie dels obstacles de la cel·la (un proces, una cel·la de cada vegada, i mai alhora amb
        la mateixa feina del mapa de detall), o diu a self.esperant per que encara no."""
        app = self.app
        mapes = getattr(app, 'mapes', None)
        if mapes is not None and any(t == 'superficie' for t, _ in mapes.feines):
            self.esperant[c] = 'el mapa de visibilitat prepara els obstacles'
            return
        if any(t == 'superficie' for t, _ in self.feines) or not app.detall.preparar:
            return
        rect = (cx - 1500, cy - 1500, cx + 1500, cy + 1500)
        mdt = mapes._mdt_5m(rect) if mapes is not None else None
        if mdt is None:
            self.esperant[c] = 'falta el relleu de 5 m del lloc'
            return
        # amb els contorns del Catastro: les columnes dins d'un edifici no son vegetacio. La superficie es desa i no
        # es refa: cal esperar que l'etapa dels edificis del lloc s'hagi fet (n'hi hagi o no) o hagi fallat
        parts_zona = next((z['clau'] for z in app.detall.zones() if app.detall.te_edificis(z['clau'], cx, cy)), None)
        if parts_zona is None and not self._sense_edificis(cx, cy):
            self.esperant[c] = 'esperant els edificis del lloc'
            return
        f = FeinaProces(c, _preparar_superficie, (cx, cy), mdt, parts_zona, descripcio='superficie de la vegetacio')
        f.lloc = _A_LATLON.transform(cx, cy)[::-1]
        self.feines[('superficie', c)] = f
        self.esperant.pop(c, None)

    def _sense_edificis(self, cx, cy):
        """Si es segur que la cel·la (cx, cy) no tindra contorns del Catastro: l'etapa dels edificis del lloc ja s'ha
        fet o ha fallat (p. ex. Navarra i el Pais Basc, sense Catastro estatal), o es una zona feta a ma."""
        from dades import llocs
        app = self.app
        c = llocs.clau_per_punt(cx, cy)
        if any(t in app.detall.feines and getattr(app.detall.feines[t], 'clau', None) == c
               for t in ('cadastre', 'edificis', 'relleu', 'malla')):
            return False
        if llocs.edificis_fets(c) or any(k[1] == c for k in app.detall.fallades if isinstance(k, tuple)):
            return True
        return any(z['estatica'] and z['clau'] for z in app.detall.zones()
                   if app.mapes._mdt_5m((cx - 1500, cy - 1500, cx + 1500, cy + 1500)) == z['cami'])

    def actualitzar(self):
        """Cel·les a prop del punt de detall: la superficie es prepara en un proces si falta, els punts en un fil i es
        pugen aqui."""
        self._recollir()
        if not self.actiu:
            return
        p = self.app.detall.punt
        if p is None:
            self.volgudes = []
            return
        x, y = _A_UTM.transform(p[1], p[0])
        cx, cy = alcaries.centre_cel(x, y)
        volgudes = []
        for dx in (-3000, 0, 3000):
            for dy in (-3000, 0, 3000):
                c = f'cel_{cx + dx:.0f}_{cy + dy:.0f}'
                d = max(abs(x - (cx + dx)) - 1500, abs(y - (cy + dy)) - 1500, 0)
                if d < RADI_KM * 1000:
                    volgudes.append((d, c, cx + dx, cy + dy))
        volgudes = sorted(volgudes)[:MAX_CEL_LES]
        self.volgudes = [c for _, c, _, _ in volgudes]
        for _, c, ccx, ccy in volgudes:
            if c in self.cel_les or ('punts', c) in self.feines or ('superficie', c) in self.feines or \
                    ('punts', c) in self.fallades or ('superficie', c) in self.fallades:
                continue
            if os.path.exists(alcaries.cami_superficie(c, 'edifici')):
                if not any(t == 'punts' for t, _ in self.feines):
                    # en un proces: el filtre i l'ordenacio de ~1 milio de punts, en un fil, retenien el GIL i
                    # allargaven algun fotograma (0,3 s a la prova)
                    f = FeinaProces(c, punts_cel, c, descripcio='vegetacio')
                    f.lloc = _A_LATLON.transform(ccx, ccy)[::-1]
                    self.feines[('punts', c)] = f
                self.esperant.pop(c, None)
            else:
                self._preparar_superficie(c, ccx, ccy)
        for c in [c for c in self.cel_les if c not in self.volgudes]:
            self._treure(c)
        self.n_punts = sum(v['n'] for v in self.cel_les.values())

    def motiu(self):
        """Per que no es veu vegetacio (o '' si se'n veu o no esta activada): el text del panell."""
        if not self.actiu:
            return ''
        app = self.app
        if any(t == 'superficie' for t, _ in self.feines):
            return ''                  # surt a Descarregues
        if any(t == 'punts' for t, _ in self.feines):
            return ''
        if not self.volgudes:
            return 'cap lloc de detall (acosta\'t al terra)'
        # la vegetacio nomes es dibuixa a menys de DIST_MAX_KM de la camera: si el terra es mes lluny, aquest es el
        # motiu (encara que la cel·la del punt de detall tambe s'hagi de preparar)
        if app.camera.alcada_sobre_terra() > DIST_MAX_KM:
            return self._text_lluny()
        c = self.volgudes[0]           # la cel·la del punt de detall
        if ('superficie', c) in self.fallades:
            e = self.fallades[('superficie', c)]
            return 'sense cobertura LiDAR en aquest lloc' if 'no cobreix' in e else f'no s\'ha pogut preparar ({e})'
        if c in self.esperant:
            return self.esperant[c]
        if c in self.cel_les and self.cel_les[c]['n'] == 0:
            return 'el LiDAR no hi mesura cap objecte de mes de 1,5 m fora dels edificis'
        d = self.distancia_km()
        if d is not None and d > DIST_MAX_KM:
            return self._text_lluny()
        return ''

    @staticmethod
    def _text_lluny():
        return f'la camera es massa lluny (es dibuixa a menys de {DIST_MAX_KM:.1f} km)'.replace('.', ',')

    def distancia_km(self):
        """Distancia de la camera a la vegetacio carregada mes propera (al rectangle de la seva cel·la), o None."""
        if not self.cel_les:
            return None
        cam = self.app.camera
        lat, lon, alt = cam.geodesiques()
        x, y = _A_UTM.transform(lon, lat)
        h = max(cam.alcada_sobre_terra(), 0.0)
        millor = None
        for c in self.cel_les:
            _, ccx, ccy = c.split('_')
            dx = max(abs(x - float(ccx)) - 1500, 0) / 1000
            dy = max(abs(y - float(ccy)) - 1500, 0) / 1000
            d = math.sqrt(dx * dx + dy * dy + h * h)
            millor = d if millor is None else min(millor, d)
        return millor

    def _treure(self, c):
        v = self.cel_les.pop(c)
        for o in (v['vao'], v['vao_i'], v['vbo']):
            if o is not None:
                o.release()

    # ------------------------------------------------------------------ dibuixar

    def render(self):
        if not self.actiu or not self.cel_les:
            return
        app = self.app
        sp = self.programa_inst if self.instancing else self.programa
        cam = app.camera
        sp['m_proj'].write(cam.m_proj)
        sp['m_view'].write(cam.m_view)
        sp['coef_log'].value = app.coef_log
        sp['dist_max'].value = DIST_MAX_KM
        sp['densitat_boira'].value = app.densitat_boira
        sp['boira_sol'].value, sp['boira_contra'].value = app.boira_sol, app.boira_contra
        sp['sol_horitzontal'].write(app.sol_horitzontal)
        sp['amunt_camera'].write(app.amunt_camera)
        # ombres del relleu i dels edificis: les reben si la vegetacio es dins dels mapes d'ombres (ombres.glsl ja
        # comprova si el punt hi es); la vegetacio no en fa (no es dins de la passada des del Sol)
        app.ombres.uniforms(sp, app.ombres.valid)
        self.soroll.use(UNITAT_SOROLL)
        sp['tex_soroll'].value = UNITAT_SOROLL
        sp['mida_soroll'].value = MIDA_SOROLL_M
        for v in self.cel_les.values():
            if v['vao'] is None:
                continue
            o = v['origen']
            lat, lon, _ = geodesia.geodesiques(o)
            est, nord, amunt = geodesia.base_local(float(lat), float(lon))
            s, l = app.sol_ecef - o, app.lluna_ecef - o
            sd = s / np.linalg.norm(s)
            elev = float(np.dot(amunt, sd))
            visible = 1.0 - area_tapada(angle_entre(s, l), math.asin(RADI_SOL_KM / np.linalg.norm(s)),
                                        math.asin(RADI_LLUNA_KM / np.linalg.norm(l)))
            sp['origen_rel'].write(glm.vec3(*(o - cam.posicio)))
            sp['est'].write(glm.vec3(*est))
            sp['nord'].write(glm.vec3(*nord))
            sp['amunt'].write(glm.vec3(*amunt))
            sp['meitat'].value = v['res'] / 2000.0
            sp['sol_dir'].write(glm.vec3(*sd))
            sp['llum_sol'].value = visible * min(max((elev + 0.0175) / 0.035, 0.0), 1.0)
            sp['llum_cel'].value = max(0.03, min(max((elev + 0.105) / 0.175, 0.0), 1.0) * (0.04 + 0.96 * visible ** 0.4))
            sp['color_sol'].value = tuple(float(c) for c in atmosfera.color_llum_sol(elev))
            sp['color_amb'].value = tuple(float(c) for c in atmosfera.color_llum_cel(elev))
            if self.instancing:      # (sense primera instancia a OpenGL 3.3: tots els punts de la cel·la)
                v['vao_i'].render(instances=v['n'])
                continue
            # nomes els trossos que tenen algun punt a menys de DIST_MAX_KM de la camera (la resta, el geometry
            # shader els descartaria un per un: ~5 milions de punts a les 4 cel·les de la UAB)
            cam_rel = cam.posicio - o
            for primer, quants, centre, radi in v['trossos']:
                if np.linalg.norm(centre - cam_rel) - radi < DIST_MAX_KM:
                    v['vao'].render(mgl.POINTS, vertices=quants, first=primer)

    def destroy(self):
        for k, f in self.feines.items():
            if hasattr(f, 'cancel'):
                f.cancel()
        for c in list(self.cel_les):
            self._treure(c)
        for o in (self.programa, self.programa_inst, self.cub, self.soroll):
            o.release()
