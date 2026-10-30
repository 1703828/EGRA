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
DIR_TEXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'textures')
TEXTURA_LLUNA = os.path.join(DIR_TEXTURES, 'lluna_1024.jpg')           # al Git
TEXTURA_LLUNA_ALTA = os.path.join(DIR_TEXTURES, 'lluna_8k.jpg')        # scripts/descarregar_textures.py --alta
ALTITUD_LLUNA = os.path.join(DIR_TEXTURES, 'lluna_altitud.npy')        # (km, float16), el mateix script
RADI_LLUNA_KM = 1737.4      # esfera de referencia de les altituds (LOLA)


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
        self.tint = (1.0, 1.0, 1.0)  # color del disc del Sol i del halo (main.py, actualitzar_cel)
        super().__init__(app)
        # el shader (esfera.frag) declara el sampler de la textura de la Lluna per a tots els modes: si
        # a la unitat 0 no hi ha cap textura completa, el controlador avisa ("unit 0 ... unloadable").
        # El Sol i el halo no la llegeixen, pero hi lliguem una textura d'1 pixel; la Lluna, la seva.
        self.textura = self.ctx.texture((1, 1), 3, bytes((255, 255, 255)))
        self.altitud = self.ctx.texture((1, 1), 1, np.zeros(1, 'f2').tobytes(), dtype='f2')   # relleu (Lluna)

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
        if 'tint' in sp:
            sp['tint'].value = tuple(self.tint)
        if 'intensitat' in sp:
            sp['intensitat'].value = self.intensitat
        if 'ambient' in sp:
            sp['ambient'].value = self.ambient
        if 'temps' in sp:
            sp['temps'].value = self.app.time
        if 'dins_atmosfera' in sp:
            sp['dins_atmosfera'].value = float(self.app.atmosfera)
        self.textura.use(0)
        self.altitud.use(1)
        if 'textura' in sp:
            sp['textura'].value = 0
        if 'altitud' in sp:
            sp['altitud'].value = 1
        if self.mode == HALO:  # es suma al que hi ha darrere (es transparent)
            self.ctx.enable(mgl.BLEND)
            self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE
            # sense escriure profunditat: a ModernGL la mascara de profunditat es del framebuffer actiu
            # (ctx.fbo), no del context
            fbo = self.ctx.fbo
            fbo.depth_mask = False
            self.vao.render()
            fbo.depth_mask = True
            self.ctx.disable(mgl.BLEND)
        else:
            self.vao.render()

    def destroy(self):
        super().destroy()
        self.textura.release()
        self.altitud.release()


class Lluna(Esfera):
    """La Lluna amb les dades de la NASA (CGI Moon Kit): color de la LRO i, si s'han baixat (descarregar_textures.py
    --alta), color a 8k i el relleu del LOLA, que fa ombra als crateres. Des de dins de l'atmosfera nomes es
    veu davant del disc del Sol, fosca (la resta es tan brillant com el cel)."""
    def __init__(self, app):
        super().__init__(app, color=(1.0, 1.0, 1.0), mode=LLUNA)
        self.atmosfera = False
        self.radi_sol = 0.0046            # radi angular del Sol vist des de la camera (rad)
        self.ambient = 0.15               # una mica de llum de la Terra (llum cendrosa)
        Image.MAX_IMAGE_PIXELS = None     # 8192 x 4096: mes gran que el limit de seguretat de PIL
        maxim = self.ctx.info['GL_MAX_TEXTURE_SIZE']
        cami = TEXTURA_LLUNA_ALTA if os.path.exists(TEXTURA_LLUNA_ALTA) else TEXTURA_LLUNA
        img = Image.open(cami).convert('RGB')
        if img.width > maxim:             # GPU antiga: la textura mes gran que admet
            img = img.resize((maxim, maxim // 2), Image.LANCZOS)
        self.textura.release()   # la d'1 pixel d'Esfera
        self.textura = self.ctx.texture(img.size, 3, img.tobytes())
        self.textura.build_mipmaps()
        self.textura.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textura.anisotropy = 16.0
        self.relleu = os.path.exists(ALTITUD_LLUNA)
        if self.relleu:
            h = np.load(ALTITUD_LLUNA)
            self.altitud.release()
            self.altitud = self.ctx.texture((h.shape[1], h.shape[0]), 1, np.ascontiguousarray(h).tobytes(), dtype='f2')
            self.altitud.build_mipmaps()
            self.altitud.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)

    def render(self):
        sp = self.shader_program
        sp['atmosfera'].value = self.atmosfera
        sp['radi_sol'].value = self.radi_sol
        sp['amb_relleu'].value = self.relleu
        sp['radi_lluna'].value = RADI_LLUNA_KM
        super().render()
