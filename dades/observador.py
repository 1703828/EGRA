"""
La ubicacio de l'observador: el punt del terreny des d'on es mira l'eclipsi.

Es nomes una dada, sense cap dibuix (el marcador que la mostra a l'escena es un objecte a part).
D'aquest mateix punt surten el model del Sol i la Lluna i les dades del CNIG del panell: els crea
tots alhora GraphicsEngine.triar_punt() (main.py), de manera que sempre corresponen al mateix lloc.
L'objecte no es pot modificar (frozen): canviar de punt vol dir crear-ne un de nou.
"""
from dataclasses import dataclass

ALCADA_ULLS_KM = 0.0017   # els ulls, 1,7 m per sobre del terra


@dataclass(frozen=True)
class Observador:
    x: float          # km cap a l'est del centre del terreny (coordenades del mon)
    z: float          # km cap al sud del centre del terreny
    lat: float        # latitud (graus)
    lon: float        # longitud (graus)
    altitud_m: float  # altitud del terra en aquest punt (MDT a resolucio completa), en metres
