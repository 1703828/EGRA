"""
La ubicacio de l'observador: el punt de la Terra des d'on es mira l'eclipsi.

Es nomes una dada, sense cap dibuix. D'aquest mateix punt surten el model del Sol i la Lluna i les
dades del CNIG del panell: els crea tots alhora GraphicsEngine.triar_punt() (main.py), de manera que
sempre corresponen al mateix lloc. L'objecte no es pot modificar (frozen): canviar de punt vol dir
crear-ne un de nou. Es independent de la camera: es pot explorar lluny sense moure l'observador.
"""
from dataclasses import dataclass

ALCADA_ULLS_KM = 0.0017   # els ulls, 1,7 m per sobre del terra

# ubicacions que es poden triar al panell. Coordenades provisionals: el centre aproximat de cada lloc
# (la tasca 0.3 del pla les ha de verificar amb una font cartografica)
UBICACIONS = [
    ('Picos de Europa (totalitat)', 43.2620, -4.9490),
    ('Vic, placa Major', 41.9302, 2.2546),
    ("L'Escala", 42.1250, 3.1330),
    ('Cerdanyola del Valles', 41.4912, 2.1406),
    ('Montmelo', 41.5517, 2.2483),
    ('UAB, placa Civica', 41.5020, 2.1040),
]


@dataclass(frozen=True)
class Observador:
    lat: float        # latitud (graus)
    lon: float        # longitud (graus)
    altitud_m: float  # altitud del terra en aquest punt (superficie dibuixada), en metres
    nom: str = ''     # nom de la ubicacio, si s'ha triat de la llista
