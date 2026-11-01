"""
Servei WCS 2.0.1 del MDT de l'IGN (sense OpenGL): peticions, lectura de la resposta i GeoTIFF de sortida.

El fan servir scripts/descarregar_mdt.py (zones grans, per rajoles), dades/llocs.py (el relleu de 5 m d'un lloc
nou, preparat en navegar) i dades/alcaries.py (el mateix format de resposta al WCS de l'MDS normalitzat).

Que hem comprovat del servei (GetCapabilities + DescribeCoverage, octubre 2026):
  - Cobertures Elevacion25830_<res> amb res = 1000, 500, 200, 25, 5. Eixos del SUBSET: "x" i "y".
  - format=image/tiff torna enters de 16 bits (metres arrodonits): perdem els decimals.
    Per aixo demanem format=ArcGrid (text, amb 3 decimals), que arriba dins d'un missatge multipart.
  - El mar i les zones de fora d'Espanya valen 0 (no hi ha valor nodata).
  - Una peticio que no toca l'extensio de la cobertura retorna un error 400.

MDT (c) Instituto Geografico Nacional (CC BY 4.0).
"""
import os
import re
import time

import numpy as np
import requests
import tifffile

URL_WCS = 'https://servicios.idee.es/wcs-inspire/mdt'
EPSG = 25830
NODATA = -32767.0  # nomes per a pixels que no ha cobert cap rajola (no n'hi hauria d'haver)


def peticio(params, intents=5, url=URL_WCS):
    """GET al WCS (per defecte el del MDT; dades/alcaries.py hi demana el de l'MDS) amb reintents (espera 2, 4,
    8... s entre intents)."""
    for intent in range(1, intents + 1):
        try:
            r = requests.get(url, params=params, timeout=300)
            if r.status_code == 200:
                return r
            # un 4xx vol dir que la peticio esta malament: no te sentit repetir-la
            if 400 <= r.status_code < 500:
                raise RuntimeError(f"Error {r.status_code} del servidor:\n{r.text[:800]}")
            print(f"    error {r.status_code}, intent {intent}/{intents}")
        except requests.RequestException as e:
            print(f"    error de xarxa ({e.__class__.__name__}), intent {intent}/{intents}")
        if intent < intents:
            time.sleep(2 ** intent)
    raise RuntimeError("No s'ha pogut completar la peticio despres de diversos intents")


def descriure_cobertura(cobertura):
    """Llegeix de DescribeCoverage l'extensio de la cobertura (xmin, ymin, xmax, ymax)."""
    r = peticio(dict(service='WCS', version='2.0.1', request='DescribeCoverage', CoverageId=cobertura))
    baix = re.search(r'<gml:lowerCorner>([^<]+)</gml:lowerCorner>', r.text)
    dalt = re.search(r'<gml:upperCorner>([^<]+)</gml:upperCorner>', r.text)
    xmin, ymin = map(float, baix.group(1).split())
    xmax, ymax = map(float, dalt.group(1).split())
    return xmin, ymin, xmax, ymax


def llegir_arcgrid(text):
    """Extreu la graella ArcGrid (.asc) de la resposta multipart del WCS.
    Retorna (array float32, x de la vora esquerra, y de la vora inferior)."""
    # la resposta te diverses parts separades per '--wcs'; ens quedem amb la de out.asc
    part = next(p for p in text.split('--wcs') if 'coverage/out.asc' in p)
    cos = re.split(r'\r?\n\r?\n', part, maxsplit=1)[1]
    linies = cos.split('\n')
    capcalera = {}
    while linies and re.match(r'^[A-Za-z_]+\s', linies[0]):
        clau, valor = linies.pop(0).split()
        capcalera[clau.lower()] = float(valor)
    ncols, nrows = int(capcalera['ncols']), int(capcalera['nrows'])
    dades = np.array(' '.join(linies).split(), dtype='f4')
    if dades.size != ncols * nrows:
        raise RuntimeError(f"Rajola incompleta: {dades.size} valors en lloc de {ncols * nrows}")
    alt = dades.reshape(nrows, ncols)
    if 'nodata_value' in capcalera:
        alt[alt == capcalera['nodata_value']] = NODATA
    return alt, capcalera['xllcorner'], capcalera['yllcorner']


def ajustar_a_graella(bbox, extensio, res):
    """Retalla la bbox a l'extensio de la cobertura i l'alinea amb la graella nativa del servidor,
    perque el WCS no hagi de remostrejar (les vores dels pixels son a extensio_xmin + k*res)."""
    xmin, ymin, xmax, ymax = bbox
    ex0, ey0, ex1, ey1 = extensio
    xmin, ymin = max(xmin, ex0), max(ymin, ey0)
    xmax, ymax = min(xmax, ex1), min(ymax, ey1)
    if xmin >= xmax or ymin >= ymax:
        raise RuntimeError("La zona demanada queda fora de la cobertura del MDT")
    # arrodonim a la vora de pixel mes propera (20 km a 5 m han de ser 4000 px, no 4001)
    xmin = ex0 + round((xmin - ex0) / res) * res
    ymin = ey0 + round((ymin - ey0) / res) * res
    xmax = ex0 + round((xmax - ex0) / res) * res
    ymax = ey0 + round((ymax - ey0) / res) * res
    return xmin, ymin, xmax, ymax


def descarregar_rectangle(res, bbox):
    """Un rectangle (xmin, ymin, xmax, ymax, EPSG:25830) del MDT en una sola peticio (com a molt 2000 px per
    costat), alineat amb la graella del servidor. Retorna (altituds float32, xmin, ymax)."""
    cobertura = f'Elevacion25830_{res}'
    xmin, ymin, xmax, ymax = ajustar_a_graella(bbox, descriure_cobertura(cobertura), res)
    r = peticio(dict(service='WCS', version='2.0.1', request='GetCoverage', CoverageId=cobertura,
                     format='ArcGrid', subset=[f'x({xmin},{xmax})', f'y({ymin},{ymax})']))
    alt, xll, yll = llegir_arcgrid(r.text)
    if alt.shape != (round((ymax - ymin) / res), round((xmax - xmin) / res)) or abs(xll - xmin) > 1e-3:
        raise RuntimeError(f"La resposta no coincideix amb la graella demanada: {alt.shape} a ({xll}, {yll})")
    return alt, xmin, ymax


def desar_geotiff(cami, alt, xmin, ymax, res):
    """Escriu un GeoTIFF float32 comprimit amb la georeferencia en EPSG:25830.
    (Etiquetes GeoTIFF estandard: rasterio/QGIS el llegeixen igual que si l'hagues escrit GDAL.)"""
    geokeys = [1, 1, 0, 4,          # versio 1.1.0, 4 claus
               1024, 0, 1, 1,       # GTModelType = projectat
               1025, 0, 1, 1,       # GTRasterType = PixelIsArea
               3072, 0, 1, EPSG,    # ProjectedCRS = EPSG:25830
               3076, 0, 1, 9001]    # unitats lineals = metre
    etiquetes = [
        (33550, 'd', 3, (res, res, 0.0), True),                # ModelPixelScale
        (33922, 'd', 6, (0, 0, 0, xmin, ymax, 0.0), True),     # ModelTiepoint: cantonada nord-oest
        (34735, 'H', len(geokeys), geokeys, True),             # GeoKeyDirectory
        (42113, 's', 0, str(int(NODATA)), True),               # GDAL_NODATA
    ]
    tmp = cami + '.tmp'
    tifffile.imwrite(tmp, alt, compression='zlib', tile=(512, 512), extratags=etiquetes)
    os.replace(tmp, cami)
