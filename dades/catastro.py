"""
Edificis del Catastro INSPIRE (conjunt de dades Buildings): descarrega per municipi i lectura (sense OpenGL).

Font: Direccio General del Catastro, servei de descarrega ATOM INSPIRE (un ZIP per municipi):
  https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml
Condicions (al mateix servei): us lliure i gratuit, citant la D. G. del Catastro com a autora i titular.
Navarra i el Pais Basc tenen cadastres propis i no hi son.

Cada ZIP porta tres GML (EPSG:25831 a Catalunya, EPSG:25830 a Picos): els edificis (building), les parts
d'edifici (buildingpart) i altres construccions. Una part d'edifici es un volum amb un nombre de plantes
sobre rasant uniforme (numberOfFloorsAboveGround): es el que fem servir (un edifici amb una torre i un cos
baix son dues parts). El Catastro no dona l'altura en metres: dades/edificis.py l'estima a partir de les
plantes. Precisio horitzontal declarada del contorn: 0,1 m.

Per trobar els municipis d'un lloc qualsevol (municipis_a_prop): el canal ATOM general te una entrada per
gerencia territorial (~una per provincia) amb el seu rectangle (lat, lon), i el canal de cada gerencia, una
entrada per municipi amb el rectangle i l'enllac al ZIP. Els canals es desen a DIR_ZIPS (son petits).
El servei WFS del Catastro (per rectangle) s'ha descartat: com a molt 1 km2 per peticio i ~2,5 min per km2 al
centre de Manresa (24 MB), contra 20 s per al ZIP de tot el municipi (6,6 MB). Comprovat el 30/10/2026.
"""
import io
import os
import re
import zipfile

import requests

from .data_io import DIR_DADES

DIR_EDIFICIS = os.path.join(DIR_DADES, 'edificis')
DIR_ZIPS = os.path.join(DIR_EDIFICIS, 'catastro')    # ZIP i canals ATOM (ignorada pel Git)
URL = 'https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/{prov}/{codi}-{nom}/A.ES.SDGC.BU.{codi}.zip'
URL_ATOM = 'https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml'


def cami_zip(codi):
    return os.path.join(DIR_ZIPS, f'A.ES.SDGC.BU.{codi}.zip')


def descarregar(prov, codi, nom, url=None):
    """El ZIP d'un municipi (nomes si no hi es). Retorna el cami."""
    cami = cami_zip(codi)
    if not os.path.exists(cami):
        os.makedirs(DIR_ZIPS, exist_ok=True)
        r = requests.get(url or URL.format(prov=prov, codi=codi, nom=nom), timeout=600)
        r.raise_for_status()
        with open(cami + '.tmp', 'wb') as f:      # primer amb un altre nom: si es talla, no queda a mitges
            f.write(r.content)
        os.replace(cami + '.tmp', cami)
        print(f'  baixat {codi} {nom}: {len(r.content) / 1e6:.1f} MB')
    return cami


def llegir_parts(cami, codi, bbox=None):
    """Parts d'edifici (amb l'us de l'edifici al qual pertanyen) d'un ZIP del Catastro. Amb bbox (xmin, ymin,
    xmax, ymax, en el CRS del fitxer), nomes les que el toquen."""
    import geopandas as gpd
    import pandas as pd
    with zipfile.ZipFile(cami) as z:
        parts = gpd.read_file(io.BytesIO(z.read(f'A.ES.SDGC.BU.{codi}.buildingpart.gml')), bbox=bbox)
        edificis = gpd.read_file(io.BytesIO(z.read(f'A.ES.SDGC.BU.{codi}.building.gml')), bbox=bbox,
                                 columns=['localId', 'currentUse'])
    parts['edifici'] = parts['localId'].str.split('_part').str[0]
    us = edificis[['localId', 'currentUse']].rename(columns={'localId': 'edifici', 'currentUse': 'us'})
    parts = parts.merge(us, on='edifici', how='left')
    parts['plantes'] = pd.to_numeric(parts['numberOfFloorsAboveGround'], errors='coerce').fillna(0).astype(int)
    parts['versio'] = parts['beginLifespanVersion'].astype(str).str[:10]
    return parts[['localId', 'edifici', 'plantes', 'us', 'versio', 'geometry']].rename(columns={'localId': 'id'})


def _canal(url, nom):
    """Un canal ATOM, del disc si ja s'havia baixat."""
    cami = os.path.join(DIR_ZIPS, nom)
    if not os.path.exists(cami):
        os.makedirs(DIR_ZIPS, exist_ok=True)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(cami + '.tmp', 'wb') as f:
            f.write(r.content)
        os.replace(cami + '.tmp', cami)
    with open(cami, encoding='utf-8', errors='replace') as f:
        return f.read()


def _entrades(text):
    """(enllac, rectangle (lat_min, lat_max, lon_min, lon_max)) de cada entrada d'un canal ATOM."""
    for entrada in re.findall(r'<entry>(.*?)</entry>', text, re.S):
        enllac = re.search(r'<link rel="enclosure" href="([^"]+)"', entrada)
        pol = re.search(r'<georss:polygon>([^<]+)</georss:polygon>', entrada)
        if not (enllac and pol):
            continue
        v = [float(t) for t in pol.group(1).split()]
        lats, lons = v[0::2], v[1::2]
        yield enllac.group(1), (min(lats), max(lats), min(lons), max(lons))


def municipis_a_prop(lat_min, lat_max, lon_min, lon_max):
    """Municipis (prov, codi, nom, url del ZIP) amb el rectangle que toca el demanat."""
    def toca(r):
        return r[0] <= lat_max and lat_min <= r[1] and r[2] <= lon_max and lon_min <= r[3]
    municipis = []
    for url_canal, r in _entrades(_canal(URL_ATOM, 'ES.SDGC.BU.atom.xml')):
        if not toca(r):
            continue
        prov = re.search(r'/(\d\d)/[^/]+$', url_canal).group(1)
        url_canal = url_canal.replace('http://', 'https://')
        for url_zip, rm in _entrades(_canal(url_canal, f'atom_{prov}.xml')):
            m = re.search(r'/(\d\d)/(\d{5})-([^/]+)/[^/]+\.zip$', url_zip)
            if m and toca(rm):
                municipis.append((m.group(1), m.group(2), m.group(3), url_zip.replace('http://', 'https://')))
    return municipis
