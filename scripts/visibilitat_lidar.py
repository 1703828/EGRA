"""
Mapa de visibilitat de l'eclipsi amb el LiDAR de l'ICGC (objectiu O3, F27): edificis i arbres amb les altures
mesurades, a 1 m, als carrers i als terrats.

1. Superficies (data/lidar/<zona>_{superficie,ulls,terra}_1m_25830.tif): els rasters del LiDAR
   (scripts/descarregar_lidar.py, EPSG:25831) es reprojecten (bilineal) a EPSG:25830, el CRS del terreny, en una
   graella d'1 m alineada al metre. On el LiDAR no te punts, el MDT de 5 m de la zona.
     superficie  el punt mes alt de cada metre (edificis, arbres, terra): els obstacles
     ulls        on hi ha els ulls: sobre la coberta a les cel·les d'edifici (classe 6), sobre el terra a la resta
                 (sota un arbre, els ulls son al terra i l'arbre tapa el Sol)
     terra       el terra nu (classe 2): el mateix calcul sense edificis ni arbres, per comparar
2. Visibilitat (dades/visibilitat.calcular): obstacles = superficie a 1 m; relleu de fora, la zona de 5 m i la
   peninsula de 200 m. Una vegada amb la superficie i una amb el terra.
3. Resultats: als carrers (cel·les sense edifici), quina part veu el Sol al maxim amb el LiDAR i quina sense
   edificis ni arbres; i, per a cada part d'edifici del Catastro, el terrat: la millor cel·la (percentil 90 del
   marge), la part del terrat amb el Sol sencer al maxim i fins a quina hora s'hi veu el Sol
   (data/lidar/<zona>_terrats_<eclipsi>.csv).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/visibilitat_lidar.py [uab] [--eclipsi 2026]
"""
import argparse
import csv
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import shapely  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.warp import reproject, Resampling  # noqa: E402

from dades import eclipsis, visibilitat  # noqa: E402

DIR = os.path.join(ARREL, 'data', 'lidar')
ZONES = {'uab': dict(mdt=os.path.join(ARREL, 'data', 'mdt', 'zones', 'valles_5m.tif'), edificis='valles')}
PENINSULA = os.path.join(ARREL, 'data', 'mdt', 'peninsula_200m.tif')
CRS = 'EPSG:25830'


def cami(nom, capa):
    return os.path.join(DIR, f'{nom}_{capa}_1m_25830.tif')


def desar(cami_sortida, dades, transform):
    with rasterio.open(cami_sortida + '.tmp', 'w', driver='GTiff', height=dades.shape[0], width=dades.shape[1],
                       count=1, dtype='float32', crs=CRS, transform=transform, compress='deflate', predictor=3,
                       tiled=True) as f:
        f.write(dades.astype('f4'), 1)
    os.replace(cami_sortida + '.tmp', cami_sortida)


def superficies(nom):
    """Els tres rasters a EPSG:25830 (si ja hi son, no es tornen a fer)."""
    if all(os.path.exists(cami(nom, c)) for c in ('superficie', 'ulls', 'terra')):
        return
    capes = {}
    for capa in ('mds', 'terra', 'edificis'):
        with rasterio.open(os.path.join(DIR, f'{nom}_{capa}_1m.tif')) as f:
            capes[capa] = (f.read(1), f.transform, f.crs, f.bounds)
    _, tr0, crs0, b = capes['mds']
    # la graella de destinacio: 1 m, alineada al metre, el rectangle que cap sencer dins del LiDAR (el quadrat del
    # fus 31 queda girat uns graus al fus 30: el rectangle exterior tindria cantonades sense dades)
    from pyproj import Transformer
    t = Transformer.from_crs(crs0, CRS, always_xy=True)
    (xa, ya), (xb, yb), (xc, yc), (xd, yd) = [t.transform(x, y) for x, y in
                                              ((b.left, b.bottom), (b.right, b.bottom), (b.right, b.top), (b.left, b.top))]
    x0, x1 = np.ceil(max(xa, xd)) + 2, np.floor(min(xb, xc)) - 2
    y0, y1 = np.ceil(max(ya, yb)) + 2, np.floor(min(yc, yd)) - 2
    cols, files = int(x1 - x0), int(y1 - y0)
    tr = from_origin(x0, y1, 1.0, 1.0)
    out = {}
    for capa, (dades, tr_o, crs_o, _) in capes.items():
        dst = np.full((files, cols), np.nan, 'f4')
        reproject(dades, dst, src_transform=tr_o, src_crs=crs_o, dst_transform=tr, dst_crs=CRS,
                  resampling=Resampling.nearest if capa == 'edificis' else Resampling.bilinear,
                  src_nodata=np.nan, dst_nodata=np.nan)
        out[capa] = dst
    # on el LiDAR no te punts: el MDT de 5 m de la zona
    with rasterio.open(ZONES[nom]['mdt']) as f:
        mdt = np.full((files, cols), np.nan, 'f4')
        reproject(f.read(1), mdt, src_transform=f.transform, src_crs=f.crs, dst_transform=tr, dst_crs=CRS,
                  resampling=Resampling.bilinear)
    terra = np.where(np.isfinite(out['terra']), out['terra'], mdt)
    sup = np.where(np.isfinite(out['mds']), out['mds'], terra)
    sup = np.maximum(sup, terra)
    edifici = np.isfinite(out['edificis'])
    ulls = np.where(edifici, sup, terra)
    for capa, dades in (('superficie', sup), ('ulls', ulls), ('terra', terra)):
        desar(cami(nom, capa), dades, tr)
    np.save(os.path.join(DIR, f'{nom}_edifici_1m_25830.npy'), edifici)
    print(f'Superficies: {cols} x {files} m, {edifici.mean() * 100:.0f} % de cel·les d\'edifici, '
          f'{np.mean(np.isnan(out["mds"])) * 100:.1f} % sense punts LiDAR (MDT de 5 m)')


def classe(marge, radi):
    return np.select([marge > radi, marge > 0, marge > -radi], [3, 2, 1], 0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('zona', nargs='?', default='uab')
    p.add_argument('--eclipsi', default='2026')
    a = p.parse_args()
    nom, clau = a.zona, a.eclipsi
    eclipsis.triar(clau)
    superficies(nom)
    lluny = [ZONES[nom]['mdt'], PENINSULA]
    res = {}
    for capa, ulls in (('superficie', cami(nom, 'ulls')), ('terra', None)):
        r = visibilitat.llegir(cami(nom, capa), clau)
        if r is None:
            print(f'Visibilitat amb {capa}...', flush=True)
            r = visibilitat.calcular(cami(nom, capa), clau, lluny=lluny, cami_ulls=ulls,
                                     avis=lambda t: print(f'  {t}', flush=True))
        res[capa] = r
    edifici = np.load(os.path.join(DIR, f'{nom}_edifici_1m_25830.npy'))
    radi = float(res['superficie']['radi_sol'])
    inici = float(res['superficie']['inici'])
    m_sup = res['superficie']['marge'] / 100.0
    m_ter = res['terra']['marge'] / 100.0
    valid = res['superficie']['marge'] > visibilitat.SENSE_MARGE
    carrer = valid & ~edifici

    print(f'\n== Al maxim de l\'eclipsi ({eclipsis.dades(clau)["titol"]}), {nom}')
    for nom_c, q in (('carrers i places (sense edifici)', carrer), ('terrats (cel·les d\'edifici)', valid & edifici)):
        cs = classe(m_sup[q], radi)
        print(f'  {nom_c}: Sol sencer {np.mean(cs == 3) * 100:.0f} %, mes de mig {np.mean(cs == 2) * 100:.0f} %, '
              f'menys de mig {np.mean(cs == 1) * 100:.0f} %, tapat {np.mean(cs == 0) * 100:.0f} %')
    ct, cs = classe(m_ter[carrer], radi), classe(m_sup[carrer], radi)
    print(f'  sense edificis ni arbres (terra nu), als mateixos carrers: Sol sencer {np.mean(ct == 3) * 100:.0f} %; '
          f'on el relleu el deixaria veure sencer, els edificis i els arbres el tapen (classe 0-1) al '
          f'{np.mean(cs[ct == 3] <= 1) * 100:.0f} %')

    # terrats: per a cada part del Catastro, les seves cel·les d'edifici
    from dades.edificis import llegir_zona
    from rasterio.features import rasterize
    with rasterio.open(cami(nom, 'superficie')) as f:
        tr, forma = f.transform, f.shape
    parts = llegir_zona(ZONES[nom]['edificis'])
    parts = parts[parts.intersects(shapely.box(*rasterio.transform.array_bounds(*forma, tr)))]   # (O, S, E, N)
    ids = rasterize(((g, i + 1) for i, g in enumerate(parts.geometry.buffer(-0.5)) if not g.is_empty),
                    out_shape=forma, transform=tr, fill=0, dtype='int32')
    sortida = os.path.join(DIR, f'{nom}_terrats_{clau}.csv')
    t_fi = res['superficie']['t_fi']
    n_amb = 0
    with open(sortida, 'w', newline='') as fcsv:
        w = csv.writer(fcsv)
        w.writerow(['id', 'plantes', 'cel_les_terrat', 'marge_millor_graus', 'terrat_sol_sencer_pct',
                    'sol_fins_a_hora_local'])
        ordre = np.argsort(ids, axis=None, kind='stable')
        ids_o = ids.ravel()[ordre]
        limits = np.searchsorted(ids_o, np.arange(1, len(parts) + 2))
        for i, (pid, plantes) in enumerate(zip(parts['id'], parts['plantes'])):
            cel = ordre[limits[i]:limits[i + 1]]
            cel = cel[edifici.ravel()[cel] & valid.ravel()[cel]]
            if len(cel) < 10:
                continue
            m = m_sup.ravel()[cel]
            tf = t_fi.ravel()[cel]
            tf = tf[tf < visibilitat.SENSE]
            hora = eclipsis.hora_local(inici + tf.max() / 3600.0) if len(tf) else ''
            w.writerow([pid, int(plantes), len(cel), f'{np.percentile(m, 90):.2f}',
                        f'{np.mean(m > radi) * 100:.0f}', hora])
            n_amb += 1
    print(f'  terrats: {n_amb} parts d\'edifici amb prou cel·les de coberta -> {sortida}')


if __name__ == '__main__':
    main()
