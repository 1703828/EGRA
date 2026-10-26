"""
Les parets del cub de navegacio (dades/navegacio.py): sis cares translucides amb ratlles diagonals que
apareixen quan la camera s'hi acosta, per indicar on s'acaba l'espai on es pot anar.

Cada cara son dos triangles. Les cantonades es calculen a la CPU en doble precisio relatives a la camera
(com la resta de l'escena) i es tornen a escriure al VBO a cada fotograma. L'opacitat de cada cara depen de
la distancia de la camera al seu pla: 0 a mes de DISTANCIA_AVIS del costat, 1 a la paret.
Es dibuixa despres dels objectes opacs, amb barreja (blending) i sense escriure profunditat.
"""
import moderngl as mgl
import numpy as np

from .programes import carregar_programa

FRACCIO_AVIS = 0.03    # la paret es comenca a veure a un 3 % del costat del cub (~7 milions de km)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class ParetCub:
    def __init__(self, app, cub):
        self.app, self.cub = app, cub
        self.ctx = app.ctx
        self.distancia_avis = FRACCIO_AVIS * cub.costat_km
        self.shader_program = carregar_programa(self.ctx, 'paret')
        self.vbo = self.ctx.buffer(reserve=6 * 6 * 4 * 4)          # 6 cares x 6 vertexs x (x, y, z, cara)
        self.vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '3f 1f', 'in_position', 'in_cara')])
        # cantonades de cada cara: (eix, costat) i els dos eixos del pla
        self.cares = []
        for eix in range(3):
            u, v = [e for e in range(3) if e != eix]
            for costat in (0, 1):
                self.cares.append((eix, costat, u, v))
        self.opacitat = np.zeros(6)

    def render(self):
        rel = self.app.camera.posicio
        lim = (self.cub.minim - rel, self.cub.maxim - rel)       # km, en doble precisio
        distancies = self.cub.distancia_a_les_parets(rel)         # x-, y-, z-, x+, y+, z+
        dist = np.array([distancies[eix + 3 * costat] for eix, costat, _, _ in self.cares])
        self.opacitat = 1.0 - smoothstep(0.0, self.distancia_avis, dist)
        if not self.opacitat.any():
            return
        vertexs = []
        for i, (eix, costat, u, v) in enumerate(self.cares):
            quad = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = np.zeros(3)
                p[eix], p[u], p[v] = lim[costat][eix], lim[a][u], lim[b][v]
                quad.append([*p, i])
            vertexs += [quad[0], quad[1], quad[2], quad[0], quad[2], quad[3]]
        self.vbo.write(np.array(vertexs, 'f4').tobytes())
        sp = self.shader_program
        sp['coef_log'].value = self.app.coef_log
        sp['opacitat'].write(self.opacitat.astype('f4').tobytes())
        sp['distancia'].write(dist.astype('f4').tobytes())
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        fbo = self.ctx.fbo              # la mascara de profunditat es del framebuffer actiu
        fbo.depth_mask = False
        self.vao.render()
        fbo.depth_mask = True
        self.ctx.disable(mgl.BLEND)

    def destroy(self):
        for obj in (self.vao, self.vbo, self.shader_program):
            obj.release()
