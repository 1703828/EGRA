"""
Camera d'exploracio: orbital al voltant d'un punt objectiu enganxat al terreny. Serveix per
inspeccionar el terreny i triar el punt d'observacio; no esta lligada a cap personatge ni observador.

Controls (es llegeixen de l'io d'imgui, que ja rep tots els esdeveniments de glfw):
  - arrossegar amb el boto esquerre:              gir i inclinacio
  - arrossegar amb el boto dret (o Maj + esquerre): desplacar l'objectiu sobre el terreny
  - roda:                                          zoom exponencial cap al punt del cursor
  - doble clic sobre el terreny:                   centrar l'objectiu en aquell punt (i el retorna,
                                                   perque main.py hi pugui posar l'observador)
Quan el cursor es sobre el panell (want_capture_mouse) la camera no reacciona.

Unitats en km. X = est, Y = altitud, Z = sud. Gir 0 = camera al sud mirant al nord.
Inclinacio negativa: la camera queda per sota de l'objectiu i mira amunt (si el terra ho permet).
"""
import math

import glm
from slimgui import imgui

FOV = 50.0              # angle de visio vertical (graus)
VELOCITAT_GIR = 0.3     # graus per pixel arrossegat
FACTOR_ZOOM = 0.85      # distancia x 0.85 per cada pas de roda
PITCH_MIN, PITCH_MAX = -30.0, 89.0


class CameraExploracio:
    def __init__(self, app, terrain):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.near, self.far = 0.01, 10.0
        self.dist_sol = 10.0           # on es dibuixa el Sol (darrere de tot)
        self.canviar_terreny(terrain)

    def canviar_terreny(self, terrain, punt=None):
        """Adapta la camera a un terreny nou. Si punt = (x, z) (el mateix lloc geografic que
        l'objectiu d'abans, en coordenades del terreny nou), es mante la vista al voltant d'aquest punt;
        si no, es posa la vista inicial del terreny."""
        self.terrain = terrain
        mida_km = max(terrain.mida)
        self.dist_min, self.dist_max = max(0.01, mida_km / 2000), 3.0 * mida_km
        self.inicial = (30.0, 35.0, 1.0 * mida_km)  # gir, inclinacio, distancia
        if punt is None:
            self.reset()
        else:
            self.target = glm.vec3(punt[0], 0.0, punt[1])  # gir, inclinacio i distancia es mantenen
            self.update()

    def reset(self):
        self.yaw, self.pitch, self.distance = self.inicial
        self.target = glm.vec3(0.0)  # centre del terreny (la Y es posa a update)
        self.update()

    # ------------------------------------------------------------ matrius

    def direccio(self):
        """Vector unitari de l'objectiu cap a la camera."""
        yaw, pitch = glm.radians(self.yaw), glm.radians(self.pitch)
        return glm.vec3(glm.cos(pitch) * glm.sin(yaw), glm.sin(pitch), glm.cos(pitch) * glm.cos(yaw))

    def endavant(self):
        """Direccio horitzontal en que mira la camera (de la camera cap a l'objectiu)."""
        yaw = glm.radians(self.yaw)
        return -glm.vec3(glm.sin(yaw), 0, glm.cos(yaw))

    def dreta(self):
        yaw = glm.radians(self.yaw)
        return glm.vec3(glm.cos(yaw), 0, -glm.sin(yaw))

    def girar(self, d_gir, d_inclinacio):
        """Fletxes: girar al voltant de l'objectiu (graus). d_gir > 0 gira la vista a la dreta i
        d_inclinacio > 0 mira mes amunt (la camera baixa)."""
        self.yaw = (self.yaw - d_gir + 180.0) % 360.0 - 180.0
        self.pitch -= d_inclinacio

    def azimut_vista(self):
        """Azimut (graus des del nord) cap on mira la camera."""
        return (-self.yaw) % 360.0

    def mirar_azimut(self, azimut):
        self.yaw = (-azimut + 180.0) % 360.0 - 180.0

    def update(self):
        t = self.terrain
        self.distance = min(max(self.distance, self.dist_min), self.dist_max)
        self.pitch = min(max(self.pitch, PITCH_MIN), PITCH_MAX)

        # objectiu dins del terreny i enganxat a la seva altitud (amb l'exageracio actual)
        mx, mz = t.mida.x / 2, t.mida.y / 2
        self.target.x = min(max(self.target.x, -mx), mx)
        self.target.z = min(max(self.target.z, -mz), mz)
        t.centre_curvatura = glm.vec2(self.target.x, self.target.z)  # la curvatura es mesura des d'aqui
        self.target.y = t.altitud_mon(self.target.x, self.target.z)

        # la camera no pot quedar sota el terra: si cal, pugem la inclinacio grau a grau
        marge = 0.02 * self.distance
        self.position = self.target + self.distance * self.direccio()
        while self.pitch < 89.0 and self.position.y < t.altitud_mon(self.position.x, self.position.z) + marge:
            self.pitch = min(self.pitch + 1.0, 89.0)
            self.position = self.target + self.distance * self.direccio()

        # near/far adaptatius: near segons el que tenim mes a prop, far fins a la cantonada mes llunyana
        altura_lliure = self.position.y - t.altitud_mon(self.position.x, self.position.z)
        self.near = max(self.distance / 1000, 0.2 * min(altura_lliure, self.distance))
        lluny = 0.0
        for cx in (-mx, mx):
            for cz in (-mz, mz):
                for cy in (t.cota_base - t.caiguda(cx, cz), t.altitud_max_mon()):
                    lluny = max(lluny, glm.length(glm.vec3(cx, cy, cz) - self.position))
        # la Lluna (si n'hi ha) tambe ha de cabre; el Sol es dibuixa encara mes lluny
        lluna = getattr(self.app, 'lluna', None)
        marge_far = 1.2
        if lluna is not None and lluna.visible:
            lluny = max(lluny, glm.length(lluna.centre - self.position) + lluna.escala.x)
            marge_far = 1.6
        self.dist_sol = 1.4 * lluny
        self.far = max(lluny * marge_far, self.near * 10)

        self.m_view = glm.lookAt(self.position, self.target, glm.vec3(0, 1, 0))
        self.m_proj = glm.perspective(glm.radians(FOV), self.aspect_ratio, self.near, self.far)
        # com set_camera del repte 4: totes les matrius noves a tots els objectes de l'escena
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)

    def desprojectar(self, px, py, profunditat, amplada, alcada):
        """Pixel del framebuffer (origen a baix a l'esquerra) + profunditat (0..1) -> punt del mon."""
        ndc = glm.vec4(2 * px / amplada - 1, 2 * py / alcada - 1, 2 * profunditat - 1, 1)
        p = glm.inverse(self.m_proj * self.m_view) * ndc
        return glm.vec3(p) / p.w

    # ------------------------------------------------------------ ratoli

    def processar_ratoli(self, punt_sota_cursor):
        """Es crida un cop per frame. punt_sota_cursor(): funcio que torna el punt del terreny
        sota el cursor (o None si es el cel); nomes es crida quan cal (zoom i doble clic).
        Retorna el punt del doble clic (o None)."""
        io = imgui.get_io()
        if io.want_capture_mouse:  # el cursor es sobre el panell
            return None
        dx, dy = io.mouse_delta
        esquerre = imgui.is_mouse_down(imgui.MouseButton.LEFT)
        dret = imgui.is_mouse_down(imgui.MouseButton.RIGHT)
        punt_doble_clic = None

        if imgui.is_mouse_double_clicked(imgui.MouseButton.LEFT):
            punt = punt_sota_cursor()
            if punt is not None:
                self.target = glm.vec3(punt)
                punt_doble_clic = punt
        elif dret or (esquerre and io.key_shift):
            self.desplacar(dx, dy)
        elif esquerre:
            self.yaw -= dx * VELOCITAT_GIR
            self.pitch += dy * VELOCITAT_GIR
            self.yaw = (self.yaw + 180.0) % 360.0 - 180.0

        if io.mouse_wheel != 0:
            self.zoom(FACTOR_ZOOM ** io.mouse_wheel, punt_sota_cursor())
        self.update()
        return punt_doble_clic

    def desplacar(self, dx, dy):
        """Moure l'objectiu sobre el terreny com si "agafessim" el terra amb el cursor."""
        alcada_pantalla = self.app.ctx.viewport[3] / imgui.get_io().display_framebuffer_scale[1]
        km_per_pixel = 2 * self.distance * math.tan(math.radians(FOV / 2)) / max(alcada_pantalla, 1)
        yaw = glm.radians(self.yaw)
        dreta = glm.vec3(glm.cos(yaw), 0, -glm.sin(yaw))     # cap a la dreta de la pantalla
        endavant = -glm.vec3(glm.sin(yaw), 0, glm.cos(yaw))  # de la camera cap a l'objectiu (horitzontal)
        escorc = max(math.sin(math.radians(self.pitch)), 0.2)  # el terra es veu escurcat si la camera es baixa
        self.target += km_per_pixel * (-dx * dreta + dy / escorc * endavant)

    def zoom(self, factor, punt=None):
        """Zoom exponencial. Si hi ha un punt sota el cursor, escalem camera i objectiu respecte
        d'aquest punt (el punt es queda quiet a la pantalla); si no, cap a l'objectiu."""
        nova = min(max(self.distance * factor, self.dist_min), self.dist_max)
        factor = nova / self.distance
        if punt is not None:
            self.target = punt + (self.target - punt) * factor
        self.distance = nova
