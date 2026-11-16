"""
Vegetacio mesurada dibuixada amb un geometry shader (tasca 45.3 del pla; acta 05, §2.1).

D'on surt: la superficie dels obstacles de cada cel·la de 3 x 3 km (dades/alcaries.preparar_superficie: terra +
alcaria del LiDAR, a 2 m amb l'ICGC o 2,5 m amb l'IGN) i les capes 'ulls' (el terra fora dels edificis) i 'edifici'
(contorns del Catastro). Cada cel·la amb un objecte de mes de MIN_M fora dels edificis es un punt: posicio del terra
i alcaria. El geometry shader (shaders/vegetacio.geom) en fa una columna de la mida de la cel·la.

Per que columnes i no arbres: l'estudi de dades (scripts/estudi_vegetacio.py, 45.1-45.2) troba capcades a la UAB,
pero el 78 % de la vegetacio forma masses continues, i substituir-la per un con per capcada canvia l'horitzo de la
posta una mediana d'1,8 graus (fins a 27): el que es veuria no seria el que calcula el mapa. Les columnes son
exactament la superficie del calcul (nivell N3 dels mapes): el Sol queda tapat a la imatge on el calcul diu que ho
esta (D94). Limitacions: el model d'alcaries es 2,5D (sense espai sota les capcades: un arbre es una massa fins a
terra) i l'ICGC no separa la vegetacio d'altres objectes (pals, tanques, cotxes); l'aspecte es de blocs.

Mode alternatiu (Avancat, didactic): instancing (shaders/vegetacio_inst.vert), amb les mateixes dades i el mateix
descart de cares. Es mes lent que el geometry shader amb aquestes dades (scripts/estudi_vegetacio_gpu.py: 15-17 ms
contra 6-7 ms de GPU per al milio de columnes de la UAB), i es pot comparar en directe.

Es dibuixen les cel·les a menys de RADI_KM del punt de detall que ja tenen la superficie preparada (no es baixa res
per la vegetacio), i nomes els punts a menys de DIST_MAX_KM de la camera (el shader no emet la resta).
"""
import math
import os

import glm
import moderngl as mgl
import numpy as np
from pyproj import Transformer

from .programes import carregar_programa
from dades import alcaries, atmosfera, geodesia
from dades.feines import Feina
from dades.model_eclipsi import area_tapada, angle_entre
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM

MIN_M = 1.5          # alcaria minima d'un objecte per dibuixar-lo (m)
RADI_KM = 2.0        # cel·les a aquesta distancia del punt de detall
DIST_MAX_KM = 1.5
MAX_CEL_LES = 4
_A_LATLON = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
_A_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True)


def punts_cel(clau_cel, avis=None):
    """Punts de vegetacio d'una cel·la (sense OpenGL): (origen ECEF, vertexs float32 (n, 5): terra (km, relatiu a
    l'origen), alcaria (km) i cares exposades (bits: est, oest, nord, sud), res (m)), o None."""
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
    veina = [np.pad(sup, 1, constant_values=-1e9)[1:-1, 2:], np.pad(sup, 1, constant_values=-1e9)[1:-1, :-2],
             np.pad(sup, 1, constant_values=-1e9)[:-2, 1:-1], np.pad(sup, 1, constant_values=-1e9)[2:, 1:-1]]
    mascara = sum((1 << i) * (veina[i] < sup - 0.3) for i in range(4))
    # a menys de 2 cel·les d'un contorn del Catastro, l'objecte mesurat sol ser part de l'edifici (rafecs, porxos o
    # el desplacament entre el contorn i el LiDAR), no un arbre: es pinta gris (bit 4). Compta igual com a obstacle
    from scipy.ndimage import binary_dilation
    prop = binary_dilation(capes['edifici'] > 0, iterations=2)
    mascara = mascara + 16 * prop
    files, cols = np.nonzero(ok)
    x, y = tr * (cols + 0.5, files + 0.5)
    lon, lat = _A_LATLON.transform(np.asarray(x), np.asarray(y))
    _, cx, cy = clau_cel.split('_')
    lo0, la0 = _A_LATLON.transform(float(cx), float(cy))
    origen = geodesia.ecef(la0, lo0, 0.0)
    base = geodesia.ecef(np.asarray(lat), np.asarray(lon), capes['ulls'][files, cols] / 1000.0) - origen
    v = np.column_stack([base, alt[files, cols] / 1000.0, mascara[files, cols]]).astype('f4')
    return origen, v, tr.a


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
        self.instancing = False           # mode alternatiu (Avancat): instancing en lloc del geometry shader
        self.programa_inst = self.ctx.program(
            vertex_shader=open(os.path.join(os.path.dirname(__file__), 'shaders', 'vegetacio_inst.vert')).read(),
            fragment_shader=open(os.path.join(os.path.dirname(__file__), 'shaders', 'vegetacio.frag')).read())
        self.cub = self.ctx.buffer(_cub().tobytes())
        self.cel_les = {}      # clau de la cel·la -> dict(vbo, vao, n, origen, res)
        self.feines = {}
        self.fallades = set()
        self.n_punts = 0

    def actualitzar(self):
        """Cel·les a prop del punt de detall amb la superficie feta: es preparen en un fil i es pugen aqui."""
        for c, f in list(self.feines.items()):
            if not f.fet:
                continue
            del self.feines[c]
            if f.resultat is None:
                self.fallades.add(c)
                continue
            origen, v, res = f.resultat
            vbo = self.ctx.buffer(v.tobytes()) if len(v) else None
            vao = self.ctx.vertex_array(self.programa, [(vbo, '3f 1f 1f', 'in_base', 'in_alt', 'in_cares')]) \
                if vbo else None
            vao_i = self.ctx.vertex_array(self.programa_inst, [(self.cub, '3f 1f', 'in_cub', 'in_cara'),
                                                               (vbo, '3f 1f 1f/i', 'in_base', 'in_alt', 'in_cares')]) \
                if vbo else None
            self.cel_les[c] = dict(vbo=vbo, vao=vao, vao_i=vao_i, n=len(v), origen=origen, res=res)
        if not self.actiu:
            return
        p = self.app.detall.punt
        if p is None:
            return
        x, y = _A_UTM.transform(p[1], p[0])
        cx, cy = alcaries.centre_cel(x, y)
        volgudes = []
        for dx in (-3000, 0, 3000):
            for dy in (-3000, 0, 3000):
                c = f'cel_{cx + dx:.0f}_{cy + dy:.0f}'
                d = max(abs(x - (cx + dx)) - 1500, abs(y - (cy + dy)) - 1500, 0)
                if d < RADI_KM * 1000 and os.path.exists(alcaries.cami_superficie(c, 'edifici')):
                    volgudes.append((d, c))
        volgudes = [c for _, c in sorted(volgudes)[:MAX_CEL_LES]]
        for c in volgudes:
            if c not in self.cel_les and c not in self.feines and c not in self.fallades and len(self.feines) < 1:
                self.feines[c] = Feina(c, lambda clau, avis: punts_cel(clau), c, descripcio='vegetacio')
        for c in [c for c in self.cel_les if c not in volgudes]:
            self._treure(c)
        self.n_punts = sum(v['n'] for v in self.cel_les.values())

    def _treure(self, c):
        v = self.cel_les.pop(c)
        for o in (v['vao'], v['vao_i'], v['vbo']):
            if o is not None:
                o.release()

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
            if self.instancing:
                v['vao_i'].render(instances=v['n'])
            else:
                v['vao'].render(mgl.POINTS)

    def destroy(self):
        for c in list(self.cel_les):
            self._treure(c)
        for o in (self.programa, self.programa_inst, self.cub):
            o.release()
