"""
El cel vist des de qualsevol lloc: dispersio de la llum del Sol a l'atmosfera (shaders/cel.frag; el model i les
aproximacions son a dades/atmosfera.py), amb l'ombra de la Lluna a cada punt del raig.

Dues passades:
  1. El calcul (cel.frag, 12 x 4 mostres per pixel) es fa en una textura petita (1/REDUCCIO de la resolucio en
     cada eix i com a molt AMPLADA_MAX px d'amplada): el cel canvia de color suaument i, a resolucio completa,
     costava ~10 ms per fotograma (i ~12 ms a 1/4 en una pantalla Retina).
  2. Es copia a la pantalla (cel_compon.frag, interpolacio lineal) amb un triangle que cobreix la pantalla a la
     profunditat maxima i el test "<=": nomes pinta els pixels on no hi ha res, i no escriu profunditat. Per
     tant no tapa ni desdibuixa els discs del Sol i la Lluna (que es dibuixen a resolucio completa) ni canvia el
     picking. El halo del Sol i les parets del cub, translucids, es dibuixen despres.
"""
import glm
import moderngl as mgl
import numpy as np

from .programes import carregar_programa
from dades import atmosfera

AMPLADA_MAX = 400     # el cel es calcula com a molt a 400 px d'amplada (a la pantalla Retina, ~1/6 per eix)
REDUCCIO = 4          # i com a molt a 1/4 de la resolucio en cada eix


class Cel:
    def __init__(self, app):
        self.app, self.ctx = app, app.ctx
        self.programa = carregar_programa(self.ctx, 'cel')
        self.vao = self.ctx.vertex_array(self.programa, [])
        self.programa_compon = carregar_programa(self.ctx, 'cel_compon')
        self.vao_compon = self.ctx.vertex_array(self.programa_compon, [])
        self.textura = self.fbo = None
        self.visible = True

    def preparar(self, mida):
        """Textura del cel a baixa resolucio per a una pantalla de la mida donada (es refa si canvia)."""
        amplada = max(16, min(mida[0] // REDUCCIO, AMPLADA_MAX))
        baixa = (amplada, max(16, round(amplada * mida[1] / max(mida[0], 1))))
        if self.textura is not None and self.textura.size == baixa:
            return
        if self.textura is not None:
            self.fbo.release()
            self.textura.release()
        self.textura = self.ctx.texture(baixa, 3, dtype='f2')    # mig float: sense esglaons al degradat
        self.textura.filter = (mgl.LINEAR, mgl.LINEAR)
        self.textura.repeat_x = self.textura.repeat_y = False
        self.fbo = self.ctx.framebuffer(color_attachments=[self.textura])

    def calcular(self):
        """Passada 1, abans de comencar el fotograma (com el mapa d'ombres): canviar de framebuffer a mig
        fotograma obliga la GPU (per rajoles, Apple) a desar i tornar a llegir tota la pantalla (~10 ms a 2560 px)."""
        if not self.visible:
            return
        app, sp = self.app, self.programa
        cam = app.camera
        rel = cam.posicio
        sp['vista_inv'].write(glm.transpose(glm.mat3(cam.m_view)))
        sp['escala_proj'].value = (1.0 / cam.m_proj[0][0], 1.0 / cam.m_proj[1][1])
        sp['cam_ecef'].write(glm.vec3(*rel))
        sp['alcada_km'].value = app.alcada_camera_km
        sp['radi_terra'].value = atmosfera.radi_terra(rel, app.alcada_camera_km)
        sp['sol_rel'].write(glm.vec3(*(app.sol_ecef - rel)))
        sp['lluna_rel'].write(glm.vec3(*(app.lluna_ecef - rel)))
        sp['radi_sol'].value, sp['radi_lluna'].value = app.radi_sol_km, app.radi_lluna_km
        sp['visible_camera'].value = 1.0 - app.tapada_camera
        pantalla, viewport = self.ctx.fbo, self.ctx.viewport
        self.preparar(viewport[2:])
        # calcul a baixa resolucio (sense test de profunditat: tots els pixels)
        self.fbo.use()
        self.ctx.disable(mgl.DEPTH_TEST)
        self.vao.render(mgl.TRIANGLES, vertices=3)
        self.ctx.enable(mgl.DEPTH_TEST)
        pantalla.use()
        self.ctx.viewport = viewport

    def render(self):
        """Passada 2, despres dels objectes opacs: copia el cel nomes on no hi ha res (profunditat maxima, test
        "<=", sense escriure-la)."""
        if not self.visible or self.textura is None:
            return
        pantalla = self.ctx.fbo
        self.textura.use(0)
        self.programa_compon['tex_cel'].value = 0
        self.ctx.depth_func = '<='
        pantalla.depth_mask = False
        self.vao_compon.render(mgl.TRIANGLES, vertices=3)
        pantalla.depth_mask = True
        self.ctx.depth_func = '<'

    def destroy(self):
        for obj in (self.vao, self.programa, self.vao_compon, self.programa_compon, self.fbo, self.textura):
            if obj is not None:
                obj.release()
