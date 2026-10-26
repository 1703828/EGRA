"""
La ubicacio de l'observador: el punt de la Terra des d'on es mira l'eclipsi.

Es nomes una dada, sense cap dibuix. D'aquest mateix punt surten el model del Sol i la Lluna i les
dades del CNIG del panell: els crea tots alhora GraphicsEngine.triar_punt() (main.py), de manera que
sempre corresponen al mateix lloc. L'objecte no es pot modificar (frozen): canviar de punt vol dir
crear-ne un de nou. Es independent de la camera: es pot explorar lluny sense moure l'observador.
"""
from dataclasses import dataclass

ALCADA_ULLS_KM = 0.0017   # els ulls, 1,7 m per sobre del terra

# ubicacions que es poden triar al panell: un lloc concret de cada poble (tasca 0.3 del pla, consultat el
# 26/10/2026). Ajuntaments: geocodificador de l'ICGC (eines.icgc.cat/geocodificador), que coincideix a
# menys de 20 m amb OpenStreetMap. Places: centre del poligon de la placa a OpenStreetMap (l'ICGC hi dona
# el primer portal, a la vora). 4 decimals = ~10 m. Picos: centre de la zona de 5 m (cas de totalitat,
# sense lloc concret). Datum ETRS89 = WGS84 a aquesta precisio.
UBICACIONS = [
    ('Picos de Europa (totalitat)', 43.2620, -4.9490),
    ('Vic, placa Major', 41.9303, 2.2540),
    ("L'Escala, ajuntament", 42.1248, 3.1322),
    ('Cerdanyola, ajuntament', 41.4910, 2.1407),
    ('Montmelo, ajuntament', 41.5517, 2.2479),
    ('UAB, placa Civica', 41.5019, 2.1039),
]


@dataclass(frozen=True)
class Observador:
    lat: float        # latitud (graus)
    lon: float        # longitud (graus)
    altitud_m: float  # altitud del terra en aquest punt (superficie dibuixada), en metres
    nom: str = ''     # nom de la ubicacio, si s'ha triat de la llista
