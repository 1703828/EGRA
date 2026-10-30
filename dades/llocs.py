"""
Llocs nous amb detall, preparats al moment (sense OpenGL): el relleu de 5 m i els edificis del Catastro al voltant
d'un punt qualsevol d'Espanya, triat amb doble clic al programa (main.py).

Un lloc es una zona de detall petita, com les de data_io.ZONES_DETALL pero feta pel programa:
  - Relleu: un quadrat de MIDA_MDT_M de costat del MDT de 5 m de l'IGN (dades/mdt_wcs.py, una sola peticio),
    a data/mdt/llocs/<clau>_5m.tif.
  - Edificis: les parts d'edifici del Catastro dins d'un quadrat de 2 x MEITAT_EDIFICIS_M de costat, dels
    municipis que el toquen (dades/catastro.py), a data/edificis/<clau>.gpkg, i la malla, a la memoria cau com
    les altres zones (dades/edificis.preparar_malla). Els ZIP dels municipis s'esborren despres de llegir-los
    (si no hi eren abans): nomes es guarda el que fa servir el lloc.
  - Fotografia aeria: la del mosaic (dades/teselles.py), que ja arriba a tot arreu.
El centre s'arrodoneix a 100 m (UTM): dos dobles clics al mateix lloc fan servir les mateixes dades.

Espai: uns 20-60 MB per lloc (sobretot la memoria cau del relleu i de la malla, segons quants edificis hi ha).
Es guarden com a molt MAX_LLOCS; en preparar-ne un de nou, s'esborren els mes antics (es poden tornar a baixar).

La preparacio (descarregues i malla, de 20 s a uns minuts) es fa en un fil (Preparacio): el bucle de dibuix no
s'atura; quan acaba, main.py carrega el lloc (objectes OpenGL) des del fil principal.
"""
import glob
import os
import threading
import time

from pyproj import Transformer

from . import catastro, mdt_wcs
from .data_io import DIR_CACHE, DIR_MDT
from .edificis import CRS, fitxer_zona, preparar_malla

DIR_LLOCS = os.path.join(DIR_MDT, 'llocs')   # ignorada pel Git (com data/mdt/zones)
RES_M = 5
MIDA_MDT_M = 6000.0          # costat del relleu de 5 m (1200 x 1200 pixels)
MEITAT_EDIFICIS_M = 1000.0   # edificis en un quadrat de 2 km de costat centrat al punt
MARGE_M = 500.0              # un punt "te edificis" si en te a 500 m al seu voltant; si no, es prepara un lloc nou
MAX_LLOCS = 3
ARRODONIMENT_M = 100.0

_a_utm = Transformer.from_crs('EPSG:4326', CRS, always_xy=True)
_a_latlon = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True)


def clau(x, y):
    return f'lloc_{x:.0f}_{y:.0f}'


def centre(clau_lloc):
    """(x, y) en EPSG:25830 del centre d'un lloc, a partir de la clau."""
    _, x, y = clau_lloc.split('_')
    return float(x), float(y)


def cami_mdt(clau_lloc):
    return os.path.join(DIR_LLOCS, f'{clau_lloc}_5m.tif')


def nom(clau_lloc):
    """Nom per al panell: les coordenades del centre."""
    lon, lat = _a_latlon.transform(*centre(clau_lloc))
    return f"Lloc {lat:.4f} N, {abs(lon):.4f} {'E' if lon >= 0 else 'O'}"


def existents():
    """Claus dels llocs preparats (el relleu es el darrer fitxer que es desa: si hi es, el lloc es complet), del
    mes antic al mes recent."""
    camins = sorted(glob.glob(os.path.join(DIR_LLOCS, 'lloc_*_5m.tif')), key=os.path.getmtime)
    return [os.path.basename(c)[:-len('_5m.tif')] for c in camins]


def cobreix(clau_lloc, x, y):
    """Si els edificis del lloc arriben a MARGE_M al voltant del punt (x, y), en EPSG:25830."""
    cx, cy = centre(clau_lloc)
    return max(abs(x - cx), abs(y - cy)) < MEITAT_EDIFICIS_M - MARGE_M


def fitxers(clau_lloc):
    """Tots els fitxers d'un lloc: dades i memoria cau (data_io, terrain.py i edificis)."""
    nom_mdt = f'{clau_lloc}_5m'
    return ([cami_mdt(clau_lloc), fitxer_zona(clau_lloc)] +
            glob.glob(os.path.join(DIR_CACHE, f'{nom_mdt}.*.npz')) +
            glob.glob(os.path.join(DIR_CACHE, f'*_{clau_lloc}.npz')))


def esborrar_antics(protegits=()):
    """Deixa espai per a un lloc nou: esborra els mes antics fins que en quedin MAX_LLOCS - 1 (no els protegits,
    p. ex. el que hi ha carregat). Retorna les claus esborrades."""
    llocs = [c for c in existents() if c not in protegits]
    sobren = len(existents()) - (MAX_LLOCS - 1)
    esborrats = llocs[:max(0, sobren)]
    for c in esborrats:
        for f in fitxers(c):
            if os.path.exists(f):
                os.remove(f)
    return esborrats


def preparar(lat, lon, avis=print, protegits=()):
    """Prepara el lloc al voltant de (lat, lon): relleu, edificis i malla. Retorna la clau."""
    x, y = _a_utm.transform(lon, lat)
    x, y = round(x / ARRODONIMENT_M) * ARRODONIMENT_M, round(y / ARRODONIMENT_M) * ARRODONIMENT_M
    c = clau(x, y)
    if os.path.exists(cami_mdt(c)):
        return c
    esborrar_antics(protegits)
    try:
        _preparar(c, x, y, avis)
    except BaseException:
        for f in fitxers(c):          # no queda un lloc a mitges
            if os.path.exists(f):
                os.remove(f)
        raise
    return c


def _preparar(c, x, y, avis):
    import geopandas as gpd
    import pandas as pd
    import shapely

    # 1. relleu (abans que els edificis: si el punt es fora del MDT, no cal baixar res mes)
    avis('Baixant el relleu de 5 m (IGN)...')
    m = MIDA_MDT_M / 2
    alt, xmin, ymax = mdt_wcs.descarregar_rectangle(RES_M, (x - m, y - m, x + m, y + m))
    if not (alt > 0).any():
        raise RuntimeError('aqui el MDT de l\'IGN no te relleu (mar o fora d\'Espanya)')

    # 2. edificis dels municipis que toquen el quadrat
    quadrat = shapely.box(x - MEITAT_EDIFICIS_M, y - MEITAT_EDIFICIS_M, x + MEITAT_EDIFICIS_M, y + MEITAT_EDIFICIS_M)
    lon0, lat0, lon1, lat1 = _a_latlon.transform_bounds(*quadrat.bounds)
    avis('Buscant els municipis (Catastro)...')
    municipis = catastro.municipis_a_prop(lat0, lat1, lon0, lon1)
    totes = []
    for i, (prov, codi, nom_m, url) in enumerate(municipis):
        avis(f'Edificis de {nom_m.title()} ({i + 1}/{len(municipis)})...')
        hi_era = os.path.exists(catastro.cami_zip(codi))
        cami_zip = catastro.descarregar(prov, codi, nom_m, url)
        try:
            parts = catastro.llegir_parts(cami_zip, codi, bbox=gpd.GeoSeries([quadrat], crs=CRS))
        finally:
            if not hi_era:
                os.remove(cami_zip)
        if len(parts):
            parts = parts[parts['plantes'] > 0].to_crs(CRS)
            totes.append(parts[parts.intersects(quadrat)])
    totes = [p for p in totes if len(p)]
    if totes:
        parts = gpd.GeoDataFrame(pd.concat(totes, ignore_index=True), crs=CRS).drop_duplicates(subset='id')
        parts['geometry'] = parts.geometry.buffer(0)      # repara anells mal tancats (com descarregar_edificis.py)
        parts = parts[~parts.geometry.is_empty]
        os.makedirs(os.path.dirname(fitxer_zona(c)), exist_ok=True)
        parts.to_file(fitxer_zona(c), layer='parts', driver='GPKG')

    # 3. el relleu al disc i la malla (cotes sobre aquest relleu)
    os.makedirs(DIR_LLOCS, exist_ok=True)
    mdt_wcs.desar_geotiff(cami_mdt(c), alt, xmin, ymax, RES_M)
    avis('Preparant la malla dels edificis...')
    preparar_malla(c, cami_mdt(c))


class Preparacio:
    """preparar() en un fil. El fil principal llegeix estat, i quan fet es True, clau o error."""

    def __init__(self, lat, lon, protegits=()):
        self.lat, self.lon = lat, lon
        self.estat, self.fet, self.clau, self.error = 'Comencant...', False, None, None
        self.t0 = time.time()
        self.fil = threading.Thread(target=self._executar, args=(protegits,), daemon=True)
        self.fil.start()

    def _executar(self, protegits):
        try:
            self.clau = preparar(self.lat, self.lon, self._avis, protegits)
        except Exception as e:   # noqa: BLE001 (xarxa, servei o dades: es mostra al panell)
            self.error = f'{e.__class__.__name__}: {e}'
            print(f'AVIS: no s\'ha pogut preparar el lloc: {self.error}')
        self.fet = True

    def _avis(self, text):
        self.estat = text
        print(f'  [lloc] {text}')

    def segons(self):
        return time.time() - self.t0

