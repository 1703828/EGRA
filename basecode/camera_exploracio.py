"""
Camera d'exploracio: una camera lliure que es pot moure del terreny fins a l'espai.

- Posicio en coordenades terrestres (ECEF, km, float64). La GPU la rep sempre com a origen: tots els
  objectes es dibuixen relatius a la camera, perque el float32 de la GPU no perdi precisio.
- Orientacio: rumb (graus des del nord, sentit horari) i inclinacio (graus sobre l'horitzo del lloc
  on es la camera). "Amunt" es la vertical d'aquell lloc.
- Ratoli (arrossegar) i fletxes: girar la mirada. W A S D: moure's endavant, enrere i als costats
  (en horitzontal). E i Q: pujar i baixar. Roda: avancar o retrocedir en la direccio en que es mira.
- La velocitat es proporcional a l'altura sobre el terra: a 1 km d'altura es va a ~1 km/s i a
  10.000 km, a ~10.000 km/s. Aixi es pot explorar tant una vall com la Terra des de l'espai.
Quan el cursor es sobre el panell (want_capture_mouse) la camera no reacciona al ratoli.
"""
import math

import glm
import numpy as np
from slimgui import imgui

from dades import geodesia

FOV = 50.0                  # angle de visio vertical (graus)
VELOCITAT_GIR = 0.2         # graus per pixel arrossegat
FAR_KM = 1e9                # pla llunya: mes enlla del Sol (150 milions de km)
ALCADA_MINIMA_KM = 0.002    # 2 m sobre el terra
COEF_LOG = 2.0 / math.log2(FAR_KM + 1.0)   # per a la profunditat logaritmica dels shaders


def direccio_mirada(lat, lon, rumb, inclinacio):
    """Vector unitari (ECEF) cap on es mira des de (lat, lon) amb el rumb i la inclinacio donats."""
    est, nord, amunt = geodesia.base_local(lat, lon)
    r, i = math.radians(rumb), math.radians(inclinacio)
    return math.cos(i) * (math.sin(r) * est + math.cos(r) * nord) + math.sin(i) * amunt


def matrius(posicio, rumb, inclinacio, fov, aspecte):
    """m_view (nomes gir: la camera es a l'origen) i m_proj per a una camera a posicio (ECEF, km)."""
    lat, lon, _ = geodesia.geodesiques(np.asarray(posicio))
    _, _, amunt = geodesia.base_local(float(lat), float(lon))
    davant = direccio_mirada(float(lat), float(lon), rumb, inclinacio)
    m_view = glm.lookAt(glm.vec3(0.0), glm.vec3(*davant), glm.vec3(*amunt))
    # near molt petit: amb la profunditat logaritmica no cal un near gran per tenir precisio
    m_proj = glm.perspective(glm.radians(fov), aspecte, 1e-6, FAR_KM)
    return m_view, m_proj


class CameraExploracio:
    def __init__(self, app, posicio, rumb=0.0, inclinacio=-20.0):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.posicio = np.asarray(posicio, dtype=float)
        self.rumb, self.inclinacio = rumb, inclinacio
        self.fov = FOV
        self.update()

    def geodesiques(self):
        lat, lon, alt = geodesia.geodesiques(self.posicio)
        return float(lat), float(lon), float(alt)

    def alcada_sobre_terra(self):
        """km per sobre del terra (del terreny dibuixat si n'hi ha; si no, de l'el·lipsoide)."""
        lat, lon, alt = self.geodesiques()
        return alt - self.app.altitud_terra_km(lat, lon)

    def velocitat(self):
        """km/s: proporcional a l'altura, amb un minim de 20 m/s."""
        return max(0.02, 0.8 * self.alcada_sobre_terra())

    def davant(self):
        lat, lon, _ = self.geodesiques()
        return direccio_mirada(lat, lon, self.rumb, self.inclinacio)

    def moure(self, endavant, dreta, amunt, dt):
        """Desplacament amb el teclat: endavant i dreta en horitzontal, amunt en vertical (-1, 0 o 1)."""
        lat, lon, _ = self.geodesiques()
        est, nord, vertical = geodesia.base_local(lat, lon)
        r = math.radians(self.rumb)
        horitzontal = math.sin(r) * est + math.cos(r) * nord
        costat = math.cos(r) * est - math.sin(r) * nord
        pas = (endavant * horitzontal + dreta * costat + amunt * vertical) * self.velocitat() * dt
        self.posicio = self.posicio + pas
        self.no_sota_terra()

    def avancar(self, quantitat):
        """Roda: avanca (o retrocedeix) en la direccio de la mirada una fraccio de l'altura."""
        self.posicio = self.posicio + self.davant() * quantitat * max(0.01, 0.25 * self.alcada_sobre_terra())
        self.no_sota_terra()

    def no_sota_terra(self):
        lat, lon, alt = self.geodesiques()
        minim = self.app.altitud_terra_km(lat, lon) + ALCADA_MINIMA_KM
        if alt < minim:
            self.posicio = geodesia.ecef(lat, lon, minim)

    def girar(self, d_rumb, d_inclinacio):
        self.rumb = (self.rumb + d_rumb) % 360.0
        self.inclinacio = min(max(self.inclinacio + d_inclinacio, -89.9), 89.9)

    def processar_ratoli(self, punt_sota_cursor):
        """Arrossegar: girar. Roda: avancar. Doble clic: retorna el punt del terreny (o None)."""
        io = imgui.get_io()
        if io.want_capture_mouse:
            return None
        if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
            dx, dy = io.mouse_delta
            if dx or dy:
                self.girar(dx * VELOCITAT_GIR * self.fov / FOV, -dy * VELOCITAT_GIR * self.fov / FOV)
        if io.mouse_wheel != 0:
            self.avancar(io.mouse_wheel)
        if imgui.is_mouse_double_clicked(imgui.MouseButton.LEFT):
            return punt_sota_cursor()
        return None

    def update(self):
        self.m_view, self.m_proj = matrius(self.posicio, self.rumb, self.inclinacio, self.fov, self.aspect_ratio)
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)

    def desprojectar(self, px, py, profunditat, amplada, alcada):
        """Pixel del framebuffer (origen a baix a l'esquerra) + profunditat logaritmica (0..1) ->
        punt del mon (ECEF, km). Desfa la profunditat logaritmica: w = 2^(d · log2(far + 1)) - 1."""
        w = 2.0 ** (profunditat * 2.0 / COEF_LOG) - 1.0
        x_ndc, y_ndc = 2 * px / amplada - 1, 2 * py / alcada - 1
        ull = glm.vec4(x_ndc * w / self.m_proj[0][0], y_ndc * w / self.m_proj[1][1], -w, 1.0)
        rel = glm.inverse(self.m_view) * ull
        return self.posicio + np.array([rel.x, rel.y, rel.z], dtype=float)
