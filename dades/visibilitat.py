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
   direccions veines). Entre dos minuts el marge s'interpola linealment (els creuaments surten d'aqui). Es desen
   (VERSIO 4, D91 i D95 del pla):
     obs          fraccio de C1-C4 amb **alguna part** del Sol lliure (marge > -radi del Sol), x FRAC (uint16). El
                  denominador es tot C4 - C1: despres de la posta el Sol queda sota l'horitzo i no compta. La Lluna
                  no compta com a obstacle: la totalitat es temps observable si el lloc del Sol es lliure.
     obs_central  el mateix dins de la fase central (C2-C3), sobre C3 - C2; SENSE si no n'hi ha.
     marge        el marge al maxim (centesimes de grau). Classes com la capa del CNIG: 3 cap part tapada
                  (marge > radi del Sol), 2 es veu mes de la meitat, 1 menys, 0 res.
     iv, n_iv     intervals de temps dins de C1-C4 amb alguna part del Sol lliure (llindar 0, marge > -r) i amb el
                  Sol sencer lliure (llindar 1, marge > +r): iv[llindar, i, 0/1] = inici/final del i-esim interval
                  (segons des de l'inici de les efemerides, SENSE si no n'hi ha). Si el Sol s'amaga i torna a sortir,
                  son intervals diferents (les interrupcions es conserven). n_iv: quants n'hi ha; si n'hi ha mes de
                  K_IV, els ultims s'ajunten a l'ultim (el temps observable obs es calcula a part i es exacte) i n_iv
                  val K_IV + 1. La resolucio temporal ve dels minuts de les efemerides i de les direccions de
                  l'horitzo (PAS_AZIMUT): una interrupcio mes curta que la mostra pot no apareixer
                  (scripts/validar_temps_visibilitat.py ho mesura).
El calcul es fa per blocs de MIDA_BLOC pixels, FILS a la vegada (la memoria no depen de la mida del MDT) i es desa a
data/cache/visibilitat_<eclipsi>_<mdt>[_<rectangle>].npz (comprimit). Es pot calcular nomes un rectangle del MDT
(rect: una cel·la de 3 x 3 km d'una zona gran; el relleu de fora del rectangle continua comptant per a l'horitzo).
Es refa si canvia el MDT o VERSIO.

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

VERSIO = 4                 # 2: maxim i fase central amb la parabola de d^2; raig des d'un quart de pixel;
                           # 3: passos de mig pixel fins a 100 m; 4: temps observable acumulat i intervals (D91, D95)
PAS_AZIMUT = 1.0           # graus entre direccions de l'horitzo
ULLS_M = 1.7
R_TERRA_M = 6371000.0
DIST_MAX_M = 200000.0
PASSOS = 300
PROP_M, PAS_PROP_PX = 100.0, 0.5    # fins a 100 m, cada mig pixel (amb el LiDAR d'1 m: els arbres i els pals)
MIDA_BLOC = 1024
FILS = max(1, min(4, (os.cpu_count() or 2) // 2))   # blocs alhora (NumPy deixa treballar els altres fils)
CEL_MIN_M = 1000.0         # cel·la de les circumstancies: com a minim 1 km i com a minim 20 pixels
SENSE = 65535              # obs, obs_central i iv sense valor
SENSE_MARGE = -32768
FRAC = 60000               # obs i obs_central: fraccio x FRAC (65535 = SENSE)
K_IV = 4                   # intervals desats per llindar (es mesura a scripts/validar_temps_visibilitat.py)
K_CALCUL = 8               # intervals que es compten en calcular (per mesurar quants en calen)


def cami_cache(clau, cami_mdt, rect=None, pas_azimut=PAS_AZIMUT):
    nom = os.path.splitext(os.path.basename(cami_mdt))[0]
    if rect is not None:
        nom += '_r' + '_'.join(f'{v:.0f}' for v in rect)
    if pas_azimut != PAS_AZIMUT:
        nom += f'_a{pas_azimut:g}'
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
    # part del Sol tapada per la Lluna al maxim (la mateixa formula que dades/model_eclipsi.py, per a arrays), amb
    # els radis aparents al minut mes proper del maxim
    rs_m, rl_m = _radis(ef, p, r['maxim'], hores[0])
    r['tapat_max'] = np.where(sense, np.nan, area_tapada(np.sqrt(d2min), rs_m, rl_m))
    return r


def _radis(ef, p, h, h_defecte):
    """Radis aparents del Sol i de la Lluna (rad) per a cada punt p a l'hora h (arrodonida al minut)."""
    h = np.round(np.where(np.isnan(h), h_defecte, h) * 60) / 60
    rs, rl = np.empty(len(p)), np.empty(len(p))
    for hh in np.unique(h):
        q = h == hh
        sol, lluna = ef.posicions(float(hh))
        rs[q] = np.arcsin(RADI_SOL_KM / np.linalg.norm(sol - p[q], axis=1))
        rl[q] = np.arcsin(RADI_LLUNA_KM / np.linalg.norm(lluna - p[q], axis=1))
    return rs, rl


def area_tapada(d, r1, r2):
    """Part del disc del Sol (radi r1) tapada per la Lluna (radi r2) amb els centres a d (rad, arrays): la formula de
    dades/model_eclipsi.py."""
    d, r1, r2 = np.broadcast_arrays(np.asarray(d, float), np.asarray(r1, float), np.asarray(r2, float))
    out = np.zeros(d.shape)
    dins = d <= np.abs(r2 - r1)
    out[dins] = np.minimum(1.0, (r2[dins] / r1[dins]) ** 2)
    m = ~dins & (d < r1 + r2)
    dd, a, b = d[m], r1[m], r2[m]
    a1 = a * a * np.arccos(np.clip((dd * dd + a * a - b * b) / (2 * dd * a), -1, 1))
    a2 = b * b * np.arccos(np.clip((dd * dd + b * b - a * a) / (2 * dd * b), -1, 1))
    a3 = 0.5 * np.sqrt(np.maximum((-dd + a + b) * (dd + a - b) * (dd - a + b) * (dd + a + b), 0))
    out[m] = (a1 + a2 - a3) / (np.pi * a * a)
    return out


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

def finestra_rect(transform, forma, rect):
    """Files i columnes (r0, r1, c0, c1) del MDT dins del rectangle UTM rect = (x0, y0, x1, y1); tot el MDT si rect es
    None."""
    files, cols = forma
    if rect is None:
        return 0, files, 0, cols
    x0, y0, x1, y1 = rect
    c0, r0 = ~transform * (x0, y1)
    c1, r1 = ~transform * (x1, y0)
    r0, r1 = max(int(round(r0)), 0), min(int(round(r1)), files)
    c0, c1 = max(int(round(c0)), 0), min(int(round(c1)), cols)
    if r1 <= r0 or c1 <= c0:
        raise ValueError(f'el rectangle {rect} no talla el MDT')
    return r0, r1, c0, c1


def calcular(cami_mdt, clau=None, cami_peninsula=None, avis=print, lluny=None, cami_ulls=None, rect=None,
             pas_azimut=PAS_AZIMUT):
    """Calcula la visibilitat d'un MDT (o del rectangle UTM rect del MDT) per a l'eclipsi (clau; per defecte l'actiu),
    la desa a la memoria cau i la retorna (dict). cami_peninsula: MDT de 200 m per al relleu llunya (zones de detall).
    lluny: llista de MDT per al relleu de fora, del mes detallat al menys (en lloc de cami_peninsula; tots en el CRS
    del MDT); cada un nomes compta fora del MDT i dels anteriors. cami_ulls: raster (mateixa graella) amb la cota
    sobre la qual hi ha els ulls, si no es la del MDT: amb un model de superficie (edificis i arbres) com a MDT, els
    ulls van sobre el terra als carrers i sobre la coberta als terrats."""
    clau = clau or eclipsis.actiu()
    marca = cami_cache(clau, cami_mdt, rect, pas_azimut) + '.calculant'
    os.makedirs(data_io.DIR_CACHE, exist_ok=True)
    with open(marca, 'w') as f:
        f.write(str(os.getpid()))
    try:
        return _calcular(cami_mdt, clau, cami_peninsula, avis, lluny, cami_ulls, rect, pas_azimut)
    finally:
        if os.path.exists(marca):
            os.remove(marca)


def en_calcul(cami_mdt, clau, rect=None, pas_azimut=PAS_AZIMUT):
    """Si un altre proces (viu) esta calculant aquesta peca ara mateix (p. ex. scripts/preparar_visibilitat.py)."""
    marca = cami_cache(clau, cami_mdt, rect, pas_azimut) + '.calculant'
    try:
        with open(marca) as f:
            pid = int(f.read().strip() or 0)
        os.kill(pid, 0)          # no envia res: nomes comprova que el proces existeix
        return pid != os.getpid()
    except (OSError, ValueError):
        return False


def _calcular(cami_mdt, clau, cami_peninsula, avis, lluny, cami_ulls, rect, pas_azimut):
    import rasterio
    ef = efemerides(clau)
    t0 = time.time()
    with rasterio.open(cami_mdt) as f:
        dem = f.read(1).astype('f4')
        transform, crs = f.transform, f.crs
    dem[~np.isfinite(dem) | (dem < -100)] = 0.0
    files, cols = dem.shape
    res = transform.a
    a_latlon = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    w_r0, w_r1, w_c0, w_c1 = finestra_rect(transform, dem.shape, rect)
    fh, fw = w_r1 - w_r0, w_c1 - w_c0

    # graella gruixuda (sobre la finestra)
    fc = max(1, int(round(max(CEL_MIN_M, 20 * res) / res)))
    ngr, ngc = math.ceil(fh / fc), math.ceil(fw / fc)
    gr, gc = np.meshgrid(w_r0 + (np.arange(ngr) + 0.5) * fc, w_c0 + (np.arange(ngc) + 0.5) * fc, indexing='ij')
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

    ulls = None
    if cami_ulls:
        with rasterio.open(cami_ulls) as f:
            ulls = f.read(1).astype('f4')
        ulls = np.where(np.isfinite(ulls), ulls, dem)

    # relleu llunya: els MDT de fora (per defecte la peninsula, si n'hi ha i no es el mateix fitxer). Les cel·les
    # amb el centre dins del MDT (o d'un MDT llunya mes detallat) no compten: alla mana el relleu mes detallat
    if lluny is None:
        lluny = [cami_peninsula] if cami_peninsula else []
    lluny = [c_ for c_ in lluny if c_ and os.path.abspath(c_) != os.path.abspath(cami_mdt)]
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

    sortida = dict(obs=np.full((fh, fw), SENSE, 'u2'), obs_central=np.full((fh, fw), SENSE, 'u2'),
                   marge=np.full((fh, fw), SENSE_MARGE, 'i2'), iv=np.full((2, K_IV, 2, fh, fw), SENSE, 'u2'),
                   n_iv=np.zeros((2, fh, fw), 'u1'))
    blocs = [(r, min(r + MIDA_BLOC, w_r1), cc, min(cc + MIDA_BLOC, w_c1))
             for r in range(w_r0, w_r1, MIDA_BLOC) for cc in range(w_c0, w_c1, MIDA_BLOC)]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    fils = ThreadPoolExecutor(FILS)
    try:
        feines = [fils.submit(_bloc, dem, res, transform, b, (w_r0, w_c0), fc, hores, k0, k1, el_g, az_g, camps,
                              pen, sortida, ef.inici, c['radi_sol'], ulls, pas_azimut) for b in blocs]
        for nb, f in enumerate(as_completed(feines)):
            f.result()
            avis(f'Horitzo: {nb + 1} de {len(blocs)} blocs ({time.time() - t0:.0f} s)')   # pot aturar el calcul
    except BaseException:
        fils.shutdown(wait=False, cancel_futures=True)   # els blocs que no han comencat ja no es fan
        raise
    fils.shutdown()
    tr_w = transform * transform.translation(w_c0, w_r0)
    r = dict(versio=np.array(VERSIO), clau=np.array(clau), mdt=np.array(os.path.abspath(cami_mdt)),
             mtime=np.array(os.path.getmtime(cami_mdt)), radi_sol=np.array(c['radi_sol']),
             inici=np.array(ef.inici), segons=np.array(time.time() - t0), res=np.array(res),
             transform=np.array(tr_w[:6]), crs=np.array(crs.to_string()),
             rect=np.array(rect if rect is not None else (np.nan,) * 4), pas_azimut=np.array(pas_azimut), **sortida)
    os.makedirs(data_io.DIR_CACHE, exist_ok=True)
    cami = cami_cache(clau, cami_mdt, rect, pas_azimut)
    np.savez_compressed(cami + '.tmp.npz', **r)
    os.replace(cami + '.tmp.npz', cami)
    avis(f'Visibilitat calculada en {time.time() - t0:.0f} s')
    return r


def vigent(cami_mdt, clau=None, rect=None, pas_azimut=PAS_AZIMUT):
    """Si la visibilitat desada correspon al MDT actual i a aquesta versio (sense llegir-ne les dades)."""
    cami = cami_cache(clau or eclipsis.actiu(), cami_mdt, rect, pas_azimut)
    if not os.path.exists(cami) or not os.path.exists(cami_mdt):
        return False
    with np.load(cami) as z:
        return int(z['versio']) == VERSIO and abs(float(z['mtime']) - os.path.getmtime(cami_mdt)) <= 1e-3


def llegir(cami_mdt, clau=None, rect=None, pas_azimut=PAS_AZIMUT):
    """La visibilitat desada (dict) si hi es i correspon al MDT actual; si no, None."""
    cami = cami_cache(clau or eclipsis.actiu(), cami_mdt, rect, pas_azimut)
    if not os.path.exists(cami) or not os.path.exists(cami_mdt):
        return None
    with np.load(cami) as z:
        if int(z['versio']) != VERSIO or abs(float(z['mtime']) - os.path.getmtime(cami_mdt)) > 1e-3:
            return None
    return llegir_npz(cami)


def llegir_npz(cami):
    """Com np.load(cami) (un .npz comprimit), pero descomprimint cada array d'un sol cop. np.load el descomprimeix a
    trossets de pocs KB amb un bucle de Python: en un fil del programa, cada trosset espera el bloqueig global de
    Python (GIL) que te el bucle de dibuix, i el mapa de la peninsula tardava 108 s a llegir-se en lloc de 2 s
    (mesurat el 16/11). zlib.decompress treballa en C i deixa anar el GIL mentre descomprimeix; l'array es crea a
    sobre de les dades descomprimides (np.frombuffer: nomes lectura)."""
    import io
    import struct
    import zipfile
    import zlib
    out = {}
    with open(cami, 'rb') as f, zipfile.ZipFile(f) as z:
        for info in z.infolist():
            f.seek(info.header_offset)
            cap = f.read(30)
            n_nom, n_extra = struct.unpack('<HH', cap[26:30])
            f.seek(info.header_offset + 30 + n_nom + n_extra)
            dades = f.read(info.compress_size)
            if info.compress_type == zipfile.ZIP_DEFLATED:
                dades = zlib.decompress(dades, -15)
            # capcalera del .npy i l'array directament sobre les dades (read_array tornaria a llegir a trossos)
            b = io.BytesIO(dades)
            versio = np.lib.format.read_magic(b)
            forma, fortran, dtype = (np.lib.format.read_array_header_1_0 if versio == (1, 0)
                                     else np.lib.format.read_array_header_2_0)(b)
            a = np.frombuffer(dades, dtype=dtype, count=int(np.prod(forma)), offset=b.tell())
            a = a.reshape(forma, order='F' if fortran else 'C')
            out[info.filename[:-4] if info.filename.endswith('.npy') else info.filename] = a
    return out


class _Intervals:
    """Intervals de temps (hores TU) en que f = marge - llindar > 0, dins de [ini, fi] de cada pixel, a partir dels
    valors de cada minut (entre minuts, f s'interpola linealment). Tambe el temps acumulat dins de [ini, fi] i dins
    de [c2, c3]. Vectoritzat per a un bloc de pixels."""

    def __init__(self, forma):
        self.n = np.zeros(forma, 'i2')
        self.obert = np.zeros(forma, bool)
        self.ultim = np.full(forma, np.nan)
        self.ini = np.full((K_IV,) + forma, np.nan)
        self.fi = np.full((K_IV,) + forma, np.nan)
        self.acum = np.zeros(forma)
        self.acum_c = np.zeros(forma)

    def pas(self, t_a, t_b, f_a, f_b, ini, fi, c2, c3):
        """Interval de temps [t_a, t_b] (un minut): f_a i f_b son f als extrems."""
        v_a, v_b = f_a > 0, f_b > 0
        tc = t_a + (t_b - t_a) * np.clip(f_a / np.where(f_a != f_b, f_a - f_b, 1.0), 0.0, 1.0)
        a = np.where(v_a, t_a, np.where(v_b, tc, np.nan))
        b = np.where(v_b, t_b, np.where(v_a, tc, np.nan))
        a, b = np.maximum(a, ini), np.minimum(b, fi)
        seg = b > a                                       # (NaN: fals)
        self.acum += np.where(seg, b - a, 0.0)
        self.acum_c += np.where(seg, np.clip(np.minimum(b, c3) - np.maximum(a, c2), 0.0, None), 0.0)
        # un segment visible que comenca quan no n'hi havia cap d'obert: interval nou
        nou = seg & ~self.obert
        idx = np.minimum(self.n, K_IV - 1)
        cap = nou & (self.n < K_IV)
        for i in range(K_IV):
            q = cap & (idx == i)
            self.ini[i][q] = a[q]
        # mes de K_IV intervals: el nou s'ajunta a l'ultim (no es tanca; el temps acumulat no canvia)
        self.n = np.where(nou, np.minimum(self.n + 1, K_CALCUL + 1), self.n)
        self.obert |= nou
        self.ultim = np.where(seg, b, self.ultim)
        # es tanca si el segment acaba abans del final del minut, o si no n'hi ha cap i n'hi havia un d'obert
        tanca = self.obert & (~seg | (b < t_b - 1e-9))
        self._tancar(tanca)

    def _tancar(self, tanca):
        idx = np.minimum(self.n, K_IV) - 1
        for i in range(K_IV):
            q = tanca & (idx == i)
            self.fi[i][q] = self.ultim[q]
        self.obert &= ~tanca

    def acabar(self):
        self._tancar(self.obert.copy())


def _bloc(dem, res, transform, finestra, origen, fc, hores, k0, k1, el_g, az_g, camps, pen, sortida, inici,
          radi_sol, ulls=None, pas_azimut=PAS_AZIMUT):
    r0, r1, c0, c1 = finestra
    o_r, o_c = origen                       # primera fila i columna de la finestra que es calcula (graella gruixuda)
    files_b, cols_b = r1 - r0, c1 - c0
    h_ulls = (dem if ulls is None else ulls)[r0:r1, c0:c1] + ULLS_M
    # cel·la mes propera de cada pixel (per a l'elevacio i l'azimut, que canvien ~0,01 graus per km) i
    # interpolacio bilineal dels contactes
    ri = np.minimum((np.arange(r0, r1) - o_r) // fc, el_g.shape[1] - 1)
    ci = np.minimum((np.arange(c0, c1) - o_c) // fc, el_g.shape[2] - 1)
    rr, cc = np.meshgrid((np.arange(r0, r1) - o_r + 0.5) / fc - 0.5, (np.arange(c0, c1) - o_c + 0.5) / fc - 0.5,
                         indexing='ij')

    def bilineal(camp):
        return map_coordinates(camp, [rr, cc], order=1, mode='nearest')
    sense = bilineal(np.isnan(camps['c1']).astype('f4')) > 0.5
    c1_p = np.where(sense, np.nan, bilineal(np.nan_to_num(camps['c1'], nan=np.nanmean(camps['c1']) if
                                                          (~np.isnan(camps['c1'])).any() else 0.0)))
    c4_p = np.where(sense, np.nan, bilineal(np.nan_to_num(camps['c4'], nan=np.nanmean(camps['c4']) if
                                                          (~np.isnan(camps['c4'])).any() else 0.0)))
    tmax_p = bilineal(np.nan_to_num(camps['maxim'], nan=-1e9))
    dur_g = np.nan_to_num(camps['c3'] - camps['c2'], nan=0.0)
    dur_p = bilineal(dur_g)
    hi_ha_central = bilineal((dur_g > 0).astype('f4')) > 0.5
    c2_p = np.where(hi_ha_central, tmax_p - dur_p / 2, np.nan)
    c3_p = np.where(hi_ha_central, tmax_p + dur_p / 2, np.nan)
    sl = (slice(r0 - o_r, r1 - o_r), slice(c0 - o_c, c1 - o_c))

    # direccions de l'horitzo que fan falta: l'azimut del Sol al bloc, quan hi pot haver eclipsi i Sol a sobre
    gi0, gi1, gj0, gj1 = ri[0], ri[-1] + 1, ci[0], ci[-1] + 1
    sel = slice(k0, k1 + 1)
    utils = el_g[sel, gi0:gi1, gj0:gj1] > -1.5
    if not utils.any():
        # el Sol es sota l'horitzo a tot el bloc durant tot l'eclipsi: res no es veu
        sortida['obs'][sl] = np.where(sense, SENSE, 0)
        sortida['obs_central'][sl] = np.where(hi_ha_central & ~sense, 0, SENSE)
        return
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
        xs = transform.c + (np.arange(c0, c1) + 0.5) * res
        ys = transform.f - (np.arange(r0, r1) + 0.5) * res
        pcol = (xs - tr_p.c) / tr_p.a - 0.5 - fin_p[2]
        prow = (tr_p.f - ys) / -tr_p.e - 0.5 - fin_p[0]
        PR, PC = np.meshgrid(prow, pcol, indexing='ij')
        h_pen_p = map_coordinates(dem_p[fin_p[0]:fin_p[1], fin_p[2]:fin_p[3]], [PR, PC], order=1, mode='nearest')
        finestres_lluny.append((dem_p, dem_lluny, tr_p, fin_p, PR, PC, h_pen_p))

    def llesca(j):
        """Tangent de l'horitzo a l'azimut j * pas_azimut (relleu proper i, si n'hi ha, llunya)."""
        if j not in llesques:
            a = (j * pas_azimut) % 360.0
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

    forma = (files_b, cols_b)
    llindars = (-radi_sol, radi_sol)            # alguna part del Sol lliure; el Sol sencer lliure
    ivs = [_Intervals(forma) for _ in llindars]
    mmax = np.full(forma, np.nan, 'f4')
    m_ant, t_ant = None, None
    finestra_t = (np.nanmin(c1_p) if np.isfinite(c1_p).any() else np.inf,
                  np.nanmax(c4_p) if np.isfinite(c4_p).any() else -np.inf)
    for k in range(k0, k1 + 1):
        t = hores[k]
        if t < finestra_t[0] - 1 / 60 or t > finestra_t[1] + 1 / 60:
            m_ant, t_ant = None, None                     # fora de l'eclipsi de tot el bloc
            continue
        el = el_g[k][np.ix_(ri, ci)]
        if (el < -1.5).all():
            m = el - 1.0      # el Sol es sota l'horitzo a tot el bloc: no cal mirar el relleu
        else:
            az = az_g[k][np.ix_(ri, ci)] / pas_azimut
            j0 = np.floor(az).astype(int)
            w = az - j0
            m = np.empty_like(el)
            for j in np.unique(j0):
                q = j0 == j
                m[q] = el[q] - (llesca(j)[q] * (1 - w[q]) + llesca(j + 1)[q] * w[q])
        if m_ant is not None:
            for iv, ll in zip(ivs, llindars):
                iv.pas(t_ant, t, m_ant - ll, m - ll, c1_p, c4_p, c2_p, c3_p)
            # el maxim cau entre els dos minuts: el marge s'interpola
            mx = (tmax_p >= t_ant) & (tmax_p < t)
            mmax[mx] = (m_ant + (m - m_ant) * (tmax_p - t_ant) / (t - t_ant))[mx]
        m_ant, t_ant = m, t
    for iv in ivs:
        iv.acabar()

    durada = (c4_p - c1_p)
    obs = np.where(sense | ~(durada > 0), SENSE, np.clip(np.round(ivs[0].acum / np.where(durada > 0, durada, 1) * FRAC),
                                                          0, FRAC))
    sortida['obs'][sl] = obs
    dc = c3_p - c2_p
    sortida['obs_central'][sl] = np.where(hi_ha_central & ~sense & (dc > 0),
                                          np.clip(np.round(ivs[0].acum_c / np.where(dc > 0, dc, 1) * FRAC), 0, FRAC),
                                          SENSE)
    sortida['marge'][sl] = np.where(np.isnan(mmax), SENSE_MARGE, np.clip(np.round(mmax * 100), -32000, 32000))
    for li, iv in enumerate(ivs):
        for i in range(K_IV):
            for e, v in enumerate((iv.ini[i], iv.fi[i])):
                sortida['iv'][li, i, e][sl] = np.where(np.isnan(v), SENSE, np.clip(np.round((v - inici) * 3600), 0,
                                                                                    SENSE - 1))
        sortida['n_iv'][li][sl] = np.minimum(iv.n, 255)


class Cancelat(Exception):
    """El calcul s'ha aturat perque ja no cal (Calcul.cancel)."""


class Calcul:
    """llegir() o, si no hi es, calcular() en un fil. El fil principal llegeix estat i, quan fet es True,
    resultat (dict) o error. Els objectes OpenGL els crea el fil principal (Terrain.posar_visibilitat).
    preparar: funcio (avis) que es crida abans, al mateix fil, si la visibilitat no es al disc (p. ex. fer la
    superficie dels obstacles d'un mapa de detall, dades/alcaries.preparar_superficie); lluny i cami_ulls, com a
    calcular()."""

    def __init__(self, cami_mdt, clau, cami_peninsula=None, nomes_llegir=False, lluny=None, cami_ulls=None,
                 preparar=None, rect=None, pas_azimut=PAS_AZIMUT):
        import threading
        self.cami, self.clau, self.nomes_llegir, self.rect = cami_mdt, clau, nomes_llegir, rect
        self.pas_azimut = pas_azimut
        self.lluny, self.cami_ulls, self.preparar = lluny, cami_ulls, preparar
        self.estat, self.fet, self.resultat, self.error = 'Llegint...', False, None, None
        self.cancelat = False
        self.fil = threading.Thread(target=self._executar, args=(cami_peninsula,), daemon=True)
        self.fil.start()

    def _executar(self, cami_peninsula):
        try:
            if self.preparar is not None:
                self.preparar(self._avis)
            self.resultat = llegir(self.cami, self.clau, self.rect, self.pas_azimut) if os.path.exists(self.cami) else None
            if self.resultat is None and not self.nomes_llegir:
                self.resultat = calcular(self.cami, self.clau, cami_peninsula, self._avis, lluny=self.lluny,
                                         cami_ulls=self.cami_ulls, rect=self.rect, pas_azimut=self.pas_azimut)
        except Cancelat:
            self.error = 'cancel·lat'
        except Exception as e:   # noqa: BLE001 (es mostra al panell)
            self.error = f'{e.__class__.__name__}: {e}'
            if not self.cancelat:   # (un calcul cancel·lat pot acabar amb un error en tancar el programa)
                print(f'AVIS: no s\'ha pogut calcular la visibilitat: {self.error}')
        self.fet = True

    def _avis(self, text):
        if self.cancelat:
            raise Cancelat()
        self.estat = text

    def cancel(self):
        """Atura el calcul despres del bloc en curs (el terreny ja no es veu): no queda res desat."""
        self.cancelat = True


# ------------------------------------------------------------ 4. circumstancies en una graella (mapes de la Lluna)

PAS_GRAELLA_LLUNA_M = 2000.0       # la part tapada i la durada de la fase central varien ~0,1 % i ~1 s per km
VERSIO_GRAELLA = 1


def cami_graella(clau):
    return os.path.join(data_io.DIR_CACHE, f'circumstancies_{clau}_peninsula.npz')


def graella_circumstancies(clau, cami_mdt, avis=print):
    """Mapes de la Lluna (ocultacio al maxim i recorregut de la fase central) en una graella UTM de
    PAS_GRAELLA_LLUNA_M sobre l'extensio del MDT (la peninsula), a l'altitud 0 (la variacio amb l'altitud del terra es
    de ~1 s i ~0,01 % per km d'altura, menys que la cel·la). Es desa a data/cache/circumstancies_<clau>_peninsula.npz.
    Camps (float32, NaN sense eclipsi): tapat_max (0-1), central (segons de fase central, 0 si no n'hi ha), c1, c4,
    maxim (hores TU); transform i crs de la graella."""
    import rasterio
    cami = cami_graella(clau)
    if os.path.exists(cami):
        with np.load(cami) as z:
            if int(z['versio']) == VERSIO_GRAELLA:
                return {k: z[k] for k in z.files}
    with rasterio.open(cami_mdt) as f:
        b, crs = f.bounds, f.crs
    pas = PAS_GRAELLA_LLUNA_M
    cols, files = int(math.ceil((b.right - b.left) / pas)), int(math.ceil((b.top - b.bottom) / pas))
    xs = b.left + (np.arange(cols) + 0.5) * pas
    ys = b.top - (np.arange(files) + 0.5) * pas
    X, Y = np.meshgrid(xs, ys)
    lon, lat = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform(X.ravel(), Y.ravel())
    conv = np.asarray(Proj(crs.to_string()).get_factors(lon, lat).meridian_convergence)
    avis(f'Circumstancies de l\'eclipsi {clau} ({files} x {cols} punts)...')
    c = circumstancies(np.asarray(lat), np.asarray(lon), np.zeros(len(lat)), conv, efemerides(clau))
    r = dict(versio=np.array(VERSIO_GRAELLA), clau=np.array(clau),
             transform=np.array((pas, 0.0, b.left, 0.0, -pas, b.top)), crs=np.array(crs.to_string()),
             radi_sol=np.array(c['radi_sol']))
    for k in ('tapat_max', 'c1', 'c4', 'maxim'):
        r[k] = c[k].reshape(files, cols).astype('f4')
    r['central'] = np.where(np.isnan(c['c1']), np.nan, np.nan_to_num((c['c3'] - c['c2']) * 3600.0, nan=0.0)) \
        .reshape(files, cols).astype('f4')
    os.makedirs(data_io.DIR_CACHE, exist_ok=True)
    np.savez_compressed(cami + '.tmp.npz', **r)
    os.replace(cami + '.tmp.npz', cami)
    return r
