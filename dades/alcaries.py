"""
Altures mesurades dels objectes sobre el terra (edificis i vegetacio), sense OpenGL: models d'alcaries
("normalitzats": altura sobre el terra, no cota) fets amb LiDAR, per a qualsevol lloc d'Espanya.

Fonts, per ordre de preferencia (font_per_rectangle tria la primera que cobreix el lloc):
  1. Catalunya: ICGC, Model d'alcaries territorial (LiDAR 2021-2023), 1 m, EPSG:25831, CC BY 4.0. Un sol GeoTIFF
     de tot Catalunya (98 GB) en format COG (Cloud Optimized GeoTIFF: blocs de 512 px i reduccions), aixi que se'n
     llegeix nomes la finestra que cal amb peticions HTTP de rang (GDAL /vsicurl/): 2 x 2 km en ~15 s, sense baixar
     el fitxer. Alcada maxima de qualsevol objecte a cada metre (edificis, arbres, pals...), sense classes.
     https://datacloud.icgc.cat/datacloud/model-alcaries/tif_unzip/model-alcaries-lidar-catalunya-1m-2021-2023.tif
  2. Resta d'Espanya: IGN/CNIG, MDS normalitzat (PNOA-LiDAR, primera cobertura 2008-2015), 2,5 m, WCS
     https://wcs-mds.idee.es/mds (CC BY 4.0 scne.es): cobertures mdsn_e025 (edificacio) i mdsn_v025 (vegetacio),
     en EPSG:3042 (els mateixos numeros que EPSG:25830, amb els eixos en l'ordre nord, est). Format ArcGrid (amb
     decimals; image/tiff dona enters). Es demana per trossos de com a molt TROS_PX pixels.
  Cap font: Ceuta i Melilla no tenen LiDAR; Navarra i el Pais Basc tenen el MDSn de l'IGN, pero no tenen edificis
  al Catastro (cadastres propis): alla no hi ha edificis per mesurar.

Diferencies que cal tenir presents: les dates (l'IGN pot tenir 10-15 anys: edificis nous no hi son i alguns dels
que hi son ja no hi son), la resolucio (2,5 m suavitza els patis i els carrers estrets) i la definicio (l'ICGC no
separa edificis i arbres; l'IGN si).

Per cel·les: tot es fa per les cel·les de 3 x 3 km de la quadricula dels llocs, a mesura que es miren. L'alcaria
d'una cel·la es demana un cop (alcaria_cel, data/alcaries/cel_<x>_<y>_alcaria.npz) i serveix per a les altures dels
edificis (preparar_alcades: les parts amb el centre a la cel·la) i per al mapa de visibilitat de detall
(preparar_superficie). Una zona gran (el Valles, 50.000 parts) no es mesura sencera: nomes on es mira.

Altura d'una part d'edifici (alcades_parts): percentil 90 de l'alcaria a les cel·les dins del contorn (reduit
MARGE_VORA_M per no agafar el carrer), nomes les que tenen objecte (> MIN_OBJECTE_M). El percentil 90, no el
maxim: una xemeneia o una antena no son la coberta. Si menys de MIN_COBERTURA de les cel·les del contorn tenen
objecte (pati, porxo, edifici fet despres del vol o enderrocat), la part queda "sense mesura" i es fa servir
l'estimacio per plantes (dades/edificis.py), identificada com a tal.
"""
import json
import os
import time

import numpy as np

from .data_io import DIR_DADES
from . import mdt_wcs

URL_ICGC = ('https://datacloud.icgc.cat/datacloud/model-alcaries/tif_unzip/'
            'model-alcaries-lidar-catalunya-1m-2021-2023.tif')
URL_IGN = 'https://wcs-mds.idee.es/mds'
CRS = 'EPSG:25830'
TROS_PX = 1600
MARGE_VORA_M = 0.5
MIN_OBJECTE_M = 1.5
MIN_COBERTURA = 0.5
DIR_ALCARIES = os.path.join(DIR_DADES, 'alcaries')      # ignorada pel Git
FONTS = {
    'icgc': dict(nom='ICGC, model d\'alcaries (LiDAR 2021-2023)', res_m=1.0, llicencia='CC BY 4.0 (ICGC)',
                 curt='ICGC 1 m 2021-23'),
    'ign': dict(nom='IGN, MDS normalitzat (PNOA-LiDAR 1a cobertura, 2008-2015)', res_m=2.5,
                llicencia='CC BY 4.0 (scne.es)', curt='IGN 2,5 m 2008-15'),
}


def _entorn_vsicurl():
    import rasterio
    return rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',
                        GDAL_HTTP_MAX_RETRY='4', GDAL_HTTP_RETRY_DELAY='2', VSI_CACHE='TRUE')


def _icgc(rect, avis):
    """Alcaria de l'ICGC al rectangle (x0, y0, x1, y1, EPSG:25830), reprojectada a una graella d'1 m en EPSG:25830
    (veinat mes proper: no inventa valors). None si el rectangle es fora de la cobertura (tot sense dades)."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling, transform_bounds
    from rasterio.windows import from_bounds
    x0, y0, x1, y1 = rect
    with _entorn_vsicurl():
        with rasterio.open('/vsicurl/' + URL_ICGC) as f:
            b = transform_bounds(CRS, f.crs, x0 - 5, y0 - 5, x1 + 5, y1 + 5)
            if b[2] <= f.bounds.left or b[0] >= f.bounds.right or b[3] <= f.bounds.bottom or b[1] >= f.bounds.top:
                return None
            avis('Llegint el model d\'alcaries de l\'ICGC (1 m)...')
            w = from_bounds(*b, f.transform).round_offsets().round_lengths()
            a = f.read(1, window=w, boundless=True, fill_value=f.nodata)
            tr_o, crs_o, nodata = f.window_transform(w), f.crs, f.nodata
    if np.mean(a == nodata) > 0.9:
        return None
    a = np.where(a == nodata, np.nan, a).astype('f4')
    cols, files = int(round(x1 - x0)), int(round(y1 - y0))
    tr = from_origin(x0, y1, 1.0, 1.0)
    out = np.full((files, cols), np.nan, 'f4')
    reproject(a, out, src_transform=tr_o, src_crs=crs_o, dst_transform=tr, dst_crs=CRS,
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    return dict(alcaria=out, transform=tr, font='icgc')


def _ign_cobertura(cobertura, rect, avis, nom):
    """Una cobertura del MDSn de l'IGN al rectangle, per trossos. Retorna (array, transform) a la graella nativa
    (2,5 m) del servidor, en EPSG:25830."""
    from rasterio.transform import from_origin
    x0, y0, x1, y1 = rect
    res = FONTS['ign']['res_m']
    tros = TROS_PX * res
    files = []
    ys = np.arange(y1, y0, -tros)
    xs = np.arange(x0, x1, tros)
    peces = {}
    for i, ya in enumerate(ys):
        for j, xa in enumerate(xs):
            avis(f'{nom}: tros {i * len(xs) + j + 1} de {len(xs) * len(ys)} (IGN, 2,5 m)...')
            yb, xb = max(ya - tros, y0), min(xa + tros, x1)
            r = mdt_wcs.peticio(dict(service='WCS', version='2.0.1', request='GetCoverage', CoverageId=cobertura,
                                     format='ArcGrid', subset=[f'x({xa:.3f},{xb:.3f})', f'y({yb:.3f},{ya:.3f})']),
                                url=URL_IGN)
            a, xll, yll = mdt_wcs.llegir_arcgrid(r.text)
            peces[(i, j)] = (a, xll, yll + a.shape[0] * res)
    # ajuntar: cada tros ve alineat amb la graella del servidor; es col·loca per la seva cantonada
    xmin = min(p[1] for p in peces.values())
    ymax = max(p[2] for p in peces.values())
    xmax = max(p[1] + p[0].shape[1] * res for p in peces.values())
    ymin = min(p[2] - p[0].shape[0] * res for p in peces.values())
    out = np.full((int(round((ymax - ymin) / res)), int(round((xmax - xmin) / res))), np.nan, 'f4')
    for a, xll, ytop in peces.values():
        r0, c0 = int(round((ymax - ytop) / res)), int(round((xll - xmin) / res))
        out[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
    out[out < -100] = np.nan
    return out, from_origin(xmin, ymax, res, res)


def _ign(rect, avis):
    e, tr = _ign_cobertura('mdsn_e025', rect, avis, 'Edificis')
    v, tr_v = _ign_cobertura('mdsn_v025', rect, avis, 'Vegetacio')
    if e.shape != v.shape or tr != tr_v:
        raise RuntimeError('les cobertures d\'edificacio i de vegetacio no tenen la mateixa graella')
    if np.all(np.isnan(e)) and np.all(np.isnan(v)):
        return None
    return dict(alcaria=np.fmax(e, v), edificis=e, vegetacio=v, transform=tr, font='ign')


def llegir(rect, avis=print):
    """Alcaria mesurada al rectangle (x0, y0, x1, y1, EPSG:25830, m) de la millor font que el cobreix:
    dict(alcaria (m sobre el terra, NaN sense dades), transform (rasterio, EPSG:25830), font ('icgc' o 'ign'),
    i, amb l'IGN, edificis i vegetacio per separat). None si cap font no hi te dades."""
    r = _icgc(rect, avis)
    if r is None:
        r = _ign(rect, avis)
    return r


# ------------------------------------------------------------ altures de les parts d'edifici

def alcades_parts(parts, a):
    """Altura mesurada (m) de cada part (GeoDataFrame en EPSG:25830) amb l'alcaria a = llegir(...): array amb NaN
    on no es pot mesurar, i la fraccio de cel·les del contorn amb objecte."""
    from rasterio.features import rasterize
    alc, tr = a['alcaria'], a['transform']
    res = tr.a
    files, cols = alc.shape
    marge = max(MARGE_VORA_M, 0.4 * res)      # a 2,5 m, un pixel de vora ja barreja carrer i coberta
    geoms = parts.geometry.buffer(-marge).values
    n = len(geoms)
    ids = rasterize(((g, i + 1) for i, g in enumerate(geoms) if g is not None and not g.is_empty),
                    out_shape=(files, cols), transform=tr, fill=0, dtype='int32', all_touched=False)
    # parts petites (o estretes) sense cap centre de cel·la a dins: totes les cel·les que toquen
    falten = np.setdiff1d(np.arange(1, n + 1), np.unique(ids))
    if len(falten):
        extra = rasterize(((geoms[i - 1], i) for i in falten if not geoms[i - 1].is_empty), out_shape=(files, cols),
                          transform=tr, fill=0, dtype='int32', all_touched=True)
        ids = np.where(ids == 0, extra, ids)
    v = alc.ravel()
    k = ids.ravel()
    sel = k > 0
    k, v = k[sel], v[sel]
    ordre = np.argsort(k, kind='stable')
    k, v = k[ordre], v[ordre]
    limits = np.searchsorted(k, np.arange(1, n + 2))
    alcada = np.full(n, np.nan)
    cobertura = np.zeros(n)
    for i in range(n):
        c = v[limits[i]:limits[i + 1]]
        if not len(c):
            continue
        obj = c[np.isfinite(c) & (c > MIN_OBJECTE_M)]
        cobertura[i] = len(obj) / len(c)
        if cobertura[i] >= MIN_COBERTURA:
            alcada[i] = float(np.percentile(obj, 90))
    return alcada, cobertura


# ------------------------------------------------------------ per cel·les de la quadricula (3 x 3 km)

from .llocs import PAS_GRAELLA_M as PAS_CEL_M   # les cel·les son les de la quadricula dels llocs (3 km)
MARGE_CEL_M = 60.0          # l'alcaria d'una cel·la arriba una mica mes enlla: les parts de la vora hi caben senceres


def centre_cel(x, y):
    return round(x / PAS_CEL_M) * PAS_CEL_M, round(y / PAS_CEL_M) * PAS_CEL_M


def cami_alcaria_cel(cx, cy):
    return os.path.join(DIR_ALCARIES, f'cel_{cx:.0f}_{cy:.0f}_alcaria.npz')


def alcaria_cel(cx, cy, avis=print):
    """L'alcaria mesurada de la cel·la de centre (cx, cy) (EPSG:25830), de la memoria cau o de la font (es desa
    comprimida, en float16: ~1 cm a 30 m). Es la mateixa per a les altures dels edificis i per al mapa de detall:
    nomes es demana un cop. dict com llegir(), o None si cap font hi te dades (tambe es desa)."""
    from rasterio import Affine
    cami = cami_alcaria_cel(cx, cy)
    if os.path.exists(cami):
        with np.load(cami, allow_pickle=False) as z:
            if not str(z['font']):
                return None
            r = dict(alcaria=z['alcaria'].astype('f4'), transform=Affine(*z['transform']), font=str(z['font']))
            if 'edificis' in z.files:
                r['edificis'] = z['edificis'].astype('f4')
            return r
    m = PAS_CEL_M / 2 + MARGE_CEL_M
    r = llegir((cx - m, cy - m, cx + m, cy + m), avis)
    os.makedirs(DIR_ALCARIES, exist_ok=True)
    d = dict(font=np.array(''), data=np.array(time.strftime('%Y-%m-%d')))
    if r is not None:
        d.update(font=np.array(r['font']), alcaria=r['alcaria'].astype('f2'), transform=np.array(list(r['transform'])[:6]))
        if 'edificis' in r:
            d['edificis'] = r['edificis'].astype('f2')
    np.savez_compressed(cami + '.tmp.npz', **d)
    os.replace(cami + '.tmp.npz', cami)
    return r


def cami_alcades(zona):
    from .catastro import DIR_EDIFICIS
    return os.path.join(DIR_EDIFICIS, f'{zona}_alcades.npz')


def llegir_alcades(zona):
    """Les altures mesurades desades d'una zona (dict: ids, alcada, cobertura, font de cada part i cel_les fetes),
    o None."""
    cami = cami_alcades(zona)
    if not os.path.exists(cami):
        return None
    with np.load(cami, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def cel_les_fetes(zona):
    """Cel·les (cx, cy) on ja s'han mesurat les parts d'una zona."""
    m = llegir_alcades(zona)
    if m is None:
        return set()
    return {tuple(float(v) for v in c.split('_')) for c in m['cel_les']}


def preparar_alcades(zona, cel, avis=print):
    """Mesura les altures de les parts d'edifici d'una zona (data/edificis/<zona>.gpkg) que tenen el centre a la
    cel·la cel = (cx, cy), amb la millor font, i les afegeix a data/edificis/<zona>_alcades.npz (les d'altres cel·les
    es conserven). Si els edificis han canviat, es torna a comencar. Retorna el dict desat."""
    from .edificis import fitxer_zona
    import geopandas as gpd
    import shapely
    gpkg = fitxer_zona(zona)
    ant = llegir_alcades(zona)
    if ant is not None and abs(float(ant['mtime_gpkg']) - os.path.getmtime(gpkg)) > 1e-3:
        ant = None
    cx, cy = cel
    nom_cel = f'{cx:.0f}_{cy:.0f}'
    if ant is not None and nom_cel in set(ant['cel_les'].tolist()):
        return ant
    t0 = time.time()
    m = PAS_CEL_M / 2
    parts = gpd.read_file(gpkg, layer='parts', bbox=(cx - m - 500, cy - m - 500, cx + m + 500, cy + m + 500))
    c = parts.geometry.centroid
    parts = parts[(c.x >= cx - m) & (c.x < cx + m) & (c.y >= cy - m) & (c.y < cy + m)].reset_index(drop=True)
    avis(f'Altures mesurades: {len(parts)} parts a la cel·la')
    alcada, cobertura, font = np.zeros(0), np.zeros(0), ''
    if len(parts):
        a = alcaria_cel(cx, cy, avis)
        if a is None:
            alcada, cobertura = np.full(len(parts), np.nan), np.zeros(len(parts))
        else:
            avis(f'Calculant l\'altura de {len(parts)} parts...')
            alcada, cobertura = alcades_parts(parts, a)
            font = a['font']
    ids = parts['id'].astype(str).to_numpy().astype('U') if len(parts) else np.zeros(0, 'U1')
    fonts = np.full(len(parts), font, dtype='U4')
    if ant is not None:
        nous = set(ids.tolist())
        q = np.array([i not in nous for i in ant['ids'].tolist()], bool)
        ids = np.concatenate([ant['ids'][q], ids]).astype('U')
        alcada = np.concatenate([ant['alcada'][q], alcada])
        cobertura = np.concatenate([ant['cobertura'][q], cobertura])
        fonts = np.concatenate([ant['font_part'][q], fonts]).astype('U4')
        cel_les = np.concatenate([ant['cel_les'], [nom_cel]]).astype('U')
    else:
        cel_les = np.array([nom_cel])
    r = dict(ids=ids, alcada=alcada, cobertura=cobertura, font_part=fonts, cel_les=cel_les,
             mtime_gpkg=np.array(os.path.getmtime(gpkg)), data=np.array(time.strftime('%Y-%m-%d')))
    np.savez_compressed(cami_alcades(zona) + '.tmp.npz', **r)
    os.replace(cami_alcades(zona) + '.tmp.npz', cami_alcades(zona))
    n = int(np.isfinite(alcada).sum())
    avis(f'Altures mesurades: {n} parts en total ({font or "sense font a la cel·la"}, {time.time() - t0:.0f} s)')
    return r


# ------------------------------------------------------------ superficie per al mapa de visibilitat

def cami_superficie(clau, capa):
    """data/alcaries/<clau>_<capa>_25830.tif (capa: superficie, ulls) i <clau>.json; clau = cel_<cx>_<cy>."""
    return os.path.join(DIR_ALCARIES, f'{clau}_{capa}_25830.tif')


def preparar_superficie(cel, cami_mdt, parts=None, res_m=None, avis=print):
    """Superficie dels obstacles (cota del terra + alcaria: edificis i, si la font els te, arbres) i cota dels ulls
    per a un rectangle, a data/alcaries/ (si ja hi son, no es tornen a fer). El terra es el MDT de 5 m (cami_mdt,
    bilineal); els ulls van sobre la coberta a les cel·les d'edifici (contorns del Catastro, si n'hi ha, o la classe
    edificacio de l'IGN) i sobre el terra a la resta (sota un arbre, els ulls son al terra i l'arbre tapa el Sol).
    cel = (cx, cy): la cel·la de la quadricula (3 x 3 km); l'alcaria es la de alcaria_cel (compartida amb les altures).
    res_m: resolucio de la sortida (per defecte la de la font); amb una resolucio mes gruixuda, cada cel·la pren
    l'objecte mes alt (no s'hi perd cap obstacle). Retorna el dict de metadades, o None si no hi ha cap font."""
    cx, cy = cel
    clau = f'cel_{cx:.0f}_{cy:.0f}'
    m = PAS_CEL_M / 2
    rect = (cx - m, cy - m, cx + m, cy + m)
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling
    meta_cami = os.path.join(DIR_ALCARIES, f'{clau}.json')
    if os.path.exists(meta_cami) and all(os.path.exists(cami_superficie(clau, c)) for c in ('superficie', 'ulls')):
        with open(meta_cami) as f:
            return json.load(f)
    a = alcaria_cel(cx, cy, avis)
    if a is None:
        return None
    alc, tr_a = a['alcaria'], a['transform']
    res = res_m or tr_a.a
    x0, y0, x1, y1 = rect
    cols, files = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    tr = from_origin(x0, y1, res, res)
    avis('Superficie dels obstacles (terra + edificis i arbres)...')
    obj = np.full((files, cols), np.nan, 'f4')
    reproject(np.nan_to_num(alc, nan=0.0), obj, src_transform=tr_a, src_crs=CRS, dst_transform=tr, dst_crs=CRS,
              resampling=Resampling.max if res > tr_a.a + 1e-6 else Resampling.nearest)
    obj = np.nan_to_num(np.maximum(obj, 0.0))
    with rasterio.open(cami_mdt) as f:
        terra = np.full((files, cols), np.nan, 'f4')
        reproject(f.read(1), terra, src_transform=f.transform, src_crs=f.crs, dst_transform=tr, dst_crs=CRS,
                  resampling=Resampling.bilinear)
    terra = np.nan_to_num(np.maximum(terra, 0.0))
    sup = terra + obj
    if parts is not None and len(parts):
        edifici = rasterize(((g, 1) for g in parts.geometry.values if not g.is_empty), out_shape=(files, cols),
                            transform=tr, fill=0, dtype='uint8') > 0
        edifici &= obj > MIN_OBJECTE_M
    elif 'edificis' in a:
        e = np.full((files, cols), np.nan, 'f4')
        reproject(np.nan_to_num(a['edificis'], nan=0.0), e, src_transform=tr_a, src_crs=CRS, dst_transform=tr,
                  dst_crs=CRS, resampling=Resampling.nearest)
        edifici = np.nan_to_num(e) > MIN_OBJECTE_M
    else:
        edifici = np.zeros((files, cols), bool)
    ulls = np.where(edifici, sup, terra)
    os.makedirs(DIR_ALCARIES, exist_ok=True)
    for capa, dades in (('superficie', sup), ('ulls', ulls)):
        cami = cami_superficie(clau, capa)
        with rasterio.open(cami + '.tmp', 'w', driver='GTiff', height=files, width=cols, count=1, dtype='float32',
                           crs=CRS, transform=tr, compress='deflate', predictor=3, tiled=True) as f:
            f.write(dades.astype('f4'), 1)
        os.replace(cami + '.tmp', cami)
    meta = dict(clau=clau, rect=list(rect), res_m=res, font=a['font'], descripcio=FONTS[a['font']]['nom'],
                mdt=os.path.abspath(cami_mdt), edificis_catastro=parts is not None and len(parts) > 0,
                cel_les_edifici=float(edifici.mean()), data=time.strftime('%Y-%m-%d'))
    with open(meta_cami + '.tmp', 'w') as f:
        json.dump(meta, f, indent=1)
    os.replace(meta_cami + '.tmp', meta_cami)
    return meta
