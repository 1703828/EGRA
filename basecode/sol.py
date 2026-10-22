"""
El Sol com a font de llum de l'escena (com self.light al repte 4).

Es una Light del basecode (Ia, Id, Is) amb la posicio donada per l'azimut i l'elevacio:
el Sol es tan lluny que nomes en fem servir la direccio (llum direccional).
De moment l'azimut i l'elevacio es posen a ma (o amb les dades del CNIG); el calcul propi de la
posicio del Sol vindra mes endavant.
"""
import glm

from .light import Light


class Sol(Light):
    def __init__(self, azimut=135.0, elevacio=35.0):
        super().__init__()
        self.azimut = azimut      # graus des del nord, sentit horari
        self.elevacio = elevacio  # graus sobre l'horitzo

    def direccio(self):
        """Vector unitari del terreny cap al Sol (nord = -Z, est = +X)."""
        az, el = glm.radians(self.azimut), glm.radians(self.elevacio)
        return glm.vec3(glm.cos(el) * glm.sin(az), glm.sin(el), -glm.cos(el) * glm.cos(az))
