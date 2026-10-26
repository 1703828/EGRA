"""
Edificis de la zona de detall (Catastro INSPIRE; dades/edificis.py prepara la malla): volums opacs amb
coberta plana i facanes, dibuixats en el mateix sistema que la resta de l'escena (ECEF relatiu a la camera,
profunditat logaritmica). Com que escriuen la profunditat, tapen el que hi ha darrere des de qualsevol
camera: el disc del Sol, el halo (que es dibuixa despres i no escriu profunditat) i el terreny.

Segueix l'estructura dels objectes del repte 4 (VBO + VAO + shader + m_model, render, destroy).
La llum (directa del Sol i del cel) es calcula un cop per fotograma al centre dels edificis amb la mateixa
formula que el terreny: elevacio del Sol i part del Sol que hi tapa la Lluna.
"""
import math
import time

import glm
import numpy as np

from .programes import carregar_programa
from dades import geodesia
from dades.edificis import preparar_malla, perfil_edificis, fraccions_disc
from dades.model_eclipsi import area_tapada, angle_entre
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM


def suau(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Edificis:
    def __init__(self, app, zona, cami_mdt):
        """Carrega (o prepara, el primer cop) la malla de la zona. self.n_triangles = 0 si no n'hi ha."""
        self.app, self.ctx = app, app.ctx
        t0 = time.time()
        m = preparar_malla(zona, cami_mdt)
        self.temps_carrega = time.time() - t0
        self.n_parts = int(m['n_parts']) if m is not None else 0
        tri = m['triangles'] if m is not None else np.zeros((0, 3, 3), 'f4')
        self.n_triangles = len(tri)
        self.origen_ecef = m['origen'] if m is not None else np.zeros(3)
        self.memoria_gpu = tri.nbytes
        self.vores = m['vores'] if m is not None else np.zeros((0, 5))
        self.perfil, self.ull_perfil = None, None   # perfil d'horitzo dels edificis des dels ulls
        self.visible = True
        self.shader_program = carregar_programa(self.ctx, 'edifici')
        self.vbo = self.ctx.buffer(tri.astype('f4').tobytes()) if self.n_triangles else None
        self.vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '3f', 'in_position')]) if self.vbo else None
        lat, lon, _ = geodesia.geodesiques(self.origen_ecef) if self.n_triangles else (0.0, 0.0, 0.0)
        self.amunt = geodesia.base_local(float(lat), float(lon))[2]

    def llum(self):
        """(llum directa del Sol, llum del cel) al centre dels edificis, com a terrain.frag."""
        app = self.app
        s, l = app.sol_ecef - self.origen_ecef, app.lluna_ecef - self.origen_ecef
        elev = float(np.dot(self.amunt, s / np.linalg.norm(s)))      # sinus de l'elevacio del Sol
        rs = math.asin(RADI_SOL_KM / np.linalg.norm(s))
        rl = math.asin(RADI_LLUNA_KM / np.linalg.norm(l))
        visible = 1.0 - area_tapada(angle_entre(s, l), rs, rl)
        llum_sol = visible * suau(-0.0175, 0.0175, elev)
        dia = suau(-0.105, 0.07, elev)
        return llum_sol, max(0.03, dia * (0.04 + 0.96 * visible ** 0.4))

    def perfil_des_de(self, ull_ecef):
        """Perfil d'horitzo dels edificis des dels ulls (es torna a calcular nomes si els ulls es mouen)."""
        if self.ull_perfil is None or not np.allclose(self.ull_perfil, ull_ecef, atol=1e-6):
            self.perfil, self.ull_perfil = perfil_edificis(self.vores, ull_ecef), np.array(ull_ecef)
        return self.perfil

    def fraccions(self, ull_ecef):
        """(part del Sol tapada per la Lluna, per edificis, visible) des dels ulls, a l'hora actual."""
        app = self.app
        return fraccions_disc(self.perfil_des_de(ull_ecef), ull_ecef, app.sol_ecef, RADI_SOL_KM,
                              app.lluna_ecef, RADI_LLUNA_KM)

    def render(self):
        if not self.visible or self.vao is None:
            return
        app, sp = self.app, self.shader_program
        rel = app.camera.posicio
        sp['m_model'].write(glm.translate(glm.vec3(*(self.origen_ecef - rel))))
        sp['coef_log'].value = app.coef_log
        s = app.sol_ecef - self.origen_ecef
        sp['sol_dir'].write(glm.vec3(*(s / np.linalg.norm(s))))
        sp['llum_sol'].value, sp['llum_cel'].value = self.llum()
        sp['color_cel'].value = tuple(app.color_cel)
        sp['densitat_boira'].value = app.densitat_boira
        self.vao.render()

    def destroy(self):
        for obj in (self.vao, self.vbo, self.shader_program):
            if obj is not None:
                obj.release()
