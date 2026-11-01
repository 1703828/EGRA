"""
Comprova les altures mesurades dels edificis (dades/alcaries.py) a la UAB, on hi ha tres mesures de les mateixes
parts del Catastro:
  A. nuvol de punts LiDAR de l'ICGC (scripts/descarregar_lidar.py; metode de scripts/comparar_altures.py:
     percentil 90 dels punts d'edifici menys el terra del voltant);
  B. model d'alcaries de l'ICGC (1 m, 2021-2023), llegit per finestres del COG (dades/alcaries.py);
  C. MDS normalitzat de l'IGN (2,5 m, PNOA-LiDAR 2008-2015, WCS).
A i B surten del mateix vol LiDAR: han de coincidir gairebe del tot (comprova la lectura del COG, la reprojeccio i
el calcul per part). C es d'un altre vol i d'una altra resolucio: la diferencia mesura quant canvia la font (no es
un error del programa). Es compara tambe amb l'estimacio plantes x 3 m.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/validar_alcaries.py
(Baixa ~5 MB de l'ICGC i ~25 MB de l'IGN; dues o tres minuts.)
"""
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import shapely  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402

from dades import alcaries  # noqa: E402
from dades.edificis import llegir_zona, ALCADA_PLANTA_M  # noqa: E402

DIR_LIDAR = os.path.join(ARREL, 'data', 'lidar')
COSTAT_M = 2000.0           # quadrat de prova, centrat a la placa Civica (dins del LiDAR de 3 x 3 km)


def nuvol_de_punts(parts):
    """Altura de cada part amb els rasters del nuvol de punts (EPSG:25831), com scripts/comparar_altures.py."""
    with rasterio.open(os.path.join(DIR_LIDAR, 'uab_edificis_1m.tif')) as f:
        edif, tr, crs = f.read(1), f.transform, f.crs
    with rasterio.open(os.path.join(DIR_LIDAR, 'uab_terra_1m.tif')) as f:
        terra = f.read(1)
    p31 = parts.to_crs(crs.to_string())
    h = np.full(len(parts), np.nan)
    for i, geom in enumerate(p31.geometry):
        dins = geom.buffer(-0.5)
        if geom.area < 30 or dins.is_empty:
            continue
        a, b, c, d = geom.buffer(7).bounds
        c0, r0 = ~tr * (a, d)
        c1, r1 = ~tr * (c, b)
        c0, r0, c1, r1 = int(c0), int(r0), int(np.ceil(c1)), int(np.ceil(r1))
        if c0 < 0 or r0 < 0 or r1 > edif.shape[0] or c1 > edif.shape[1]:
            continue
        tr_w = tr * rasterio.Affine.translation(c0, r0)
        forma = (r1 - r0, c1 - c0)
        m_dins = ~geometry_mask([dins], forma, tr_w)
        m_anell = ~geometry_mask([geom.buffer(6).difference(geom.buffer(2))], forma, tr_w)
        e, t = edif[r0:r1, c0:c1][m_dins], terra[r0:r1, c0:c1][m_anell]
        e, t = e[np.isfinite(e)], t[np.isfinite(t)]
        if len(e) >= 0.5 * m_dins.sum() and len(t) >= 5:
            h[i] = float(np.percentile(e, 90) - np.median(t))
    return h


def resum(nom, a, b, area):
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    print(f'  {nom}: {ok.sum()} parts amb totes dues; diferencia mediana {np.median(d):+.2f} m, error absolut mitja '
          f'{np.abs(d).mean():.2f} m, dins de +-1 m {np.mean(np.abs(d) <= 1) * 100:.0f} %, dins de +-3 m '
          f'{np.mean(np.abs(d) <= 3) * 100:.0f} %; ponderat per area, dins de +-1 m '
          f'{np.sum(area[ok][np.abs(d) <= 1]) / np.sum(area[ok]) * 100:.0f} %')
    return d


def main():
    from pyproj import Transformer
    x, y = Transformer.from_crs('EPSG:4326', alcaries.CRS, always_xy=True).transform(2.1039, 41.5019)
    m = COSTAT_M / 2
    rect = (round(x - m), round(y - m), round(x + m), round(y + m))
    parts = llegir_zona('valles')
    parts = parts[parts.within(shapely.box(*rect)) & (parts.geometry.area >= 30)].reset_index(drop=True)
    print(f'== Altures de {len(parts)} parts del Catastro (>= 30 m2) en un quadrat de {COSTAT_M / 1000:.0f} km a la UAB')
    area = parts.geometry.area.to_numpy()
    h_a = nuvol_de_punts(parts)
    print(f'A. nuvol de punts (ICGC): {np.isfinite(h_a).sum()} parts mesurades')
    icgc = alcaries._icgc(rect, avis=lambda t: None)
    h_b, cob_b = alcaries.alcades_parts(parts, icgc)
    print(f'B. model d\'alcaries ICGC (COG, 1 m): {np.isfinite(h_b).sum()} parts mesurades')
    ign = alcaries._ign(rect, avis=lambda t: None)
    h_c, cob_c = alcaries.alcades_parts(parts, ign)
    print(f'C. MDSn IGN (2,5 m): {np.isfinite(h_c).sum()} parts mesurades')
    est = parts['plantes'].to_numpy() * ALCADA_PLANTA_M
    print('\n== Comparacions')
    d_ab = resum('B - A (mateix vol: ha de ser ~0)', h_b, h_a, area)
    resum('C - B (IGN contra ICGC: dues fonts)', h_c, h_b, area)
    resum('estimada - B (plantes x 3 m contra ICGC)', est, h_b, area)
    resum('estimada - C (plantes x 3 m contra IGN)', est, h_c, area)
    # comprovacio automatica: B i A han de coincidir (mateix LiDAR); tolerancia 1 m a la mediana absoluta (els dos
    # productes no fan servir els mateixos punts: classe edifici contra objecte mes alt, terra del voltant contra
    # terra interpolat sota l'edifici)
    ok = np.median(np.abs(d_ab)) < 1.0 and np.isfinite(h_b).sum() > 0.8 * np.isfinite(h_a).sum()
    print(('\nOK    ' if ok else '\nFALLA ') + 'el model d\'alcaries de l\'ICGC reprodueix el nuvol de punts (|mediana| < 1 m '
          'i el 80 % de les parts mesurades)')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
