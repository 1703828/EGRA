"""
Descarrega l'ortofoto del PNOA (IGN) per a una zona de detall: el color real del terra (carrers, places,
vegetacio, cobertes).

Font: servei WMS "PNOA maxima actualitat" de l'IGN, capa OI.OrthoimageCoverage
  https://www.ign.es/wms-inspire/pnoa-ma
Condicions (llegides al GetCapabilities del servei el 27/10/2026): AccessConstraints "CC BY 4.0 scne.es",
Fees "No se aplican condiciones". Atribucio: "Ortofoto: PNOA cedida por (c) Instituto Geografico Nacional".
El servei dona ortofotos de 0,25 o 0,50 m segons la zona (a escales mes petites que ~1:70.000, Sentinel-2); no
son ortofotos vertaderes (els edificis alts hi surten inclinats).

Dues capes per zona, en EPSG:25830 (el CRS del MDT; el servei reprojecta des del CRS original):
  1. Tota la zona a 5 m, exactament amb la graella del MDT de la zona (mateixos limits i pixels).
  2. Per a cada punt d'observacio de la zona, un quadrat de 4 x 4 km (2 km al voltant del punt, la mateixa area
     que els edificis) a 0,5 m, alineat amb la graella de 5 m del MDT. El WMS dona com a molt 4096 px per
     peticio: es demana per trossos de 4000 px i s'ajunten.
Fitxers: data/ortofoto/<zona>_5m.tif i data/ortofoto/<zona>_<punt>_0p5m.tif (GeoTIFF RGB, JPEG; carpeta ignorada
pel Git) i data/ortofoto/<zona>.json amb la data i la resolucio del vol (GetFeatureInfo de la capa de mosaic).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/descarregar_ortofoto.py vic
"""
import hashlib
import io
import json
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import requests  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from dades.data_io import ZONES_DETALL  # noqa: E402
from dades.edificis import ZONA_DE_LA_UBICACIO  # noqa: E402
from dades.observador import UBICACIONS  # noqa: E402

URL = 'https://www.ign.es/wms-inspire/pnoa-ma'
CAPA = 'OI.OrthoimageCoverage'
CRS = 'EPSG:25830'
DIR = os.path.join(ARREL, 'data', 'ortofoto')
MIDA_DETALL_M = 4000.0
RES_DETALL_M = 0.5
TROS_PX = 4000


def peticio(bbox, amplada, alcada):
    """Imatge RGB (array) del WMS per a bbox = (x0, y0, x1, y1) en EPSG:25830."""
    params = dict(SERVICE='WMS', VERSION='1.3.0', REQUEST='GetMap', LAYERS=CAPA, STYLES='', CRS=CRS,
                  BBOX=','.join(f'{v:.3f}' for v in bbox), WIDTH=amplada, HEIGHT=alcada, FORMAT='image/jpeg')
    for intent in range(4):
        try:
            r = requests.get(URL, params=params, timeout=180)
            if r.ok and r.headers.get('Content-Type', '').startswith('image'):
                return np.asarray(Image.open(io.BytesIO(r.content)).convert('RGB')), len(r.content)
            print(f'   resposta inesperada ({r.status_code}, {r.headers.get("Content-Type")}): {r.text[:200]}')
        except requests.RequestException as e:
            print(f'   error de xarxa: {e}')
        time.sleep(5 * (intent + 1))
    raise RuntimeError('el servei WMS no ha respost')


def desar(cami, img, x0, y1, res):
    """GeoTIFF RGB amb compressio JPEG (YCbCr) i la georeferencia de la cantonada nord-oest."""
    with rasterio.open(cami, 'w', driver='GTiff', width=img.shape[1], height=img.shape[0], count=3, dtype='uint8',
                       crs=CRS, transform=from_origin(x0, y1, res, res), compress='JPEG', photometric='YCBCR',
                       jpeg_quality=90, tiled=True, blockxsize=512, blockysize=512) as f:
        f.write(np.moveaxis(img, 2, 0))
    h = hashlib.sha256(open(cami, 'rb').read()).hexdigest()
    print(f'   {os.path.relpath(cami, ARREL)}: {img.shape[1]} x {img.shape[0]} px, {os.path.getsize(cami) / 1e6:.1f} MB, '
          f'sha256 {h[:16]}...')
    return h


def data_del_vol(x, y):
    """(data 'aaaa-mm', resolucio en m) de l'ortofoto al punt (GetFeatureInfo de la capa de mosaic)."""
    params = dict(SERVICE='WMS', VERSION='1.3.0', REQUEST='GetFeatureInfo', LAYERS='OI.MosaicElement',
                  QUERY_LAYERS='OI.MosaicElement', CRS=CRS, BBOX=f'{x - 50},{y - 50},{x + 50},{y + 50}',
                  WIDTH=101, HEIGHT=101, I=50, J=50, INFO_FORMAT='text/html', STYLES='')
    import re
    text = re.sub(r'<[^>]*>', ' ', requests.get(URL, params=params, timeout=60).text)
    data = re.search(r'Fecha[^0-9]*([0-9]{4}-[0-9]{2})', text)
    res = re.search(r'Resoluci[^0-9]*([0-9.]+)', text)
    return (data.group(1) if data else None), (float(res.group(1)) if res else None)


def main(zona):
    cami_mdt = next(c for _, c, z in ZONES_DETALL if z == zona)
    os.makedirs(DIR, exist_ok=True)
    with rasterio.open(cami_mdt) as f:
        b, res_mdt, w, h = f.bounds, f.transform.a, f.width, f.height
        assert f.crs.to_string() == CRS, f'el MDT de la zona hauria de ser {CRS}'
    metadades = dict(font=URL, capa=CAPA, llicencia='CC BY 4.0 (scne.es)', crs=CRS, data_descarrega=time.strftime('%Y-%m-%d'),
                     fitxers={})
    t0, bytes_xarxa = time.time(), 0
    # 1. tota la zona, amb la graella del MDT
    print(f'== {zona}: tota la zona a {res_mdt:g} m ({w} x {h} px)')
    img, n = peticio((b.left, b.bottom, b.right, b.top), w, h)
    bytes_xarxa += n
    cami = os.path.join(DIR, f'{zona}_{res_mdt:g}m.tif')
    metadades['fitxers'][os.path.basename(cami)] = dict(resolucio_m=res_mdt, limits=list(b), sha256=desar(cami, img, b.left, b.top, res_mdt))
    # 2. detall al voltant dels punts d'observacio de la zona
    a_utm = Transformer.from_crs('EPSG:4326', CRS, always_xy=True)
    for nom, lat, lon in UBICACIONS:
        if ZONA_DE_LA_UBICACIO.get(nom) != zona:
            continue
        x, y = a_utm.transform(lon, lat)
        # quadrat de 4 km alineat amb la graella de 5 m del MDT
        x0 = b.left + round((x - MIDA_DETALL_M / 2 - b.left) / res_mdt) * res_mdt
        y1 = b.top - round((b.top - (y + MIDA_DETALL_M / 2)) / res_mdt) * res_mdt
        n_px = int(round(MIDA_DETALL_M / RES_DETALL_M))
        print(f'== {nom}: {MIDA_DETALL_M / 1000:g} x {MIDA_DETALL_M / 1000:g} km a {RES_DETALL_M} m ({n_px} x {n_px} px)')
        img = np.zeros((n_px, n_px, 3), 'u1')
        for fi in range(0, n_px, TROS_PX):
            for co in range(0, n_px, TROS_PX):
                a, c = min(TROS_PX, n_px - fi), min(TROS_PX, n_px - co)
                bb = (x0 + co * RES_DETALL_M, y1 - (fi + a) * RES_DETALL_M, x0 + (co + c) * RES_DETALL_M, y1 - fi * RES_DETALL_M)
                tros, n = peticio(bb, c, a)
                bytes_xarxa += n
                img[fi:fi + a, co:co + c] = tros
        clau = nom.split(',')[0].split(' ')[0].lower().replace("l'", '')
        cami = os.path.join(DIR, f'{zona}_{clau}_0p5m.tif')
        data, res_vol = data_del_vol(x, y)
        print(f'   vol del PNOA al punt: {data}, {res_vol} m')
        metadades['fitxers'][os.path.basename(cami)] = dict(
            punt=nom, resolucio_m=RES_DETALL_M, limits=[x0, y1 - MIDA_DETALL_M, x0 + MIDA_DETALL_M, y1],
            data_vol=data, resolucio_vol_m=res_vol, sha256=desar(cami, img, x0, y1, RES_DETALL_M))
    with open(os.path.join(DIR, f'{zona}.json'), 'w') as f:
        json.dump(metadades, f, indent=1, ensure_ascii=False)
    print(f'Fet en {time.time() - t0:.0f} s; {bytes_xarxa / 1e6:.1f} MB descarregats')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'vic')
