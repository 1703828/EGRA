"""
Edificis de la zona de detall (Catastro INSPIRE; dades/edificis.py prepara la malla): volums opacs amb
coberta plana i facanes, dibuixats en el mateix sistema que la resta de l'escena (ECEF relatiu a la camera,
profunditat logaritmica). Com que escriuen la profunditat, tapen el que hi ha darrere des de qualsevol
camera: el disc del Sol, el halo (que es dibuixa despres i no escriu profunditat) i el terreny.

Segueix l'estructura dels objectes del repte 4 (VBO + VAO + shader + m_model, render, destroy).

Aspecte (shaders/edifici.frag): facanes amb finestres procedimentals, una fila per planta (plantes del Catastro,
cada 3 m) i colors de facana variats per edifici (aproximacio estetica); cobertes amb el color de l'ortofoto al
seu lloc (dada real, dades/edificis.colors_cobertes) o, si no n'hi ha, un color de teula o de terrat. Les dades
de cada part (color de coberta i plantes) van en una textura que el shader llegeix amb l'index de la part.
La llum (directa del Sol i del cel) es calcula un cop per fotograma al centre dels edificis amb la mateixa
formula que el terreny: elevacio del Sol i part del Sol que hi tapa la Lluna.
"""
import math
import time

import glm
import moderngl as mgl
import numpy as np

from .programes import carregar_programa
from dades import geodesia
from dades.edificis import preparar_malla, perfil_edificis, fraccions_disc, contorns_de_bytes
from dades.obstacles import Obstacles
from dades.model_eclipsi import area_tapada, angle_entre
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM
from dades import atmosfera
from dades.edificis import colors_cobertes, ALCADA_PLANTA_M

AMPLADA_TEXTURA_PARTS = 1024
UNITAT_PARTS = 0


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
        atr = m['atributs'] if m is not None else np.zeros((0, 3, 4), 'f4')
        self.n_triangles = len(tri)
        self.zona = zona
        self.contorns = contorns_de_bytes(m) if self.n_parts else None
        alcada = (m['cota_coberta'] - m['cota_sol']) if self.n_parts else np.zeros(0)
        self.plantes = np.clip(np.round(alcada / ALCADA_PLANTA_M), 1, 127).astype('u1')
        self.colors_coberta, self.camins_orto = None, None
        self.origen_ecef = m['origen'] if m is not None else np.zeros(3)
        self.memoria_gpu = tri.nbytes + atr.nbytes
        self.vores = m['vores'] if m is not None else np.zeros((0, 5))
        self.perfil, self.ull_perfil = None, None   # perfil d'horitzo dels edificis des dels ulls
        # els mateixos contorns com a obstacles (caminar, volar a prop del terra, punts d'observacio)
        self.obstacles = Obstacles(self.contorns, m['cota_coberta']) if self.n_parts else None
        self.visible = True
        self.shader_program = carregar_programa(self.ctx, 'edifici')
        # VBO entrellacat: posicio (3 floats) i atributs de la textura (u, v, llargada, part)
        vertexs = np.concatenate([tri.reshape(-1, 3), atr.reshape(-1, 4)], axis=1).astype('f4')
        self.vbo = self.ctx.buffer(vertexs.tobytes()) if self.n_triangles else None
        self.vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '3f 4f', 'in_position', 'in_atr')]) \
            if self.vbo else None
        self.tex_parts = None
        self.actualitzar_textura_parts()
        lat, lon, _ = geodesia.geodesiques(self.origen_ecef) if self.n_triangles else (0.0, 0.0, 0.0)
        self.amunt = geodesia.base_local(float(lat), float(lon))[2]

    def posar_cobertes(self, general, detall):
        """Color de les cobertes a partir de l'ortofoto de la zona (o sense, si no n'hi ha)."""
        if not self.n_parts or (general, detall) == self.camins_orto:
            return
        self.camins_orto = (general, detall)
        self.colors_coberta = colors_cobertes(self.zona, self.contorns, general, detall) if general else None
        self.actualitzar_textura_parts()

    def actualitzar_textura_parts(self):
        """Textura RGBA8 amb una texel per part: RGB = color de la coberta; A = plantes, + 128 si el color ve de
        l'ortofoto (si no, el shader en tria un de teula o de terrat)."""
        if not self.n_parts:
            return
        n, w = self.n_parts, AMPLADA_TEXTURA_PARTS
        h = (n + w - 1) // w
        d = np.zeros((h * w, 4), 'u1')
        d[:n, 3] = self.plantes
        if self.colors_coberta is not None:
            ok = ~np.isnan(self.colors_coberta[:, 0])
            d[:n][ok, :3] = np.round(self.colors_coberta[ok] * 255).astype('u1')
            d[:n][ok, 3] += 128
        if self.tex_parts is not None:
            self.tex_parts.release()
        self.tex_parts = self.ctx.texture((w, h), 4, d.tobytes())
        self.tex_parts.filter = (mgl.NEAREST, mgl.NEAREST)

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
        elev = float(np.dot(self.amunt, s / np.linalg.norm(s)))
        sp['color_sol'].value = tuple(float(v) for v in atmosfera.color_llum_sol(elev))
        sp['color_amb'].value = tuple(float(v) for v in atmosfera.color_llum_cel(elev))
        sp['amunt'].write(glm.vec3(*self.amunt))
        sp['densitat_boira'].value = app.densitat_boira
        sp['boira_sol'].value, sp['boira_contra'].value = app.boira_sol, app.boira_contra
        sp['sol_horitzontal'].write(app.sol_horitzontal)
        sp['amunt_camera'].write(app.amunt_camera)
        self.tex_parts.use(UNITAT_PARTS)
        sp['tex_parts'].value = UNITAT_PARTS
        # les cares del darrere no es dibuixen (tots els triangles miren cap a fora, dades/edificis.malla_zona):
        # el shader escriu gl_FragDepth i la GPU no pot descartar abans els fragments tapats
        self.ctx.enable(mgl.CULL_FACE)
        self.vao.render()
        self.ctx.disable(mgl.CULL_FACE)

    def destroy(self):
        for obj in (self.vao, self.vbo, self.shader_program, self.tex_parts):
            if obj is not None:
                obj.release()
