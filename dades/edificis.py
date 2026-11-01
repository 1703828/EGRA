"""
Edificis de les zones de detall: lectura, altures, malla i ocultacio del Sol (sense OpenGL).

Dades: parts d'edifici del Catastro INSPIRE (scripts/descarregar_edificis.py), ja en EPSG:25830, a
data/edificis/<zona>.gpkg. Cada part es un contorn amb un nombre de plantes sobre rasant.

Altures, dues versions de la mateixa zona:
  - estimades (sempre, de seguida): altura sobre el sol de cada part = plantes x ALCADA_PLANTA_M. El Catastro no
    dona l'altura en metres; el valor de 3,0 m per planta es una aproximacio habitual (la planta baixa i les
    cobertes inclinades o amb ampit la fan variar). A la UAB queda ~2-3 m per sota de la mesurada
    (scripts/validar_alcaries.py). Nomes per a la vista provisional: el mapa de visibilitat no les fa servir.
  - mesurades (dades/alcaries.py, per cel·les de 3 x 3 km a mesura que es miren): l'altura de cada part surt
    d'un model d'alcaries LiDAR (ICGC a Catalunya, IGN a la resta); les parts que no s'hi poden mesurar (o de
    cel·les encara no mesurades) conserven l'estimacio, marcada com a tal (origen_alcada = 0).
  - cota del sol de referencia (absoluta, m sobre el nivell del mar) = mediana del MDT de 5 m als vertexs i
    al centre del contorn; cota de la coberta = referencia + altura. En un terreny inclinat, la diferencia
    entre el punt mes alt i el mes baix sota l'edifici es una incertesa mes de la coberta.
  - les facanes baixen fins a 1 m per sota del punt mes baix del terra sota l'edifici (el del MDT o el de la
    malla del terreny, el que sigui mes baix): l'edifici no flota ni deixa escletxes en pendent.

Malla (malla_zona): coberta plana triangulada amb triangulacio restringida (respecta els patis interiors) i
una facana per cada costat del contorn. Posicions en coordenades terrestres (ECEF, km) relatives a un
origen, en doble precisio (la GPU les rep en float32 relatives a la camera, com el terreny).

Ocultacio del Sol (arestes, perfil_edificis i fraccions_disc): un calcul geometric independent de la imatge. Des dels
ulls, per a cada azimut (cada 0,01 graus) es busca l'angle mes alt de les cobertes dels edificis (vores
dels contorns mostrejades amb un pas angular mes fi que l'interval del perfil), amb la curvatura de la Terra (es treballa en ECEF i
es passa a l'horitzo local dels ulls). Un punt del disc del Sol queda tapat si es per sota del perfil en el
seu azimut. Es mostreja tot el disc (no nomes el centre) per separar ocultacio parcial i total.
"""
import math
import os

import numpy as np
import shapely
from pyproj import Proj, Transformer

from . import geodesia
from .catastro import DIR_EDIFICIS

RADI_ZONA_M = 2000.0         # edificis preparats al voltant de cada punt d'observacio (scripts/descarregar_edificis.py)
ALCADA_PLANTA_M = 3.0
SOTERRAMENT_M = 1.0          # les facanes baixen aixo per sota del punt mes baix del terra
PAS_PERFIL_GRAUS = 0.01
CRS = 'EPSG:25830'

# zona de detall (clau de dades/data_io.ZONES_DETALL) de cada ubicacio de la llista
ZONA_DE_LA_UBICACIO = {
    'Picos de Europa (totalitat)': 'picos', 'Vic, placa Major': 'vic', "L'Escala, ajuntament": 'escala',
    'Cerdanyola, ajuntament': 'valles', 'Montmelo, ajuntament': 'valles', 'UAB, placa Civica': 'valles',
}


def fitxer_zona(zona):
    return os.path.join(DIR_EDIFICIS, f'{zona}.gpkg')


def llegir_zona(zona, mesurades=False):
    """GeoDataFrame de les parts d'edifici d'una zona (EPSG:25830), o None si no se n'han preparat. alcada_m es
    l'estimacio per plantes; amb mesurades=True (i les altures de dades/alcaries.py preparades), la mesurada a les
    parts on n'hi ha. origen_alcada: 1 mesurada, 0 estimada."""
    cami = fitxer_zona(zona)
    if not os.path.exists(cami):
        return None
    import geopandas as gpd
    parts = gpd.read_file(cami, layer='parts')
    parts['alcada_m'] = parts['plantes'] * ALCADA_PLANTA_M
    parts['origen_alcada'] = 0
    if mesurades:
        from .alcaries import llegir_alcades
        m = llegir_alcades(zona)
        if m is not None:
            alcada = dict(zip(m['ids'].astype(str), m['alcada']))     # nomes les cel·les ja mesurades
            h = parts['id'].astype(str).map(alcada).to_numpy(dtype=float)
            ok = np.isfinite(h)
            parts.loc[ok, 'alcada_m'] = h[ok]
            parts.loc[ok, 'origen_alcada'] = 1
    return parts


def poligons(geom):
    return list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]


def cotes(parts, terra_m, terra_malla_m=None):
    """Cota del sol de referencia, cota de la coberta i cota de la base de les facanes (m) de cada part.
    terra_m(xs, ys) -> altitud del MDT a resolucio completa; terra_malla_m, la de la malla del terreny."""
    ref, coberta, base, desnivell = [], [], [], []
    for geom, h in zip(parts.geometry, parts['alcada_m']):
        xy = np.vstack([np.asarray(p.exterior.coords) for p in poligons(geom)] + [np.asarray(geom.centroid.coords)])
        g = np.asarray(terra_m(xy[:, 0], xy[:, 1]), dtype=float)
        gmin = g.min()
        if terra_malla_m is not None:
            gmin = min(gmin, float(np.min(terra_malla_m(xy[:, 0], xy[:, 1]))))
        r = float(np.median(g))
        ref.append(r)
        coberta.append(r + h)
        base.append(gmin - SOTERRAMENT_M)
        desnivell.append(float(g.max() - g.min()))
    parts = parts.copy()
    parts['cota_sol'], parts['cota_coberta'], parts['cota_base'], parts['desnivell'] = ref, coberta, base, desnivell
    return parts


def malla_zona(parts, origen_ecef):
    """Triangles (N x 3 x 3, km, ECEF - origen) de les cobertes i les facanes de totes les parts, i els atributs
    de cada vertex per a les textures (N x 3 x 4): u (m al llarg del costat de la facana), v (m sobre la cota del
    sol de referencia: les plantes comencen a v = 0), llargada del costat (m; -1 a les cobertes) i index de la part.
    Tots els triangles miren cap a fora (contorn exterior en sentit antihorari i patis en horari; cobertes cap
    amunt): aixi la GPU pot descartar les cares del darrere (basecode/edificis.py)."""
    a_latlon = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True)
    tri, atr = [], []      # (x, y, z_m) i (u, v, llargada, part) de cada vertex de cada triangle
    for k, (geom, zc, zb, zs) in enumerate(zip(parts.geometry, parts['cota_coberta'], parts['cota_base'],
                                               parts['cota_sol'])):
        for p in poligons(geom):
            p = shapely.geometry.polygon.orient(p, 1.0)      # exterior antihorari, patis horaris
            # coberta: triangulacio restringida al contorn (amb els patis)
            # (amb vertexs alineats, GEOS avisa d'un valor invalid; comprovat que l'area dels triangles es la
            # del contorn a totes les parts del Valles)
            with np.errstate(invalid='ignore'):
                triangles = shapely.constrained_delaunay_triangles(p).geoms
            for t in triangles:
                c = np.asarray(t.exterior.coords)[:3]
                if (c[1, 0] - c[0, 0]) * (c[2, 1] - c[0, 1]) - (c[1, 1] - c[0, 1]) * (c[2, 0] - c[0, 0]) < 0:
                    c = c[[0, 2, 1]]                          # antihorari vist des de dalt: normal cap amunt
                tri.append(np.column_stack([c, np.full(3, zc)]))
                atr.append(np.array([[0.0, 0.0, -1.0, k]] * 3))
            # facanes: un rectangle (dos triangles) per costat de cada anell
            for anell in [p.exterior, *p.interiors]:
                c = np.asarray(anell.coords)
                a, b = c[:-1], c[1:]
                for (x0, y0), (x1, y1) in zip(a, b):
                    q = np.array([[x0, y0, zb], [x1, y1, zb], [x1, y1, zc], [x0, y0, zc]])
                    llarg = math.hypot(x1 - x0, y1 - y0)
                    w = np.array([[0.0, zb - zs, llarg, k], [llarg, zb - zs, llarg, k],
                                  [llarg, zc - zs, llarg, k], [0.0, zc - zs, llarg, k]])
                    tri += [q[[0, 1, 2]], q[[0, 2, 3]]]
                    atr += [w[[0, 1, 2]], w[[0, 2, 3]]]
    if not tri:
        return np.zeros((0, 3, 3), 'f4'), np.zeros((0, 3, 4), 'f4')
    v = np.array(tri).reshape(-1, 3)
    lon, lat = a_latlon.transform(v[:, 0], v[:, 1])
    ecef = geodesia.ecef(lat, lon, v[:, 2] / 1000.0) - origen_ecef
    return ecef.reshape(-1, 3, 3), np.array(atr, dtype='f4')


def dins_dun_edifici(parts, x, y):
    """Identificador de la part que conte el punt (x, y) en EPSG:25830, o None."""
    p = shapely.Point(x, y)
    for pid, geom in zip(parts['id'], parts.geometry):
        if geom.contains(p):
            return pid
    return None


def arestes(parts):
    """Totes les vores de les cobertes (exteriors i patis): array (N, 5) amb xa, ya, xb, yb i la cota de
    la coberta (m), en EPSG:25830. Es calcula un cop per zona."""
    files = []
    for geom, zc in zip(parts.geometry, parts['cota_coberta']):
        for p in poligons(geom):
            for anell in [p.exterior, *p.interiors]:
                c = np.asarray(anell.coords)
                files.append(np.column_stack([c[:-1], c[1:], np.full(len(c) - 1, zc)]))
    return np.vstack(files) if files else np.zeros((0, 5))


def perfil_edificis(vores, ull_ecef, radi_km=2.5, exacte=False):
    """Perfil d'horitzo dels edificis vist des dels ulls: array de 36000 elevacions (graus, una per cada
    0,01 graus d'azimut; -90 on no hi ha cap edifici). vores = arestes(parts). Cada vora es mostreja amb un
    pas angular mes fi que l'interval d'azimut del perfil (0,6 x 0,01 graus a la distancia mes curta) i els punts es passen a l'horitzo local dels ulls des de
    coordenades terrestres: hi ha la curvatura i la diferencia entre el nord de quadricula i el geografic."""
    lat0, lon0, _ = (float(c) for c in geodesia.geodesiques(np.asarray(ull_ecef)))
    x0, y0 = Transformer.from_crs('EPSG:4326', CRS, always_xy=True).transform(lon0, lat0)
    est, nord, amunt = geodesia.base_local(lat0, lon0)
    perfil = np.full(int(round(360 / PAS_PERFIL_GRAUS)), -90.0)
    xa, ya, xb, yb, zc = vores.T
    d = np.hypot((xa + xb) / 2 - x0, (ya + yb) / 2 - y0)
    sel = d < radi_km * 1000
    if not sel.any():
        return perfil
    xa, ya, xb, yb, zc, d = xa[sel], ya[sel], xb[sel], yb[sel], zc[sel], d[sel]
    # pas angular: ~0,6 vegades l'amplada d'un interval d'azimut del perfil, a la distancia de la vora mes
    # propera als ulls (si no, una facana propera quedaria plena de forats)
    d_min = np.minimum(np.hypot(xa - x0, ya - y0), np.hypot(xb - x0, yb - y0))
    d_min = np.minimum(d_min, d)
    pas = np.maximum(0.001, d_min * math.radians(PAS_PERFIL_GRAUS) * 0.6)
    n = np.maximum(2, np.ceil(np.hypot(xb - xa, yb - ya) / pas).astype(int) + 1)
    quina = np.repeat(np.arange(len(n)), n)
    s = (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)) / np.repeat(n - 1, n)
    x, y = xa[quina] + s * (xb - xa)[quina], ya[quina] + s * (yb - ya)[quina]
    if exacte:
        lon, lat = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True).transform(x, y)
        v = geodesia.ecef(lat, lon, zc[quina] / 1000.0) - ull_ecef
        e, nn, u = v @ est, v @ nord, v @ amunt
    else:
        # dins de pocs km, de la quadricula UTM a l'horitzo local: un gir (la convergencia de meridians), un
        # factor d'escala i la caiguda per la curvatura d^2 / 2R (comprovat contra el calcul exacte en ECEF a
        # scripts/validar_edificis.py)
        f = Proj(CRS).get_factors(lon0, lat0)
        g, k = math.radians(f.meridian_convergence), f.meridional_scale
        dx, dy = (x - x0) / k / 1000.0, (y - y0) / k / 1000.0
        # azimut geografic = azimut de quadricula + convergencia (pla, §6.6)
        e, nn = dx * math.cos(g) + dy * math.sin(g), dy * math.cos(g) - dx * math.sin(g)
        alt0 = float(geodesia.geodesiques(np.asarray(ull_ecef))[2])
        u = zc[quina] / 1000.0 - alt0 - (e ** 2 + nn ** 2) / (2 * 6371.0)
    az = np.degrees(np.arctan2(e, nn)) % 360.0
    el = np.degrees(np.arctan2(u, np.hypot(e, nn)))
    np.maximum.at(perfil, (az / PAS_PERFIL_GRAUS).astype(int) % len(perfil), el)
    return perfil


def disc(n=60):
    """Punts d'un disc unitari (graella regular dins del cercle): (dx, dy), ~n x n x pi/4."""
    g = (np.arange(n) + 0.5) / n * 2 - 1
    dx, dy = np.meshgrid(g, g)
    dins = dx ** 2 + dy ** 2 <= 1
    return dx[dins], dy[dins]


def fraccions_disc(perfil, ull_ecef, sol_ecef, radi_sol_km, lluna_ecef, radi_lluna_km, n=60):
    """Quina part del disc del Sol, vist des dels ulls, tapa la Lluna i quina tapen els edificis.
    Retorna (part tapada per la Lluna, part tapada pels edificis, part visible), sobre el disc sencer."""
    lat0, lon0, _ = (float(c) for c in geodesia.geodesiques(np.asarray(ull_ecef)))
    est, nord, amunt = geodesia.base_local(lat0, lon0)
    s = sol_ecef - ull_ecef
    d = s / np.linalg.norm(s)
    rs = math.asin(radi_sol_km / np.linalg.norm(s))
    # base del pla del cel al voltant del centre del Sol: horitzontal (cap a l'est del Sol) i "amunt"
    h = np.cross(amunt, d)
    h /= np.linalg.norm(h)
    v = np.cross(d, h)
    dx, dy = disc(n)
    dirs = d[None, :] + rs * (dx[:, None] * h[None, :] + dy[:, None] * v[None, :])
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    e, nn, u = dirs @ est, dirs @ nord, dirs @ amunt
    az = np.degrees(np.arctan2(e, nn)) % 360.0
    el = np.degrees(np.arcsin(np.clip(u, -1, 1)))
    tapat_edifici = el < perfil[(az / PAS_PERFIL_GRAUS).astype(int) % len(perfil)]
    l = lluna_ecef - ull_ecef
    rl = math.asin(radi_lluna_km / np.linalg.norm(l))
    tapat_lluna = dirs @ (l / np.linalg.norm(l)) > math.cos(rl)
    total = len(dirs)
    return (float(tapat_lluna.sum()) / total, float(tapat_edifici.sum()) / total,
            float((~tapat_lluna & ~tapat_edifici).sum()) / total)


# ------------------------------------------------------------ malla preparada (memoria cau)

VERSIO_MALLA = 6            # 3: contorns (obstacles); 4: atributs de les textures; 5: triangles cap a fora;
                            # 6: plantes i origen de l'altura (estimada o mesurada) de cada part


def mostrejador(alt, transform):
    """Funcio (xs, ys) EPSG:25830 -> altitud (m) amb interpolacio bilineal, amb el conveni dels centres de
    pixel del terreny (el pixel k te el centre a (k + 0,5) x resolucio de la vora)."""
    from scipy.ndimage import map_coordinates
    res = transform.a

    def f(xs, ys):
        cols = (np.asarray(xs) - transform.c) / res - 0.5
        files = (transform.f - np.asarray(ys)) / res - 0.5
        return np.maximum(map_coordinates(alt, [files, cols], order=1, mode='nearest'), 0.0)
    return f


def contorns_a_bytes(geoms):
    """Contorns en WKB, tots seguits (np.savez sense pickle no desa objectes): bytes i on comenca cadascun."""
    wkb = shapely.to_wkb(geoms)
    inici = np.concatenate([[0], np.cumsum([len(b) for b in wkb])]).astype('i8')
    return dict(contorns_wkb=np.frombuffer(b''.join(wkb), dtype='u1'), contorns_inici=inici)


def contorns_de_bytes(m):
    """El contrari de contorns_a_bytes: array de poligons shapely (EPSG:25830)."""
    dades, inici = m['contorns_wkb'].tobytes(), m['contorns_inici']
    return shapely.from_wkb([dades[a:b] for a, b in zip(inici[:-1], inici[1:])])


VERSIO_COBERTES = 2          # 2: de les teselles del PNOA, a tot arreu (abans, de l'ortofoto de les zones fetes a ma)
ZOOM_COBERTES = 17           # teselles de ~0,9 m per pixel a Catalunya: una coberta de 10 x 10 m en te ~120
ERODIR_COBERTES_M = 1.0      # es descarta la vora de cada contorn (barreja amb el carrer, les facanes i les ombres)
FILS_COBERTES = 8            # baixades en paral·lel (les teselles que ja hi son es llegeixen del disc)


def cami_cobertes(zona):
    from . import data_io
    return os.path.join(data_io.DIR_CACHE, f'cobertes_{zona}.npz')


def cobertes_desades(zona, n_parts):
    """Colors de les cobertes ja calculats (colors_cobertes) per a aquesta zona i aquest nombre de parts, o None."""
    cami = cami_cobertes(zona)
    if not os.path.exists(cami):
        return None
    try:
        with np.load(cami) as z:
            if np.array_equal(z['clau'], [VERSIO_COBERTES, n_parts, ZOOM_COBERTES]):
                return z['colors']
    except (OSError, ValueError, KeyError):
        pass
    return None


def colors_cobertes(zona, contorns, avis=print):
    """Color de cada coberta (RGB 0..1; NaN si no se'n pot treure) a partir de la fotografia aeria del PNOA, la
    mateixa a tot Espanya: la mitjana dels pixels de les teselles de ZOOM_COBERTES que queden dins del contorn
    (sense ERODIR_COBERTES_M de vora). Nomes es baixen les teselles que tenen edificis, i es desen a la memoria cau de
    teselles (dades/teselles.py), com les del mosaic. Com que la foto no es ortofoto vertadera, la teulada dels
    edificis alts hi es desplacada uns metres: la mitjana de tota la coberta en redueix l'efecte.
    Resultat a data/cache/cobertes_<zona>.npz (cobertes_desades). Es llarg (minuts en una zona gran): en un proces."""
    from concurrent.futures import ThreadPoolExecutor
    import requests
    from affine import Affine
    from rasterio import features
    from . import data_io, teselles
    n = len(contorns)
    interiors = shapely.buffer(contorns, -ERODIR_COBERTES_M)
    petits = shapely.is_empty(interiors)
    interiors[petits] = contorns[petits]                # els molt petits, sencers
    a_geo = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
    costat = teselles.MIDA << ZOOM_COBERTES             # pixels del mon a aquest zoom

    def a_pixels(xy):
        lon, lat = a_geo.transform(xy[:, 0], xy[:, 1])
        mx, my = teselles.mercator(lat, lon)
        return np.column_stack([np.asarray(mx) * costat, np.asarray(my) * costat])
    px = shapely.transform(interiors, a_pixels)
    b = shapely.bounds(px)
    t0 = np.floor(b[:, :2] / teselles.MIDA).astype(int)
    t1 = np.floor(b[:, 2:] / teselles.MIDA).astype(int)
    per_tesella = {}
    for k in range(n):
        for tx in range(t0[k, 0], t1[k, 0] + 1):
            for ty in range(t0[k, 1], t1[k, 1] + 1):
                per_tesella.setdefault((tx, ty), []).append(k)
    suma, compte = np.zeros((n, 3)), np.zeros(n)
    fallades = 0
    sessions = {}

    def acumular(rgb, tx, ty, parts, geoms, tots):
        etiquetes = features.rasterize(((geoms[k], k + 1) for k in parts), out_shape=(teselles.MIDA, teselles.MIDA),
                                       transform=Affine.translation(tx * teselles.MIDA, ty * teselles.MIDA),
                                       fill=0, dtype='int32', all_touched=tots)
        dins = etiquetes > 0
        k = etiquetes[dins] - 1
        compte[:] += np.bincount(k, minlength=n)
        for c in range(3):
            suma[:, c] += np.bincount(k, weights=rgb[..., c][dins], minlength=n)

    def baixar(t):
        import threading
        s = sessions.setdefault(threading.get_ident(), requests.Session())
        try:
            return t, teselles.tesella(ZOOM_COBERTES, t[0], t[1], s)
        except Exception:    # noqa: BLE001 (xarxa: aquella tesella queda sense color)
            return t, None
    avis(f'Color de les cobertes: {len(per_tesella)} teselles...')
    with ThreadPoolExecutor(FILS_COBERTES) as ex:
        for i, ((tx, ty), rgb) in enumerate(ex.map(baixar, list(per_tesella))):
            if rgb is None:
                fallades += 1
                continue
            acumular(rgb, tx, ty, per_tesella[(tx, ty)], px, False)
            if i % 100 == 99:
                avis(f'Color de les cobertes: {i + 1} de {len(per_tesella)} teselles')
    # contorns tan petits o prims que, sense la vora, no contenen el centre de cap pixel: tots els pixels que toquen
    # el contorn sencer (ja son al disc)
    buides = set(np.flatnonzero(compte == 0))
    if buides:
        sencers = shapely.transform(contorns, a_pixels)
        for (tx, ty), parts in per_tesella.items():
            parts = [k for k in parts if k in buides]
            if parts:
                rgb = baixar((tx, ty))[1]
                if rgb is not None:
                    acumular(rgb, tx, ty, parts, sencers, True)
    colors = np.full((n, 3), np.nan)
    ok = compte > 0
    colors[ok] = suma[ok] / compte[ok, None] / 255.0
    if not fallades:                                    # amb teselles fallades, es tornara a provar un altre dia
        os.makedirs(data_io.DIR_CACHE, exist_ok=True)
        np.savez(cami_cobertes(zona), clau=[VERSIO_COBERTES, n, ZOOM_COBERTES], colors=colors)
    return colors


def cami_malla(zona, mesurades=False):
    from . import data_io
    return os.path.join(data_io.DIR_CACHE, f'edificis_{zona}{"_mesurades" if mesurades else ""}.npz')


def preparar_malla(zona, cami_mdt, mesurades=False, nomes_llegir=False):
    """Malla dels edificis d'una zona, a data/cache/edificis_<zona>[_mesurades].npz: triangles (float32, km)
    relatius a un origen (float64, ECEF, el centre dels edificis a l'el·lipsoide), les cotes de cada part, les
    plantes i l'origen de l'altura. Es torna a calcular nomes si han canviat els edificis, el MDT, les altures
    mesurades o VERSIO_MALLA. mesurades=True: amb les altures de dades/alcaries.py (None si no s'han preparat).
    nomes_llegir: None si la memoria cau no hi es (no la calcula). Retorna el dict, o None sense dades."""
    from .alcaries import cami_alcades
    cache = cami_malla(zona, mesurades)
    gpkg = fitxer_zona(zona)
    if not os.path.exists(gpkg) or (mesurades and not os.path.exists(cami_alcades(zona))):
        return None
    clau = np.array([VERSIO_MALLA, os.path.getmtime(gpkg), os.path.getmtime(cami_mdt),
                     os.path.getmtime(cami_alcades(zona)) if mesurades else 0.0])
    if os.path.exists(cache):
        with np.load(cache, allow_pickle=False) as z:
            if z['clau'].shape == clau.shape and np.array_equal(z['clau'], clau):
                return {k: z[k] for k in z.files}
    if nomes_llegir:
        return None
    from . import data_io
    parts = llegir_zona(zona, mesurades)
    if parts is None or len(parts) == 0:
        return dict(triangles=np.zeros((0, 3, 3), 'f4'), origen=np.zeros(3), n_parts=np.array(0), clau=clau,
                    vores=np.zeros((0, 5)), contorns_wkb=np.zeros(0, 'u1'), contorns_inici=np.zeros(1, 'i8'),
                    cota_coberta=np.zeros(0), cota_sol=np.zeros(0), atributs=np.zeros((0, 3, 4), 'f4'),
                    plantes=np.zeros(0, 'i2'), origen_alcada=np.zeros(0, 'u1'), font_alcada=np.array(''))
    d = data_io.carregar_terreny(cami_mdt, 16384, data_io.vertexs_maxims(cami_mdt))
    terra = mostrejador(d['alt'], d['transform'])
    # la malla del terreny (fora del pegat dens) fa servir l'altitud mitjanada per blocs als vertexs
    files, cols = d['alt'].shape
    t_v = d['transform'] * __import__('rasterio').Affine.scale(cols / d['alt_vertexs'].shape[1], files / d['alt_vertexs'].shape[0])
    terra_malla = mostrejador(d['alt_vertexs'], t_v)
    parts = cotes(parts, terra, terra_malla)
    x0, y0, x1, y1 = parts.total_bounds
    lon, lat = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True).transform((x0 + x1) / 2, (y0 + y1) / 2)
    origen = geodesia.ecef(lat, lon, 0.0)
    tri, atributs = malla_zona(parts, origen)
    font = ''
    if mesurades:
        from .alcaries import llegir_alcades
        f = llegir_alcades(zona)['font_part']
        f = f[f != '']
        font = str(max(set(f.tolist()), key=f.tolist().count)) if len(f) else ''   # la font de la majoria
    r = dict(triangles=tri.astype('f4'), atributs=atributs, origen=origen, n_parts=np.array(len(parts)), clau=clau,
             plantes=parts['plantes'].to_numpy().astype('i2'), origen_alcada=parts['origen_alcada'].to_numpy().astype('u1'),
             font_alcada=np.array(font),
             cota_sol=parts['cota_sol'].to_numpy(), cota_coberta=parts['cota_coberta'].to_numpy(),
             desnivell=parts['desnivell'].to_numpy(), vores=arestes(parts), **contorns_a_bytes(parts.geometry.values))
    os.makedirs(data_io.DIR_CACHE, exist_ok=True)
    # comprimida: ~5 vegades menys espai; llegir-la tarda ~0,1 s mes. Primer amb un altre nom (es pot preparar en un fil)
    np.savez_compressed(cache + '.tmp.npz', **r)
    os.replace(cache + '.tmp.npz', cache)
    return r
