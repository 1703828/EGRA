"""
On es veu l'eclipsi (objectiu O3): per a cada pixel d'un MDT, si el relleu tapa el Sol durant l'eclipsi (sense
OpenGL). El criteri es geometric, no de llum: el Sol es veu si, en la seva direccio, el seu centre queda per
sobre de l'horitzo (l'angle mes alt del relleu en aquella direccio, vist des dels ulls a 1,7 m).

1. Circumstancies (graella gruixuda, ~1 km a les zones i 4 km a la peninsula; cada minut de les efemerides):
   elevacio aparent del Sol (amb refraccio), azimut de quadricula, contactes C1-C4, maxim i fase central, amb
   les mateixes formules que dades/model_eclipsi.py pero per a molts punts alhora. Canvien a poc a poc amb la
   distancia (0,01 graus i ~1 s per km): entre cel·les s'interpola o es fa servir la mes propera.
2. Horitzo (resolucio completa del MDT): per a cada direccio (cada PAS_AZIMUT graus d'azimut de quadricula),
   per a tots els pixels alhora, es recorre el relleu en aquella direccio a distancies creixents (5 m a 200 km
   en ~300 passos) i es guarda la tangent mes alta: (h - h_ulls) / d - d / 2R (la caiguda per la curvatura de
   la Terra, R = 6371 km, sense refraccio terrestre: D18); fins a 100 m, cada mig pixel. El relleu es llegeix
   amb interpolacio bilineal (amb el
   pixel mes proper, en un vessant fort, l'horitzo d'un obstacle a 100 m s'equivocava fins a 0,3 graus). A les zones de detall, el relleu de fora de la
   zona surt del MDT de la peninsula (200 m), fins a 200 km; dins de la zona, nomes el de 5 m (el de 200 m,
   mitjana de cel·les grans, en un vessant pot quedar mes alt que el relleu real i alcaria l'horitzo).
   Azimut geografic = azimut de quadricula + convergencia de meridians (pla, §6.6).
3. Per a cada minut i cada pixel: marge = elevacio del Sol - horitzo en el seu azimut (interpolat entre les dues
   direccions veines). Es desen:
     t_ini, t_fi  primer i darrer moment, entre C1 i C4, amb el centre del Sol per sobre de l'horitzo (segons des
                  de l'inici de les efemerides; els creuaments s'interpolen entre minuts). Un sol interval: si el
                  Sol s'amaga i torna a sortir, l'interval va del primer moment al darrer.
     marge        el marge al maxim (centesimes de grau). Classes com la capa del CNIG: 3 cap part tapada
                  (marge > radi del Sol), 2 es veu mes de la meitat, 1 menys, 0 res.
     central      segons de fase central (totalitat o anularitat) amb el centre del Sol visible.
El calcul es fa per blocs de MIDA_BLOC pixels, FILS a la vegada (la memoria no depen de la mida del MDT) i es desa a
data/cache/visibilitat_<eclipsi>_<mdt>.npz (comprimit). Es refa si canvia el MDT o VERSIO.

Aproximacions: relleu del MDT (terra nu: sense arbres ni edificis); fora d'Espanya el MDT val 0; el pixel del
MDT es la mitjana de la seva area (a 200 m, un cim o un fons de vall queda suavitzat); el factor d'escala de la
projeccio (< 0,2 %) no es corregeix.
"""
import math
import os
import time

import numpy as np
from pyproj import Proj, Transformer
from scipy.ndimage import map_coordinates

from . import data_io, eclipsis, geodesia
from .efemerides import RADI_SOL_KM, RADI_LLUNA_KM
from .model_eclipsi import efemerides

VERSIO = 3                 # 2: maxim i fase central amb la parabola de d^2; raig des d'un quart de pixel;
                           # 3: passos de mig pixel fins a 100 m
PAS_AZIMUT = 1.0           # graus entre direccions de l'horitzo
ULLS_M = 1.7
R_TERRA_M = 6371000.0
DIST_MAX_M = 200000.0
PASSOS = 300
PROP_M, PAS_PROP_PX = 100.0, 0.5    # fins a 100 m, cada mig pixel (amb el LiDAR d'1 m: els arbres i els pals)
MIDA_BLOC = 1024
FILS = max(1, min(4, (os.cpu_count() or 2) // 2))   # blocs alhora (NumPy deixa treballar els altres fils)
CEL_MIN_M = 1000.0         # cel·la de les circumstancies: com a minim 1 km i com a minim 20 pixels
SENSE = 65535              # t_ini, t_fi i central sense valor
SENSE_MARGE = -32768


def cami_cache(clau, cami_mdt):
    nom = os.path.splitext(os.path.basename(cami_mdt))[0]
    return os.path.join(data_io.DIR_CACHE, f'visibilitat_{clau}_{nom}.npz')


def refraccio(el):
    """Refraccio astronomica estandard (Bennett), com geodesia.refraccio_graus, per a arrays (graus)."""
    el = np.asarray(el, dtype=float)
    r = 1.0 / np.tan(np.radians(el + 7.31 / (el + 4.4))) / 60.0
    return np.where(el < -1.0, 0.0, r)


# ------------------------------------------------------------ 1. circumstancies en una graella gruixuda

def circumstancies(lat, lon, alt_m, convergencia, ef=None):
    """Per a n punts (arrays): cada minut de les efemerides on algun punt te eclipsi, l'elevacio aparent i
    l'azimut de quadricula del Sol (graus, arrays (nt, n)); i per punt, els contactes (hores TU; NaN si no n'hi ha):
    c1, c2, maxim, c3, c4. Retorna un dict amb 'hores' (nt), 'el', 'az', els contactes i 'radi_sol' (graus)."""
    ef = ef or efemerides()
    p = geodesia.ecef(lat, lon, alt_m / 1000.0)
    fi, la = np.radians(lat), np.radians(lon)
    est = np.stack([-np.sin(la), np.cos(la), np.zeros_like(la)], -1)
    nord = np.stack([-np.sin(fi) * np.cos(la), -np.sin(fi) * np.sin(la), np.cos(fi)], -1)
    amunt = np.stack([np.cos(fi) * np.cos(la), np.cos(fi) * np.sin(la), np.sin(fi)], -1)
    hores = ef.hores[(ef.hores >= ef.inici) & (ef.hores <= ef.final)]
    n, nt = len(lat), len(hores)
    ext, dist, difr = np.empty((nt, n), 'f8'), np.empty((nt, n), 'f8'), np.empty((nt, n), 'f4')
    el, az = np.empty((nt, n), 'f4'), np.empty((nt, n), 'f4')
    radi_sol = 0.0
    for k, h in enumerate(hores):
        sol, lluna = ef.posicions(h)
        s, l = sol - p, lluna - p
        ns, nl = np.linalg.norm(s, axis=1), np.linalg.norm(l, axis=1)
        su, lu = s / ns[:, None], l / nl[:, None]
        d = 2 * np.arcsin(np.minimum(1.0, np.linalg.norm(su - lu, axis=1) / 2))
        rs, rl = np.arcsin(RADI_SOL_KM / ns), np.arcsin(RADI_LLUNA_KM / nl)
        ext[k], dist[k], difr[k] = d - (rs + rl), d, np.abs(rl - rs)
        e, nn, u = (su * est).sum(1), (su * nord).sum(1), (su * amunt).sum(1)
        g = np.degrees(np.arcsin(np.clip(u, -1, 1)))
        el[k] = g + refraccio(g)
        az[k] = (np.degrees(np.arctan2(e, nn)) - convergencia) % 360.0      # azimut de quadricula
        radi_sol = math.degrees(float(rs.mean()))

    def creuament(f, baixant):
        """Hora (per punt) on f passa de > 0 a <= 0 (baixant) o al reves; interpolacio lineal entre minuts."""
        a, b = f[:-1], f[1:]
        m = (a > 0) & (b <= 0) if baixant else (a <= 0) & (b > 0)
        t = np.full(n, np.nan)
        k = np.where(m.any(0), m.argmax(0) if baixant else nt - 2 - m[::-1].argmax(0), -1)
        ok = k >= 0
        ka, j = k[ok], np.nonzero(ok)[0]
        fa, fb = f[ka, j], f[ka + 1, j]
        t[ok] = hores[ka] + (hores[ka + 1] - hores[ka]) * fa / (fa - fb)
        return t

    r = dict(hores=hores, el=el, az=az, radi_sol=radi_sol, c1=creuament(ext, True), c4=creuament(ext, False))
    # maxim i fase central. Prop del maxim la Lluna es mou gairebe en linia recta respecte del Sol: la separacio
    # al quadrat es una parabola del temps, d^2 = a (t - tmax)^2 + dmin^2 (la separacio, en canvi, te forma de V
    # i una parabola no l'ajusta: el maxim s'equivocava uns segons). Ajust per minims quadrats amb els cinc minuts
    # del voltant; C2 i C3 son on d = |rl - rs| (un disc sencer dins de l'altre).
    k = np.clip(dist.argmin(0), 2, nt - 3)
    j = np.arange(n)
    tau = np.arange(-2, 3, dtype=float)                                  # minuts respecte de la mostra k
    y = np.stack([dist[k + i, j] ** 2 for i in range(-2, 3)])            # (5, n)
    a, b, c = np.polyfit(tau, y, 2)
    a = np.maximum(a, 1e-30)
    tmin = -b / (2 * a)
    d2min = np.maximum(c - b * b / (4 * a), 0.0)
    dt = hores[1] - hores[0]
    sense = np.isnan(r['c1'])
    r['maxim'] = np.where(sense, np.nan, hores[k] + tmin * dt)
    dr2 = difr[k, j].astype('f8') ** 2
    central = ~sense & (d2min < dr2)
    mig = np.sqrt(np.where(central, dr2 - d2min, 0.0) / a) * dt          # mitja durada (h)
    r['c2'] = np.where(central, r['maxim'] - mig, np.nan)
    r['c3'] = np.where(central, r['maxim'] + mig, np.nan)
    return r


# ------------------------------------------------------------ 2. horitzo en una direccio

def _desplacat(dem, di, dj, r0, r1, c0, c1):
    """dem[r + di, c + dj] per a les files r0..r1 i columnes c0..c1 (NaN fora del MDT)."""
    files, cols = dem.shape
    out = np.full((r1 - r0, c1 - c0), np.nan, 'f4')
    a0, a1 = max(r0 + di, 0), min(r1 + di, files)
    b0, b1 = max(c0 + dj, 0), min(c1 + dj, cols)
    if a0 < a1 and b0 < b1:
        out[a0 - di - r0:a1 - di - r0, b0 - dj - c0:b1 - dj - c0] = dem[a0:a1, b0:b1]
    return out


def distancies_px(k_min, k_max, prop_px):
    """Distancies (pixels) on es llegeix el relleu: cada PAS_PROP_PX fins a prop_px (a prop, un obstacle prim
    -una branca, un pal- fa un angle gran i, amb passos creixents, se'l saltava: al LiDAR d'1 m, fins a 2,7 graus
    d'error) i despres PASSOS distancies creixents."""
    prop = np.arange(k_min, min(prop_px, k_max), PAS_PROP_PX)
    lluny = np.geomspace(max(prop_px, k_min), k_max, PASSOS) if k_max > prop_px else np.zeros(0)
    return np.unique(np.round(np.concatenate([prop, lluny]), 2))


def horitzo(dem, res, az_quadricula, finestra, h_ulls, dist_min=0.0, dist_max=DIST_MAX_M):
    """Tangent de l'horitzo (la mes alta) en la direccio az_quadricula (graus) per als pixels de la finestra
    (r0, r1, c0, c1) del MDT, des dels ulls a h_ulls (m, array de la finestra), i la distancia (m) on es troba.
    NaN si no hi ha relleu en aquella direccio (fora del MDT)."""
    r0, r1, c0, c1 = finestra
    dc, dr = math.sin(math.radians(az_quadricula)), -math.cos(math.radians(az_quadricula))
    millor = np.full((r1 - r0, c1 - c0), np.nan, 'f4')
    on = np.zeros_like(millor)
    k_min = max(0.25, dist_min / res)      # des d'un quart de pixel: amb pixels grans (200 m) l'obstacle pot ser a dins
    k_max = min(dist_max / res, 2.0 * max(dem.shape))
    for k in distancies_px(k_min, k_max, PROP_M / res):
        fr, fc = k * dr, k * dc
        i0, j0 = math.floor(fr), math.floor(fc)
        a, b = fr - i0, fc - j0
        h = ((1 - a) * (1 - b) * _desplacat(dem, i0, j0, *finestra)
             + (1 - a) * b * _desplacat(dem, i0, j0 + 1, *finestra)
             + a * (1 - b) * _desplacat(dem, i0 + 1, j0, *finestra)
             + a * b * _desplacat(dem, i0 + 1, j0 + 1, *finestra))
        d = float(k * res)
        t = (h - h_ulls) / d - d / (2 * R_TERRA_M)
        mes = t > np.nan_to_num(millor, nan=-np.inf)
        millor[mes] = t[mes]
        on[mes] = d
    return millor, on


# ------------------------------------------------------------ 3. el MDT sencer, per blocs

def calcular(cami_mdt, clau=None, cami_peninsula=None, avis=print, lluny=None, cami_ulls=None):
    """Calcula la visibilitat d'un MDT per a l'eclipsi (clau; per defecte l'actiu), la desa a la memoria cau i
    la retorna (dict). cami_peninsula: MDT de 200 m per al relleu llunya (zones de detall). lluny: llista de MDT
    per al relleu de fora, del mes detallat al menys (en lloc de cami_peninsula; tots en el CRS del MDT); cada un
    nomes compta fora del MDT i dels anteriors. cami_ulls: raster (mateixa graella) amb la cota sobre la qual hi ha
    els ulls, si no es la del MDT: amb un model de superficie (edificis i arbres) com a MDT, els ulls van sobre
    el terra als carrers i sobre la coberta als terrats."""
    import rasterio
    clau = clau or eclipsis.actiu()
    ef = efemerides(clau)
    t0 = time.time()
    with rasterio.open(cami_mdt) as f:
        dem = f.read(1).astype('f4')
        transform, crs = f.transform, f.crs
    dem[~np.isfinite(dem) | (dem < -100)] = 0.0
    files, cols = dem.shape
    res = transform.a
    a_latlon = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)

    # graella gruixuda
    fc = max(1, int(round(max(CEL_MIN_M, 20 * res) / res)))
    ngr, ngc = math.ceil(files / fc), math.ceil(cols / fc)
    gr, gc = np.meshgrid((np.arange(ngr) + 0.5) * fc, (np.arange(ngc) + 0.5) * fc, indexing='ij')
    gx, gy = transform.c + gc.ravel() * res, transform.f - gr.ravel() * res
    glon, glat = a_latlon.transform(gx, gy)
    galt = np.maximum(dem[np.minimum(gr.ravel().astype(int), files - 1), np.minimum(gc.ravel().astype(int), cols - 1)], 0)
    conv = np.asarray(Proj(crs.to_string()).get_factors(glon, glat).meridian_convergence)
    avis(f'Circumstancies de l\'eclipsi ({ngr} x {ngc} cel·les)...')
    c = circumstancies(np.asarray(glat), np.asarray(glon), galt, conv, ef)
    hores = c['hores']
    # minuts que calen: de la C1 mes primerenca a la C4 mes tardana (amb un minut de marge)
    if np.all(np.isnan(c['c1'])):
        k0, k1 = 0, -1
    else:
        k0 = max(0, int(np.searchsorted(hores, np.nanmin(c['c1']))) - 1)
        k1 = min(len(hores) - 1, int(np.searchsorted(hores, np.nanmax(c['c4']))) + 1)
    el_g = c['el'].reshape(len(hores), ngr, ngc)
    az_g = c['az'].reshape(len(hores), ngr, ngc)
    camps = {k: c[k].reshape(ngr, ngc) for k in ('c1', 'c4', 'maxim', 'c2', 'c3')}
    durada = np.nan_to_num(camps['c3'] - camps['c2'], nan=0.0)

    ulls = None
    if cami_ulls:
        with rasterio.open(cami_ulls) as f:
            ulls = f.read(1).astype('f4')
        ulls = np.where(np.isfinite(ulls), ulls, dem)

    # relleu llunya: els MDT de fora (per defecte la peninsula, si n'hi ha i no es el mateix fitxer). Les cel·les
    # amb el centre dins del MDT (o d'un MDT llunya mes detallat) no compten: alla mana el relleu mes detallat
    if lluny is None:
        lluny = [cami_peninsula] if cami_peninsula else []
    lluny = [c for c in lluny if c and os.path.abspath(c) != os.path.abspath(cami_mdt)]
    pen, extensions = [], [transform * (0, 0) + transform * (cols, files)]
    for cami_l in lluny:
        with rasterio.open(cami_l) as f:
            dem_p, tr_p = np.maximum(np.nan_to_num(f.read(1).astype('f4')), 0.0), f.transform
        dem_lluny = dem_p.copy()
        rs_, cs_ = np.arange(dem_p.shape[0]) + 0.5, np.arange(dem_p.shape[1]) + 0.5
        for x0, y1, x1, y0 in extensions:
            pc0, pr0 = ~tr_p * (x0, y1)
            pc1, pr1 = ~tr_p * (x1, y0)
            dem_lluny[np.ix_((rs_ > pr0) & (rs_ < pr1), (cs_ > pc0) & (cs_ < pc1))] = np.nan
        pen.append((dem_p, dem_lluny, tr_p))
        extensions.append(tr_p * (0, 0) + tr_p * (dem_p.shape[1], dem_p.shape[0]))

    t_ini = np.full((files, cols), SENSE, 'u2')
    t_fi = np.full((files, cols), SENSE, 'u2')
    marge = np.full((files, cols), SENSE_MARGE, 'i2')
    central = np.full((files, cols), SENSE, 'u2')
    blocs = [(r, min(r + MIDA_BLOC, files), cc, min(cc + MIDA_BLOC, cols))
             for r in range(0, files, MIDA_BLOC) for cc in range(0, cols, MIDA_BLOC)]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(FILS) as fils:
        feines = [fils.submit(_bloc, dem, res, transform, b, fc, hores, k0, k1, el_g, az_g, camps, durada, pen,
                              t_ini, t_fi, marge, central, ef.inici, ulls) for b in blocs]
        for nb, f in enumerate(as_completed(feines)):
            f.result()
            avis(f'Horitzo: {nb + 1} de {len(blocs)} blocs ({time.time() - t0:.0f} s)')
    r = dict(versio=np.array(VERSIO), clau=np.array(clau), mdt=np.array(os.path.abspath(cami_mdt)),
             mtime=np.array(os.path.getmtime(cami_mdt)), t_ini=t_ini, t_fi=t_fi, marge=marge, central=central,
             radi_sol=np.array(c['radi_sol']), durada_max=np.array(float(durada.max())),
             inici=np.array(ef.inici), segons=np.array(time.time() - t0))
    os.makedirs(data_io.DIR_CACHE, exist_ok=True)
    cami = cami_cache(clau, cami_mdt)
    np.savez_compressed(cami + '.tmp.npz', **r)
    os.replace(cami + '.tmp.npz', cami)
    avis(f'Visibilitat calculada en {time.time() - t0:.0f} s')
    return r


def llegir(cami_mdt, clau=None):
    """La visibilitat desada (dict) si hi es i correspon al MDT actual; si no, None."""
    cami = cami_cache(clau or eclipsis.actiu(), cami_mdt)
    if not os.path.exists(cami):
        return None
    with np.load(cami) as z:
        if int(z['versio']) != VERSIO or abs(float(z['mtime']) - os.path.getmtime(cami_mdt)) > 1e-3:
            return None
        return {k: z[k] for k in z.files}


def _bloc(dem, res, transform, finestra, fc, hores, k0, k1, el_g, az_g, camps, durada, pen,
          t_ini, t_fi, marge, central, inici, ulls=None):
    r0, r1, c0, c1 = finestra
    files_b, cols_b = r1 - r0, c1 - c0
    h_ulls = (dem if ulls is None else ulls)[r0:r1, c0:c1] + ULLS_M
    # cel·la mes propera de cada pixel (per a l'elevacio i l'azimut, que canvien ~0,01 graus per km) i
    # interpolacio bilineal dels contactes
    ri = np.minimum(np.arange(r0, r1) // fc, el_g.shape[1] - 1)
    ci = np.minimum(np.arange(c0, c1) // fc, el_g.shape[2] - 1)
    rr, cc = np.meshgrid((np.arange(r0, r1) + 0.5) / fc - 0.5, (np.arange(c0, c1) + 0.5) / fc - 0.5, indexing='ij')

    def bilineal(camp):
        return map_coordinates(camp, [rr, cc], order=1, mode='nearest')
    c1_p = bilineal(np.nan_to_num(camps['c1'], nan=1e9))
    c4_p = bilineal(np.nan_to_num(camps['c4'], nan=-1e9))
    tmax_p = bilineal(np.nan_to_num(camps['maxim'], nan=-1e9))
    dur_p = bilineal(durada) / 3600.0
    c2_p, c3_p = tmax_p - dur_p / 2, tmax_p + dur_p / 2

    # direccions de l'horitzo que fan falta: l'azimut del Sol al bloc, quan hi pot haver eclipsi i Sol a sobre
    gi0, gi1, gj0, gj1 = ri[0], ri[-1] + 1, ci[0], ci[-1] + 1
    sel = slice(k0, k1 + 1)
    utils = el_g[sel, gi0:gi1, gj0:gj1] > -1.5
    if not utils.any():
        return
    azs = az_g[sel, gi0:gi1, gj0:gj1][utils]
    llesques = {}

    # relleu llunya: per a cada MDT de fora, la finestra que cobreix el bloc, calculada a la seva resolucio
    finestres_lluny = []
    for dem_p, dem_lluny, tr_p in pen:
        x0, y0 = transform * (c0, r0)
        x1, y1 = transform * (c1, r1)
        pc0, pr0 = ~tr_p * (x0, y0)
        pc1, pr1 = ~tr_p * (x1, y1)
        fin_p = (max(int(math.floor(min(pr0, pr1))) - 1, 0), min(int(math.ceil(max(pr0, pr1))) + 2, dem_p.shape[0]),
                 max(int(math.floor(min(pc0, pc1))) - 1, 0), min(int(math.ceil(max(pc0, pc1))) + 2, dem_p.shape[1]))
        # posicio de cada pixel del bloc a la finestra (centres de pixel)
        xs = transform.c + (np.arange(c0, c1) + 0.5) * res
        ys = transform.f - (np.arange(r0, r1) + 0.5) * res
        pcol = (xs - tr_p.c) / tr_p.a - 0.5 - fin_p[2]
        prow = (tr_p.f - ys) / -tr_p.e - 0.5 - fin_p[0]
        PR, PC = np.meshgrid(prow, pcol, indexing='ij')
        h_pen_p = map_coordinates(dem_p[fin_p[0]:fin_p[1], fin_p[2]:fin_p[3]], [PR, PC], order=1, mode='nearest')
        finestres_lluny.append((dem_p, dem_lluny, tr_p, fin_p, PR, PC, h_pen_p))

    def llesca(j):
        """Tangent de l'horitzo a l'azimut j * PAS_AZIMUT (relleu proper i, si n'hi ha, llunya)."""
        if j not in llesques:
            a = (j * PAS_AZIMUT) % 360.0
            t, _ = horitzo(dem, res, a, finestra, h_ulls)
            for dem_p, dem_lluny, tr_p, fin_p, PR, PC, h_pen_p in finestres_lluny:
                hp = dem_p[fin_p[0]:fin_p[1], fin_p[2]:fin_p[3]] + ULLS_M
                tp, dp = horitzo(dem_lluny, tr_p.a, a, fin_p, hp)
                tp_b = map_coordinates(np.nan_to_num(tp, nan=-1.0), [PR, PC], order=1, mode='nearest')
                dp_b = map_coordinates(np.where(np.isnan(tp), 1e9, dp), [PR, PC], order=1, mode='nearest')
                # el relleu llunya es va calcular des de l'altura del MDT de fora: es corregeix a la dels ulls
                tl = tp_b + (h_pen_p - (h_ulls - ULLS_M)) / np.maximum(dp_b, tr_p.a)
                t = np.fmax(t, np.where(tp_b > -1.0, tl, np.nan))
            llesques[j] = np.degrees(np.arctan(np.nan_to_num(t, nan=-1.0))).astype('f4')
            # nomes es guarden les direccions que encara poden fer falta (l'azimut del Sol avanca)
            for v in [v for v in llesques if v < j - 2]:
                del llesques[v]
        return llesques[j]

    ti = np.full((files_b, cols_b), np.nan)
    tf = np.full((files_b, cols_b), np.nan)
    mmax = np.full((files_b, cols_b), np.nan, 'f4')
    m_ant, t_ant, dins_ant = None, None, None
    for k in range(k0, k1 + 1):
        t = hores[k]
        dins = (t >= c1_p) & (t <= c4_p)
        el = el_g[k][np.ix_(ri, ci)]
        if not dins.any() and dins_ant is not None and not dins_ant.any():
            m_ant, t_ant, dins_ant = None, t, dins
            continue
        if (el < -1.5).all():
            m = el - 1.0      # el Sol es sota l'horitzo a tot el bloc: no cal mirar el relleu
        else:
            az = az_g[k][np.ix_(ri, ci)] / PAS_AZIMUT
            j0 = np.floor(az).astype(int)
            w = az - j0
            m = np.empty_like(el)
            for j in np.unique(j0):
                q = j0 == j
                m[q] = el[q] - (llesca(j)[q] * (1 - w[q]) + llesca(j + 1)[q] * w[q])
        vis = m > 0
        if m_ant is not None:
            vis_ant = m_ant > 0
            dt = t - t_ant
            frac = np.clip(m_ant / np.where(m_ant != m, m_ant - m, 1.0), 0.0, 1.0)
            tc = t_ant + dt * frac
            # surt (de tapat a visible) dins de l'interval: primer moment
            surt = dins & dins_ant & vis & ~vis_ant & np.isnan(ti)
            ti[surt] = tc[surt]
            # s'amaga: darrer moment (fins ara)
            amaga = dins & dins_ant & ~vis & vis_ant
            tf[amaga] = tc[amaga]
            # el maxim cau entre els dos minuts: el marge s'interpola
            mx = (tmax_p >= t_ant) & (tmax_p < t)
            mmax[mx] = (m_ant + (m - m_ant) * (tmax_p - t_ant) / dt)[mx]
            # surt de l'interval (C4) amb el Sol visible: visible fins a C4
            acaba = dins_ant & ~dins & vis_ant
            tf[acaba] = c4_p[acaba]
            entra = dins & ~dins_ant
        else:
            entra = dins
        # entra a l'interval (C1) amb el Sol visible: visible des de C1
        ini = entra & vis & np.isnan(ti)
        ti[ini] = c1_p[ini]
        m_ant, t_ant, dins_ant = m, t, dins
    # visible a l'ultim minut calculat (encara dins de l'interval)
    if m_ant is not None:
        fi = dins_ant & (m_ant > 0)
        tf[fi] = np.minimum(c4_p, t_ant)[fi]
    ok = ~np.isnan(ti) & ~np.isnan(tf) & (tf >= ti)
    t_ini[r0:r1, c0:c1] = np.where(ok, np.clip(np.round((ti - inici) * 3600), 0, SENSE - 1), SENSE)
    t_fi[r0:r1, c0:c1] = np.where(ok, np.clip(np.round((tf - inici) * 3600), 0, SENSE - 1), SENSE)
    marge[r0:r1, c0:c1] = np.where(np.isnan(mmax), SENSE_MARGE, np.clip(np.round(mmax * 100), -32000, 32000))
    sec = np.where(ok, np.clip(np.minimum(tf, c3_p) - np.maximum(ti, c2_p), 0, None) * 3600, 0.0)
    central[r0:r1, c0:c1] = np.where(dur_p > 0, np.clip(np.round(sec * 10), 0, SENSE - 1), SENSE)


class Calcul:
    """llegir() o, si no hi es, calcular() en un fil. El fil principal llegeix estat i, quan fet es True,
    resultat (dict) o error. Els objectes OpenGL els crea el fil principal (Terrain.posar_visibilitat)."""

    def __init__(self, cami_mdt, clau, cami_peninsula=None, nomes_llegir=False):
        import threading
        self.cami, self.clau, self.nomes_llegir = cami_mdt, clau, nomes_llegir
        self.estat, self.fet, self.resultat, self.error = 'Llegint...', False, None, None
        self.fil = threading.Thread(target=self._executar, args=(cami_peninsula,), daemon=True)
        self.fil.start()

    def _executar(self, cami_peninsula):
        try:
            self.resultat = llegir(self.cami, self.clau)
            if self.resultat is None and not self.nomes_llegir:
                self.resultat = calcular(self.cami, self.clau, cami_peninsula, self._avis)
        except Exception as e:   # noqa: BLE001 (es mostra al panell)
            self.error = f'{e.__class__.__name__}: {e}'
            print(f'AVIS: no s\'ha pogut calcular la visibilitat: {self.error}')
        self.fet = True

    def _avis(self, text):
        self.estat = text
