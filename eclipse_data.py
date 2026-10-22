"""
Dades de l'eclipsi total del 12/08/2026 (dataset del CNIG, veure data/eclipsi2026/LLEGENDA.md).

- reprojectar_a_graella(): passa els GeoTIFF (EPSG:3857) a una graella alineada amb un terreny
  (EPSG:25830) per dibuixar-los com a overlays: enfosquiment, durada de la totalitat, franja de
  totalitat i classe d'ombres del relleu.

Nota sobre el GeoPackage: el poligon 0-10 s de la capa durtot inclou tota la zona sense totalitat
(durada 0), aixi que no te la vora exacta de la franja. La franja i les corbes de durada (cada 10 s)
es treuen de les bandes 9, 10 i 5 del GeoTIFF, que son les mateixes dades amb que es va fer la capa.
- punt(): valors exactes dels GeoTIFF originals en un punt (lat, lon), per al punt d'observacio.

Informacio astronomica oficial de l'IGN a partir de calculs de l'Observatori Astronomic Nacional (CC BY 4.0).
"""
import math
import os

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.warp import reproject, Resampling
from scipy import ndimage

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'eclipsi2026')
EFEMERIDES = os.path.join(DIR, '10bandas2026_3857_COG.tiff')
OMBRES = os.path.join(DIR, 'terrain_shadows_2026_3857_COG_DEF_OVERSx6_8704x8192.tif')
CORBES = os.path.join(DIR, 'Eclipses_2026.gpkg')
FITXERS = (EFEMERIDES, OMBRES, CORBES)

NODATA_EFEMERIDES = -1000.0
NODATA_OMBRES = 61
CLASSE_NO_DOCUMENTADA = 4  # la tractem com a sense dades
SENSE_DADES = 255          # valor de les ombres reprojectades on no hi ha dades

# bandes del GeoTIFF d'efemerides (LLEGENDA.md)
ELEVACIO, AZIMUT, ENFOSQUIMENT, SORTIDA, POSTA = 1, 2, 3, 4, 5
INICI_PARCIAL, MAXIM, FINAL_PARCIAL, INICI_TOTAL, FINAL_TOTAL = 6, 7, 8, 9, 10

CLASSES_OMBRES = {
    0: "el relleu tapa tot el Sol",
    1: "es veu nomes part de la meitat superior del Sol",
    2: "es veu la meitat superior i part de la inferior",
    3: "el relleu no tapa el Sol",
}
HORES_CEST = 2  # hora local d'estiu = TU + 2
MAX_OVERLAY = 2048  # pixels maxims per costat de la graella dels overlays


def disponible():
    return all(os.path.exists(f) for f in FITXERS)


# ------------------------------------------------------------ overlays per a un terreny

def reprojectar_a_graella(transform, crs, forma):
    """Reprojecta les dades de l'eclipsi a la mateixa extensio que un terreny (transform, crs, forma
    = (files, cols) del terreny), amb com a maxim MAX_OVERLAY pixels per costat.
    Retorna (efem, ombres):
      efem    (files, cols, 4) float16: enfosquiment (0..1), durada de la totalitat (s, 0 fora de la
              franja), franja de totalitat visible (1 dins, 0 fora), dades valides (1/0)
      ombres  (files, cols) uint8: classe 0..3 del CNIG o SENSE_DADES
    La fila 0 es el nord, com les textures del terreny (els dos overlays fan servir els mateixos UV)."""
    files, cols = forma
    f = max(1, math.ceil(max(files, cols) / MAX_OVERLAY))
    of, oc = math.ceil(files / f), math.ceil(cols / f)
    # mateixa extensio que el terreny, pixels mes grans
    t = transform * rasterio.Affine.scale(cols / oc, files / of)

    def bilineal(banda):
        desti = np.full((of, oc), np.nan, dtype='f4')
        with rasterio.open(EFEMERIDES) as ds:
            reproject(rasterio.band(ds, banda), desti, dst_transform=t, dst_crs=crs,
                      resampling=Resampling.bilinear, src_nodata=NODATA_EFEMERIDES, dst_nodata=np.nan)
        return desti

    enfosquiment = bilineal(ENFOSQUIMENT)
    inici, final, posta = bilineal(INICI_TOTAL), bilineal(FINAL_TOTAL), bilineal(POSTA)
    # franja de totalitat: hi ha totalitat i comenca abans de la posta (com la capa durtot del CNIG)
    franja = np.isfinite(inici) & np.isfinite(posta) & (inici <= posta)
    durada = np.where(franja, (final - inici) * 3600.0, np.nan)

    efem = np.zeros((of, oc, 4), dtype='f4')
    valid = np.isfinite(enfosquiment)
    efem[..., 0] = np.where(valid, enfosquiment, 0.0)
    efem[..., 1] = np.where(np.isfinite(durada), durada, 0.0)
    # la mascara ve de pixels d'~1.2 km i fa escales: suavitzada, la vora es una linia llisa
    efem[..., 2] = ndimage.gaussian_filter(franja.astype('f4'), sigma=3.0)
    efem[..., 3] = valid

    ombres = np.full((of, oc), NODATA_OMBRES, dtype='u1')
    with rasterio.open(OMBRES) as ds:
        reproject(rasterio.band(ds, 1), ombres, dst_transform=t, dst_crs=crs,
                  resampling=Resampling.nearest, src_nodata=NODATA_OMBRES, dst_nodata=NODATA_OMBRES)
    ombres[(ombres == NODATA_OMBRES) | (ombres == CLASSE_NO_DOCUMENTADA)] = SENSE_DADES
    return efem.astype('f2'), ombres


# ------------------------------------------------------------ valors en un punt

def hora_local(hores_tu):
    """Hora TU decimal (p. ex. 18.4667) -> 'hh:mm:ss' en hora local (CEST = TU + 2)."""
    s = round((hores_tu + HORES_CEST) * 3600) % 86400
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def punt(lat, lon):
    """Valors de l'eclipsi al pixel dels GeoTIFF originals que conte (lat, lon).
    Retorna un dict (None si el punt es fora de les dades):
      elevacio, azimut (graus al maxim), enfosquiment (0..1), durada (s o None)
      fases: llista de (nom, 'hh:mm:ss' CEST, visible) amb visible = False si es despres de la posta
      posta ('hh:mm:ss' CEST), classe_ombres (0..3 o None) i text_ombres
    """
    x, y = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform(lon, lat)
    with rasterio.open(EFEMERIDES) as ds:
        fila, col = ds.index(x, y)
        if not (0 <= fila < ds.height and 0 <= col < ds.width):
            return None
        v = ds.read(window=((fila, fila + 1), (col, col + 1)))[:, 0, 0]
    if v[ENFOSQUIMENT - 1] == NODATA_EFEMERIDES:
        return None
    b = {i + 1: (None if valor == NODATA_EFEMERIDES else float(valor)) for i, valor in enumerate(v)}

    posta = b[POSTA]
    fases = []
    for nom, banda in (("Inici parcialitat", INICI_PARCIAL), ("Inici totalitat", INICI_TOTAL),
                       ("Maxim", MAXIM), ("Final totalitat", FINAL_TOTAL), ("Final parcialitat", FINAL_PARCIAL)):
        if b[banda] is not None:
            fases.append((nom, hora_local(b[banda]), posta is None or b[banda] <= posta))
    durada = None
    if b[INICI_TOTAL] is not None and b[FINAL_TOTAL] is not None:
        durada = (b[FINAL_TOTAL] - b[INICI_TOTAL]) * 3600.0

    classe = None
    with rasterio.open(OMBRES) as ds:
        fila, col = ds.index(x, y)
        if 0 <= fila < ds.height and 0 <= col < ds.width:
            c = int(ds.read(1, window=((fila, fila + 1), (col, col + 1)))[0, 0])
            classe = c if c in CLASSES_OMBRES else None

    return dict(elevacio=b[ELEVACIO], azimut=b[AZIMUT], enfosquiment=b[ENFOSQUIMENT], durada=durada,
                maxim_tu=b[MAXIM], fases=fases,
                # hores TU decimals (None si la fase no hi es): les fa servir model_eclipsi.py
                hores_tu=dict(c1=b[INICI_PARCIAL], c2=b[INICI_TOTAL], maxim=b[MAXIM], c3=b[FINAL_TOTAL],
                              c4=b[FINAL_PARCIAL], posta=posta), posta=hora_local(posta) if posta is not None else None,
                classe_ombres=classe,
                text_ombres=CLASSES_OMBRES.get(classe, "sense dades") if classe is not None else "sense dades")


if __name__ == '__main__':
    # comprovacio rapida: Picos de Europa
    import pprint
    pprint.pprint(punt(43.262, -4.949))
