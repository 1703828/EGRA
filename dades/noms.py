"""
Nom del lloc d'un punt (sense OpenGL): el nucli de poblacio mes proper i el municipi administratiu. Son dues dades
diferents: entre Vic i Tona, un punt pot ser del municipi de Malla i tenir Tona com a nucli mes proper.

1. Nucli de poblacio mes proper: Nomenclator Geografic Basic d'Espanya (NGBE) de l'IGN, servei WFS INSPIRE
   (https://www.ign.es/wfs-inspire/ngbe, capa GN:NamedPlace; CC BY 4.0 ign.es). Es demanen nomes els llocs de
   poblacio (TIPUS: capitals de municipi, entitats singulars, nuclis) d'una cel·la de CEL_GRAUS x CEL_GRAUS graus
   i de les veines (cada cel·la, un cop: es desa a data/cache/noms/). El mes proper es la distancia en linia
   recta al punt del nomenclator (que es el centre del nucli o l'ajuntament, no el limit del nucli).
2. Municipi: geocodificador invers de CartoCiudad (IGN), https://www.cartociudad.es/geocoder/api/geocoder/
   reverseGeocode: el municipi (i la provincia) de l'adreca o el portal mes proper al punt. En camp obert lluny de
   tota adreca pot no tornar res (p. ex. a Picos); llavors el municipi queda "no disponible". Es desa per punt
   (arrodonit a ~10 m). Si l'adreca pertany a un nucli (camp "poblacion", p. ex. Valencia a Benimaclet), aquell es
   el nucli del punt: dins d'una ciutat gran, el punt del nomenclator (l'ajuntament) pot ser mes lluny que el
   d'un poble vei i el "mes proper" seria enganyos.

Tot es fa en un fil (Consulta): la xarxa mai atura el dibuix.
"""
import json
import math
import os

import requests

from .data_io import DIR_CACHE
from .feines import Feina

DIR_NOMS = os.path.join(DIR_CACHE, 'noms')
URL_NGBE = 'https://www.ign.es/wfs-inspire/ngbe'
URL_CARTOCIUDAD = 'https://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode'
CEL_GRAUS = 0.1            # ~11 x 8 km
TIPUS = ['Capital de municipio', 'Entidad singular', 'Núcleos de población', 'Capital de EATIM',
         'Entidad colectiva']
AGENT = 'EGRA-eclipsi-2026 (projecte universitari)'


def _desar(cami, dades):
    os.makedirs(os.path.dirname(cami), exist_ok=True)
    with open(cami + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(dades, f, ensure_ascii=False)
    os.replace(cami + '.tmp', cami)


def _nom(propietats):
    """El primer nom (grafia) d'un lloc del nomenclator (pot tenir-ne en mes d'una llengua)."""
    noms = propietats.get('name')
    noms = noms if isinstance(noms, list) else [noms]
    for n in noms:
        grafia = (n or {}).get('GeographicalName', {}).get('spelling', {})
        grafia = grafia[0] if isinstance(grafia, list) else grafia
        text = grafia.get('SpellingOfName', {}).get('text') if isinstance(grafia, dict) else None
        if text:
            return text
    return None


def nuclis_cel(i, j):
    """Llocs de poblacio de la cel·la (i, j) (latitud i * CEL_GRAUS, longitud j * CEL_GRAUS): [(nom, tipus, lat,
    lon)]. Del disc si ja s'havia demanat."""
    cami = os.path.join(DIR_NOMS, f'ngbe_{i}_{j}.json')
    if os.path.exists(cami):
        with open(cami, encoding='utf-8') as f:
            return [tuple(v) for v in json.load(f)]
    lat0, lon0 = i * CEL_GRAUS, j * CEL_GRAUS
    conds = ''.join(f'<fes:PropertyIsEqualTo><fes:ValueReference>gn:localType</fes:ValueReference>'
                    f'<fes:Literal>{t}</fes:Literal></fes:PropertyIsEqualTo>' for t in TIPUS)
    caixa = (f'<fes:BBOX><fes:ValueReference>gn:geometry</fes:ValueReference><gml:Envelope srsName="urn:ogc:def:crs:'
             f'EPSG::4326"><gml:lowerCorner>{lat0:.4f} {lon0:.4f}</gml:lowerCorner><gml:upperCorner>'
             f'{lat0 + CEL_GRAUS:.4f} {lon0 + CEL_GRAUS:.4f}</gml:upperCorner></gml:Envelope></fes:BBOX>')
    filtre = (f'<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" '
              f'xmlns:gn="http://inspire.ec.europa.eu/schemas/gn/4.0"><fes:And>{caixa}<fes:Or>{conds}</fes:Or>'
              f'</fes:And></fes:Filter>')
    r = requests.get(URL_NGBE, params=dict(service='WFS', version='2.0.0', request='GetFeature',
                                           typeNames='GN:NamedPlace', outputFormat='application/geo+json',
                                           filter=filtre, count=5000),
                     timeout=60, headers={'User-Agent': AGENT})
    r.raise_for_status()
    llocs = {}
    for f in r.json().get('features', []):
        nom = _nom(f.get('properties', {}))
        tipus = (f['properties'].get('localType') or {}).get('LocalisedCharacterString', {}).get('value', '')
        lon, lat = f['geometry']['coordinates'][:2]
        if nom:
            # el mateix nucli hi surt diverses vegades (capital, entitat singular, nucli): una sola, la de mes rang
            clau = (nom, round(lat, 4), round(lon, 4))
            if clau not in llocs or TIPUS.index(tipus) < TIPUS.index(llocs[clau][1]):
                llocs[clau] = (nom, tipus, lat, lon)
    resultat = list(llocs.values())
    _desar(cami, resultat)
    return resultat


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia sobre l'esfera (km): n'hi ha prou per triar el mes proper i mostrar-ne la distancia."""
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def nucli_mes_proper(lat, lon):
    """(nom, tipus, distancia en km, lat, lon) del lloc de poblacio mes proper, buscant a la cel·la del punt i a
    les vuit veines; None si no n'hi ha cap (mar obert o fora d'Espanya)."""
    i0, j0 = math.floor(lat / CEL_GRAUS), math.floor(lon / CEL_GRAUS)
    millor = None
    for i in range(i0 - 1, i0 + 2):
        for j in range(j0 - 1, j0 + 2):
            for nom, tipus, la, lo in nuclis_cel(i, j):
                d = distancia_km(lat, lon, la, lo)
                if millor is None or d < millor[2]:
                    millor = (nom, tipus, d, la, lo)
    return millor


def municipi(lat, lon):
    """dict(muni, provincia, poblacion, lat, lon de l'adreca) segons CartoCiudad, o None si no hi ha cap adreca a
    prop. poblacion: el nucli al qual pertany l'adreca (pot ser None, fora dels nuclis)."""
    cami = os.path.join(DIR_NOMS, f'muni_{lat:.4f}_{lon:.4f}.json')
    if os.path.exists(cami):
        with open(cami, encoding='utf-8') as f:
            d = json.load(f)
    else:
        r = requests.get(URL_CARTOCIUDAD, params=dict(lat=f'{lat:.6f}', lon=f'{lon:.6f}'), timeout=30,
                         headers={'User-Agent': AGENT})
        r.raise_for_status()
        j = r.json() if r.status_code == 200 and r.text.strip() else {}
        d = dict(muni=j.get('muni'), provincia=j.get('province'), poblacion=j.get('poblacion'),
                 lat=j.get('lat'), lon=j.get('lng'))
        _desar(cami, d)
    return d if d.get('muni') else None


def consultar(lat, lon, avis=print):
    """Les dues dades d'un punt: dict(nucli=(nom, tipus, km, lat, lon) o None, municipi=(municipi, provincia) o
    None, errors=[...]). Una dada que falla (servei caigut) no impedeix l'altra. Si l'adreca mes propera (a menys
    de 300 m) pertany a un nucli, el nucli es aquell, amb tipus 'dins del nucli' i distancia 0."""
    r = dict(nucli=None, municipi=None, errors=[])
    m = None
    avis('Buscant el municipi (CartoCiudad)...')
    try:
        m = municipi(lat, lon)
        if m:
            r['municipi'] = (m['muni'], m['provincia'])
    except Exception as e:   # noqa: BLE001
        r['errors'].append(f'municipi: {e.__class__.__name__}')
    if m and m.get('poblacion') and m.get('lat') is not None and distancia_km(lat, lon, m['lat'], m['lon']) < 0.3:
        r['nucli'] = (m['poblacion'], 'dins del nucli', 0.0, lat, lon)
        return r
    avis('Buscant el nucli mes proper (IGN, NGBE)...')
    try:
        r['nucli'] = nucli_mes_proper(lat, lon)
    except Exception as e:   # noqa: BLE001
        r['errors'].append(f'nomenclator: {e.__class__.__name__}')
    return r


class Consulta(Feina):
    """consultar() en un fil, per al punt (lat, lon)."""

    def __init__(self, lat, lon):
        super().__init__((round(lat, 5), round(lon, 5)), consultar, lat, lon, descripcio='nom del lloc')


# ------------------------------------------------------------ noms sobre el mapa (ui.py, noms_al_mapa)

FITXER_NOMS_MAPA = os.path.join(os.path.dirname(DIR_CACHE), 'noms_mapa.json')   # scripts/preparar_noms_mapa.py


def noms_mapa():
    """[(nom, nivell, lat, lon)] dels noms que s'escriuen sobre el mapa (0 capitals de l'Estat i de comunitat, 1 de
    provincia, 2 de comarca de Catalunya), o [] si el fitxer no hi es."""
    if not os.path.exists(FITXER_NOMS_MAPA):
        return []
    with open(FITXER_NOMS_MAPA, encoding='utf-8') as f:
        return [(d['nom'], d['nivell'], d['lat'], d['lon']) for d in json.load(f)['llocs']]
