"""
La Terra: l'el·lipsoide WGS84 amb una textura de color, il·luminada pel Sol i amb l'ombra de la Lluna.

Segueix l'estructura dels objectes del repte 4 (VBO/IBO + VAO + shader + m_model, render, destroy).
La malla es una graella de longitud x latitud (1024 x 512 trams, ~0,35°): la cara plana entre
vertexs queda com a molt ~120 m per sota de l'el·lipsoide, que el terreny detallat tapa.
Coordenades terrestres (ECEF) en km; es dibuixa relativa a la camera (app.camera.posicio).
Textura: NASA Visible Earth, "Blue Marble" (scripts/descarregar_textures.py).
"""
import os

import glm
import moderngl as mgl
import numpy as np
from PIL import Image

from .programes import carregar_programa
from dades import geodesia

TEXTURA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'textures', 'terra_2048.jpg')
N_LON, N_LAT = 1024, 512


class Terra:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        self.vbo, self.ibo = self.get_vbo()
        self.shader_program = carregar_programa(self.ctx, 'terra')
        self.vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_uv')],
                                         index_buffer=self.ibo)
        img = Image.open(TEXTURA).convert('RGB')
        self.textura = self.ctx.texture(img.size, 3, img.tobytes())
        self.textura.build_mipmaps()
        self.textura.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textura.repeat_y = False
        self.visible = True

    def get_vbo(self):
        lon = np.linspace(-180.0, 180.0, N_LON + 1)
        lat = np.linspace(90.0, -90.0, N_LAT + 1)          # fila 0 = pol nord, com la textura
        lon2, lat2 = np.meshgrid(lon, lat)
        p = geodesia.ecef(lat2, lon2, 0.0)
        fi, la = np.radians(lat2), np.radians(lon2)
        n = np.stack([np.cos(fi) * np.cos(la), np.cos(fi) * np.sin(la), np.sin(fi)], axis=-1)
        uv = np.stack([(lon2 + 180.0) / 360.0, (90.0 - lat2) / 180.0], axis=-1)
        vertexs = np.concatenate([p, n, uv], axis=-1).reshape(-1, 8).astype('f4')
        i = np.arange((N_LAT + 1) * (N_LON + 1)).reshape(N_LAT + 1, N_LON + 1)
        a, b, c, d = i[:-1, :-1], i[:-1, 1:], i[1:, :-1], i[1:, 1:]
        index = np.stack([a, c, b, b, c, d], axis=-1).reshape(-1).astype('i4')
        return self.ctx.buffer(vertexs), self.ctx.buffer(index)

    def render(self):
        if not self.visible:
            return
        app, sp = self.app, self.shader_program
        rel = app.camera.posicio
        sp['m_model'].write(glm.translate(glm.vec3(*(-rel))))       # el centre de la Terra, des de la camera
        sp['sol_rel'].write(glm.vec3(*(app.sol_ecef - rel)))
        sp['lluna_rel'].write(glm.vec3(*(app.lluna_ecef - rel)))
        sp['radi_sol'].value, sp['radi_lluna'].value = app.radi_sol_km, app.radi_lluna_km
        sp['coef_log'].value = app.coef_log
        sp['atmosfera'].value = app.atmosfera
        sp['ressaltar_ombra'].value = app.ressaltar_ombra
        self.textura.use(0)
        sp['textura'].value = 0
        self.vao.render()

    def destroy(self):
        for obj in (self.vbo, self.ibo, self.vao, self.shader_program, self.textura):
            obj.release()
