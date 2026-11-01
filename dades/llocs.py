"""
Llocs amb detall preparats pel programa (sense OpenGL): el relleu de 5 m i els edificis del Catastro de qualsevol
lloc d'Espanya, preparats en segon pla quan la camera s'hi acosta (basecode/detall.py) o quan s'hi tria un punt.

Un lloc es una zona de detall petita, com les de data_io.ZONES_DETALL pero feta pel programa. Els llocs nous son
a una quadricula fixa (EPSG:25830): el centre es un multiple de PAS_GRAELLA_M (3 km) i el lloc que toca a un punt
es el del centre mes proper. Aixi, tornar al mateix lloc (o moure's poc) fa servir les mateixes dades, i el punt
sempre queda a 1,5 km o mes de la vora del relleu.
  - Relleu (etapa 1, preparar_relleu): un quadrat de MIDA_MDT_M (6 km) del MDT de 5 m de l'IGN (dades/mdt_wcs.py,
    una sola peticio), a data/mdt/llocs/<clau>_5m.tif. Es el darrer fitxer que es desa: si hi es, el relleu es
    complet.
  - Edificis (etapa 2, preparar_edificis, nomes si es demanen): les parts d'edifici del Catastro de la cel·la de la
    quadricula (MEITAT_EDIFICIS_M al voltant del centre: 3 x 3 km), dels municipis que la toquen (dades/catastro.py),
    a data/edificis/<clau>.gpkg, i la malla amb les altures estimades (dades/edificis.preparar_malla). Els ZIP dels
    municipis s'esborren despres de llegir-los (si no hi eren abans). <clau>.json diu que l'etapa s'ha fet (tambe
    si no hi ha cap edifici: no es torna a provar).
  - Fotografia aeria: la del mosaic (dades/teselles.py), que ja arriba a tot arreu.
Els llocs d'abans de la quadricula (centre arrodonit a 100 m, preparats amb doble clic) es continuen fent servir; els
seus edificis cobreixen 2 x 2 km (MEITAT_ANTIGA_M).

Espai: uns 20-60 MB per lloc (sobretot la memoria cau del relleu i de la malla). Es guarden com a molt MAX_LLOCS; en
preparar-ne un de nou, s'esborren els mes antics (no els protegits: els que hi ha carregats).
"""
import glob
import json
import os
import threading
import time

from pyproj import Transformer

from . import catastro, mdt_wcs
from .data_io import DIR_CACHE, DIR_MDT
from .edificis import CRS, fitxer_zona, preparar_malla

DIR_LLOCS = os.path.join(DIR_MDT, 'llocs')   # ignorada pel Git (com data/mdt/zones)
RES_M = 5
PAS_GRAELLA_M = 3000.0       # distancia entre centres de llocs
MIDA_MDT_M = 6000.0          # costat del relleu de 5 m (1200 x 1200 pixels)
MEITAT_EDIFICIS_M = 1500.0   # edificis a la cel·la del lloc (3 x 3 km)
MEITAT_ANTIGA_M = 1000.0     # llocs d'abans de la quadricula (doble clic): 2 x 2 km
MARGE_M = 500.0              # zones fetes a ma: un punt "te edificis" si n'hi ha a 500 m al seu voltant
MAX_LLOCS = 6

_a_utm = Transformer.from_crs('EPSG:4326', CRS, always_xy=True)
_a_latlon = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True)
_bloqueig_esborrar = threading.Lock()


def clau(x, y):
    return f'lloc_{x:.0f}_{y:.0f}'


def clau_per_punt(x, y):
    """Clau del lloc de la quadricula que correspon al punt (x, y), EPSG:25830: el del centre mes proper."""
    return clau(round(x / PAS_GRAELLA_M) * PAS_GRAELLA_M, round(y / PAS_GRAELLA_M) * PAS_GRAELLA_M)


def clau_latlon(lat, lon):
    return clau_per_punt(*_a_utm.transform(lon, lat))


def centre(clau_lloc):
    """(x, y) en EPSG:25830 del centre d'un lloc, a partir de la clau."""
    _, x, y = clau_lloc.split('_')
    return float(x), float(y)


def de_quadricula(clau_lloc):
    x, y = centre(clau_lloc)
    return x % PAS_GRAELLA_M == 0 and y % PAS_GRAELLA_M == 0


def meitat_edificis(clau_lloc):
    return MEITAT_EDIFICIS_M if de_quadricula(clau_lloc) else MEITAT_ANTIGA_M


def cami_mdt(clau_lloc):
    return os.path.join(DIR_LLOCS, f'{clau_lloc}_5m.tif')


def cami_us(clau_lloc):
    return os.path.join(DIR_LLOCS, f'{clau_lloc}.us')


def cami_meta(clau_lloc):
    return os.path.join(DIR_LLOCS, f'{clau_lloc}.json')


def meta(clau_lloc):
    cami = cami_meta(clau_lloc)
    if not os.path.exists(cami):
        return {}
    with open(cami) as f:
        return json.load(f)


def _desar_meta(clau_lloc, **canvis):
    m = meta(clau_lloc)
    m.update(canvis)
    with open(cami_meta(clau_lloc) + '.tmp', 'w') as f:
        json.dump(m, f, indent=1)
    os.replace(cami_meta(clau_lloc) + '.tmp', cami_meta(clau_lloc))


def nom(clau_lloc):
    """Nom per al panell: les coordenades del centre."""
    lon, lat = _a_latlon.transform(*centre(clau_lloc))
    return f"Lloc {lat:.4f} N, {abs(lon):.4f} {'E' if lon >= 0 else 'O'}"


def existents():
    """Claus dels llocs amb el relleu preparat, del mes antic al mes recent (darrer us: la data del marcador <clau>.us
    o, si no n'hi ha, la del fitxer del relleu)."""
    claus = [os.path.basename(c)[:-len('_5m.tif')] for c in glob.glob(os.path.join(DIR_LLOCS, 'lloc_*_5m.tif'))]

    def us(c):
        m = cami_us(c)
        return os.path.getmtime(m) if os.path.exists(m) else os.path.getmtime(cami_mdt(c))
    return sorted(claus, key=us)


def te_relleu(clau_lloc):
    return os.path.exists(cami_mdt(clau_lloc))


def edificis_fets(clau_lloc):
    """Si l'etapa dels edificis ja s'ha fet (n'hi hagi o no). Els llocs antics tenien els edificis amb el relleu."""
    return 'edificis' in meta(clau_lloc) or (not de_quadricula(clau_lloc) and te_relleu(clau_lloc))


def cobreix(clau_lloc, x, y):
    """Si els edificis del lloc cobreixen el punt (x, y), en EPSG:25830 (els antics, amb un marge de 500 m)."""
    cx, cy = centre(clau_lloc)
    marge = 0.0 if de_quadricula(clau_lloc) else MARGE_M
    return max(abs(x - cx), abs(y - cy)) < meitat_edificis(clau_lloc) - marge


def fitxers(clau_lloc):
    """Tots els fitxers d'un lloc: dades i memoria cau (data_io, terrain.py, edificis, altures i mapes)."""
    from .alcaries import DIR_ALCARIES
    nom_mdt = f'{clau_lloc}_5m'
    return ([cami_mdt(clau_lloc), cami_meta(clau_lloc), cami_us(clau_lloc), fitxer_zona(clau_lloc)] +
            glob.glob(os.path.join(DIR_CACHE, f'{nom_mdt}.*.npz')) +
            glob.glob(os.path.join(DIR_CACHE, f'*_{clau_lloc}.npz')) +
            glob.glob(os.path.join(DIR_CACHE, f'*_{clau_lloc}_*.npz')) +
            glob.glob(os.path.join(DIR_CACHE, f'edificis_{clau_lloc}*.npz')) +
            glob.glob(os.path.join(os.path.dirname(fitxer_zona(clau_lloc)), f'{clau_lloc}_alcades.npz')) +
            glob.glob(os.path.join(DIR_ALCARIES, f'{clau_lloc}*')))


def tocar(clau_lloc):
    """Marca el lloc com a fet servir ara (l'esborrat comenca pels que fa mes temps que no es fan servir), amb un
    marcador buit (<clau>.us). La data del fitxer del relleu no es toca: les memories cau (derivats, malla, mapa) en
    depenen."""
    if te_relleu(clau_lloc):
        with open(cami_us(clau_lloc), 'a'):
            pass
        os.utime(cami_us(clau_lloc))


def esborrar_antics(protegits=()):
    """Deixa espai per a un lloc nou: esborra els mes antics fins que en quedin MAX_LLOCS - 1 (no els protegits,
    p. ex. els que hi ha carregats). Retorna les claus esborrades."""
    with _bloqueig_esborrar:
        llocs = [c for c in existents() if c not in protegits]
        sobren = len(existents()) - (MAX_LLOCS - 1)
        esborrats = llocs[:max(0, sobren)]
        for c in esborrats:
            for f in fitxers(c):
                if os.path.exists(f):
                    os.remove(f)
        return esborrats


def preparar_relleu(clau_lloc, avis=print, protegits=()):
    """Etapa 1: el relleu de 5 m del lloc (si ja hi es, no fa res). Llanca una excepcio si alla no hi ha relleu (mar o
    fora d'Espanya)."""
    if te_relleu(clau_lloc):
        return cami_mdt(clau_lloc)
    esborrar_antics(protegits)
    x, y = centre(clau_lloc)
    avis('Baixant el relleu de 5 m (IGN)...')
    m = MIDA_MDT_M / 2
    alt, xmin, ymax = mdt_wcs.descarregar_rectangle(RES_M, (x - m, y - m, x + m, y + m))
    if not (alt > 0).any():
        raise RuntimeError('aqui el MDT de l\'IGN no te relleu (mar o fora d\'Espanya)')
    os.makedirs(DIR_LLOCS, exist_ok=True)
    _desar_meta(clau_lloc, relleu=dict(font='IGN, MDT de 5 m (WCS Elevacion25830_5)', res_m=RES_M,
                                       costat_m=MIDA_MDT_M, data=time.strftime('%Y-%m-%d')))
    mdt_wcs.desar_geotiff(cami_mdt(clau_lloc), alt, xmin, ymax, RES_M)
    return cami_mdt(clau_lloc)


def preparar_edificis(clau_lloc, avis=print):
    """Etapa 2: les parts d'edifici del Catastro de la cel·la del lloc i la malla (altures estimades). Cal el relleu.
    Retorna el nombre de parts."""
    import geopandas as gpd
    import pandas as pd
    import shapely
    if edificis_fets(clau_lloc):
        return meta(clau_lloc).get('edificis', {}).get('parts', 0)
    x, y = centre(clau_lloc)
    mm = meitat_edificis(clau_lloc)
    quadrat = shapely.box(x - mm, y - mm, x + mm, y + mm)
    lon0, lat0, lon1, lat1 = _a_latlon.transform_bounds(*quadrat.bounds)
    avis('Buscant els municipis (Catastro)...')
    municipis = catastro.municipis_a_prop(lat0, lat1, lon0, lon1)
    totes = []
    for i, (prov, codi, nom_m, url) in enumerate(municipis):
        avis(f'Edificis de {nom_m.title()} ({i + 1}/{len(municipis)}, Catastro)...')
        hi_era = os.path.exists(catastro.cami_zip(codi))
        cami_zip = catastro.descarregar(prov, codi, nom_m, url)
        try:
            parts = catastro.llegir_parts(cami_zip, codi, bbox=gpd.GeoSeries([quadrat], crs=CRS))
        finally:
            if not hi_era and os.path.exists(cami_zip):
                os.remove(cami_zip)
        if len(parts):
            parts = parts[parts['plantes'] > 0].to_crs(CRS)
            totes.append(parts[parts.intersects(quadrat)])
    totes = [p for p in totes if len(p)]
    n = 0
    if totes:
        parts = gpd.GeoDataFrame(pd.concat(totes, ignore_index=True), crs=CRS).drop_duplicates(subset='id')
        parts['geometry'] = parts.geometry.buffer(0)      # repara anells mal tancats (com descarregar_edificis.py)
        parts = parts[~parts.geometry.is_empty]
        os.makedirs(os.path.dirname(fitxer_zona(clau_lloc)), exist_ok=True)
        tmp = fitxer_zona(clau_lloc) + '.tmp.gpkg'
        parts.to_file(tmp, layer='parts', driver='GPKG')
        os.replace(tmp, fitxer_zona(clau_lloc))
        n = len(parts)
        avis(f'Preparant la malla de {n} parts d\'edifici...')
        preparar_malla(clau_lloc, cami_mdt(clau_lloc))
    _desar_meta(clau_lloc, edificis=dict(font='Catastro INSPIRE (D. G. del Catastro)', parts=n,
                                         municipis=[m[2] for m in municipis], meitat_m=mm,
                                         data=time.strftime('%Y-%m-%d')))
    return n


def preparar(lat, lon, avis=print, protegits=()):
    """Les dues etapes al voltant de (lat, lon) (scripts). Retorna la clau."""
    c = clau_latlon(lat, lon)
    try:
        preparar_relleu(c, avis, protegits)
        preparar_edificis(c, avis)
    except BaseException:
        if not te_relleu(c):
            for f in fitxers(c):          # no queda un lloc a mitges
                if os.path.exists(f):
                    os.remove(f)
        raise
    return c
