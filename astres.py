"""
Esferes de l'escena (fetes amb coordenades esferiques, com al repte 4): la Lluna, el Sol i la seva
resplendor (halo / corona). Les peces del personatge (personatge.py) tambe son Esferes.

- La Lluna es posa a la seva direccio vista des de l'observador (model_eclipsi.py), a una distancia
  que es tria al panell, amb el radi que li dona la seva mida aparent real.
- El Sol es tan lluny que es dibuixa "a l'infinit": a la seva direccio des de la camera, darrere
  de tota la resta, amb el radi que li dona la seva mida aparent real.
"""
import math

import glm
import moderngl as mgl
import numpy as np

from basecode import shaders
from basecode.objects import GouraudObject

# radis angulars (radi / distancia) aproximats per al 12/08/2026: la Terra es a prop de l'afeli
# (Sol a ~151,6 milions de km) i la Lluna es veu un 3,9 % mes gran que el Sol (eclipsi total)
RADI_SOL, DIST_SOL = 696000.0, 151.6e6       # km
RADI_LLUNA, DIST_LLUNA = 1737.4, 364200.0    # km (distancia des de l'observador)
RADI_ANGULAR_SOL = RADI_SOL / DIST_SOL
RADI_ANGULAR_LLUNA = RADI_LLUNA / DIST_LLUNA

# modes del shader basecode/shaders/esfera.frag
IL_LUMINADA, EMISSIVA, HALO = 0, 1, 2


def punt_esfera(theta, phi):
    """Coordenades esferiques (radi 1) -> cartesianes, amb l'eix polar = Y."""
    return (math.sin(theta) * math.cos(phi), math.cos(theta), math.sin(theta) * math.sin(phi))


class Esfera(GouraudObject):
    """Esfera de radi 1 centrada a l'origen; la posicio i la mida (escala) van a m_model."""
    N_THETA = 40   # franges de dalt a baix
    N_PHI = 80     # franges al voltant

    def __init__(self, app, color, mode=IL_LUMINADA):
        self.color = color
        self.mode = mode
        self.centre = glm.vec3(0.0)
        self.escala = glm.vec3(1.0)
        self.intensitat = 1.0     # opacitat del halo
        self.ambient = 1.0        # multiplica la llum ambient del Sol (light.Ia)
        super().__init__(app)

    def situar(self, centre, radi):
        self.centre = glm.vec3(centre)
        self.escala = glm.vec3(radi)

    def get_vertex_data(self):
        dt, dp = math.pi / self.N_THETA, 2 * math.pi / self.N_PHI
        vertexs = []
        for i in range(self.N_THETA):
            for j in range(self.N_PHI):
                v0 = punt_esfera(i * dt, j * dp)
                v1 = punt_esfera(i * dt, (j + 1) * dp)
                v2 = punt_esfera((i + 1) * dt, j * dp)
                v3 = punt_esfera((i + 1) * dt, (j + 1) * dp)
                for v in (v0, v2, v1, v1, v2, v3):
                    vertexs.append((self.color, v, v))  # radi 1: la normal es la posicio
        return np.array(vertexs, dtype='f4')

    def get_shader_program(self):
        # basecode/shaders/esfera.vert i .frag: llum direccional del Sol, emissiva o halo
        return shaders.load_program(self.ctx, 'esfera')

    def get_model_matrix(self):
        return glm.translate(self.centre) * glm.scale(self.escala)

    def on_init(self):
        self.shader_program['light.Ia'].write(self.app.light.Ia)
        self.shader_program['light.Id'].write(self.app.light.Id)
        self.shader_program['mode'].value = self.mode

    def render(self):
        if not self.visible:
            return
        sp = self.shader_program
        self.m_model = self.get_model_matrix()
        sp['m_model'].write(self.m_model)
        sp['sun_dir'].write(self.app.light.direccio())
        sp['cam_pos'].write(self.app.camera.position)
        sp['intensitat'].value = self.intensitat
        sp['ambient'].value = self.ambient
        if self.mode == HALO:  # es suma al que hi ha darrere (es transparent)
            self.ctx.enable(mgl.BLEND)
            self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE
            self.vao.render()
            self.ctx.disable(mgl.BLEND)
        else:
            self.vao.render()


class Lluna(Esfera):
    """La Lluna nova: la cara que veiem no te llum del Sol. Dins de l'atmosfera (primera persona)
    nomes es veu davant del disc del Sol, fosca (la resta es tan brillant com el cel)."""
    def __init__(self, app):
        super().__init__(app, color=(0.62, 0.61, 0.58))
        self.atmosfera = False

    def render(self):
        sp = self.shader_program
        sp['atmosfera'].value = self.atmosfera
        sp['radi_sol'].value = RADI_ANGULAR_SOL
        super().render()
