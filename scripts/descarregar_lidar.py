"""
Descarrega el LiDAR territorial de l'ICGC (3a cobertura, 2021-2023) al voltant d'un punt i en fa rasters d'1 m:
altures mesurades (no estimades) dels edificis, els arbres i el terra (objectiu O3, F27; D81).

Font: Institut Cartografic i Geologic de Catalunya (ICGC), LiDAR territorial v3r1 2021-2023, fulls d'1 x 1 km en LAZ
(nuvol de punts LAS 1.4 classificat segons l'ASPRS, >= 8 punts/m2), EPSG:25831.
  Index de fulls: https://datacloud.icgc.cat/datacloud/lidar-territorial/json/lidar-territorial-tall.json
  Fitxers: https://datacloud.icgc.cat/datacloud/lidar-territorial/laz_unzip/full10km<ID10K>/
           lidar-territorial-v3r1-full1km<ID1K>-2021-2023.laz
Llicencia: CC BY 4.0 (ICGC).

Cada full (280-470 MB) es baixa, es converteix i s'esborra abans de baixar el seguent: al disc nomes queden els
rasters. Per a cada cel·la d'1 x 1 m (graella alineada amb els fulls, EPSG:25831, sense reprojectar):
  mds       la cota mes alta de tots els punts que no son soroll (classes 7 i 18): edificis, arbres i terra
  terra     la mitjana de la cota dels punts de terra (classe 2); NaN on no n'hi ha (sota els edificis)
  edificis  la cota mes alta dels punts d'edifici (classe 6); NaN on no n'hi ha
Cotes en metres, les del fitxer (vegeu el sistema vertical que s'imprimeix de la capcalera). Sortida:
data/lidar/<nom>_{mds,terra,edificis}_1m.tif (GeoTIFF float32, comprimit) i <nom>.json (fulls, punts, dates).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/descarregar_lidar.py uab
"""
import json
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import requests  # noqa: E402

DIR = os.path.join(ARREL, 'data', 'lidar')       # ignorada pel Git
URL_INDEX = 'https://datacloud.icgc.cat/datacloud/lidar-territorial/json/lidar-territorial-tall.json'
URL_FULL = ('https://datacloud.icgc.cat/datacloud/lidar-territorial/laz_unzip/full10km{id10}/'
            'lidar-territorial-v3r1-full1km{id1}-2021-2023.laz')
CRS = 'EPSG:25831'
RES = 1.0
SOROLL = (7, 18)
# zones: centre (lat, lon) i costat del quadrat (km)
ZONES = {'uab': dict(centre=(41.5022, 2.1042), costat_km=3)}   # 3 x 3 fulls, centrats a la placa Civica


def fulls(lat, lon, costat_km):
    """(ID1K, ID10K, x0, y0) dels costat_km x costat_km fulls (senar) centrats en el full que conte el punt."""
    import math
    from pyproj import Transformer
    x, y = Transformer.from_crs('EPSG:4326', CRS, always_xy=True).transform(lon, lat)
    cx, cy = math.floor(x / 1000) * 1000, math.floor(y / 1000) * 1000      # cantonada SO del full central
    m = (costat_km // 2) * 1000
    index = requests.get(URL_INDEX, timeout=120).json()
    out = []
    for f in index['features']:
        x0 = min(p[0] for p in f['geometry']['coordinates'][0])
        y0 = min(p[1] for p in f['geometry']['coordinates'][0])
        if cx - m <= x0 <= cx + m and cy - m <= y0 <= cy + m:
            out.append((f['properties']['ID1K'], f['properties']['ID10K'], x0, y0))
    return sorted(out, key=lambda f: (-f[3], f[2]))


def rasteritzar(cami, x0, y0, mida=1000):
    """Els tres rasters (fila 0 = nord) d'un full d'1 km amb la cantonada sud-oest a (x0, y0)."""
    import laspy
    n = int(mida / RES)
    mds = np.full(n * n, -np.inf, 'f4')
    edif = np.full(n * n, -np.inf, 'f4')
    suma, compte = np.zeros(n * n, 'f8'), np.zeros(n * n, 'i4')
    info = {}
    with laspy.open(cami) as f:
        info['punts'] = int(f.header.point_count)
        info['crs'] = str(f.header.parse_crs()) if f.header.parse_crs() is not None else None
        for punts in f.chunk_iterator(5_000_000):
            x, y, z = np.asarray(punts.x), np.asarray(punts.y), np.asarray(punts.z, dtype='f4')
            cl = np.asarray(punts.classification)
            col = np.floor((x - x0) / RES).astype(int)
            fila = np.floor((y0 + mida - y) / RES).astype(int)
            dins = (col >= 0) & (col < n) & (fila >= 0) & (fila < n) & ~np.isin(cl, SOROLL)
            idx, z, cl = fila[dins] * n + col[dins], z[dins], cl[dins]
            np.maximum.at(mds, idx, z)
            e = cl == 6
            np.maximum.at(edif, idx[e], z[e])
            t = cl == 2
            np.add.at(suma, idx[t], z[t])
            np.add.at(compte, idx[t], 1)
    terra = np.where(compte > 0, suma / np.maximum(compte, 1), np.nan).astype('f4')
    mds[np.isinf(mds)] = np.nan
    edif[np.isinf(edif)] = np.nan
    return mds.reshape(n, n), terra.reshape(n, n), edif.reshape(n, n), info


def desar(cami, dades, x0, ymax):
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(cami + '.tmp', 'w', driver='GTiff', height=dades.shape[0], width=dades.shape[1], count=1,
                       dtype='float32', crs=CRS, transform=from_origin(x0, ymax, RES, RES), nodata=np.nan,
                       compress='deflate', predictor=3, tiled=True) as f:
        f.write(dades, 1)
    os.replace(cami + '.tmp', cami)


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else 'uab'
    z = ZONES[nom]
    os.makedirs(DIR, exist_ok=True)
    llista = fulls(*z['centre'], z['costat_km'])
    xs, ys = sorted({f[2] for f in llista}), sorted({f[3] for f in llista})
    x0, ymax = xs[0], ys[-1] + 1000
    n_c, n_f = len(xs), len(ys)
    capes = {k: np.full((n_f * 1000, n_c * 1000), np.nan, 'f4') for k in ('mds', 'terra', 'edificis')}
    meta = dict(font='ICGC, LiDAR territorial v3r1 2021-2023 (CC BY 4.0)', crs=CRS, resolucio_m=RES,
                data_descarrega=time.strftime('%Y-%m-%d'), fulls=[])
    print(f'{nom}: {len(llista)} fulls ({n_c} x {n_f} km)')
    for i, (id1, id10, fx, fy) in enumerate(llista):
        url = URL_FULL.format(id1=id1, id10=id10)
        tmp = os.path.join(DIR, f'{id1}.laz')
        t0 = time.time()
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(tmp, 'wb') as f:
                for tros in r.iter_content(1 << 20):
                    f.write(tros)
        mida = os.path.getsize(tmp)
        t1 = time.time()
        try:
            mds, terra, edif, info = rasteritzar(tmp, fx, fy)
        finally:
            os.remove(tmp)            # el LAZ no es guarda
        c, f_ = xs.index(fx), n_f - 1 - ys.index(fy)
        for k, v in (('mds', mds), ('terra', terra), ('edificis', edif)):
            capes[k][f_ * 1000:(f_ + 1) * 1000, c * 1000:(c + 1) * 1000] = v
        meta['fulls'].append(dict(id1k=id1, url=url, mida_bytes=mida, punts=info['punts'], crs_capcalera=info['crs'],
                                  cel_les_edifici=int(np.isfinite(edif).sum())))
        print(f'  [{i + 1}/{len(llista)}] full {id1}: {mida / 1e6:.0f} MB en {t1 - t0:.0f} s, {info["punts"]:,} punts, '
              f'rasteritzat en {time.time() - t1:.0f} s, {np.isfinite(edif).mean() * 100:.0f} % amb edifici', flush=True)
        if i == 0:
            print(f'     CRS de la capcalera: {info["crs"]}')
    for k, v in capes.items():
        desar(os.path.join(DIR, f'{nom}_{k}_1m.tif'), v, x0, ymax)
    meta['limits'] = [x0, ymax - n_f * 1000, x0 + n_c * 1000, ymax]
    with open(os.path.join(DIR, f'{nom}.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print(f'Desat a {DIR}: ' + ', '.join(f'{nom}_{k}_1m.tif ({os.path.getsize(os.path.join(DIR, f"{nom}_{k}_1m.tif")) / 1e6:.0f} MB)'
                                          for k in capes))


if __name__ == '__main__':
    main()
