"""
T0 -- Descarrega del MDT pel servei WCS 2.0.1 de l'IGN.

Demana una zona (bbox en lat/lon) a una resolucio donada i en fa un sol GeoTIFF
en EPSG:25830 (ETRS89 / UTM 30N) a data/cache/.

La zona es divideix en rajoles (2000x2000 pixels com a maxim per peticio). Cada rajola
es guarda a data/cache/rajoles/<nom>_<res>m_x<xmin>_y<ymax>_r<rajola>/ i, si ja hi es, no es torna a baixar.

Exemples (executar des de l'arrel del projecte):
    python scripts/descarregar_mdt.py peninsula
    python scripts/descarregar_mdt.py asturias
    python scripts/descarregar_mdt.py detall --centre 43.54 -6.54
    python scripts/descarregar_mdt.py --res 25 --bbox 43.3 43.6 -6.8 -6.3 --sortida prova_25m.tif

Que hem comprovat del servei (GetCapabilities + DescribeCoverage, octubre 2026):
  - Cobertures Elevacion25830_<res> amb res = 1000, 500, 200, 25, 5. Eixos del SUBSET: "x" i "y".
  - format=image/tiff torna enters de 16 bits (metres arrodonits): perdem els decimals.
    Per aixo demanem format=ArcGrid (text, amb 3 decimals), que arriba dins d'un missatge multipart.
  - El mar i les zones de fora d'Espanya valen 0 (no hi ha valor nodata).
  - Una peticio que no toca l'extensio de la cobertura retorna un error 400.

MDT (c) Instituto Geografico Nacional (CC BY 4.0).
"""
import argparse
import math
import os
import re
import sys
import time

import numpy as np
import requests
import tifffile
from pyproj import Transformer

URL_WCS = 'https://servicios.idee.es/wcs-inspire/mdt'
EPSG = 25830
NODATA = -32767.0  # nomes per a pixels que no ha cobert cap rajola (no n'hi hauria d'haver)

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CACHE = os.path.join(ARREL, 'data', 'cache')

# configuracions predefinides: resolucio (m), bbox (lat_min, lat_max, lon_min, lon_max), fitxer
PREDEFINITS = {
    'peninsula': dict(res=200, bbox=(35.9, 43.9, -9.5, 3.4), sortida='peninsula_200m.tif'),
    'asturias':  dict(res=25,  bbox=(42.88, 43.67, -7.19, -4.51), sortida='asturias_25m.tif'),
    'detall':    dict(res=5,   bbox=None, sortida='detall_5m.tif'),  # bbox a partir de --centre
}
CENTRE_DETALL = (43.54, -6.54)  # Luarca (lat, lon), per defecte
MIDA_DETALL_KM = 20.0


# ---------------------------------------------------------------- peticions al servidor

def peticio(params, intents=5):
    """GET al WCS amb reintents (espera 2, 4, 8... s entre intents)."""
    for intent in range(1, intents + 1):
        try:
            r = requests.get(URL_WCS, params=params, timeout=300)
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


# ---------------------------------------------------------------- geometria de la zona

def bbox_utm(lat_min, lat_max, lon_min, lon_max):
    """bbox en lat/lon (ETRS89 ~ WGS84) -> bbox en EPSG:25830 que la conte tota."""
    t = Transformer.from_crs(4326, EPSG, always_xy=True)
    return t.transform_bounds(lon_min, lat_min, lon_max, lat_max, densify_pts=21)


def bbox_centre(lat, lon, mida_km):
    """Quadrat de mida_km x mida_km centrat en (lat, lon), directament en UTM."""
    x, y = Transformer.from_crs(4326, EPSG, always_xy=True).transform(lon, lat)
    m = mida_km * 1000 / 2
    return x - m, y - m, x + m, y + m


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


# ---------------------------------------------------------------- descarrega i mosaic

def descarregar(res, bbox, sortida, mida_rajola=2000):
    cobertura = f'Elevacion25830_{res}'
    print(f"Cobertura {cobertura}")
    extensio = descriure_cobertura(cobertura)
    xmin, ymin, xmax, ymax = ajustar_a_graella(bbox, extensio, res)
    ample = round((xmax - xmin) / res)
    alt = round((ymax - ymin) / res)
    files_r, cols_r = math.ceil(alt / mida_rajola), math.ceil(ample / mida_rajola)
    print(f"Zona EPSG:{EPSG}  x {xmin:.1f}..{xmax:.1f}  y {ymin:.1f}..{ymax:.1f}")
    print(f"Mida {ample} x {alt} pixels de {res} m ({ample * res / 1000:.1f} x {alt * res / 1000:.1f} km)"
          f" -> {files_r * cols_r} rajoles de {mida_rajola} px com a maxim")

    # la carpeta depen de la zona i la resolucio: si canviem el centre no es barregen rajoles antigues
    zona = f'{os.path.splitext(sortida)[0]}_{res}m_x{xmin:.0f}_y{ymax:.0f}_r{mida_rajola}'
    dir_rajoles = os.path.join(DIR_CACHE, 'rajoles', zona)
    os.makedirs(dir_rajoles, exist_ok=True)
    mosaic = np.full((alt, ample), NODATA, dtype='f4')

    total, n = files_r * cols_r, 0
    t0 = time.time()
    for fr in range(files_r):
        for cr in range(cols_r):
            n += 1
            # extensio de la rajola en pixels del mosaic (fila 0 = nord)
            c0, c1 = cr * mida_rajola, min((cr + 1) * mida_rajola, ample)
            f0, f1 = fr * mida_rajola, min((fr + 1) * mida_rajola, alt)
            rx0, rx1 = xmin + c0 * res, xmin + c1 * res
            ry0, ry1 = ymax - f1 * res, ymax - f0 * res
            fitxer = os.path.join(dir_rajoles, f'r{fr:03d}_c{cr:03d}.npy')

            if os.path.exists(fitxer):
                rajola = np.load(fitxer)
                estat = 'ja hi era'
            else:
                r = peticio(dict(service='WCS', version='2.0.1', request='GetCoverage',
                                 CoverageId=cobertura, format='ArcGrid',
                                 subset=[f'x({rx0},{rx1})', f'y({ry0},{ry1})']))
                rajola, xll, yll = llegir_arcgrid(r.text)
                if rajola.shape != (f1 - f0, c1 - c0) or abs(xll - rx0) > 1e-3 or abs(yll - ry0) > 1e-3:
                    raise RuntimeError(f"La rajola no coincideix amb la graella demanada: "
                                       f"{rajola.shape} a ({xll}, {yll})")
                # guardar primer amb un altre nom: si es talla a mitges no queda una rajola corrupta
                np.save(fitxer + '.tmp.npy', rajola)
                os.replace(fitxer + '.tmp.npy', fitxer)
                estat = f'{len(r.content) / 1e6:.0f} MB'
            mosaic[f0:f1, c0:c1] = rajola
            print(f"  [{n}/{total}] rajola fila {fr} col {cr}: {estat}  ({time.time() - t0:.0f} s)")

    cami = os.path.join(DIR_CACHE, sortida)
    desar_geotiff(cami, mosaic, xmin, ymax, res)
    valid = mosaic[mosaic != NODATA]
    print(f"Desat {cami}")
    print(f"  {ample} x {alt} px, altituds {valid.min():.1f} .. {valid.max():.1f} m, "
          f"{(valid == 0).mean() * 100:.1f}% a 0 m (mar o fora d'Espanya)")


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


# ---------------------------------------------------------------- linia de comandes

def main():
    p = argparse.ArgumentParser(description="Descarrega el MDT de l'IGN pel WCS (EPSG:25830).")
    p.add_argument('predefinit', nargs='?', choices=PREDEFINITS.keys(),
                   help='configuracio predefinida')
    p.add_argument('--res', type=int, choices=[5, 25, 200, 500, 1000], help='resolucio en metres')
    p.add_argument('--bbox', type=float, nargs=4, metavar=('LAT_MIN', 'LAT_MAX', 'LON_MIN', 'LON_MAX'))
    p.add_argument('--centre', type=float, nargs=2, metavar=('LAT', 'LON'),
                   help=f'centre de la zona de detall (per defecte {CENTRE_DETALL})')
    p.add_argument('--mida-km', type=float, default=MIDA_DETALL_KM, help='costat de la zona amb --centre')
    p.add_argument('--sortida', help='nom del fitxer de sortida dins de data/cache/')
    p.add_argument('--rajola', type=int, default=2000, help='pixels maxims per costat de cada peticio')
    a = p.parse_args()

    conf = dict(PREDEFINITS[a.predefinit]) if a.predefinit else {}
    res = a.res or conf.get('res')
    sortida = a.sortida or conf.get('sortida')
    if a.bbox:
        bbox = bbox_utm(*a.bbox)
    elif a.centre or a.predefinit == 'detall':
        bbox = bbox_centre(*(a.centre or CENTRE_DETALL), a.mida_km)
    elif conf.get('bbox'):
        bbox = bbox_utm(*conf['bbox'])
    else:
        bbox = None
    if not (res and bbox and sortida):
        p.error("cal un predefinit o bé --res, --bbox (o --centre) i --sortida")

    descarregar(res, bbox, sortida, a.rajola)


if __name__ == '__main__':
    sys.exit(main())
