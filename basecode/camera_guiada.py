"""
Camera guiada: allunyar-se del punt d'observacio fins a l'espai per una trajectoria fixa, sense perdre's
(la geometria es a dades/trajectoria.py).

- Allunyar-se no es fer zoom: la camera es mou de debo (el zoom optic, canviar el camp de visio sense
  moure's, es el de la vista d'observacio).
- La posicio nomes depen del progres (0 = a prop del punt, 1 = vista ampla amb el Sol). La roda (o lliscar
  amb dos dits) i W / S el fan avancar o retrocedir; els mateixos passos enrere tornen exactament al mateix
  lloc, perque la posicio es una funcio del progres i no s'acumula res.
- La mirada es la de referencia del tram (cap al punt, la Terra, Terra-Lluna, Terra-Sol) mes un gir i una
  inclinacio que controla l'usuari (ratoli o fletxes). Canviar el progres no toca aquests dos angles; el
  boto Recentrar els posa a zero. Cap enquadrament automatic no els sobreescriu.
- La trajectoria es calcula amb el Sol i la Lluna d'un instant (l'ancora): en entrar al mode, en recentrar
  i en canviar d'ubicacio des del panell. Si l'hora canvia (reproduir, barra de temps), la camera no es mou
  (el temps es independent de la camera); els astres segueixen el seu cami i Recentrar torna a enquadrar.
- Salvaguardes (no acumulen res: depenen nomes del progres i de l'hora): la camera es queda a 20 m o mes
  del terreny dibuixat i fora de la Lluna (que es mou si l'hora canvia).
Mateixa estructura que les altres cameres: posicio (ECEF, km, float64), m_view (nomes gir: tot es dibuixa
relatiu a la camera), m_proj, update().
"""
import math

import glm
import numpy as np
from slimgui import imgui

from .camera_exploracio import FAR_KM, INCLINACIO_MAX
from .control_ratoli import graus_per_punt
from dades import geodesia
from dades.efemerides import RADI_LLUNA_KM
from dades.trajectoria import Trajectoria, orientacio, angles_cap_a, S1, S2, S3

FOV = 50.0                  # angle de visio vertical (graus), com la camera d'exploracio
PAS_RODA = 1.0 / 40.0       # progres per pas de roda: tot el recorregut en 40 passos
PASSOS_RODA_MAX = 3.0       # passos de roda per fotograma com a molt: un gest rapid no fa salts
VELOCITAT_TECLAT = 0.15     # progres per segon amb W / S (tot el recorregut en ~7 s)
MARGE_TERRA_KM = 0.02       # la camera sempre a 20 m o mes del terreny dibuixat
MARGE_LLUNA = 1.5           # i fora d'una esfera d'1,5 radis lunars
TRAMS = [(S1, 'A prop del punt'), (S2, 'Sortint cap a la Terra'), (S3, 'La Terra i la Lluna'),
         (1.0, 'La Terra, la Lluna i el Sol')]


class CameraGuiada:
    def __init__(self, app):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.fov = FOV
        self.progres = 0.0
        self.gir, self.inclinacio = 0.0, 0.0      # mirada de l'usuari, relativa a la de referencia
        self.trajectoria, self.hora_ancora = None, None
        self.posicio = app.ulls()

    # ------------------------------------------------------------ trajectoria
    def ancorar(self):
        """Calcula la trajectoria per al punt d'observacio i l'hora actuals (no toca ni el progres ni la
        mirada de l'usuari)."""
        app = self.app
        sol, lluna = app.ef.posicions(app.hora)
        o = app.observador
        self.trajectoria = Trajectoria(o.lat, o.lon, app.ulls(), sol, lluna)
        self.hora_ancora = app.hora

    def recentrar(self):
        """Accio explicita: trajectoria amb l'hora actual i la mirada de referencia del tram."""
        self.ancorar()
        self.gir, self.inclinacio = 0.0, 0.0

    def tram(self):
        return next(nom for s, nom in TRAMS if self.progres <= s)

    def moure_progres(self, delta):
        if math.isfinite(delta):
            self.progres = min(max(self.progres + delta, 0.0), 1.0)

    def avancar(self, passos):
        """Roda: passos positius (endavant) acosten al punt, negatius allunyen. Accepta passos fraccionaris
        (trackpad) i en limita el nombre per fotograma."""
        self.moure_progres(-min(max(passos, -PASSOS_RODA_MAX), PASSOS_RODA_MAX) * PAS_RODA)

    # ------------------------------------------------------------ mirada
    def girar_ratoli(self, dx, dy):
        v = graus_per_punt(self.fov, FOV)
        self.girar(dx * v, -dy * v)

    def girar(self, d_gir, d_inclinacio):
        self.orientar(self.gir + d_gir, self.inclinacio + d_inclinacio)

    def orientar(self, gir, inclinacio):
        """Gir normalitzat a (-180, 180] i inclinacio limitada a +-INCLINACIO_MAX (respecte de la referencia)."""
        if math.isfinite(gir) and math.isfinite(inclinacio):
            self.gir = 180.0 - (180.0 - gir) % 360.0
            self.inclinacio = min(max(inclinacio, -INCLINACIO_MAX), INCLINACIO_MAX)

    def mirar_cap_a(self, punt):
        """Mira cap a un punt (ECEF) des d'on es la camera, una sola vegada."""
        f, up = self.trajectoria.marc(self.progres)
        self.orientar(*angles_cap_a(f, up, np.asarray(punt) - self.posicio))

    def processar_ratoli(self, roda, capturat):
        """Roda: progres. Amb el cursor lliure, arrossegar gira; amb la mirada capturada, el gir el fa main.py."""
        if roda:
            self.avancar(roda)
        io = imgui.get_io()
        if capturat or io.want_capture_mouse:
            return
        if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
            dx, dy = io.mouse_delta
            if dx or dy:
                self.girar_ratoli(dx, dy)

    # ------------------------------------------------------------ cada fotograma
    def calcular_posicio(self):
        app = self.app
        p = self.trajectoria.posicio(self.progres)
        lat, lon, alt = (float(v) for v in geodesia.geodesiques(p))
        if alt < 10.0:
            minim = app.altitud_terra_km(lat, lon) + MARGE_TERRA_KM
            if alt < minim:
                p = geodesia.ecef(lat, lon, minim)
        d = p - app.lluna_ecef
        if np.linalg.norm(d) < MARGE_LLUNA * RADI_LLUNA_KM:
            p = app.lluna_ecef + d / np.linalg.norm(d) * MARGE_LLUNA * RADI_LLUNA_KM
        return p

    def direccio(self):
        """(direccio de la mirada, amunt de la camera), unitaris i perpendiculars."""
        f, up = self.trajectoria.marc(self.progres)
        return orientacio(f, up, self.gir, self.inclinacio)

    def update(self):
        if self.trajectoria is None:
            self.ancorar()
        self.posicio = self.calcular_posicio()
        d, up = self.direccio()
        self.m_view = glm.lookAt(glm.vec3(0.0), glm.vec3(*d), glm.vec3(*up))
        self.m_proj = glm.perspective(glm.radians(self.fov), self.aspect_ratio, 1e-6, FAR_KM)
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)
