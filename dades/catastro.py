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

Memoria cau dels ZIP (F51, 19/11/2026): es conserven entre cel·les i sessions (dues cel·les veines del mateix
municipi fan servir el mateix ZIP), com a molt MAX_ZIPS_MB; en passar-se'n, s'esborren els que fa mes temps que no es
fan servir (la data de modificacio es toca a cada us). La descarrega es fa per trossos a <zip>.part: si es talla, la
seguent la repren on era (capcalera HTTP Range) o, si el servidor no ho admet, la torna a comencar. El ZIP nomes pren
el seu nom quan es complet i valid (zip_valid: el CRC de cada fitxer), de manera que mai no se'n llegeix un de mig baixat.
"""
import io
import os
import re
import zipfile

import requests

from .data_io import DIR_GENERATS

DIR_EDIFICIS = os.path.join(DIR_GENERATS, 'edificis')     # data/edificis (o la carpeta de proves)
DIR_ZIPS = os.path.join(DIR_EDIFICIS, 'catastro')    # ZIP i canals ATOM (ignorada pel Git)
URL = 'https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/{prov}/{codi}-{nom}/A.ES.SDGC.BU.{codi}.zip'
MAX_ZIPS_MB = 300.0          # espai maxim dels ZIP desats (el disc de l'equip va just: memoria "espai-disc-limitat")
TROS_BYTES = 1 << 20         # la descarrega s'escriu per trossos d'1 MB (es pot reprendre)
URL_ATOM = 'https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml'


def cami_zip(codi):
    return os.path.join(DIR_ZIPS, f'A.ES.SDGC.BU.{codi}.zip')


def descarregar(prov, codi, nom, url=None, avis=None):
    """El ZIP d'un municipi: el desat (si es valid) o el baixa, reprenent una descarrega tallada (<zip>.part).
    Retorna el cami. Marca el ZIP com a fet servir ara (netejar_zips esborra primer els que fa mes que no)."""
    cami = cami_zip(codi)
    if os.path.exists(cami):
        if zipfile.is_zipfile(cami):
            os.utime(cami)
            return cami
        os.remove(cami)                           # malmes (no hauria de passar: nomes es desa sencer)
    os.makedirs(DIR_ZIPS, exist_ok=True)
    part = cami + '.part'
    url = url or URL.format(prov=prov, codi=codi, nom=nom)
    for _ in range(2):                            # el segon intent, des de zero (p. ex. si la represa no quadra)
        ja = os.path.getsize(part) if os.path.exists(part) else 0
        with requests.get(url, timeout=600, stream=True, headers={'Range': f'bytes={ja}-'} if ja else {}) as r:
            if r.status_code == 416:              # ja el teniem sencer
                pass
            else:
                r.raise_for_status()
                represa = ja and r.status_code == 206
                with open(part, 'ab' if represa else 'wb') as f:
                    for tros in r.iter_content(TROS_BYTES):
                        f.write(tros)
        if zip_valid(part):
            os.replace(part, cami)
            print(f'  baixat {codi} {nom}: {os.path.getsize(cami) / 1e6:.1f} MB' + (' (repres)' if ja else ''))
            netejar_zips(protegits={cami})
            return cami
        os.remove(part)
    raise RuntimeError(f'el ZIP del Catastro de {nom} no es valid')


def zip_valid(cami):
    """Si el ZIP es sencer: no n'hi ha prou amb zipfile.is_zipfile (nomes mira el final del fitxer: una represa sobre
    un .part malmes el donaria per bo); testzip comprova el CRC de cada fitxer de dins (~0,1 s per a 20 MB)."""
    try:
        with zipfile.ZipFile(cami) as z:
            return z.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def netejar_zips(maxim_mb=MAX_ZIPS_MB, protegits=()):
    """Esborra els ZIP que fa mes temps que no es fan servir fins que n'hi hagi com a molt maxim_mb. Retorna els
    esborrats."""
    if not os.path.isdir(DIR_ZIPS):
        return []
    zips = [os.path.join(DIR_ZIPS, f) for f in os.listdir(DIR_ZIPS) if f.endswith('.zip')]
    zips.sort(key=os.path.getmtime)
    total = sum(os.path.getsize(z) for z in zips)
    esborrats = []
    for z in zips:
        if total <= maxim_mb * 1e6:
            break
        if z in protegits:
            continue
        total -= os.path.getsize(z)
        os.remove(z)
        esborrats.append(z)
    return esborrats


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
