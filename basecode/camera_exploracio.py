"""
Camera d'exploracio: una camera lliure que es pot moure del terreny fins a l'espai.

- Posicio en coordenades terrestres (ECEF, km, float64). La GPU la rep sempre com a origen: tots els
  objectes es dibuixen relatius a la camera, perque el float32 de la GPU no perdi precisio.
- Orientacio: la direccio de la mirada es un vector fix del mon (ECEF, davant_ecef). Nomes canvia quan
  l'usuari gira; moure's no la modifica (abans es guardava com a rumb i inclinacio respecte de l'horitzo
  del lloc, i en moure's per l'espai la mirada derivava). rumb i inclinacio es calculen a partir del
  vector, respecte de l'horitzo del lloc on es la camera; girar fa voltar la mirada al voltant de la
  vertical d'aquell lloc (com en un joc en primera persona).
- Ratoli (capturat o arrossegant) i fletxes: girar la mirada. La sensibilitat no depen de la distancia.
- W A S D: endavant, enrere i als costats en horitzontal. E i Q: endavant i enrere en la direccio de la
  mirada (si es mira el Sol, E s'hi acosta). Roda o dos dits al trackpad: el mateix que E i Q, a passos.
- Velocitat adaptada a l'entorn: proporcional a la distancia a la superficie mes propera (el terra, la
  Lluna o el Sol): precisa a prop, rapida a l'espai. Com que es pren el minim de les tres distancies, no
  salta quan canvia quin astre es el mes proper. Cap pas pot ser mes llarg que la meitat d'aquesta distancia
  (ni amb un fotograma lent), i despres de cada moviment la camera es treu de dins dels astres.
- Viatge (apropar-se a un astre, iniciar_viatge): transicio suau i breu; qualsevol entrada de moviment el
  cancel·la (main.py). Acaba amb la camera quieta.
- La camera no pot sortir del cub de navegacio (app.cub, dades/navegacio.py): tota posicio nova passa pel
  cub, i a la paret s'atura nomes el moviment cap a fora.
Quan el cursor es sobre el panell (want_capture_mouse) la camera no reacciona al ratoli.
"""
import math

import glm
import numpy as np
from slimgui import imgui

from dades import geodesia
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM
from dades.navegacio import planificar_trajecte, distancia_enquadrar, suavitzat
from .control_ratoli import SENSIBILITAT

FOV = 50.0                  # angle de visio vertical (graus)
VELOCITAT_GIR = 0.2         # graus per pixel arrossegat
FAR_KM = 1e9                # pla llunya: mes enlla del Sol (150 milions de km)
ALCADA_MINIMA_KM = 0.001    # 1 m sobre el terra (els ulls de l'observador son a 1,7 m)
DISTANCIA_MINIMA_KM = 1.0   # i 1 km sobre la superficie de la Lluna i del Sol
VELOCITAT_RELATIVA = 1.2    # km/s per km de distancia a la superficie mes propera (del terra a 20.000 km mirant
                            # amunt, ~14 s mantenint E; amb Ctrl, ~3 s)
VELOCITAT_MINIMA = 0.005    # km/s (5 m/s)
PAS_MAXIM = 0.5             # cap pas pot superar aquesta fraccio de la distancia a la superficie
PAS_RODA = 0.35             # cada pas de roda acosta o allunya un 35 % de la distancia a la superficie
PASSOS_RODA_MAX = 3.0       # passos de roda per fotograma com a molt: un gest rapid no fa salts
INCLINACIO_MAX = 89.99      # graus: la mirada no pot quedar exactament vertical (no es capgira)
TEMPS_FOV = 0.25            # s: en passar de l'observacio, el camp de visio torna a FOV sense salt
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
        self.posicio = posicio
        self.amunt_vista = None        # l'"amunt" de la imatge de l'ultim fotograma
        self.orientar(rumb, inclinacio)
        self.fov = self.fov_objectiu = FOV
        self.viatge = None
        self.update()

    # ------------------------------------------------------------ posicio i orientacio

    @property
    def posicio(self):
        return self._posicio

    @posicio.setter
    def posicio(self, p):
        """Tota posicio nova passa pel cub de navegacio (si n'hi ha): cada coordenada que en surt es queda
        a la paret. A la paret s'atura nomes el moviment cap a fora, sense rebots."""
        p = np.asarray(p, dtype=float)
        cub = getattr(self.app, 'cub', None)
        self._posicio = cub.limitar(p) if cub is not None else p

    def geodesiques(self):
        lat, lon, alt = geodesia.geodesiques(self.posicio)
        return float(lat), float(lon), float(alt)

    def orientar(self, rumb, inclinacio):
        """Mirada amb un rumb i una inclinacio respecte de l'horitzo del lloc on es la camera."""
        lat, lon, _ = self.geodesiques()
        inclinacio = min(max(inclinacio, -INCLINACIO_MAX), INCLINACIO_MAX)
        self.davant_ecef = direccio_mirada(lat, lon, rumb, inclinacio)

    def mirar_cap_a(self, punt):
        """Orienta la mirada cap a un punt (ECEF), un sol cop."""
        lat, lon, _ = self.geodesiques()
        self.orientar(*geodesia.azimut_elevacio(np.asarray(punt) - self.posicio, lat, lon))

    def _rumb_inclinacio(self):
        lat, lon, _ = self.geodesiques()
        return geodesia.azimut_elevacio(self.davant_ecef, lat, lon)

    @property
    def rumb(self):
        return self._rumb_inclinacio()[0]

    @rumb.setter
    def rumb(self, valor):
        self.orientar(valor, self._rumb_inclinacio()[1])

    @property
    def inclinacio(self):
        return self._rumb_inclinacio()[1]

    @inclinacio.setter
    def inclinacio(self, valor):
        self.orientar(self._rumb_inclinacio()[0], valor)

    def davant(self):
        return self.davant_ecef

    def girar(self, d_rumb, d_inclinacio):
        """Gira la mirada al voltant de la vertical del lloc (rumb) i amunt o avall (inclinacio)."""
        rumb, inclinacio = self._rumb_inclinacio()
        self.orientar(rumb + d_rumb, inclinacio + d_inclinacio)

    def girar_ratoli(self, dx, dy):
        """Moviment del ratoli capturat (punts de pantalla): mateixa sensibilitat que en arrossegar, i menor
        amb zoom. No depen de la distancia ni del temps del fotograma; cap inercia."""
        v = SENSIBILITAT * self.fov / FOV
        self.girar(dx * v, -dy * v)

    # ------------------------------------------------------------ distancies i velocitat

    def alcada_sobre_terra(self):
        """km per sobre del terra (del terreny dibuixat si n'hi ha; si no, de l'el·lipsoide)."""
        lat, lon, alt = self.geodesiques()
        return alt - self.app.altitud_terra_km(lat, lon)

    def cossos(self):
        """(nom, centre ECEF, radi) de la Lluna i el Sol a l'hora actual."""
        app = self.app
        return [('Lluna', getattr(app, 'lluna_ecef', None), RADI_LLUNA_KM), ('Sol', getattr(app, 'sol_ecef', None), RADI_SOL_KM)]

    def superficie_propera(self):
        """(distancia en km a la superficie mes propera, direccio unitaria cap al seu centre)."""
        d, cap = self.alcada_sobre_terra(), -self.posicio / np.linalg.norm(self.posicio)
        for _, centre, radi in self.cossos():
            if centre is None:
                continue
            v = centre - self.posicio
            dist = float(np.linalg.norm(v)) - radi
            if dist < d:
                d, cap = dist, v / np.linalg.norm(v)
        return max(d, ALCADA_MINIMA_KM), cap

    def velocitat(self):
        """km/s: proporcional a la distancia a la superficie mes propera, amb un minim de 5 m/s."""
        return max(VELOCITAT_MINIMA, VELOCITAT_RELATIVA * self.superficie_propera()[0])

    def desplacar(self, pas):
        """Mou la camera un vector (km): com a molt PAS_MAXIM de la distancia a la superficie mes propera
        (no es pot travessar res d'un sol pas) i, despres, fora del terra i dels astres."""
        d, _ = self.superficie_propera()
        longitud = float(np.linalg.norm(pas))
        if longitud > PAS_MAXIM * d:
            pas = pas * (PAS_MAXIM * d / longitud)
        self.posicio = self.posicio + pas
        self.fora_dels_astres()

    def moure(self, endavant, dreta, avant_mirada, dt):
        """Teclat (-1, 0 o 1): W/S endavant i enrere en horitzontal, A/D als costats, E/Q en la direccio de
        la mirada. La velocitat es per segon (es multiplica pel temps del fotograma)."""
        lat, lon, _ = self.geodesiques()
        est, nord, _ = geodesia.base_local(lat, lon)
        r = math.radians(self.rumb)
        horitzontal = math.sin(r) * est + math.cos(r) * nord
        costat = math.cos(r) * est - math.sin(r) * nord
        direccio = endavant * horitzontal + dreta * costat + avant_mirada * self.davant_ecef
        self.desplacar(direccio * self.velocitat() * dt)

    def avancar(self, passos):
        """Roda (passos > 0: endavant) en la direccio de la mirada. n passos multipliquen la distancia a la
        superficie mes propera per (1 + PAS_RODA)^-n: endavant s'hi acosta cada cop mes a poc a poc; enrere
        se n'allunya cada cop mes de pressa. El desplacament es aquest canvi dividit pel cosinus entre la
        mirada i la direccio cap a l'astre (minim 0,3): mirant de biaix, nomes una part del pas acosta.
        El trackpad dona passos fraccionaris. Com a molt PASSOS_RODA_MAX per fotograma."""
        passos = min(max(passos, -PASSOS_RODA_MAX), PASSOS_RODA_MAX)
        d, cap = self.superficie_propera()
        canvi = d * (1.0 - (1.0 + PAS_RODA) ** -passos)           # > 0 endavant
        cosinus = max(abs(float(np.dot(self.davant_ecef, cap))), 0.3)
        pas = self.davant_ecef * canvi / cosinus
        self.posicio = self.posicio + pas                          # la roda pot fer passos mes llargs que
        self.fora_dels_astres()                                    # PAS_MAXIM: el canvi ja es d'una fraccio de d

    def fora_dels_astres(self):
        """Si la camera ha quedat sota el terra o dins de la Lluna o el Sol, la treu fins a la superficie."""
        lat, lon, alt = self.geodesiques()
        minim = self.app.altitud_terra_km(lat, lon) + ALCADA_MINIMA_KM
        if alt < minim:
            self.posicio = geodesia.ecef(lat, lon, minim)
        for _, centre, radi in self.cossos():
            if centre is None:
                continue
            v = self.posicio - centre
            if np.linalg.norm(v) < radi + DISTANCIA_MINIMA_KM:
                self.posicio = centre + v / np.linalg.norm(v) * (radi + DISTANCIA_MINIMA_KM)

    no_sota_terra = fora_dels_astres

    # ------------------------------------------------------------ viatge cap a un astre

    def iniciar_viatge(self, centre_fn, radi, obstacles):
        """Transicio fins a una distancia des d'on l'astre es veu sencer, amb marge. centre_fn() dona el
        centre actual de l'astre (es pot moure durant el viatge si el temps corre); obstacles: (centre, radi)
        dels altres astres, que el cami no travessa. La mirada gira cap a l'astre durant el primer terc."""
        r_final = distancia_enquadrar(radi, self.fov_objectiu, self.aspect_ratio)
        trajecte = planificar_trajecte(self.posicio, centre_fn(), r_final, obstacles)
        self.viatge = dict(trajecte=trajecte, centre=centre_fn, t=0.0, davant0=self.davant_ecef.copy())

    def actualitzar_viatge(self, dt):
        """Un fotograma del viatge (dt en segons reals). Al final, la camera queda quieta mirant l'astre."""
        v = self.viatge
        if v is None:
            return
        v['t'] = min(v['t'] + dt, v['trajecte'].durada)
        s = suavitzat(v['t'] / v['trajecte'].durada)
        centre = v['centre']()
        self.posicio = centre + v['trajecte'].posicio_relativa(s)
        cap = (centre - self.posicio) / np.linalg.norm(centre - self.posicio)
        g = suavitzat(min(v['t'] / (0.35 * v['trajecte'].durada), 1.0))
        davant = (1 - g) * v['davant0'] + g * cap
        if np.linalg.norm(davant) > 1e-6:
            self.davant_ecef = davant / np.linalg.norm(davant)
            self.mirar_cap_a(self.posicio + self.davant_ecef)    # limita la inclinacio (no vertical)
        if v['t'] >= v['trajecte'].durada:
            self.viatge = None

    # ------------------------------------------------------------ ratoli i matrius

    def processar_ratoli(self, punt_sota_cursor, roda, capturat):
        """Roda (passos d'aquest fotograma, main.py): avancar. Amb el cursor lliure: arrossegar gira i el
        doble clic retorna el punt del terreny (o None). Amb la mirada capturada, el gir el fa main.py."""
        if capturat:
            if roda:
                self.avancar(roda)
            return None
        io = imgui.get_io()
        if io.want_capture_mouse:
            return None
        if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
            dx, dy = io.mouse_delta
            if dx or dy:
                self.girar(dx * VELOCITAT_GIR * self.fov / FOV, -dy * VELOCITAT_GIR * self.fov / FOV)
        if roda:
            self.avancar(roda)
        if imgui.is_mouse_double_clicked(imgui.MouseButton.LEFT):
            return punt_sota_cursor()
        return None

    def actualitzar(self, dt):
        """Un cop per fotograma (dt en segons): el viatge, si n'hi ha, i el camp de visio, que torna a FOV
        de mica en mica (despres de passar de l'observacio amb zoom, sense salt)."""
        self.actualitzar_viatge(dt)
        self.fov = self.fov_objectiu + (self.fov - self.fov_objectiu) * math.exp(-dt / TEMPS_FOV)

    def update(self):
        # "amunt" de la imatge: la vertical del lloc, perpendicular a la mirada; si son gairebe paral·leles,
        # el de l'ultim fotograma (aixi no salta)
        lat, lon, _ = self.geodesiques()
        _, _, vertical = geodesia.base_local(lat, lon)
        amunt = vertical - np.dot(vertical, self.davant_ecef) * self.davant_ecef
        if np.linalg.norm(amunt) > 1e-4 or self.amunt_vista is None:
            self.amunt_vista = amunt / max(np.linalg.norm(amunt), 1e-12)
        self.m_view = glm.lookAt(glm.vec3(0.0), glm.vec3(*self.davant_ecef), glm.vec3(*self.amunt_vista))
        self.m_proj = glm.perspective(glm.radians(self.fov), self.aspect_ratio, 1e-6, FAR_KM)
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
