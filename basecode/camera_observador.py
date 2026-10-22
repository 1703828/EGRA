"""
Camera d'observacio: els ulls de l'observador, 1,7 m sobre el terra (app.ulls()).

- Arrossegar amb el ratoli (boto esquerre) o les fletxes: mirar al voltant.
- Roda: zoom (com uns prismatics): el Sol fa ~0,5 graus i sense zoom es veu molt petit.
- Si 'seguir_sol' es True, la camera mira el Sol cada frame (ho activa la tecla P); qualsevol gir
  manual ho desactiva.
La camera no canvia mai la ubicacio de l'observador (app.observador): nomes mira i fa zoom. Per
canviar de punt cal triar-lo a la camera d'exploracio (i no es pot durant la reproduccio).
Unitats en km. X = est, Y = altitud, Z = sud. Gir = azimut cap on mira (graus des del nord, horari).
"""
import glm
from slimgui import imgui

from dades.observador import ALCADA_ULLS_KM

FOV = 60.0               # angle de visio vertical sense zoom (graus)
FOV_MIN = 1.5            # zoom maxim: el Sol ocupa un terc de la pantalla
VELOCITAT_RATOLI = 0.15  # graus per pixel arrossegat
NEAR = 0.0005            # km (50 cm)


class CameraObservador:
    def __init__(self, app):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.yaw, self.pitch = 0.0, 10.0   # azimut i elevacio cap on mira (graus)
        self.seguir_sol = False
        self.fov = FOV
        self.position = glm.vec3(0.0)
        self.target = glm.vec3(0.0)        # punt del terra sota els peus (els eixos s'hi dibuixen)
        self.distance = 0.0                # la boira del terreny comenca a la camera
        self.near, self.far, self.dist_sol = NEAR, 10.0, 5.0

    def davant(self):
        yaw, pitch = glm.radians(self.yaw), glm.radians(self.pitch)
        return glm.vec3(glm.cos(pitch) * glm.sin(yaw), glm.sin(pitch), -glm.cos(pitch) * glm.cos(yaw))

    def endavant(self):
        """Direccio horitzontal en que mira la camera (per caminar)."""
        yaw = glm.radians(self.yaw)
        return glm.vec3(glm.sin(yaw), 0, -glm.cos(yaw))

    def dreta(self):
        yaw = glm.radians(self.yaw)
        return glm.vec3(glm.cos(yaw), 0, glm.sin(yaw))

    def girar(self, d_gir, d_inclinacio):
        self.yaw = (self.yaw + d_gir) % 360.0
        self.pitch += d_inclinacio
        self.seguir_sol = False

    def azimut_vista(self):
        return self.yaw % 360.0

    def mirar(self, azimut, elevacio):
        self.yaw, self.pitch = azimut % 360.0, elevacio

    def zoom(self):
        return FOV / self.fov

    def processar_ratoli(self):
        io = imgui.get_io()
        if io.want_capture_mouse:
            return
        if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
            dx, dy = io.mouse_delta
            if dx or dy:  # amb zoom, el ratoli gira menys (com amb uns prismatics)
                v = VELOCITAT_RATOLI * self.fov / FOV
                self.girar(dx * v, -dy * v)
        if io.mouse_wheel != 0:
            self.fov = min(max(self.fov * 0.85 ** io.mouse_wheel, FOV_MIN), FOV)

    def update(self):
        if self.seguir_sol:
            self.mirar(self.app.light.azimut, self.app.light.elevacio)
        self.pitch = min(max(self.pitch, -89.0), 89.0)
        self.position = self.app.ulls()
        self.target = self.position - glm.vec3(0, ALCADA_ULLS_KM, 0)   # el terra sota els peus

        # far: la cantonada del terreny mes llunyana i la Lluna; el Sol es dibuixa encara mes lluny
        t = self.app.terrain
        mx, mz = t.mida.x / 2, t.mida.y / 2
        lluny = max(glm.length(glm.vec3(cx, cy, cz) - self.position)
                    for cx in (-mx, mx) for cy in (t.cota_base, t.altitud_max_mon()) for cz in (-mz, mz))
        lluna = self.app.lluna
        lluny = max(lluny, glm.length(lluna.centre - self.position) + lluna.escala.x)
        self.dist_sol = 1.4 * lluny
        self.far = 1.6 * lluny

        self.m_view = glm.lookAt(self.position, self.position + self.davant(), glm.vec3(0, 1, 0))
        self.m_proj = glm.perspective(glm.radians(self.fov), self.aspect_ratio, self.near, self.far)
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)
