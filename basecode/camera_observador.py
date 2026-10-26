"""
Camera d'observacio: els ulls de l'observador, 1,7 m sobre el terra (app.ulls(), ECEF en km).

- La posicio no es mou: nomes es gira el cap. La mirada conserva l'orientacio que deixa l'usuari;
  el Sol no se segueix automaticament.
- Arrossegar amb el ratoli (boto esquerre), moure'l amb la mirada capturada (main.py) o les fletxes:
  mirar al voltant.
- Roda (o lliscar amb dos dits al trackpad): zoom com uns prismatics (camp de visio), sense moure els
  ulls. El Sol fa ~0,5 graus i sense zoom es veu petit.
Rumb = graus des del nord en sentit horari; inclinacio = graus sobre l'horitzo del lloc.
"""
import glm
from slimgui import imgui

from .control_ratoli import SENSIBILITAT

from .camera_exploracio import matrius

FOV = 60.0               # angle de visio vertical sense zoom (graus)
FOV_MIN = 1.5            # zoom maxim: el Sol ocupa un terc de la pantalla
VELOCITAT_RATOLI = 0.15  # graus per pixel arrossegat


class CameraObservador:
    def __init__(self, app):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.rumb, self.inclinacio = 0.0, 10.0
        self.fov = FOV
        self.posicio = app.ulls()

    def girar_ratoli(self, dx, dy):
        """Moviment del ratoli capturat (punts de pantalla): mateixa sensibilitat que en arrossegar, i menor
        amb zoom. Cap inercia: la mirada nomes canvia quan el ratoli es mou."""
        v = SENSIBILITAT * self.fov / FOV
        self.girar(dx * v, -dy * v)

    def girar(self, d_rumb, d_inclinacio):
        self.rumb = (self.rumb + d_rumb) % 360.0
        self.inclinacio = min(max(self.inclinacio + d_inclinacio, -89.0), 89.0)

    def mirar(self, rumb, inclinacio):
        self.rumb, self.inclinacio = rumb % 360.0, inclinacio

    def zoom(self):
        return FOV / self.fov

    def processar_ratoli(self, roda, capturat):
        """Roda (passos d'aquest fotograma, main.py): zoom. Amb el cursor lliure, arrossegar gira el cap;
        amb la mirada capturada, el gir el fa main.py."""
        if roda:
            roda = min(max(roda, -3.0), 3.0)   # un gest rapid no fa salts
            self.fov = min(max(self.fov * 0.85 ** roda, FOV_MIN), FOV)
        io = imgui.get_io()
        if capturat or io.want_capture_mouse:
            return
        if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
            dx, dy = io.mouse_delta
            if dx or dy:  # amb zoom, el ratoli gira menys (com amb uns prismatics)
                v = VELOCITAT_RATOLI * self.fov / FOV
                self.girar(dx * v, -dy * v)

    def update(self):
        self.posicio = self.app.ulls()
        self.m_view, self.m_proj = matrius(self.posicio, self.rumb, self.inclinacio, self.fov, self.aspect_ratio)
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)
