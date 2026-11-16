"""
Mapes de l'eclipsi sobre el terreny (objectius O3 i O4 del pla): quins hi ha, d'on surten les dades a cada escala,
com es preparen mentre s'explora i com els llegeix el shader del terreny (basecode/shaders/mapes.glsl).

Els quatre mapes (definicions a PLA_DE_TREBALL.md, O4.1; llegendes fixes, D96):
  ocultacio  part del Sol tapada per la Lluna. "Al maxim": de la graella de circumstancies (2 km, interpolada:
             varia molt a poc a poc). "Ara": la calcula el shader per a cada punt (tapat_des_de), com l'ombra de la
             Lluna. No te detall d'edificis i no depen de la camera: no cal preparar res en moure's.
  durada     temps observable (D91): fraccio de C1-C4 amb alguna part del Sol lliure d'obstacles; o la de la fase
             central. Resum de tot l'eclipsi: no canvia amb la barra del temps.
  relleu     el relleu (i els obstacles mesurats) deixen el Sol sencer, en part o gens a l'instant de la barra; o les
             classes al maxim (com la capa del CNIG).
  ombra      on es l'ombra de la Lluna ara (fase central) i les corbes de la penombra; i el recorregut de la fase
             central (limits i durada), de la graella de circumstancies.

Nivells de dades dels mapes durada i relleu (dades/visibilitat.py, el mateix calcul a totes les escales; nomes canvia
el model del terreny). El shader fa servir, a cada punt, el mes detallat que hi ha a la GPU:
  N0  la peninsula, MDT de 200 m (un sol fitxer; scripts/preparar_visibilitat.py).
  N2  cel·les de 3 x 3 km del relleu de 5 m (zones fetes a ma o llocs de la quadricula).
  N3  peces d'1 x 1 km de la superficie dels obstacles mesurats (terra + alcaria LiDAR: edificis i vegetacio, 2 m o
      2,5 m; dades/alcaries.py), amb l'horitzo cada 0,25 graus (D95: conserva les interrupcions curtes).
  (N1, blocs de 25 m, es la tasca 42.6 del pla.)
Quin nivell cal surt de la mida d'un pixel de la pantalla sobre el terra (petjada de la vista, amb la camera
inclinada o no): una graella de raigs des de la camera. Les peces es preparen en segon pla (llegir: un fil; calcular:
un proces, D89), de mes a menys necessaries; mentrestant es veu el nivell de sota. Les peces carregades es
conserven (fins a CAPACITAT per nivell) mentre la vista les vulgui; travessar la vora d'una cel·la no en treu cap.

La camera nomes decideix quines peces i de quin nivell calen. Cap resultat no depen de la camera: la clau d'una peca
es el nivell, el rectangle i l'eclipsi. El temps (la barra) nomes canvia el que el shader treu de les dades
(intervals a l'instant); avancar-lo no recalcula res.

Textures: per nivell, una textura array (GL_TEXTURE_2D_ARRAY, OpenGL 3.0, dins del 3.3 core) amb una capa per peca i
dada, RGBA de 16 bits sense filtre (NEAREST: son classes i temps, no es poden barrejar):
  capa 0     obs, obs_central, marge + 32768, n_iv[0] + 16 n_iv[1]
  capa 1..K  interval i: (inici, final) amb alguna part del Sol lliure i (inici, final) amb el Sol sencer (s des de
             l'inici de les efemerides). Nomes amb el mapa "relleu ara". K_GPU intervals per nivell; si n'hi ha mes,
             els ultims s'ajunten a l'ultim (el temps observable de la capa 0 es exacte).
"""
import math
import os
import time

import glm
import moderngl as mgl
import numpy as np
from pyproj import Transformer

from dades import alcaries, eclipsis, geodesia, llocs, visibilitat
from dades.data_io import ZONES_DETALL
from dades.feines import Feina, FeinaProces

_A_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True)
_A_LATLON = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
_LIMITS = {}        # cami d'un MDT -> limits (no es torna a obrir el fitxer a cada revisio)
# unitats de textura (n'hi ha 16, de la 0 a la 15: terrain.frag fa servir de la 0 a la 9 i la 12 es el mapa d'ombres fi,
# basecode/ombres_relleu.py): les textures array dels nivells N0-N3 i la graella de circumstancies
UNITATS = (10, 11, 13, 14)
UNITAT_GRAELLA = 15
NIVELLS = (0, 1, 2, 3)
NOM_NIVELL = {0: 'relleu 200 m', 1: 'relleu 25 m', 2: 'relleu 5 m', 3: 'obstacles mesurats'}
CAPACITAT = {0: 1, 1: 4, 2: 9, 3: 16}     # peces a la GPU per nivell
MIDA_PX = {1: (960, 960), 2: (600, 600), 3: (512, 512)}   # mida de la capa (N0: la del MDT de la peninsula)
K_GPU = {0: 1, 1: 2, 2: 2, 3: 2}          # intervals a la GPU (relleu ara); la mesura de la F42 ho justifica
PAS_N2_M, PAS_N3_M = 3000.0, 1000.0
PAS_AZIMUT_N3 = 0.25                       # D95 (scripts/validar_temps_visibilitat.py)
# mida maxima del pixel de la pantalla sobre el terra (m) per a cada nivell: per sota d'aixo, cal el nivell
PIXEL_MAX_M = {3: 4.0, 2: 30.0}
MAX_DESITJADES = {2: 6, 3: 6}
REVISIO_S = 0.25
MAX_LECTURES = 2

# ------------------------------------------------------------ llegendes (D96): els llindars i els colors son fixos
# (no depenen de l'escala ni de l'eclipsi); el shader i el panell els llegeixen d'aqui.
MAPES = [('cap', 'Cap'), ('ocultacio', 'Ocultacio (Lluna)'), ('durada', 'Temps observable'),
         ('relleu', 'Sol tapat pel relleu'), ('ombra', 'Ombra de la Lluna')]
MODES = {'ocultacio': [('maxim', 'Al maxim'), ('ara', 'Ara')],
         'durada': [('tot', 'Tot l\'eclipsi'), ('central', 'Fase central')],
         'relleu': [('ara', 'Ara'), ('maxim', 'Al maxim')],
         'ombra': [('ara', 'Ara i recorregut')]}
# ocultacio: classes < 10 %, 10-20 ... 80-90 %, 90-95, 95-99, 99-<100 %; la fase central, a part
OCULT_LLINDARS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99]
OCULT_COLORS = [(1.00, 0.97, 0.72), (1.00, 0.90, 0.42), (1.00, 0.79, 0.27), (0.99, 0.66, 0.21), (0.97, 0.53, 0.20),
                (0.93, 0.41, 0.25), (0.88, 0.31, 0.35), (0.82, 0.23, 0.45), (0.74, 0.16, 0.55), (0.62, 0.11, 0.62),
                (0.48, 0.07, 0.62), (0.33, 0.04, 0.54)]
COLOR_TOTALITAT = (0.10, 0.00, 0.20)
COLOR_ANULARITAT = (0.10, 0.80, 0.80)
OCULT_TEXTOS = ['< 10 %'] + [f'{a * 100:.0f} - {b * 100:.0f} %' for a, b in zip(OCULT_LLINDARS[:-1], OCULT_LLINDARS[1:])] \
    + ['99 - <100 %']
# temps observable: paleta seqüencial ordenada (de blau fosc a groc, sense morat: el morat es de l'ocultacio)
DURADA_LLINDARS = [0.20, 0.40, 0.60, 0.70, 0.80, 0.90, 0.95]
DURADA_COLORS = [(0.00, 0.13, 0.30), (0.07, 0.22, 0.43), (0.24, 0.30, 0.43), (0.37, 0.38, 0.44), (0.49, 0.48, 0.47),
                 (0.61, 0.58, 0.46), (0.75, 0.69, 0.41), (0.88, 0.80, 0.33), (1.00, 0.92, 0.27)]
DURADA_TEXTOS = ['0 % (gens)', '< 20 %', '20 - 40 %', '40 - 60 %', '60 - 70 %', '70 - 80 %', '80 - 90 %', '90 - 95 %',
                 '>= 95 %']
CENTRAL_LLINDARS = [0.25, 0.50, 0.75]          # + 0 i 100 % com a classes propies
CENTRAL_COLORS = [DURADA_COLORS[0], DURADA_COLORS[2], DURADA_COLORS[4], DURADA_COLORS[6], DURADA_COLORS[7],
                  DURADA_COLORS[8]]
CENTRAL_TEXTOS = ['0 % (gens)', '< 25 %', '25 - 50 %', '50 - 75 %', '75 - <100 %', '100 % (tota)']
COLOR_FORA_CENTRAL = (0.60, 0.60, 0.60)
# relleu: sense morat; de clar (Sol lliure) a fosc (tapat)
RELLEU_COLORS = [(0.20, 0.22, 0.28), (0.76, 0.30, 0.12), (0.95, 0.62, 0.20), (0.98, 0.94, 0.62)]
RELLEU_TEXTOS_MAXIM = ['Tapat', 'Menys de mig Sol', 'Mes de mig Sol', 'Sencer']
RELLEU_TEXTOS_ARA = ['Tapat pel relleu o obstacles', 'En part', None, 'Sencer']
COLOR_POSTA = (0.48, 0.50, 0.56)
COLOR_LIMITS_CENTRAL = (0.55, 0.95, 1.00)
COLOR_SENSE_ECLIPSI = (0.70, 0.70, 0.70)


def _limits(cami):
    if cami not in _LIMITS:
        import rasterio
        with rasterio.open(cami) as f:
            _LIMITS[cami] = f.bounds
    return _LIMITS[cami]


def _dins_peninsula(app, x, y):
    lon, lat = _A_LATLON.transform(x, y)
    return app.peninsula.conte(lat, lon) and app.peninsula.es_terra(lat, lon)


class Peca:
    """Una peca de mapa d'un nivell: dades a la CPU (per tornar-les a pujar i per a la consulta) i on es a la GPU."""

    def __init__(self, nivell, clau, rect, res, descripcio, dades, transform):
        self.nivell, self.clau, self.rect, self.res = nivell, clau, rect, res
        self.descripcio, self.dades, self.transform = descripcio, dades, transform
        self.forma = dades['capa0'].shape[:2]         # (files, columnes)
        self.slot, self.us = None, time.time()


def empaquetar(r, k):
    """Del resultat de dades/visibilitat (dict) a les capes de la GPU (uint16): capa0 (files, cols, 4) i k capes
    d'intervals. Es fa al fil de lectura (no al de dibuix)."""
    n = r['n_iv'].astype('u2')
    capa0 = np.stack([r['obs'], r['obs_central'], (r['marge'].astype('i4') + 32768).astype('u2'),
                      np.minimum(n[0], 15) + 16 * np.minimum(n[1], 15)], -1)
    iv = r['iv']
    capes = []
    for i in range(k):
        ini_a, fi_a, ini_s, fi_s = iv[0, i, 0], iv[0, i, 1], iv[1, i, 0], iv[1, i, 1]
        if i == k - 1 and iv.shape[1] > k:
            # els intervals de mes s'ajunten a l'ultim: el final es el de l'ultim que hi ha
            fi_a = _ultim_final(iv[0, i:, 1])
            fi_s = _ultim_final(iv[1, i:, 1])
        capes.append(np.stack([ini_a, fi_a, ini_s, fi_s], -1))
    return dict(capa0=np.ascontiguousarray(capa0), intervals=[np.ascontiguousarray(c) for c in capes])


def _ultim_final(fins):
    v = np.where(fins == visibilitat.SENSE, 0, fins).max(0)
    return np.where((fins != visibilitat.SENSE).any(0), v, visibilitat.SENSE).astype('u2')


def _llegir_peca(nivell, clau_peca, cami, eclipsi, rect, pas, k, avis):
    """Feina (fil): llegeix una peca ja calculada i l'empaqueta. None si no hi es."""
    avis('Llegint el mapa...')
    r = visibilitat.llegir(cami, eclipsi, rect, pas)
    if r is None:
        return None
    d = empaquetar(r, k)
    if nivell == 3:
        _marcar_edificis(d['capa0'], cami, r)
    # nomes les capes empaquetades (la consulta d'un punt les descodifica)
    return dict(dades=d, transform=tuple(float(v) for v in r['transform']), res=float(r['res']),
                radi_sol=float(r['radi_sol']), inici=float(r['inici']))


BIT_EDIFICI = 256       # a la capa 0 (canal A): el pixel es dins d'un contorn del Catastro (ulls al terrat)


def _marcar_edificis(capa0, cami_sup, r):
    """Marca a la capa 0 els pixels dins dels edificis (raster 'edifici' de la cel·la, dades/alcaries.py)."""
    import rasterio
    from rasterio.windows import from_bounds
    cami = cami_sup.replace('_superficie_', '_edifici_')
    if not os.path.exists(cami):
        return
    tr = rasterio.Affine(*r['transform'])
    files, cols = capa0.shape[:2]
    x0, y1 = tr.c, tr.f
    x1, y0 = x0 + tr.a * cols, y1 + tr.e * files
    with rasterio.open(cami) as f:
        e = f.read(1, window=from_bounds(x0, y0, x1, y1, f.transform), boundless=True, fill_value=0)
    if e.shape == (files, cols):
        capa0[..., 3] |= np.where(e > 0, BIT_EDIFICI, 0).astype('u2')


def _calcular_peca(cami, eclipsi, lluny, cami_ulls, rect, pas, avis):
    """FeinaProces: calcula una peca i la desa (el fil principal la llegira despres)."""
    eclipsis.triar(eclipsi)
    visibilitat.calcular(cami, eclipsi, lluny=lluny, cami_ulls=cami_ulls, rect=rect, pas_azimut=pas, avis=avis)
    return True


def _preparar_superficie(cel, cami_mdt, parts_zona, avis):
    from .detall import _preparar_superficie as preparar
    return preparar(cel, cami_mdt, parts_zona, avis)


def _preparar_relleu(c, avis):
    llocs.preparar_relleu(c, avis)
    return c


class Mapes:
    def __init__(self, app):
        self.app, self.ctx = app, app.ctx
        self.quin, self.mode = None, {m: modes[0][0] for m, modes in MODES.items()}
        self.terrats = True       # el mapa tambe a les cobertes dels edificis (valor amb els ulls al terrat)
        self.peces = {}           # (nivell, clau, eclipsi) -> Peca carregada a la GPU
        self.feines = {}          # (tipus, clau) -> Feina
        self.fallades = {}        # (tipus, clau) -> error
        self.desitjades = []      # [(nivell, clau, rect)] que la vista vol, de mes a menys necessaria
        self.ultima = -1e9
        self.textures = {}        # nivell -> (textura array, capes per peca)
        self.amb_intervals = False   # capes dels intervals a la GPU (nomes per al mapa del relleu ara)
        buida = np.zeros((1, 1, 4), 'u2')
        self.buida = self.ctx.texture_array((1, 1, 1), 4, buida.tobytes(), dtype='nu2')
        # (un sampler2D no pot llegir d'una textura array: si no, el dibuix dona GL_INVALID_OPERATION)
        self.buida_2d = self.ctx.texture((1, 1), 4, np.full(4, -1.0, 'f4').tobytes(), dtype='f4')
        self.graella, self.tex_graella, self.feina_graella = None, None, None
        self.nivell_centre = None   # nivell de dades al centre de la pantalla (panell)
        self.pixel_centre_m = None
        self.radi_sol, self.inici = 0.0, 0.0

    # ------------------------------------------------------------ que es mostra

    def mostrar(self, quin, mode=None):
        """quin: None o 'cap' (cap mapa), 'ocultacio', 'durada', 'relleu', 'ombra'."""
        self.quin = None if quin in (None, 'cap') else quin
        if mode is not None and self.quin:
            self.mode[self.quin] = mode
        self._capes_segons_mode()

    def posar_mode(self, mode):
        if self.quin:
            self.mode[self.quin] = mode
            self._capes_segons_mode()

    def mode_actual(self):
        return self.mode.get(self.quin) if self.quin else None

    def amb_nivells(self):
        """Si el mapa actiu fa servir les dades per nivells (durada i relleu)."""
        return self.quin in ('durada', 'relleu')

    def _capes_segons_mode(self):
        """Capes per peca a la GPU: 1 (resum) o 1 + K_GPU (amb els intervals, per al mapa del relleu ara)."""
        cal = self.quin == 'relleu' and self.mode['relleu'] == 'ara'
        if cal != self.amb_intervals:
            self.amb_intervals = cal
            for nivell in list(self.textures):
                self.textures.pop(nivell)[0].release()
            for p in self.peces.values():
                p.slot = None
                self._pujar(p)

    def ocupat(self):
        return bool(self.feines) or self.feina_graella is not None

    # ------------------------------------------------------------ cada fotograma

    def actualitzar(self):
        app = self.app
        clau_ecl = eclipsis.actiu()
        # els calculs d'un altre eclipsi (s'ha canviat) o amb el mapa tret ja no calen: s'aturen (cada un ocupa tots
        # els nuclis; el de la peninsula, desenes de minuts)
        for (t, k), f in self.feines.items():
            if t == 'calcular' and (k[2] != clau_ecl or not self.amb_nivells()) and hasattr(f, 'cancel'):
                f.cancel()
        self._recollir(clau_ecl)
        if self.quin is None:
            return
        if self.quin in ('ocultacio', 'ombra'):
            self._graella(clau_ecl)
            return
        ara = time.time()
        if ara - self.ultima < REVISIO_S:
            return
        self.ultima = ara
        self.desitjades = self._desitjades()
        vistes = set()
        for nivell, clau, rect in self.desitjades:
            vistes.add((nivell, clau, clau_ecl))
            self._preparar(nivell, clau, rect, clau_ecl)
        for k, p in self.peces.items():
            if k in vistes:
                p.us = ara
        # les peces d'un altre eclipsi ja no serveixen
        for k in [k for k in self.peces if k[2] != clau_ecl]:
            self._treure(k)

    # ------------------------------------------------------------ petjada de la vista

    def _raigs(self, n_x=9, n_y=7):
        """Punts del terra (ECEF) que es veuen en una graella de la pantalla, amb la mida del pixel sobre el terra (m)
        i la distancia a la camera (km). El terra es l'el·lipsoide aixecat a l'altura del terreny sota la camera."""
        cam = self.app.camera
        o = np.asarray(cam.posicio, float)
        lat, lon, _ = geodesia.geodesiques(o)
        h = self.app.altitud_terra_km(float(lat), float(lon))
        inv = glm.inverse(cam.m_proj * cam.m_view)
        a_, b_ = geodesia.A_KM + h, geodesia.B_KM + h
        k = np.array([1.0, 1.0, a_ / b_])
        alt_px = self.app.WIN_SIZE[1]
        fov = math.radians(getattr(cam, 'fov', 50.0))
        px_rad = 2 * math.tan(fov / 2) / max(alt_px, 1)
        out = []
        for y in np.linspace(-0.95, 0.95, n_y):
            for x in np.linspace(-0.95, 0.95, n_x):
                q = inv * glm.vec4(x, y, 1.0, 1.0)
                d = np.array([q.x, q.y, q.z]) / (q.w if abs(q.w) > 1e-12 else 1.0)
                d /= np.linalg.norm(d)
                oo, dd = o * k, d * k
                aa, bb, cc = dd @ dd, 2 * (oo @ dd), oo @ oo - a_ ** 2
                disc = bb * bb - 4 * aa * cc
                if disc <= 0:
                    continue
                t = (-bb - math.sqrt(disc)) / (2 * aa)
                if t <= 0:
                    continue
                p = o + t * d
                amunt = p / np.linalg.norm(p)
                rasant = max(abs(float(d @ amunt)), 0.1)
                out.append((p, t * px_rad / rasant * 1000.0, t))
        return out

    def _desitjades(self):
        """Peces de N2 i N3 que la vista necessita, de la mes necessaria (pixel mes petit) a la que menys."""
        app = self.app
        punts = self._raigs()
        if not punts:
            self.nivell_centre, self.pixel_centre_m = None, None
            return [(0, 'peninsula', None)]
        ps = np.array([p for p, _, _ in punts])
        mides = np.array([m for _, m, _ in punts])
        lat, lon, _ = geodesia.geodesiques(ps)
        xs, ys = _A_UTM.transform(np.asarray(lon), np.asarray(lat))
        centre = len(punts) // 2
        self.pixel_centre_m = float(mides[centre])
        volgudes = {2: {}, 3: {}}
        for x, y, m in zip(xs, ys, mides):
            for nivell in (3, 2):
                # on cal el detall dels obstacles, tambe el relleu de 5 m: es el que es veu mentre es calcula
                if m < PIXEL_MAX_M[nivell]:
                    pas = PAS_N3_M if nivell == 3 else PAS_N2_M
                    off = 500.0 if nivell == 3 else 0.0       # les peces d'1 km dins de les cel·les de 3 km
                    if nivell == 3:
                        x0 = math.floor((x - off) / pas) * pas + off
                        y0 = math.floor((y - off) / pas) * pas + off
                    else:
                        cx, cy = alcaries.centre_cel(x, y)
                        x0, y0 = cx - pas / 2, cy - pas / 2
                    clau = f'n{nivell}_{x0:.0f}_{y0:.0f}'
                    if clau not in volgudes[nivell] or volgudes[nivell][clau][0] > m:
                        volgudes[nivell][clau] = (m, (x0, y0, x0 + pas, y0 + pas))
        # ordre de preparacio: la peninsula (es veu sempre), despres les cel·les de 5 m (rapides: ~15 s) i despres les
        # peces dels obstacles (~1 min cadascuna); dins de cada nivell, la que es veu mes gran primer
        out = [(0, 'peninsula', None)]
        for nivell in (2, 3):
            v = sorted(volgudes[nivell].items(), key=lambda kv: kv[1][0])[:MAX_DESITJADES[nivell]]
            out += [(nivell, clau, rect) for clau, (m, rect) in v if _dins_peninsula(app, (rect[0] + rect[2]) / 2,
                                                                                         (rect[1] + rect[3]) / 2)]
        return out

    # ------------------------------------------------------------ preparar peces

    def _mdt_5m(self, rect):
        """Un MDT de 5 m que cobreix el rectangle: una zona feta a ma o el lloc de la quadricula; o None."""
        x0, y0, x1, y1 = rect
        for _, cami, _ in ZONES_DETALL:
            if not os.path.exists(cami):
                continue
            b = _limits(cami)
            if b.left <= x0 - 1000 and b.right >= x1 + 1000 and b.bottom <= y0 - 1000 and b.top >= y1 + 1000:
                return cami
        c = llocs.clau_per_punt((x0 + x1) / 2, (y0 + y1) / 2)
        return llocs.cami_mdt(c) if llocs.te_relleu(c) else None

    def _preparar(self, nivell, clau, rect, eclipsi):
        k = (nivell, clau, eclipsi)
        if k in self.peces or ('llegir', k) in self.feines or ('calcular', k) in self.feines:
            return
        if any(f == ('calcular', k) for f in self.fallades) or any(f == ('llegir', k) for f in self.fallades):
            return
        app = self.app
        pen = app.peninsula.cami
        if nivell == 0:
            cami, lluny, ulls, r, pas = pen, None, None, None, visibilitat.PAS_AZIMUT
        elif nivell == 2:
            cami = self._mdt_5m(rect)
            if cami is None:
                self._preparar_relleu(rect)
                return
            lluny, ulls, r, pas = [pen], None, rect, visibilitat.PAS_AZIMUT
        else:
            cx, cy = alcaries.centre_cel((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
            cel = f'cel_{cx:.0f}_{cy:.0f}'
            sup = alcaries.cami_superficie(cel, 'superficie')
            mdt = self._mdt_5m((cx - 1500, cy - 1500, cx + 1500, cy + 1500))
            if mdt is None:
                self._preparar_relleu(rect)
                return
            if not os.path.exists(sup) or not os.path.exists(alcaries.cami_superficie(cel, 'edifici')):
                self._preparar_sup((cx, cy), cel, mdt)
                return
            cami, lluny, ulls, r, pas = sup, [mdt, pen], alcaries.cami_superficie(cel, 'ulls'), rect, PAS_AZIMUT_N3
        if visibilitat.vigent(cami, eclipsi, r, pas):
            if sum(1 for t, _ in self.feines if t == 'llegir') < MAX_LECTURES:
                # en un fil: visibilitat.llegir_npz descomprimeix d'un sol cop (sense, la peninsula tardava 108 s)
                self.feines[('llegir', k)] = Feina(k, _llegir_peca, nivell, clau, cami, eclipsi, r, pas, K_GPU[nivell],
                                                   descripcio=f'llegir el mapa {clau}')
            return
        # calcular: d'un en un (cada calcul fa servir tots els nuclis), i el de la peninsula nomes si no n'hi ha cap
        # altre (es llarg); el detall del que es mira, primer
        if any(t == 'calcular' for t, _ in self.feines) or app.detall.detall_en_curs():
            return
        if visibilitat.en_calcul(cami, eclipsi, r, pas):
            return      # un altre proces l'esta calculant (p. ex. scripts/preparar_visibilitat.py)
        self.feines[('calcular', k)] = FeinaProces(k, _calcular_peca, cami, eclipsi, lluny, ulls, r, pas,
                                                   descripcio=f'calcular el mapa {clau}')

    def _preparar_relleu(self, rect):
        """El relleu de 5 m del lloc de la quadricula (la mateixa feina que basecode/detall.py), un de cada vegada."""
        app = self.app
        c = llocs.clau_per_punt((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
        if 'relleu' in app.detall.feines or ('relleu', c) in app.detall.fallades or ('relleu', c) in self.fallades \
                or any(t == 'relleu' for t, _ in self.feines) or not app.detall.preparar:
            return
        self.feines[('relleu', c)] = FeinaProces(c, _preparar_relleu, c, descripcio='relleu de 5 m del mapa')

    def _preparar_sup(self, cel, clau_cel, mdt):
        app = self.app
        if ('superficie', clau_cel) in self.fallades or any(t == 'superficie' for t, _ in self.feines) \
                or 'superficie' in app.detall.feines or not app.detall.preparar:
            return
        cx, cy = cel
        parts_zona = next((z['clau'] for z in app.detall.zones() if app.detall.te_edificis(z['clau'], cx, cy)), None)
        self.feines[('superficie', clau_cel)] = FeinaProces(clau_cel, _preparar_superficie, cel, mdt, parts_zona,
                                                            descripcio='superficie dels obstacles')

    def _recollir(self, eclipsi):
        if self.feina_graella is not None and self.feina_graella.fet:
            f, self.feina_graella = self.feina_graella, None
            if f.resultat is not None and f.clau == eclipsi:
                self._posar_graella(f.resultat)
            elif f.error:
                self.fallades[('graella', f.clau)] = f.error
        for kf in list(self.feines):
            f = self.feines.get(kf)
            if f is None or not f.fet:
                continue
            del self.feines[kf]
            tipus, k = kf
            if f.error:
                if not getattr(f, 'cancelada', False):
                    self.fallades[kf] = f.error
                continue
            if tipus == 'llegir':
                if f.resultat is None or k[2] != eclipsi:
                    continue              # un altre eclipsi (o ja no hi es): no s'aplica
                self._afegir(k, f.resultat)
            # 'calcular', 'relleu', 'superficie': el resultat queda al disc; la propera revisio el llegira

    def _afegir(self, k, r):
        nivell, clau, eclipsi = k
        self.radi_sol, self.inici = r['radi_sol'], r['inici']
        desc = NOM_NIVELL[nivell] + (f' ({r["res"]:g} m)' if nivell else '')
        tr = r['transform']
        files, cols = r['dades']['capa0'].shape[:2]
        rect = (tr[2], tr[5] + tr[4] * files, tr[2] + tr[0] * cols, tr[5])
        p = Peca(nivell, clau, rect, r['res'], desc, r['dades'], tr)
        # si el nivell es ple, surt la que fa mes temps que no es vol
        mateix = [kk for kk in self.peces if kk[0] == nivell]
        if len(mateix) >= CAPACITAT[nivell]:
            self._treure(min(mateix, key=lambda kk: self.peces[kk].us))
        self.peces[k] = p
        self._pujar(p)

    def _treure(self, k):
        p = self.peces.pop(k, None)
        if p is not None:
            p.slot = None

    def _textura(self, nivell, w, h):
        capes = 1 + (K_GPU[nivell] if self.amb_intervals else 0)
        t = self.textures.get(nivell)
        if t is None:
            n = CAPACITAT[nivell] * capes
            tex = self.ctx.texture_array((w, h, n), 4, None, dtype='nu2')
            tex.filter = (mgl.NEAREST, mgl.NEAREST)
            tex.repeat_x = tex.repeat_y = False
            t = self.textures[nivell] = (tex, capes, (w, h))
        return t

    def _pujar(self, p):
        """Puja la peca a un lloc lliure de la textura del seu nivell."""
        files, cols = p.forma
        w, h = (cols, files) if p.nivell == 0 else MIDA_PX[p.nivell]
        if cols > w or files > h:
            print(f'AVIS: la peca {p.clau} ({cols} x {files}) no cap a la textura ({w} x {h})')
            return
        tex, capes, _ = self._textura(p.nivell, w, h)
        ocupats = {q.slot for q in self.peces.values() if q.nivell == p.nivell and q.slot is not None and q is not p}
        p.slot = next(s for s in range(CAPACITAT[p.nivell]) if s not in ocupats)
        dades = [p.dades['capa0']] + p.dades['intervals'][:capes - 1]
        for i, d in enumerate(dades):
            tex.write(d.tobytes(), viewport=(0, 0, p.slot * capes + i, cols, files, 1))

    # ------------------------------------------------------------ mapes de la Lluna (graella de circumstancies)

    def _graella(self, eclipsi):
        if self.graella is not None and str(self.graella['clau']) == eclipsi:
            return
        if self.feina_graella is not None or ('graella', eclipsi) in self.fallades:
            return
        cami = self.app.peninsula.cami
        self.feina_graella = Feina(eclipsi, lambda avis: visibilitat.graella_circumstancies(eclipsi, cami, avis),
                                   descripcio='circumstancies de l\'eclipsi')

    def _posar_graella(self, g):
        if self.tex_graella is not None:
            self.tex_graella.release()
        dades = np.stack([np.nan_to_num(g['tapat_max'], nan=-1.0), np.nan_to_num(g['central'], nan=-1.0),
                          np.zeros_like(g['central']), np.zeros_like(g['central'])], -1).astype('f4')
        self.tex_graella = self.ctx.texture((dades.shape[1], dades.shape[0]), 4, dades.tobytes(), dtype='f4')
        self.tex_graella.filter = (mgl.LINEAR, mgl.LINEAR)
        self.tex_graella.repeat_x = self.tex_graella.repeat_y = False
        self.graella = g

    # ------------------------------------------------------------ shader

    def aplicar(self, sp, terreny):
        """Uniforms del mapa per dibuixar un terreny: on es cada peca en les UV del terreny (calculades aqui, en doble
        precisio)."""
        self._aplicar(sp, terreny.uv_de_utm, NIVELLS, False)

    def aplicar_edificis(self, sp, edificis):
        """Uniforms del mapa per dibuixar les cobertes dels edificis (terrats): nomes les peces dels obstacles (N3),
        amb les coordenades del mapa en metres relatius a l'origen dels edificis (x a l'est, y al sud, com les files),
        i la correspondencia lineal de posicio (ECEF relativa a l'origen) a aquestes coordenades. En 3 km, el terme
        que la linealitzacio deixa (la curvatura de la Terra i de la projeccio) es de l'ordre de centimetres en
        horitzontal: molt menys que els pixels de 2 m."""
        if 'mapa' not in sp:
            return
        if getattr(edificis, '_a_utm', None) is None:
            o = np.asarray(edificis.origen_ecef, float)

            def utm(p):
                la, lo, _ = geodesia.geodesiques(p)
                return np.array(_A_UTM.transform(float(lo), float(la)))
            u0 = utm(o)
            h = 0.01                      # km
            jac = np.stack([(utm(o + h * e) - utm(o - h * e)) / (2 * h) for e in np.eye(3)], 1)   # m per km
            a = np.zeros((3, 3))
            a[0], a[1] = jac[0], -jac[1]
            edificis._a_utm, edificis._origen_utm = a, u0
        a, (ox, oy) = edificis._a_utm, edificis._origen_utm
        sp['a_utm'].write(np.ascontiguousarray(a.T, 'f4').tobytes())     # mat3 de GLSL: per columnes
        sp['cam_menys_origen'].write(glm.vec3(*(self.app.camera.posicio - edificis.origen_ecef)))
        sp['sol_rel'].write(glm.vec3(*(self.app.sol_ecef - self.app.camera.posicio)))
        s, l = self.app.sol_ecef - edificis.origen_ecef, self.app.lluna_ecef - edificis.origen_ecef
        from dades.model_eclipsi import area_tapada, angle_entre
        from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM
        rs, rl, d = math.asin(RADI_SOL_KM / np.linalg.norm(s)), math.asin(RADI_LLUNA_KM / np.linalg.norm(l)), \
            angle_entre(s, l)
        sp['tapat_aqui'].value = float(area_tapada(d, rs, rl))
        sp['central_aqui'].value = bool(d < abs(rl - rs))
        mostrar = self.terrats and self.quin in ('durada', 'relleu')
        self._aplicar(sp, lambda x, y: (x - ox, oy - y), (3,) if mostrar else (), True)
        if not mostrar:
            sp['mapa'].value = 0

    def _aplicar(self, sp, coords, nivells, cobertes):
        if 'mapa' not in sp:
            return
        codi = {None: 0, 'ocultacio': 1, 'durada': 2, 'relleu': 3, 'ombra': 4}[self.quin]
        sp['mapa'].value = codi
        sp['mapa_cobertes'].value = cobertes
        # cada sampler ha de tenir sempre una textura del seu tipus a la seva unitat (si dos samplers de tipus
        # diferents comparteixen unitat, el dibuix dona GL_INVALID_OPERATION), encara que no hi hagi mapa
        for nivell in NIVELLS:
            t = self.textures.get(nivell)
            (t[0] if t is not None else self.buida).use(UNITATS[nivell])
            sp[f'mapa_n{nivell}'].value = UNITATS[nivell]
        (self.tex_graella or self.buida_2d).use(UNITAT_GRAELLA)
        sp['tex_graella'].value = UNITAT_GRAELLA
        if codi == 0:
            return
        mode = self.mode[self.quin]
        sp['mapa_mode'].value = 1 if mode in ('ara', 'central') else 0
        app = self.app
        ecl = eclipsis.ECLIPSIS[eclipsis.actiu()]
        sp['mapa_anular'].value = ecl['tipus'] == 'anular'
        sp['hora_s'].value = (app.hora - self.inici) * 3600.0 if self.inici else 0.0
        sp['radi_sol_graus'].value = self.radi_sol or 0.266
        # graella de circumstancies
        if self.tex_graella is not None:
            tr = self.graella['transform']
            files, cols = self.graella['tapat_max'].shape
            u0, v0 = coords(tr[2], tr[5])
            u1, v1 = coords(tr[2] + tr[0] * cols, tr[5] + tr[4] * files)
            sp['rect_graella'].value = (u0, v0, u1, v1)
        else:
            sp['rect_graella'].value = (0.0, 0.0, 0.0, 0.0)
        sp['hi_ha_graella'].value = self.tex_graella is not None
        # peces
        rects, escales, capes0, n_per_nivell = [], [], [], []
        for nivell in NIVELLS:
            ps = [p for p in self.peces.values() if p.nivell == nivell and p.slot is not None and nivell in nivells]
            ps.sort(key=lambda p: p.slot)
            t = self.textures.get(nivell)
            for p in ps:
                x0, y0, x1, y1 = p.rect
                u0, v0 = coords(x0, y1)
                u1, v1 = coords(x1, y0)
                rects.append((u0, v0, u1, v1))
                w, h = t[2]
                escales.append((p.forma[1] / w, p.forma[0] / h))
                capes0.append(p.slot * t[1])
            n_per_nivell.append(len(ps))
        maxim = sum(CAPACITAT.values())
        rects += [(0.0, 0.0, 0.0, 0.0)] * (maxim - len(rects))
        escales += [(0.0, 0.0)] * (maxim - len(escales))
        capes0 += [0] * (maxim - len(capes0))
        sp['mapa_rect'].write(np.array(rects, 'f4').tobytes())
        sp['mapa_escala'].write(np.array(escales, 'f4').tobytes())
        sp['mapa_capa'].write(np.array(capes0, 'i4').tobytes())
        sp['mapa_n'].write(np.array(n_per_nivell, 'i4').tobytes())
        sp['mapa_k'].write(np.array([K_GPU[n] if self.amb_intervals else 0 for n in NIVELLS], 'i4').tobytes())

    def uniforms_fixos(self, sp):
        """Colors i llindars (una vegada per programa)."""
        if 'mapa' not in sp:
            return
        sp['ocult_llindars'].write(np.array(OCULT_LLINDARS, 'f4').tobytes())
        sp['ocult_colors'].write(np.array(OCULT_COLORS, 'f4').tobytes())
        sp['mapa_color_total'].value = COLOR_TOTALITAT
        sp['mapa_color_anular'].value = COLOR_ANULARITAT
        sp['durada_llindars'].write(np.array(DURADA_LLINDARS, 'f4').tobytes())
        sp['durada_colors'].write(np.array(DURADA_COLORS, 'f4').tobytes())
        sp['central_llindars'].write(np.array(CENTRAL_LLINDARS, 'f4').tobytes())
        sp['central_colors'].write(np.array(CENTRAL_COLORS, 'f4').tobytes())
        sp['color_fora_central'].value = COLOR_FORA_CENTRAL
        sp['relleu_colors'].write(np.array(RELLEU_COLORS, 'f4').tobytes())
        sp['color_posta'].value = COLOR_POSTA
        sp['color_limits_central'].value = COLOR_LIMITS_CENTRAL
        sp['color_sense_eclipsi'].value = COLOR_SENSE_ECLIPSI
        sp['frac_escala'].value = float(visibilitat.FRAC)

    # ------------------------------------------------------------ consulta i panell

    def nivell_a(self, lat, lon):
        """La peca mes detallada carregada que conte el punt (i hi te dades), o None."""
        x, y = _A_UTM.transform(lon, lat)
        for nivell in (3, 2, 1, 0):
            for p in self.peces.values():
                if p.nivell != nivell:
                    continue
                x0, y0, x1, y1 = p.rect
                if x0 <= x < x1 and y0 <= y < y1:
                    c, f = int((x - x0) / p.res), int((y1 - y) / p.res)
                    if 0 <= f < p.forma[0] and 0 <= c < p.forma[1] and \
                            p.dades['capa0'][f, c, 0] != visibilitat.SENSE:
                        return p, f, c
        return None

    def consulta(self, lat, lon, model):
        """El que diu el mapa de temps observable en un punt (tasca 43.5), amb tot el necessari per entendre'l:
        dict, o None si no hi ha cap peca amb dades. model: ModelEclipsi del punt (contactes locals)."""
        r = self.nivell_a(lat, lon)
        if r is None or model is None or not model.valid:
            return None
        p, f, c = r
        v = p.dades['capa0'][f, c].astype(int)
        frac = v[0] / visibilitat.FRAC
        hh = model.hores
        durada = (hh['c4'] - hh['c1']) * 60.0
        central = None if v[1] == visibilitat.SENSE else v[1] / visibilitat.FRAC
        dur_c = (hh['c3'] - hh['c2']) * 3600.0 if hh.get('c2') is not None and hh.get('c3') is not None else None
        intervals = []
        for capa in p.dades['intervals'][:1] if p.nivell == 0 else p.dades['intervals']:
            ini, fi = int(capa[f, c, 0]), int(capa[f, c, 1])
            if ini != visibilitat.SENSE:
                intervals.append((self.inici + ini / 3600.0, self.inici + fi / 3600.0))
        n = v[3] % 16
        edifici = p.nivell == 3 and bool(v[3] & BIT_EDIFICI)
        if p.nivell == 3:
            obstacles = 'relleu, edificis i vegetacio (' + p.descripcio + ', alcaria LiDAR)'
        else:
            obstacles = 'nomes el relleu (' + NOM_NIVELL[p.nivell] + '): sense edificis ni vegetacio'
        return dict(lat=lat, lon=lon, eclipsi=eclipsis.actiu(), nivell=p.nivell, dades=p.descripcio,
                    res_m=p.res, tipus='terrat (ulls a 1,7 m sobre la coberta)' if edifici else
                    'carrer (ulls a 1,7 m sobre el terra)', obstacles=obstacles, frac=frac, minuts=frac * durada,
                    durada_min=durada, central=central, segons_central=None if central is None or dur_c is None
                    else central * dur_c, durada_central_s=dur_c, intervals=intervals, n_intervals=n,
                    marge_maxim=None if v[2] == 0 else (v[2] - 32768) / 100.0,
                    c1=hh['c1'], c4=hh['c4'], posta=hh.get('posta'))

    def exportar(self, r, cami=None):
        """Afegeix una consulta (consulta()) a data/exportacions/consultes.csv (tasca 43.6). Retorna el cami."""
        import csv
        from dades import data_io
        cami = cami or os.path.join(os.path.dirname(data_io.DIR_CACHE), 'exportacions', 'consultes.csv')
        os.makedirs(os.path.dirname(cami), exist_ok=True)
        nou = not os.path.exists(cami)
        hl = eclipsis.hora_local
        with open(cami, 'a', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            if nou:
                w.writerow(['data_consulta', 'eclipsi', 'lat', 'lon', 'tipus', 'nivell', 'dades', 'resolucio_m',
                            'obstacles', 'c1_local', 'c4_local', 'temps_observable_min', 'durada_c1_c4_min',
                            'percentatge', 'fase_central_observable_s', 'durada_fase_central_s', 'intervals_local',
                            'nombre_intervals', 'marge_al_maxim_graus', 'criteri'])
            w.writerow([time.strftime('%Y-%m-%d %H:%M'), r['eclipsi'], f"{r['lat']:.6f}", f"{r['lon']:.6f}",
                        r['tipus'], f"N{r['nivell']}", r['dades'], f"{r['res_m']:g}", r['obstacles'], hl(r['c1']),
                        hl(r['c4']), f"{r['minuts']:.1f}", f"{r['durada_min']:.1f}", f"{100 * r['frac']:.1f}",
                        '' if r['segons_central'] is None else f"{r['segons_central']:.0f}",
                        '' if r['durada_central_s'] is None else f"{r['durada_central_s']:.0f}",
                        ' '.join(f'{hl(a)}-{hl(b)}' for a, b in r['intervals']), r['n_intervals'],
                        '' if r['marge_maxim'] is None else f"{r['marge_maxim']:.2f}",
                        'alguna part del Sol lliure d\'obstacles (D91); sense meteorologia'])
        return cami

    def resum(self):
        """Per a les proves: peces carregades per nivell, feines i el nivell al centre."""
        n = {f'n{nv}': sum(1 for p in self.peces.values() if p.nivell == nv) for nv in NIVELLS}
        return dict(peces=n, feines=sorted(f'{t}:{k[1] if isinstance(k, tuple) else k}' for t, k in self.feines),
                    nivell_centre=self.text_nivell_centre(), pixel_centre_m=self.pixel_centre_m,
                    fallades=len(self.fallades))

    def text_nivell_centre(self):
        if self.quin is None:
            return ''
        if not self.amb_nivells():
            return 'graella de circumstancies (2 km)' if self.quin == 'ocultacio' and \
                self.mode['ocultacio'] == 'maxim' else 'calculat per a cada punt'
        app = self.app
        lat, lon = None, None
        punts = self._raigs(1, 1)
        if punts:
            la, lo, _ = geodesia.geodesiques(punts[0][0])
            lat, lon = float(la), float(lo)
        if lat is None:
            return 'cap (la vista no mira el terra)'
        r = self.nivell_a(lat, lon)
        return r[0].descripcio if r is not None else 'sense dades'

    def text_estat(self):
        """Linia d'estat per al panell: que es prepara."""
        if not self.feines and self.feina_graella is None:
            return ''
        noms = {'llegir': 'llegint', 'calcular': 'calculant', 'relleu': 'baixant el relleu',
                'superficie': 'preparant els obstacles'}
        parts = []
        for (t, k), f in self.feines.items():
            nivell = k[0] if isinstance(k, tuple) else None
            parts.append(f'{noms.get(t, t)}' + (f' {NOM_NIVELL[nivell]}' if nivell is not None else '') +
                         f' ({f.segons():.0f} s)')
        if self.feina_graella is not None:
            parts.append('circumstancies')
        return '; '.join(parts)

    def destroy(self):
        for t in self.textures.values():
            t[0].release()
        self.buida.release()
        self.buida_2d.release()
        if self.tex_graella is not None:
            self.tex_graella.release()
