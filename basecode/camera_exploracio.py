"""
Camera d'exploracio: una camera lliure que es pot moure del terreny fins a l'espai.

- Posicio en coordenades terrestres (ECEF, km, float64). La GPU la rep sempre com a origen: tots els
  objectes es dibuixen relatius a la camera, perque el float32 de la GPU no perdi precisio.
- Orientacio: rumb (graus des del nord, sentit horari) i inclinacio (graus sobre l'horitzo del lloc
  on es la camera). "Amunt" es la vertical d'aquell lloc.
- Ratoli a la vista aeria (vol lliure, cursor lliure), com a Google Earth:
    arrossegar (boto esquerre): s'agafa el terra pel punt clicat i es desplaca; el punt es queda sota el cursor
      (la camera gira al voltant del centre de la Terra, sense canviar d'altura). En deixar-lo anar amb el
      ratoli en moviment, continua una mica i s'atura suaument (inercia). Si es clica el cel, gira la mirada;
    Shift + arrossegar o boto del mig: orbitar al voltant del punt del centre de la pantalla (horitzontal: girar
      al voltant de la seva vertical; vertical: inclinar la vista), sense passar per sota del terra;
    roda (o dos dits): apropar-se o allunyar-se del punt sota el cursor, que es queda sota el cursor. Cada pas
      de roda escurca la distancia un ~26 % (o l'allarga un 35 %) i el moviment es reparteix en uns quants
      fotogrames (animacio suau, sense salts).
  Caminant, arrossegar gira la mirada, com abans.
- Ratoli (moure'l amb la mirada capturada, main.py) i fletxes: girar la mirada. La
  inclinacio es limita a +-INCLINACIO_MAX i el rumb es normalitza a [0, 360) a qualsevol lloc on es canvia
  la mirada (orientar), tambe des dels botons: lookAt no troba mai la mirada paral·lela a l'amunt.
  W A S D: moure's endavant, enrere i als costats (en horitzontal). E i Q: pujar i baixar.
  Roda amb la mirada capturada: avancar o retrocedir en la direccio en que es mira.
- La velocitat es proporcional a l'altura sobre el terra: a 1 km d'altura es va a ~1 km/s i a
  10.000 km, a ~10.000 km/s. Aixi es pot explorar tant una vall com la Terra des de l'espai. La roda
  tambe: cada pas canvia l'altura ~35 %, precis a prop del terra i rapid a l'espai.
- Dos modes de desplacament (panell): "Vol lliure" (el d'abans) i "Caminar". Caminant, W A S D mouen en
  horitzontal a velocitat humana (VELOCITAT_CAMINAR_M_S, Shift per correr) i els ulls segueixen el relleu
  dibuixat a ALCADA_ULLS_KM, tant en pujada com en baixada; E / Q i la roda no hi fan res. El moviment es
  subdivideix en passos de PAS_MAXIM_KM, i al mar o on no hi ha relleu la camera s'atura a la vora.
  A tots dos modes, la combinacio de tecles es normalitza: en diagonal no es va mes de pressa.
- Edificis (si es mostren): caminant son obstacles per al cos (un cercle de RADI_COS_M) i es llisca per les
  facanes; en vol lliure, la camera (radi RADI_VOL_M) no pot entrar per una facana per sota de la coberta,
  pero hi pot passar per sobre (s'atura a MARGE_COBERTA_M sobre el terrat si hi baixa). Si mai queda dins
  d'un edifici, es treu al punt exterior mes proper (sortir_dels_edificis). Geometria: dades/obstacles.py.
- La camera no pot sortir del cub de navegacio (app.cub, dades/navegacio.py): tota posicio nova
  (teclat, roda, botons) passa pel cub, i a la paret s'atura nomes el moviment cap a fora.
Quan el cursor es sobre el panell (want_capture_mouse) la camera no reacciona al ratoli.
"""
import math
import time

import glm
import numpy as np
from slimgui import imgui

from dades import geodesia
from dades.observador import ALCADA_ULLS_KM
from dades.obstacles import RADI_COS_M
from .control_ratoli import graus_per_punt

FOV = 50.0                  # angle de visio vertical (graus)
INCLINACIO_MAX = 89.0       # graus: la mirada no arriba mai a la vertical (lookAt hi seria singular)
FAR_KM = 1e9                # pla llunya: mes enlla del Sol (150 milions de km)
ALCADA_MINIMA_KM = 0.002    # 2 m sobre el terra
PAS_RODA = 0.35             # cada pas de roda canvia l'altura ~35 % (veure avancar)
PASSOS_RODA_MAX = 3.0       # passos de roda per fotograma com a molt: un gest rapid no fa salts
COEF_LOG = 2.0 / math.log2(FAR_KM + 1.0)   # per a la profunditat logaritmica dels shaders
VELOCITAT_CAMINAR_M_S = 1.5  # caminar (m/s); la velocitat no depen de l'altura
FACTOR_CORRER = 3.0         # Shift: correr (4,5 m/s)
PAS_MAXIM_KM = 0.0005       # el moviment caminant es fa en passos de 0,5 m com a molt (el MDT es de 5 m):
                            # un fotograma llarg no pot saltar-se una carena
ALCADA_ENTRAR_MAX_KM = 5.0  # per passar a caminar cal ser a menys d'aquesta altura sobre el terra
RADI_VOL_M = 0.5            # vol lliure: distancia minima a les facanes (m)
MARGE_COBERTA_M = 0.5       # vol lliure: altura minima sobre les cobertes (m)
PAS_VOL_M = 0.5             # vol lliure a l'altura dels edificis: el moviment es fa en passos de 0,5 m
TOLERANCIA_M = 0.01         # sobre una coberta (a MARGE_COBERTA_M), els arrodoniments no la fan obstacle
TEMPS_ZOOM_S = 0.12         # roda: el zoom pendent es redueix a 1/e en aquest temps (animacio suau)
ZOOM_PENDENT_MAX = 6.0      # passos de roda acumulats com a molt
FRENADA_INERCIA = 3.0       # 1/s: despres d'arrossegar, la velocitat de gir es redueix a 1/e en 1/3 s
GIR_MAX_RAD = 0.5           # arrossegar el terra: gir maxim per fotograma (cursor a prop de l'horitzo)
GRAUS_ORBITA = 0.3          # orbitar: graus per punt de pantalla


def limitar_orientacio(rumb, inclinacio):
    """(rumb a [0, 360), inclinacio a +-INCLINACIO_MAX), o None si algun valor no es finit (qui crida conserva
    la mirada anterior). Les cameres hi passen tota mirada nova: ratoli, fletxes, botons i scripts."""
    if not (math.isfinite(rumb) and math.isfinite(inclinacio)):
        return None
    return rumb % 360.0, min(max(inclinacio, -INCLINACIO_MAX), INCLINACIO_MAX)


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
        self.rumb, self.inclinacio = 0.0, 0.0
        self.orientar(rumb, inclinacio)
        self.caminar = False        # False: vol lliure; True: caminar sobre el relleu
        self.a_la_vora = False      # caminant, l'ultim pas s'ha aturat a la vora del relleu
        self.contra_edifici = False # caminant, l'ultim pas ha topat amb un edifici
        self.fov = FOV
        self.arrossegament = None   # (mode, punt): 'terra' (desplacar), 'orbita' o 'mirada', i el punt agafat
        self.pixel_clic = None      # pixel on s'ha premut el boto (el punt agafat es llegeix en comencar a moure)
        self.inercia = None         # vector de gir (rad/s, ECEF) que continua despres de deixar anar el terra
        self.gir_recent = None      # (vector de gir, temps) de l'ultim moviment arrossegant (per a la inercia)
        self.zoom_pendent, self.zoom_punt = 0.0, None   # roda: passos que falten i punt cap on es va
        self.update()

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

    def direccions(self, lat, lon):
        """(endavant, dreta, amunt) en ECEF al punt (lat, lon): endavant i dreta son horitzontals segons el
        rumb (la inclinacio no hi compta: mirar amunt o avall no fa volar)."""
        est, nord, amunt = geodesia.base_local(lat, lon)
        r = math.radians(self.rumb)
        return math.sin(r) * est + math.cos(r) * nord, math.cos(r) * est - math.sin(r) * nord, amunt

    def moure(self, endavant, dreta, amunt, dt):
        """Vol lliure amb el teclat: endavant i dreta en horitzontal, amunt en vertical (-1, 0 o 1). La
        combinacio es normalitza (en diagonal no es va mes de pressa)."""
        n = math.sqrt(endavant ** 2 + dreta ** 2 + amunt ** 2)
        if n == 0:
            return
        lat, lon, _ = self.geodesiques()
        davant, costat, vertical = self.direccions(lat, lon)
        pas = (endavant * davant + dreta * costat + amunt * vertical) / max(n, 1.0) * self.velocitat() * dt
        self.desplacar(pas)

    def desplacar(self, delta):
        """Vol lliure: suma delta (ECEF, km) a la posicio. A l'altura dels edificis, en passos de PAS_VOL_M: si
        un pas baixa sobre una coberta venint de dalt, s'hi queda a MARGE_COBERTA_M; si va contra una facana
        per sota de la coberta, hi llisca (dades/obstacles.py). Despres, mai sota el terra."""
        obs = self.app.obstacles_actius()
        p0, p1 = self.posicio, self.posicio + delta
        alt_min = min(float(geodesia.geodesiques(p0)[2]), float(geodesia.geodesiques(p1)[2])) * 1000.0
        if obs is None or alt_min > obs.coberta_max + MARGE_COBERTA_M:
            self.posicio = p1
            self.no_sota_terra()
            return
        n = max(1, math.ceil(np.linalg.norm(delta) * 1000.0 / PAS_VOL_M))
        p = p0
        for _ in range(n):
            lat0, lon0, alt0 = (float(v) for v in geodesia.geodesiques(p))
            lat1, lon1, alt1 = (float(v) for v in geodesia.geodesiques(p + delta / n))
            x0, y0 = obs.utm(lat0, lon0)
            x1, y1 = obs.utm(lat1, lon1)
            sota = alt1 * 1000.0 - MARGE_COBERTA_M + TOLERANCIA_M   # obstacles: cobertes mes altes que aixo
            i = obs.dins(x1, y1, sota)
            if i is not None and alt0 * 1000.0 >= obs.coberta[i] + MARGE_COBERTA_M - TOLERANCIA_M:
                alt1 = (obs.coberta[i] + MARGE_COBERTA_M) / 1000.0       # venint de dalt: sobre la coberta
            else:
                x1, y1, _ = obs.moure(x0, y0, x1, y1, RADI_VOL_M, sota)
                lat1, lon1 = obs.latlon(x1, y1)
            p = geodesia.ecef(lat1, lon1, alt1)
        self.posicio = p
        self.no_sota_terra()

    def sortir_dels_edificis(self):
        """Recuperacio: si la camera es dins d'un edifici (o enganxada a una facana), la treu al punt exterior
        mes proper a la mateixa altura sobre el terra (caminant, al carrer). Retorna la distancia (m) o 0."""
        obs = self.app.obstacles_actius()
        if obs is None:
            return 0.0
        lat, lon, alt = self.geodesiques()
        x, y = obs.utm(lat, lon)
        radi = RADI_COS_M if self.caminar else RADI_VOL_M
        sota = None if self.caminar else alt * 1000.0 - MARGE_COBERTA_M + TOLERANCIA_M
        if obs.separacio(x, y, sota) >= radi - 1e-3:
            return 0.0
        exterior = obs.punt_exterior(x, y, marges=(radi + 0.2,))
        if exterior is None:
            return 0.0
        lat2, lon2 = obs.latlon(exterior[0], exterior[1])
        h = self.app.altitud_caminable_km(lat2, lon2) if self.caminar else None
        if self.caminar and h is not None:
            self.posicio = geodesia.ecef(lat2, lon2, h + ALCADA_ULLS_KM)
        else:
            self.posicio = geodesia.ecef(lat2, lon2, alt - self.app.altitud_terra_km(lat, lon)
                                         + self.app.altitud_terra_km(lat2, lon2))
        return exterior[2]

    def caminar_pas(self, endavant, dreta, dt, correr=False):
        """Caminar: avanca velocitat x dt en horitzontal (entrada normalitzada) en passos de PAS_MAXIM_KM com a
        molt. A cada pas, la posicio horitzontal nova es posa a ALCADA_ULLS_KM sobre el relleu dibuixat en
        aquell punt (puja i baixa amb el terreny). Si el pas cau on no hi ha relleu (mar, fora de les dades),
        la camera s'atura a l'ultim punt bo. Els edificis que es mostren son obstacles: el cos (RADI_COS_M) hi
        llisca (dades/obstacles.py). Retorna la llista de posicions per on ha passat (proves)."""
        n = math.hypot(endavant, dreta)
        cami = [self.posicio]
        if n == 0 or dt <= 0:
            return cami
        distancia = VELOCITAT_CAMINAR_M_S / 1000.0 * (FACTOR_CORRER if correr else 1.0) * dt
        passos = max(1, math.ceil(distancia / PAS_MAXIM_KM))
        p = self.posicio
        self.a_la_vora = self.contra_edifici = False
        obs = self.app.obstacles_actius()
        for _ in range(passos):
            lat0, lon0, _ = (float(v) for v in geodesia.geodesiques(p))
            davant, costat, _ = self.direccions(lat0, lon0)
            q = p + (endavant * davant + dreta * costat) / n * (distancia / passos)
            lat, lon, _ = (float(v) for v in geodesia.geodesiques(q))
            if obs is not None:
                x, y, xoc = obs.moure(*obs.utm(lat0, lon0), *obs.utm(lat, lon), RADI_COS_M)
                lat, lon = obs.latlon(x, y)
                self.contra_edifici |= xoc
            h = self.app.altitud_caminable_km(lat, lon)
            if h is None:
                self.a_la_vora = True
                break
            p = geodesia.ecef(lat, lon, h + ALCADA_ULLS_KM)
            cami.append(p)
        self.posicio = p
        return cami

    def seguir_terra(self):
        """Caminant, a cada fotograma: els ulls a ALCADA_ULLS_KM del relleu dibuixat sota la camera (si el
        relleu canvia, p. ex. l'exageracio o la zona de detall carregada, la camera el segueix)."""
        lat, lon, _ = self.geodesiques()
        h = self.app.altitud_caminable_km(lat, lon)
        if h is not None:
            self.posicio = geodesia.ecef(lat, lon, h + ALCADA_ULLS_KM)

    def entrar_caminar(self):
        """Passa a caminar: baixa (o puja) en vertical fins als ulls sobre el relleu, sense moure's en
        horitzontal. Nomes si hi ha relleu de terra a sota i la camera es a menys d'ALCADA_ENTRAR_MAX_KM;
        si no, no fa res i retorna el motiu (per tornar al punt d'observacio cal una accio explicita).
        Retorna (fet, text)."""
        lat, lon, alt = self.geodesiques()
        h = self.app.altitud_caminable_km(lat, lon)
        if alt - (h or 0.0) > ALCADA_ENTRAR_MAX_KM:
            return False, f'Massa amunt per caminar ({alt - (h or 0.0):,.0f} km sobre el terra)'
        if h is None:
            return False, "Aqui sota no hi ha relleu (mar o sense dades)"
        canvi = (h + ALCADA_ULLS_KM - alt) * 1000.0
        self.posicio = geodesia.ecef(lat, lon, h + ALCADA_ULLS_KM)
        self.caminar = True
        text = f'Caminant: {"baixat" if canvi < 0 else "pujat"} {abs(canvi):,.0f} m fins al terra'
        fora = self.sortir_dels_edificis()      # si s'ha baixat sobre un edifici: al carrer mes proper
        if fora:
            text += f', al carrer a {fora:.0f} m (sota hi havia un edifici)'
        return True, text

    def avancar(self, passos):
        """Roda: avanca (passos > 0) o retrocedeix en la direccio de la mirada. n passos multipliquen l'altura
        per (1 + PAS_RODA)^-n: endavant s'acosta al terra cada cop mes a poc a poc i no el travessa; enrere
        s'allunya cada cop mes de pressa. El desplacament es el canvi d'altura dividit pel sinus de la
        inclinacio (amb la mirada inclinada, nomes una part es vertical; minim 0,3). El trackpad dona
        passos fraccionaris. Com a molt PASSOS_RODA_MAX per fotograma."""
        passos = min(max(passos, -PASSOS_RODA_MAX), PASSOS_RODA_MAX)
        alcada = max(self.alcada_sobre_terra(), 0.005)
        canvi = alcada * (1.0 - (1.0 + PAS_RODA) ** -passos)          # > 0 endavant
        inclinacio = max(abs(math.sin(math.radians(self.inclinacio))), 0.3)
        self.desplacar(self.davant() * canvi / inclinacio)

    def no_sota_terra(self):
        lat, lon, alt = self.geodesiques()
        minim = self.app.altitud_terra_km(lat, lon) + ALCADA_MINIMA_KM
        if alt < minim:
            self.posicio = geodesia.ecef(lat, lon, minim)

    def girar_ratoli(self, dx, dy):
        """Moviment del ratoli (punts de pantalla), capturat o arrossegant: dreta mira a la dreta, amunt mira
        amunt. Cap inercia: la mirada nomes canvia quan el ratoli es mou."""
        v = graus_per_punt(self.fov, FOV)
        self.girar(dx * v, -dy * v)

    def girar(self, d_rumb, d_inclinacio):
        self.orientar(self.rumb + d_rumb, self.inclinacio + d_inclinacio)

    def orientar(self, rumb, inclinacio):
        o = limitar_orientacio(rumb, inclinacio)
        if o is not None:
            self.rumb, self.inclinacio = o

    def processar_ratoli(self, punt_sota_cursor, roda, capturat):
        """Ratoli, un cop per fotograma (main.py, despres de dibuixar: el picking llegeix la profunditat). Roda: passos
        d'aquest fotograma. Amb la mirada capturada, la roda avanca en la direccio de la mirada i el gir el fa
        main.py. Amb el cursor lliure: caminant, arrossegar gira; en vol lliure, els controls de la vista aeria
        (capcalera del fitxer). El doble clic retorna el punt del terreny (o None)."""
        dt = min(max(self.app.dt, 0.0), 0.1)
        if self.caminar:
            roda = 0.0          # caminant, la roda no mou la camera (no volem que dos sistemes la moguin)
            self.inercia, self.zoom_pendent, self.arrossegament = None, 0.0, None
        if capturat:
            self.inercia, self.zoom_pendent, self.arrossegament = None, 0.0, None
            if roda:
                self.avancar(roda)
            return None
        io = imgui.get_io()
        if io.want_capture_mouse:
            self.arrossegament = None
            self.animar(dt)
            return None
        if self.caminar:
            if imgui.is_mouse_dragging(imgui.MouseButton.LEFT, 0.0):
                dx, dy = io.mouse_delta
                if dx or dy:
                    self.girar_ratoli(dx, dy)
        else:
            self.ratoli_aeri(punt_sota_cursor, roda, io)
        self.animar(dt)
        if imgui.is_mouse_double_clicked(imgui.MouseButton.LEFT):
            self.inercia, self.zoom_pendent = None, 0.0
            return punt_sota_cursor()
        return None

    # ------------------------------------------------------------ vista aeria (com Google Earth)

    def ratoli_aeri(self, punt_sota_cursor, roda, io):
        esquerre, mig = imgui.MouseButton.LEFT, imgui.MouseButton.MIDDLE
        if imgui.is_mouse_clicked(esquerre) or imgui.is_mouse_clicked(mig):
            # el punt agafat es llegeix quan el ratoli comenca a moure's (no a cada clic: el doble clic no ha
            # d'esperar la lectura de la profunditat)
            self.arrossegament = ('orbita' if imgui.is_mouse_clicked(mig) or io.key_shift else 'terra', None)
            self.inercia, self.gir_recent = None, None
            self.pixel_clic = self.app.pixel_cursor()
        premut = imgui.is_mouse_down(esquerre) or imgui.is_mouse_down(mig)
        if self.arrossegament is not None and premut:
            mode, punt = self.arrossegament
            dx, dy = io.mouse_delta
            if punt is None and mode != 'mirada' and (dx or dy):
                # terra: el punt on s'ha clicat; orbita: el del centre de la pantalla (es queda al centre)
                _, _, amplada, alcada = self.app.ctx.viewport
                pixel = self.pixel_clic if mode == 'terra' else (amplada // 2, alcada // 2)
                punt = punt_sota_cursor(pixel) if pixel is not None else None
                if punt is None:
                    mode = 'mirada'                     # el cel: girar la mirada
                self.arrossegament = (mode, punt)
            if punt is None and mode != 'mirada':
                pass
            elif mode == 'terra':
                d = self.raig_cursor()
                if d is not None:
                    self.arrossegar_terra(punt, d)
            elif (dx or dy) and mode == 'orbita':
                self.orbitar(punt, dx, dy)
            elif dx or dy:
                self.girar_ratoli(dx, dy)
        elif self.arrossegament is not None:
            # s'ha deixat anar: si el terra es movia (ultim moviment fa menys de 0,05 s), continua amb inercia
            if self.arrossegament[0] == 'terra' and self.gir_recent is not None and \
                    time.perf_counter() - self.gir_recent[1] < 0.05:
                self.inercia = self.gir_recent[0]
            self.arrossegament = None
        if roda:
            punt = punt_sota_cursor()
            if punt is None:
                self.avancar(roda)                    # el cel: com abans, en la direccio de la mirada
            else:
                self.zoom_punt = punt
                self.zoom_pendent = min(max(self.zoom_pendent + roda, -ZOOM_PENDENT_MAX), ZOOM_PENDENT_MAX)

    def aturar_moviment(self):
        """Atura la inercia i el zoom pendent (canvi de vista, Mirar l'eclipsi)."""
        self.inercia, self.zoom_pendent, self.zoom_punt, self.arrossegament = None, 0.0, None, None

    def animar(self, dt):
        """El que continua sense tocar el ratoli: el zoom pendent de la roda i la inercia del terra."""
        if self.zoom_punt is not None and abs(self.zoom_pendent) > 1e-3:
            part = self.zoom_pendent * (1.0 - math.exp(-dt / TEMPS_ZOOM_S))
            self.zoom_pendent -= part
            self.apropar(self.zoom_punt, part)
        else:
            self.zoom_pendent = 0.0
        if self.inercia is not None:
            self.girar_posicio(self.inercia * dt)
            self.inercia = self.inercia * math.exp(-FRENADA_INERCIA * dt)
            if np.linalg.norm(self.inercia) * self.alcada_sobre_terra() < 1e-4:   # menys de 0,1 m/s
                self.inercia = None

    def raig_cursor(self):
        """Direccio (ECEF, unitaria) del raig que surt de la camera pel pixel del cursor, o None."""
        pixel = self.app.pixel_cursor()
        if pixel is None:
            return None
        px, py, amplada, alcada = pixel
        x_ndc, y_ndc = 2 * (px + 0.5) / amplada - 1, 2 * (py + 0.5) / alcada - 1
        ull = glm.vec4(x_ndc / self.m_proj[0][0], y_ndc / self.m_proj[1][1], -1.0, 0.0)
        d = glm.inverse(self.m_view) * ull
        d = np.array([d.x, d.y, d.z], dtype=float)
        return d / np.linalg.norm(d)

    def arrossegar_terra(self, punt, d):
        """Gira la camera al voltant del centre de la Terra perque el raig del cursor (d) torni a passar per punt.
        El raig es talla amb l'esfera del radi del punt (des de dalt) o, si la camera es mes avall que el punt
        (p. ex. una muntanya), amb el pla horitzontal del punt. Sense tall (cursor sobre l'horitzo), no fa res."""
        c = self.posicio
        r = float(np.linalg.norm(punt))
        if np.linalg.norm(c) > r:
            b = float(c @ d)
            disc = b * b - (float(c @ c) - r * r)
            if disc < 0:
                return
            t = -b - math.sqrt(disc)
        else:
            n = punt / r
            den = float(d @ n)
            if abs(den) < 1e-9:
                return
            t = float((punt - c) @ n) / den
        if t <= 0:
            return
        q = c + t * d
        eix = np.cross(q, punt)
        sin_a, cos_a = np.linalg.norm(eix), float(q @ punt)
        if sin_a < 1e-15:
            return
        angle = min(math.atan2(sin_a, cos_a), GIR_MAX_RAD)
        gir = eix / sin_a * angle
        self.girar_posicio(gir)
        ara = time.perf_counter()
        dt = min(max(self.app.dt, 1e-3), 0.1)
        self.gir_recent = (gir / dt, ara)

    def girar_posicio(self, gir):
        """Gira la camera (posicio i mirada) al voltant del centre de la Terra: vector de gir (eix x angle, rad)."""
        angle = float(np.linalg.norm(gir))
        if angle < 1e-15:
            return
        m = rotacio(gir / angle, angle)
        davant = m @ self.davant()
        self.posicio = m @ self.posicio
        self.mirar_cap_a(davant)
        self.no_sota_terra()

    def orbitar(self, punt, dx, dy):
        """Orbitar al voltant de punt (el del centre de la pantalla en comencar): dx gira al voltant de la vertical
        del punt; dy inclina (gir al voltant de l'eix horitzontal de la camera que passa pel punt). Despres es
        mira exactament el punt: es queda al centre. La inclinacio no deixa la camera sota l'horitzo del punt ni
        mirant amunt."""
        amunt = punt / np.linalg.norm(punt)
        m = rotacio(amunt, -math.radians(dx * GRAUS_ORBITA))
        c, davant = punt + m @ (self.posicio - punt), m @ self.davant()
        dreta = np.cross(davant, amunt)
        if dy and np.linalg.norm(dreta) > 1e-9:
            m2 = rotacio(dreta / np.linalg.norm(dreta), -math.radians(dy * GRAUS_ORBITA))
            c2, davant2 = punt + m2 @ (c - punt), m2 @ davant
            # nomes si la camera queda per sobre del pla horitzontal del punt i mirant avall
            if float((c2 - punt) @ amunt) > 0.002 and float(davant2 @ (c2 / np.linalg.norm(c2))) < -0.02:
                c = c2
        self.posicio = c
        self.no_sota_terra()
        self.mirar_cap_a(punt - self.posicio)

    def apropar(self, punt, passos):
        """Roda: acosta la camera al punt (passos > 0) o l'allunya, en la recta camera-punt: el punt es queda al
        mateix lloc de la pantalla (la mirada no canvia). passos multiplica la distancia per (1 + PAS_RODA)^-passos:
        mai s'arriba al punt."""
        f = 1.0 - (1.0 + PAS_RODA) ** -passos                 # > 0 apropar-se, < 0 allunyar-se
        self.desplacar((punt - self.posicio) * f)

    def mirar_cap_a(self, direccio):
        lat, lon, _ = self.geodesiques()
        self.orientar(*geodesia.azimut_elevacio(direccio, lat, lon))

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


def rotacio(eix, angle):
    """Matriu 3 x 3 de gir d'angle (rad) al voltant de l'eix unitari (formula de Rodrigues)."""
    k = np.array([[0.0, -eix[2], eix[1]], [eix[2], 0.0, -eix[0]], [-eix[1], eix[0], 0.0]])
    return np.eye(3) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)
