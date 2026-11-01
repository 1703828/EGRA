"""
Descarrega i prepara els edificis de les zones de detall (Catastro INSPIRE, conjunt de dades Buildings).

Font: Direccio General del Catastro, servei de descarrega ATOM INSPIRE (un ZIP per municipi):
  https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml
Cada ZIP porta tres GML (EPSG:25831 a Catalunya, EPSG:25830 a Picos): els edificis (building), les parts
d'edifici (buildingpart) i altres construccions. Una part d'edifici es un volum amb un nombre de plantes
sobre rasant uniforme (numberOfFloorsAboveGround): es el que fem servir (un edifici amb una torre i un cos
baix son dues parts). El Catastro no dona l'altura en metres: dades/edificis.py l'estima a partir de les
plantes. Precisio horitzontal declarada del contorn: 0,1 m.

Preparacio (per a cada zona de detall):
  1. Es baixen els municipis de la llista (nomes si no hi son) a data/edificis/catastro/ (ignorada pel Git).
  2. Es llegeixen les parts d'edifici; es descarten les que no tenen cap planta sobre rasant (soterranis,
     patis).
  3. Es reprojecten al CRS del terreny (EPSG:25830): es una transformacio entre fusos UTM del mateix datum
     (ETRS89), sense canvi de datum.
  4. Es guarden les que son a menys de RADI_M d'algun punt d'observacio de la zona. Si una part es a
     prop de dos punts (UAB i Cerdanyola) nomes hi es una vegada (identificador unic del Catastro).
  5. Es desa data/edificis/<zona>.gpkg (capa "parts") amb l'identificador, l'edifici, les plantes, l'us de
     l'edifici i la data de la darrera versio.
  6. Es prepara la malla a data/cache/edificis_<zona>.npz (dades/edificis.py, preparar_malla).

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/descarregar_edificis.py             # totes les zones
    python scripts/descarregar_edificis.py valles      # nomes una
"""
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from dades.observador import UBICACIONS_PROVES as UBICACIONS  # noqa: E402
from dades.edificis import fitxer_zona, ZONA_DE_LA_UBICACIO, RADI_ZONA_M, preparar_malla  # noqa: E402
from dades.data_io import ZONES_DETALL  # noqa: E402
from dades.catastro import DIR_ZIPS, descarregar, llegir_parts  # noqa: E402

RADI_M = RADI_ZONA_M
CRS_TERRENY = 'EPSG:25830'

# municipis que toquen els cercles de 2 km al voltant dels punts d'observacio (comprovat amb les dades: el
# script diu quantes parts aporta cadascun)
MUNICIPIS = {
    'valles': [('08', '08266', 'CERDANYOLA DEL VALLES'), ('08', '08204', 'SANT CUGAT DEL VALLES'),
               ('08', '08252', 'BARBERA DEL VALLES'), ('08', '08312', 'BADIA DEL VALLES'),
               ('08', '08186', 'SABADELL'), ('08', '08179', 'RIPOLLET'), ('08', '08124', 'MONTCADA I REIXAC'),
               ('08', '08134', 'MONTMELO'), ('08', '08135', 'MONTORNES DEL VALLES'),
               ('08', '08158', 'PARETS DEL VALLES'), ('08', '08123', 'MOLLET DEL VALLES'),
               ('08', '08095', 'GRANOLLERS'), ('08', '08104', 'LA LLAGOSTA')],
    'vic': [('08', '08299', 'VIC'), ('08', '08099', 'GURB'), ('08', '08224', 'CALLDETENES'),
            ('08', '08246', 'SANTA EUGENIA DE BERGA')],
    'escala': [('17', '17068', 'L ESCALA')],
    'picos': [('24', '24119', 'POSADA DE VALDEON'), ('39', '39015', 'CAMALEÑO'), ('33', '33008', 'CABRALES')],
}


def preparar(zona):
    os.makedirs(DIR_ZIPS, exist_ok=True)
    punts = [(nom, lat, lon) for nom, lat, lon in UBICACIONS if ZONA_DE_LA_UBICACIO.get(nom) == zona]
    cercles = gpd.GeoSeries([Point(lon, lat) for _, lat, lon in punts], crs='EPSG:4326').to_crs(CRS_TERRENY).buffer(RADI_M)
    area = unary_union(list(cercles))
    print(f'== {zona}: {len(punts)} punts ({", ".join(n for n, _, _ in punts)}), radi {RADI_M:.0f} m')
    totes = []
    for prov, codi, nom in MUNICIPIS[zona]:
        parts = llegir_parts(descarregar(prov, codi, nom), codi)
        crs_origen = parts.crs
        parts = parts[parts['plantes'] > 0].to_crs(CRS_TERRENY)
        dins = parts[parts.intersects(area)]
        print(f'  {codi} {nom}: {len(parts)} parts amb plantes ({crs_origen.to_epsg()}), {len(dins)} dins de l\'area')
        totes.append(dins)
    parts = gpd.GeoDataFrame(pd.concat(totes, ignore_index=True), crs=CRS_TERRENY)
    n = len(parts)
    parts = parts.drop_duplicates(subset='id')
    parts['geometry'] = parts.geometry.buffer(0)          # repara anells mal tancats o autointerseccions
    parts = parts[~parts.geometry.is_empty]
    print(f'  total: {len(parts)} parts ({n - len(parts)} duplicades o buides), plantes de {parts.plantes.min() if len(parts) else 0} '
          f'a {parts.plantes.max() if len(parts) else 0}, versions de {parts.versio.min() if len(parts) else "-"} '
          f'a {parts.versio.max() if len(parts) else "-"}')
    sortida = fitxer_zona(zona)
    if os.path.exists(sortida):
        os.remove(sortida)
    parts.to_file(sortida, layer='parts', driver='GPKG')
    print(f'  desat {sortida}')
    # 6. la malla (cotes sobre el MDT de la zona, triangles en ECEF) a la memoria cau, perque el programa no
    #    s'aturi a calcular-la la primera vegada que carrega la zona
    cami_mdt = next(c for _, c, z in ZONES_DETALL if z == zona)
    if os.path.exists(cami_mdt):
        m = preparar_malla(zona, cami_mdt)
        print(f"  malla: {int(m['n_parts'])} parts, {len(m['triangles']):,} triangles (data/cache/edificis_{zona}.npz)")


def main():
    zones = sys.argv[1:] or list(MUNICIPIS)
    for zona in zones:
        preparar(zona)


if __name__ == '__main__':
    main()
