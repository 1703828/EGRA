"""
Compara les altures dels edificis estimades amb el Catastro (plantes x 3 m, dades/edificis.py) amb les mesurades
pel LiDAR de l'ICGC (scripts/descarregar_lidar.py), i el terra del LiDAR amb el MDT de 5 m de l'IGN.

1. Edificis: per a cada part del Catastro que cau sencera dins del LiDAR (reprojectada de EPSG:25830 a
   EPSG:25831, el CRS del LiDAR), l'altura mesurada = el percentil 90 de la cota dels punts d'edifici dins del
   contorn (sense els 0,5 m de la vora: les facanes i els contorns no coincideixen al centimetre) menys la
   mediana del terra en una franja de 2 a 6 m al voltant del contorn. El percentil 90 i no el maxim: una
   xemeneia o una antena no son l'altura de la coberta. Es compara amb plantes x 3 m.
2. Terra: la cota del terra del LiDAR (mitjana de la classe 2 a cada metre) contra el MDT de 5 m de l'IGN al
   mateix punt (bilineal, reprojectat). Tots dos son cotes sobre el nivell del mar (si no ho fossin, hi hauria
   una diferencia constant d'uns 50 m: l'ondulacio del geoide).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/comparar_altures.py [uab]
"""
import json
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import shapely  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402

from dades.edificis import llegir_zona, ALCADA_PLANTA_M  # noqa: E402

DIR = os.path.join(ARREL, 'data', 'lidar')
ZONA_EDIFICIS = {'uab': 'valles'}
MDT = {'uab': os.path.join(ARREL, 'data', 'mdt', 'zones', 'valles_5m.tif')}


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else 'uab'
    with rasterio.open(os.path.join(DIR, f'{nom}_edificis_1m.tif')) as f:
        edif, tr, crs = f.read(1), f.transform, f.crs
    with rasterio.open(os.path.join(DIR, f'{nom}_terra_1m.tif')) as f:
        terra = f.read(1)
    meta = json.load(open(os.path.join(DIR, f'{nom}.json')))
    x0, y0, x1, y1 = meta['limits']

    print('== 1. Altures dels edificis: Catastro (plantes x 3 m) contra LiDAR')
    parts = llegir_zona(ZONA_EDIFICIS[nom]).to_crs(crs.to_string())
    caixa = shapely.box(x0 + 10, y0 + 10, x1 - 10, y1 - 10)
    parts = parts[parts.within(caixa)]
    files = []
    for geom, plantes in zip(parts.geometry, parts['plantes']):
        if geom.area < 30:
            continue
        dins = geom.buffer(-0.5)
        if dins.is_empty:
            continue
        a, b, c, d = geom.buffer(7).bounds
        c0, r0 = ~tr * (a, d)
        c1, r1 = ~tr * (c, b)
        c0, r0, c1, r1 = int(c0), int(r0), int(np.ceil(c1)), int(np.ceil(r1))
        tr_w = tr * rasterio.Affine.translation(c0, r0)
        forma = (r1 - r0, c1 - c0)
        m_dins = ~geometry_mask([dins], forma, tr_w)
        m_anell = ~geometry_mask([geom.buffer(6).difference(geom.buffer(2))], forma, tr_w)
        e, t = edif[r0:r1, c0:c1][m_dins], terra[r0:r1, c0:c1][m_anell]
        e, t = e[np.isfinite(e)], t[np.isfinite(t)]
        if len(e) < 0.5 * m_dins.sum() or len(t) < 5:
            continue      # el LiDAR no hi veu prou edifici (pati, porxo, construccio nova) o no hi ha terra al voltant
        files.append((plantes, float(np.percentile(e, 90) - np.median(t)), geom.area))
    pl, h, area = (np.array(v) for v in zip(*files))
    est = pl * ALCADA_PLANTA_M
    dif = est - h
    print(f'{len(files)} parts amb prou punts d\'edifici (de {len(parts)} dins del LiDAR)')
    print(f'  estimada - mesurada: mediana {np.median(dif):+.1f} m, error absolut mitja {np.abs(dif).mean():.1f} m, '
          f'dins de +-1,5 m: {(np.abs(dif) <= 1.5).mean() * 100:.0f} %, dins de +-3 m: {(np.abs(dif) <= 3).mean() * 100:.0f} %')
    print(f'  pitjors: estimada {est[np.argmax(np.abs(dif))]:.0f} m, mesurada {h[np.argmax(np.abs(dif))]:.1f} m')
    print('  plantes   parts   altura mesurada (mediana, p10-p90)   metres per planta (mediana)')
    for p in sorted(set(pl.tolist())):
        q = pl == p
        if q.sum() >= 5:
            print(f'  {int(p):6d}  {q.sum():6d}   {np.median(h[q]):6.1f} m ({np.percentile(h[q], 10):5.1f} - '
                  f'{np.percentile(h[q], 90):5.1f})              {np.median(h[q] / p):.2f}')

    print('\n== 2. Terra: LiDAR (ICGC) contra el MDT de 5 m (IGN)')
    with rasterio.open(MDT[nom]) as f:
        mdt, trm, crsm = f.read(1), f.transform, f.crs
    files_t, cols_t = np.nonzero(np.isfinite(terra))
    sel = np.random.default_rng(0).choice(len(files_t), size=min(200000, len(files_t)), replace=False)
    xs, ys = tr * (cols_t[sel] + 0.5, files_t[sel] + 0.5)
    xm, ym = Transformer.from_crs(crs, crsm, always_xy=True).transform(np.asarray(xs), np.asarray(ys))
    cm, rm = (np.asarray(xm) - trm.c) / trm.a - 0.5, (trm.f - np.asarray(ym)) / -trm.e - 0.5
    d = terra[files_t[sel], cols_t[sel]] - map_coordinates(mdt, [rm, cm], order=1)
    print(f'  LiDAR - MDT: mediana {np.median(d):+.2f} m, p5 a p95 {np.percentile(d, 5):+.2f} a '
          f'{np.percentile(d, 95):+.2f} m ({len(d):,} punts de terra)')


if __name__ == '__main__':
    main()
