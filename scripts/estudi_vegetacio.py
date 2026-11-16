"""
Estudi de dades per a la vegetacio dibuixada amb un geometry shader (tasques 45.1 i 45.2 del pla).

Dades: els rasters d'1 m del LiDAR de l'ICGC a la UAB (scripts/descarregar_lidar.py; EPSG:25831): superficie (MDS,
el punt mes alt de cada metre), terra i edificis (classe 6 de l'ASPRS). Els fitxers LAS originals, amb les classes
de vegetacio, no es van conservar (2,8 GB). Alcaria de la vegetacio (CHM) = MDS - terra fora dels edificis: inclou
tot el que no es edifici ni terra (arbres, pero tambe pals, cotxes o tanques).

45.1  Hi ha arbres individuals? Es busquen capcades: maxims locals del CHM suavitzat (finestra de 5 m, alcaria
      >= 3 m) i, per a cada una, el radi on el CHM baixa a la meitat (mediana de 8 direccions). Es mesura quina part de
      la vegetacio queda dins de capcades aillades (cercles que no se'n toquen d'altres) i quina son masses
      continues (bosc), i es desen captures de 4 llocs amb la fotografia aeria al costat per comparar-les.
45.2  Coherencia amb la visibilitat: horitzo cada 0,25 graus de 260 a 300 graus (la posta del 2026) des de punts del
      carrer, amb la superficie mesurada i amb la superficie on la vegetacio se substitueix per les formes
      simplificades (con de radi r i alcaria h, el que dibuixaria el shader). Diferencia en graus: si es menor que el
      radi del Sol (0,27 graus), dibuixar-les no canvia el que es veu del Sol; si no, el dibuix es nomes una
      aproximacio visual i el calcul continua amb la superficie mesurada (D94).
Captures a captures/proves/vegetacio_*.png.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/estudi_vegetacio.py
"""
import math
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage  # noqa: E402

LIDAR = os.path.join(ARREL, 'data', 'lidar')
SORTIDA = os.path.join(ARREL, 'captures', 'proves')
H_MIN = 3.0           # alcaria minima d'un arbre (m)
FINESTRA = 5          # m: finestra dels maxims locals
R_MAX = 12.0


def capcades(chm):
    """Maxims locals (files, cols, alcaria) i radi de cada capcada (m)."""
    s = ndimage.gaussian_filter(np.nan_to_num(chm), 1.0)
    maxs = (s == ndimage.maximum_filter(s, size=FINESTRA)) & (s >= H_MIN)
    f, c = np.nonzero(maxs)
    h = s[f, c]
    dirs = [(math.cos(a), math.sin(a)) for a in np.radians(np.arange(0, 360, 45))]
    radis = np.zeros(len(f))
    for k in range(len(f)):
        rs = []
        for dx, dy in dirs:
            r = 0
            for d in range(1, int(R_MAX) + 1):
                ff, cc = int(round(f[k] - d * dy)), int(round(c[k] + d * dx))
                if not (0 <= ff < s.shape[0] and 0 <= cc < s.shape[1]) or s[ff, cc] < 0.5 * h[k]:
                    break
                r = d
            rs.append(r + 0.5)
        radis[k] = np.median(rs)
    return f, c, h, radis


def horitzo_local(sup, f0, c0, h_ulls, azimuts, dist_max=400):
    """Elevacio (graus) de l'horitzo proper (fins a dist_max m) per a cada azimut de quadricula, cada 0,5 m."""
    out = []
    ds = np.arange(1.0, dist_max, 0.5)
    for az in azimuts:
        dc, dr = math.sin(math.radians(az)), -math.cos(math.radians(az))
        ff, cc = f0 + ds * dr, c0 + ds * dc
        ok = (ff >= 0) & (ff < sup.shape[0] - 1) & (cc >= 0) & (cc < sup.shape[1] - 1)
        h = ndimage.map_coordinates(sup, [ff[ok], cc[ok]], order=1)
        out.append(np.degrees(np.arctan((h - h_ulls) / ds[ok])).max() if ok.any() else -90.0)
    return np.array(out)


def main():
    with rasterio.open(os.path.join(LIDAR, 'uab_mds_1m.tif')) as f:
        mds, tr = f.read(1), f.transform
    terra = rasterio.open(os.path.join(LIDAR, 'uab_terra_1m.tif')).read(1)
    edif = rasterio.open(os.path.join(LIDAR, 'uab_edificis_1m.tif')).read(1)
    # cel·les sense punts de terra (sota els edificis): el terra mes proper
    _, (fi, ci) = ndimage.distance_transform_edt(~np.isfinite(terra), return_indices=True)
    terra = terra[fi, ci]
    es_edifici = ndimage.binary_dilation(np.isfinite(edif), iterations=1)
    chm = np.where(es_edifici, 0.0, np.nan_to_num(mds - terra))
    veg = chm >= 2.0
    print(f'Area: {mds.shape[1]} x {mds.shape[0]} m; vegetacio (>= 2 m, fora dels edificis): '
          f'{veg.mean() * 100:.1f} % de l\'area', flush=True)

    # 45.1
    f, c, h, r = capcades(chm)
    print(f'capcades detectades: {len(f)}; alcaria mediana {np.median(h):.1f} m (p10 {np.percentile(h, 10):.1f}, '
          f'p90 {np.percentile(h, 90):.1f}); radi mediana {np.median(r):.1f} m (p10 {np.percentile(r, 10):.1f}, '
          f'p90 {np.percentile(r, 90):.1f})', flush=True)
    # capcades aillades: el seu cercle no toca cap altre cercle
    from scipy.spatial import cKDTree
    arbre = cKDTree(np.column_stack([f, c]))
    parells = arbre.query_pairs(2 * R_MAX)
    toca = np.zeros(len(f), bool)
    for i, j in parells:
        if math.hypot(f[i] - f[j], c[i] - c[j]) < r[i] + r[j]:
            toca[i] = toca[j] = True
    print(f'capcades aillades (el cercle no en toca cap altre): {(~toca).sum()} ({(~toca).mean() * 100:.0f} %)')
    # masses continues: components de vegetacio > 400 m2 amb mes de 5 capcades
    etiq, n = ndimage.label(veg)
    mides = ndimage.sum(veg, etiq, range(1, n + 1))
    per_comp = np.bincount(etiq[f, c], minlength=n + 1)[1:]
    grans = (mides > 400) & (per_comp > 5)
    area_massa = mides[grans].sum() / max(veg.sum(), 1)
    print(f'vegetacio en masses continues (> 400 m2 i > 5 capcades): {area_massa * 100:.0f} % de l\'area vegetal; '
          f'en {grans.sum()} masses', flush=True)

    # 45.2: superficie amb les formes simplificades (cons) contra la mesurada
    con = np.zeros_like(chm)
    yy, xx = np.mgrid[0:chm.shape[0], 0:chm.shape[1]]
    for k in range(len(f)):
        rr = int(math.ceil(r[k]))
        a0, a1, b0, b1 = max(f[k] - rr, 0), min(f[k] + rr + 1, chm.shape[0]), max(c[k] - rr, 0), min(c[k] + rr + 1,
                                                                                                    chm.shape[1])
        d = np.hypot(yy[a0:a1, b0:b1] - f[k], xx[a0:a1, b0:b1] - c[k])
        con[a0:a1, b0:b1] = np.maximum(con[a0:a1, b0:b1], np.where(d <= r[k], h[k] * (1 - d / (r[k] + 1e-6)), 0))
    base = np.nan_to_num(terra) + np.where(np.isfinite(edif), np.nan_to_num(mds - terra), 0.0)
    sup_real = np.nan_to_num(mds)
    sup_formes = np.maximum(base, np.nan_to_num(terra) + con)
    rng = np.random.default_rng(7)
    lliures = np.argwhere(~veg & ~es_edifici)
    lliures = lliures[(lliures[:, 0] > 450) & (lliures[:, 0] < mds.shape[0] - 450) & (lliures[:, 1] > 450)
                      & (lliures[:, 1] < mds.shape[1] - 450)]
    mostra = lliures[rng.choice(len(lliures), 20, replace=False)]
    azimuts = np.arange(260.0, 300.0, 0.25)
    difs, punts_afectats = [], 0
    for f0, c0 in mostra:
        hu = float(np.nan_to_num(terra[f0, c0])) + 1.7
        a = horitzo_local(sup_real, f0, c0, hu, azimuts)
        b = horitzo_local(sup_formes, f0, c0, hu, azimuts)
        d = np.abs(a - b)
        difs.append(d)
        punts_afectats += int((d > 0.27).any())
    difs = np.concatenate(difs)
    print(f'horitzo a la posta (260-300 graus, 20 punts del carrer, fins a 400 m): diferencia formes - mesurat '
          f'mediana {np.median(difs):.2f} graus, 90 % {np.percentile(difs, 90):.2f}, maxima {difs.max():.1f}; '
          f'{punts_afectats} de 20 punts amb alguna direccio > 0,27 graus (radi del Sol)', flush=True)

    # captures: 4 llocs de 160 x 160 m (CHM amb les capcades i la fotografia aeria)
    try:
        captures(mds, chm, f, c, r, tr)
    except Exception as e:   # noqa: BLE001 (sense xarxa, sense fotografia)
        print(f'(captures sense fotografia: {e})')
    return 0


def captures(mds, chm, f, c, r, tr):
    from PIL import Image, ImageDraw
    import requests
    from pyproj import Transformer
    from dades import teselles
    os.makedirs(SORTIDA, exist_ok=True)
    a_ll = Transformer.from_crs('EPSG:25831', 'EPSG:4326', always_xy=True)
    sessio = requests.Session()
    llocs = [(mds.shape[0] // 2, mds.shape[1] // 2), (800, 800), (2000, 1200), (1200, 2200)]
    for n, (f0, c0) in enumerate(llocs):
        m = 80
        tros = np.clip(chm[f0 - m:f0 + m, c0 - m:c0 + m] / 25.0, 0, 1)
        im = Image.fromarray((np.stack([tros] * 3, -1) * 255).astype('u1')).resize((480, 480), Image.NEAREST)
        dib = ImageDraw.Draw(im)
        k = 3.0
        for ff, cc, rr in zip(f, c, r):
            if abs(ff - f0) < m and abs(cc - c0) < m:
                x, y = (cc - c0 + m) * k, (ff - f0 + m) * k
                dib.ellipse([x - rr * k, y - rr * k, x + rr * k, y + rr * k], outline=(255, 60, 60))
        # fotografia aeria del mateix quadrat (PNOA, z = 19)
        x0, y0 = tr * (c0 - m, f0 - m)
        x1, y1 = tr * (c0 + m, f0 + m)
        lo0, la0 = a_ll.transform(x0, y0)
        lo1, la1 = a_ll.transform(x1, y1)
        z = 19
        X0, Y0 = teselles.mercator(la0, lo0)
        X1, Y1 = teselles.mercator(la1, lo1)
        n_t = 2 ** z
        tx0, tx1, ty0, ty1 = int(X0 * n_t), int(X1 * n_t), int(Y0 * n_t), int(Y1 * n_t)
        mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), 'u1')
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = \
                    teselles.tesella(z, tx, ty, sessio)
        px0, py0 = (X0 * n_t - tx0) * 256, (Y0 * n_t - ty0) * 256
        px1, py1 = (X1 * n_t - tx0) * 256, (Y1 * n_t - ty0) * 256
        foto = Image.fromarray(mosaic).crop((int(px0), int(py0), int(px1), int(py1))).resize((480, 480))
        tot = Image.new('RGB', (960, 480))
        tot.paste(im, (0, 0))
        tot.paste(foto, (480, 0))
        tot.save(os.path.join(SORTIDA, f'vegetacio_{n}.png'))
    print(f'captures: {SORTIDA}/vegetacio_*.png (esquerra: alcaria de la vegetacio i capcades; dreta: PNOA)')


if __name__ == '__main__':
    sys.exit(main())
