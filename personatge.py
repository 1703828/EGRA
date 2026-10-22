"""
El personatge ("jugador") de la vista de joc, com a la plantilla de joc d'Spline: camina pel terreny
amb el teclat i salta. La camera en tercera persona el segueix i la de primera persona hi posa els ulls.
"""
import glm

from astres import Esfera


class Personatge:
    """El "jugador": un ninot fet de dues esferes (cos i cap) que camina pel terreny i salta.
    La posicio (x, z) es al terra; l'altura es la del terreny. En tercera persona es dibuixa mes
    gran quan la camera s'allunya (com un marcador de videojoc); en primera persona no es dibuixa."""
    ALCADA_REAL = 0.0017   # km (1,7 m): els ulls de la camera en primera persona
    GRAVETAT = 18.0        # en alcades per segon^2 (salt d'~0,8 alcades que dura ~0,6 s)
    IMPULS = 5.4           # alcades per segon

    def __init__(self, app, x=0.0, z=0.0):
        self.app = app
        self.x, self.z = x, z
        self.salt, self.v_salt = 0.0, 0.0   # altura del salt i velocitat, en alcades
        self.alcada = self.ALCADA_REAL      # alcada amb que es dibuixa (km)
        self.visible = True
        self.cos = Esfera(app, color=(0.95, 0.35, 0.15))
        self.cap = Esfera(app, color=(0.98, 0.80, 0.62))
        self.cos.ambient = self.cap.ambient = 4.0   # que no quedi negre a contrallum

    def objectes(self):
        return [self.cos, self.cap]

    def saltar(self):
        if self.salt == 0.0:
            self.v_salt = self.IMPULS

    def actualitzar(self, dt):
        if self.salt > 0.0 or self.v_salt > 0.0:
            self.v_salt -= self.GRAVETAT * dt
            self.salt += self.v_salt * dt
            if self.salt <= 0.0:
                self.salt, self.v_salt = 0.0, 0.0

    def terra(self):
        """Punt del terra sota el personatge (km del mon)."""
        return glm.vec3(self.x, self.app.terrain.altitud_mon(self.x, self.z), self.z)

    def peus(self, alcada=None):
        """Punt dels peus, amb el salt (en km, segons l'alcada amb que es dibuixa)."""
        h = self.alcada if alcada is None else alcada
        return self.terra() + glm.vec3(0, self.salt * h, 0)

    def render(self):
        if not self.visible:
            return
        h, p = self.alcada, self.peus()
        self.cos.centre, self.cos.escala = p + glm.vec3(0, 0.38 * h, 0), glm.vec3(0.22, 0.38, 0.22) * h
        self.cap.centre, self.cap.escala = p + glm.vec3(0, 0.88 * h, 0), glm.vec3(0.13 * h)
        self.cos.render()
        self.cap.render()

    def destroy(self):
        self.cos.destroy()
        self.cap.destroy()
