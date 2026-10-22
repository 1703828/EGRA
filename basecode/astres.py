"""
Esferes de l'escena (fetes amb coordenades esferiques, com al repte 4): el Sol, la seva resplendor
(halo / corona) i la Lluna.

Tots es dibuixen a la seva posicio i mida reals (km), relatives a la camera: el GraphicsEngine en
calcula la posicio en coordenades terrestres (doble precisio), li resta la de la camera i crida
situar(). La profunditat es logaritmica (coef_log), perque a la mateixa imatge hi pot haver el
terra a un metre i el Sol a 150 milions de km.
"""
import math
import os

import glm
import moderngl as mgl
import numpy as np
from PIL import Image

from .objects import GouraudObject
from .programes import carregar_programa

# modes del shader basecode/shaders/esfera.frag
IL_LUMINADA, SOL, HALO, LLUNA = 0, 1, 2, 3
TEXTURA_LLUNA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'data', 'textures', 'lluna_1024.jpg')


def punt_esfera(theta, phi):
    """Coordenades esferiques (radi 1) -> cartesianes, amb l'eix polar = Y."""
    return (math.sin(theta) * math.cos(phi), math.cos(theta), math.sin(theta) * math.sin(phi))


class Esfera(GouraudObject):
    """Esfera de radi 1 centrada a l'origen; la posicio, l'orientacio i la mida van a m_model."""
    N_THETA = 64   # franges de dalt a baix
    N_PHI = 128    # franges al voltant

    def __init__(self, app, color, mode=IL_LUMINADA):
        self.color = color
        self.mode = mode
        self.centre = glm.vec3(0.0)      # relatiu a la camera (km)
        self.escala = glm.vec3(1.0)
        self.rotacio = glm.mat4(1.0)
        self.intensitat = 1.0     # opacitat del halo
        self.ambient = 1.0        # multiplica la llum ambient del Sol (light.Ia)
        self.sun_dir = glm.vec3(0.0, 1.0, 0.0)
        super().__init__(app)
        # el shader (esfera.frag) declara el sampler de la textura de la Lluna per a tots els modes: si
        # a la unitat 0 no hi ha cap textura completa, el controlador avisa ("unit 0 ... unloadable").
        # El Sol i el halo no la llegeixen, pero hi lliguem una textura d'1 pixel; la Lluna, la seva.
        self.textura = self.ctx.texture((1, 1), 3, bytes((255, 255, 255)))

    def situar(self, centre, radi, rotacio=None):
        self.centre = glm.vec3(centre)
        self.escala = glm.vec3(radi)
        if rotacio is not None:
            self.rotacio = rotacio

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
        # basecode/shaders/esfera.vert i .frag: il·luminada, Sol, halo o Lluna
        return carregar_programa(self.ctx, 'esfera')

    def get_model_matrix(self):
        return glm.translate(self.centre) * self.rotacio * glm.scale(self.escala)

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
        sp['cam_pos'].write(glm.vec3(0.0))          # tot es relatiu a la camera
        sp['coef_log'].value = self.app.coef_log
        if 'sun_dir' in sp:
            sp['sun_dir'].write(self.sun_dir)
        if 'intensitat' in sp:
            sp['intensitat'].value = self.intensitat
        if 'ambient' in sp:
            sp['ambient'].value = self.ambient
        if 'temps' in sp:
            sp['temps'].value = self.app.time
        self.textura.use(0)
        if 'textura' in sp:
            sp['textura'].value = 0
        if self.mode == HALO:  # es suma al que hi ha darrere (es transparent)
            self.ctx.enable(mgl.BLEND)
            self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE
            self.ctx.depth_mask = False
            self.vao.render()
            self.ctx.depth_mask = True
            self.ctx.disable(mgl.BLEND)
        else:
            self.vao.render()

    def destroy(self):
        super().destroy()
        self.textura.release()


class Lluna(Esfera):
    """La Lluna amb la textura de la NASA (CGI Moon Kit, LRO). Des de dins de l'atmosfera nomes es
    veu davant del disc del Sol, fosca (la resta es tan brillant com el cel)."""
    def __init__(self, app):
        super().__init__(app, color=(1.0, 1.0, 1.0), mode=LLUNA)
        self.atmosfera = False
        self.radi_sol = 0.0046            # radi angular del Sol vist des de la camera (rad)
        self.ambient = 0.15               # una mica de llum de la Terra (llum cendrosa)
        img = Image.open(TEXTURA_LLUNA).convert('RGB')
        self.textura.release()   # la d'1 pixel d'Esfera
        self.textura = self.ctx.texture(img.size, 3, img.tobytes())
        self.textura.build_mipmaps()
        self.textura.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)

    def render(self):
        sp = self.shader_program
        sp['atmosfera'].value = self.atmosfera
        sp['radi_sol'].value = self.radi_sol
        super().render()
