"""
Prepara data/noms_mapa.json: els noms de lloc que el programa escriu sobre el mapa segons l'altura de la camera
(ui.py, noms_al_mapa), com a Google Maps.

Nivells (de mes a menys important):
  0  Capital de l'Estat i capitals de comunitat autonoma (i Ceuta i Melilla)
  1  Capitals de provincia
  2  Capitals de comarca de Catalunya (llista de sota: les 43 comarques, amb Terrassa, cocapital del Valles
     Occidental). El nomenclator de l'IGN no te el tipus "capital de comarca": la llista es fa a ma i les
     coordenades surten del nomenclator (la capital de municipi amb aquell nom dins de Catalunya).

Font: Nomenclator Geografic Basic d'Espanya (NGBE), IGN, servei WFS INSPIRE (https://www.ign.es/wfs-inspire/ngbe,
capa GN:NamedPlace; CC BY 4.0 ign.es), el mateix de dades/noms.py. Demanar-ho tot Espanya d'un cop fa esgotar el temps
del servidor (504): es demana per caixes de CAIXA_GRAUS, i les que fallen es parteixen en quatre.

Executa (des de l'arrel, amb l'entorn egra; uns minuts):
    python scripts/preparar_noms_mapa.py
"""
import json
import os
import sys
import unicodedata

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import requests  # noqa: E402

from dades.noms import URL_NGBE, AGENT, _nom  # noqa: E402

SORTIDA = os.path.join(ARREL, 'data', 'noms_mapa.json')
CAIXA_GRAUS = 2.0
ESPANYA = (27.5, -18.5, 44.0, 4.5)            # lat min, lon min, lat max, lon max (amb les Canaries)
CATALUNYA = (40.5, 0.1, 42.9, 3.4)
TIPUS_NIVELL = {'Capital de Estado': 0,
                'Capital de comunidad autónoma y ciudad con estatuto de autonomía': 0,
                'Capital de provincia': 1}
# capitals de comunitat autonoma: el nomenclator en marca algunes (Valencia, Toledo...) nomes com a capital de provincia
CAPITALS_COMUNITAT = ['Madrid', 'Barcelona', 'València', 'Sevilla', 'Santiago de Compostela', 'Oviedo', 'Santander',
                      'Vitoria-Gasteiz', 'Pamplona', 'Logroño', 'Zaragoza', 'Toledo', 'Valladolid', 'Mérida', 'Murcia',
                      'Palma', 'Las Palmas de Gran Canaria', 'Santa Cruz de Tenerife', 'Ceuta', 'Melilla']
MATEIX_LLOC_KM = 3.0          # dos noms a menys d'aquesta distancia son el mateix lloc (p. ex. Pamplona i Iruna)
# capitals de comarca de Catalunya (Llei 2/2023 del Llucanes; Terrassa, cocapital del Valles Occidental)
CAPITALS_COMARCA = [
    'Valls', 'Figueres', 'Vilafranca del Penedès', "la Seu d'Urgell", 'el Pont de Suert', 'Igualada', 'Vielha',
    'Manresa', 'Reus', 'Tortosa', "la Bisbal d'Empordà", 'Sant Feliu de Llobregat', 'el Vendrell', 'Barcelona',
    'Berga', 'Puigcerdà', 'Montblanc', 'Vilanova i la Geltrú', 'les Borges Blanques', 'Olot', 'Girona', 'Mataró',
    'Moià', 'Amposta', 'Balaguer', 'Vic', 'Tremp', 'Sort', 'Mollerussa', 'Banyoles', 'Falset', "Móra d'Ebre",
    'Ripoll', 'Cervera', 'Lleida', 'Santa Coloma de Farners', 'Solsona', 'Tarragona', 'Gandesa', 'Tàrrega',
    'Sabadell', 'Terrassa', 'Granollers', 'Prats de Lluçanès']


def normal(text):
    """Per comparar noms: sense accents, en minuscules i sense articles ni apostrofs."""
    t = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').lower().replace("'", ' ')
    paraules = [p for p in t.replace('-', ' ').split() if p not in ('la', 'el', 'les', 'l', 'els')]
    return ' '.join(paraules)


def demanar(caixa, tipus):
    lat0, lon0, lat1, lon1 = caixa
    conds = ''.join(f'<fes:PropertyIsEqualTo><fes:ValueReference>gn:localType</fes:ValueReference>'
                    f'<fes:Literal>{t}</fes:Literal></fes:PropertyIsEqualTo>' for t in tipus)
    conds = f'<fes:Or>{conds}</fes:Or>' if len(tipus) > 1 else conds
    filtre = (f'<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" '
              f'xmlns:gn="http://inspire.ec.europa.eu/schemas/gn/4.0"><fes:And><fes:BBOX><fes:ValueReference>'
              f'gn:geometry</fes:ValueReference><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>'
              f'{lat0:.4f} {lon0:.4f}</gml:lowerCorner><gml:upperCorner>{lat1:.4f} {lon1:.4f}</gml:upperCorner>'
              f'</gml:Envelope></fes:BBOX>{conds}</fes:And></fes:Filter>')
    r = requests.get(URL_NGBE, params=dict(service='WFS', version='2.0.0', request='GetFeature',
                                           typeNames='GN:NamedPlace', outputFormat='application/geo+json',
                                           filter=filtre, count=10000), timeout=180, headers={'User-Agent': AGENT})
    r.raise_for_status()
    out = []
    for f in r.json().get('features', []):
        nom = _nom(f.get('properties', {}))
        t = (f['properties'].get('localType') or {}).get('LocalisedCharacterString', {}).get('value', '')
        lon, lat = f['geometry']['coordinates'][:2]
        if nom:
            out.append((nom, t, lat, lon))
    return out


def demanar_robust(caixa, tipus, minim=0.25):
    """demanar(), desat a data/cache/noms/ (es pot reprendre); si el servidor triga massa (504), la caixa es parteix
    en quatre (fins a minim graus)."""
    from dades.noms import DIR_NOMS
    cami = os.path.join(DIR_NOMS, 'mapa_' + '_'.join(f'{v:.2f}' for v in caixa) + f'_{len(tipus)}.json')
    if os.path.exists(cami):
        with open(cami, encoding='utf-8') as f:
            return [tuple(v) for v in json.load(f)]
    try:
        out = demanar(caixa, tipus)
    except (requests.HTTPError, requests.Timeout, requests.ConnectionError):
        lat0, lon0, lat1, lon1 = caixa
        if lat1 - lat0 <= minim:
            raise
        lm, om = (lat0 + lat1) / 2, (lon0 + lon1) / 2
        out = []
        for c in ((lat0, lon0, lm, om), (lat0, om, lm, lon1), (lm, lon0, lat1, om), (lm, om, lat1, lon1)):
            out += demanar_robust(c, tipus, minim)
        return out
    os.makedirs(DIR_NOMS, exist_ok=True)
    with open(cami, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def caixes(limits, pas):
    lat0, lon0, lat1, lon1 = limits
    lat = lat0
    while lat < lat1:
        lon = lon0
        while lon < lon1:
            yield lat, lon, min(lat + pas, lat1), min(lon + pas, lon1)
            lon += pas
        lat += pas


def main():
    llocs = {}
    for caixa in caixes(ESPANYA, CAIXA_GRAUS):
        for nom, t, lat, lon in demanar_robust(caixa, list(TIPUS_NIVELL)):
            nivell = TIPUS_NIVELL.get(t)
            if nivell is not None and (nom not in llocs or nivell < llocs[nom]['nivell']):
                llocs[nom] = dict(nom=nom, nivell=nivell, lat=round(lat, 5), lon=round(lon, 5))
        print(f'  caixa {caixa}: {len(llocs)} capitals fins ara', flush=True)
    # capitals de comarca: les capitals de municipi de Catalunya amb aquests noms
    volguts = {normal(n): n for n in CAPITALS_COMARCA}
    trobats = {}
    for caixa in caixes(CATALUNYA, 1.0):
        for nom, t, lat, lon in demanar_robust(caixa, ['Capital de municipio', 'Capital de provincia',
                                                'Capital de comunidad autónoma y ciudad con estatuto de autonomía']):
            k = normal(nom)
            if k in volguts and k not in trobats:
                trobats[k] = dict(nom=nom, nivell=2, lat=round(lat, 5), lon=round(lon, 5))
    falten = [n for k, n in volguts.items() if k not in trobats]
    for k, d in trobats.items():
        if not any(normal(v['nom']) == k for v in llocs.values()):   # Barcelona, Girona... ja hi son amb mes rang
            llocs[d['nom']] = d
    comunitat = {normal(n) for n in CAPITALS_COMUNITAT}
    for d in llocs.values():
        if normal(d['nom']) in comunitat:
            d['nivell'] = 0
    # un sol nom per lloc (el de mes rang; a igual rang, el primer per ordre alfabetic)
    from dades.noms import distancia_km
    resultat = []
    for d in sorted(llocs.values(), key=lambda d: (d['nivell'], d['nom'])):
        if all(distancia_km(d['lat'], d['lon'], e['lat'], e['lon']) > MATEIX_LLOC_KM for e in resultat):
            resultat.append(d)
    with open(SORTIDA, 'w', encoding='utf-8') as f:
        json.dump(dict(font="Nomenclator Geografic Basic d'Espanya (NGBE), IGN, CC BY 4.0; capitals de comarca: "
                            "llista de scripts/preparar_noms_mapa.py", llocs=resultat), f, ensure_ascii=False, indent=0)
    n = [sum(d['nivell'] == k for d in resultat) for k in range(3)]
    print(f'{SORTIDA}: {len(resultat)} noms (nivell 0: {n[0]}, 1: {n[1]}, 2: {n[2]})')
    if falten:
        print(f'AVIS: capitals de comarca no trobades: {falten}')


if __name__ == '__main__':
    main()
