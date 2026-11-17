"""
Projecte EGRA -- Simulacio de l'eclipsi total del 12/08/2026 sobre terreny real.
Programa principal: GraphicsEngine (subclasse de GraphicsEngineBase del basecode de classe), que
coordina l'escena: crea els objectes, fa avancar el temps i els dibuixa.

L'escena es un model geometric coherent en coordenades terrestres (ECEF, km): la Terra (el·lipsoide
WGS84 amb textura), el relleu de la peninsula (MDT de 200 m), una zona de detall (MDT de 5 m) al
voltant del punt d'observacio (Picos, Vic, l'Escala o el Valles) i el Sol i la Lluna a les seves
posicions reals (efemerides de JPL Horizons). L'ombra de la Lluna es calcula per a cada punt.

Nivells de detall del relleu, de lluny a prop: la graella general de la peninsula (~1 km entre
vertexs), un pegat de la peninsula al voltant del punt de detall (200 m, ~100 km), la zona de 5 m
(~10-20 m entre vertexs) i un pegat de la zona al voltant del punt de detall (5 m, ~2,5 km). Cada nivell
fa un forat al de sota i, a la vora, la seva altura passa suaument a la del de sota.
Detall segons el que es mira (basecode/detall.py): el punt de detall es el que mira la camera (o el de sota, a prop
del terra); el relleu de 5 m, els edificis (amb altures mesurades) i el mapa de visibilitat de
detall d'aquell lloc es preparen i es carreguen en segon pla, sense aturar el dibuix.

Espai de navegacio: un cub fix que conte la Terra, la Lluna i el Sol (dades/navegacio.py); la camera
d'exploracio no en pot sortir i, a prop, se'n veuen les parets (basecode/paret_cub.py).
Ratoli: Tab (o un clic dret a l'escena) captura el ratoli per mirar sense premer cap boto; Tab o Esc
l'alliberen (basecode/control_ratoli.py). GraphicsEngine.run() es el bucle del basecode amb un sol canvi per
a l'Esc.

Tres coses independents:
  - el temps de simulacio (self.hora, TU): nomes canvia quan es reprodueix (tecla P);
  - el punt d'observacio (self.observador): nomes canvia quan se'n tria un (i no durant la reproduccio);
  - la camera: una sola vista (basecode/camera_exploracio.py), lliure de l'espai fins als ulls (1,7 m sobre el
    terra). El doble clic al terreny hi posa el punt d'observacio i la camera, als ulls i mirant cap al Sol; des
    d'alli es continua explorant amb la mateixa camera.

Segueix l'estructura del repte 4: on_init crea la llum, les cameres i l'escena; drawables() son els
objectes als quals la camera escriu m_proj i m_view; render() els dibuixa i build_ui() crida ui.py.

On es cada cosa:
  ui.py                            panell i barra de temps (slimgui)
  basecode/                        codi de classe (sense canvis) + els nostres objectes grafics:
    terra.py                         la Terra (globus)
    mosaic.py                        fotografia aeria (PNOA, Sentinel-2) carregada a mesura que cal
    terrain.py                       relleu d'un MDT (mode globus: posat sobre la Terra)
    astres.py                        el Sol, el seu halo i la Lluna
    sol.py                           la llum (Light del basecode)
    camera_exploracio.py             la camera (de l'espai fins als ulls de l'observador)
    camera_orbital.py                camera del mode pla (nomes per als scripts)
    programes.py                     carrega shaders amb opcions (#define)
  dades/                           sense OpenGL: efemerides, geodesia, model de l'eclipsi, observador,
                                   lectura dels MDT i dades del CNIG

Executa:  python main.py
"""
import math
import os
import sys
import time


def _add_basecode_to_path():
    # retorna la carpeta on viu basecode/ (i tambe models/, al mateix nivell)
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        if os.path.isdir(os.path.join(d, 'basecode')):
            sys.path.insert(0, d)
            return d
        d = os.path.dirname(d)
    raise RuntimeError("No es troba la carpeta 'basecode' al costat d'aquest fitxer ni en cap carpeta pare")


_CODE_DIR = _add_basecode_to_path()

import glfw
import glm
import numpy as np
import moderngl as mgl
from slimgui import imgui
from OpenGL import GL

from basecode.engine import GraphicsEngineBase
from basecode.camera_exploracio import CameraExploracio, COEF_LOG, FOV as FOV_EXPLORACIO
from basecode.astres import Esfera, Lluna, SOL, HALO
from basecode.sol import Sol
from basecode.terra import Terra
from basecode.terrain import Terrain, COLOR_CEL
from basecode.ombres_relleu import OmbresRelleu
from basecode.paret_cub import ParetCub
from basecode.control_ratoli import ControlRatoli
from basecode import window as winmod
from dades.data_io import TERRENYS
from dades.model_eclipsi import ModelEclipsi, area_tapada, angle_entre, efemerides, punt_ombra
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM
from dades.observador import Observador, ALCADA_ULLS_KM, UBICACIONS, UBICACIO_INICIAL
from dades.navegacio import cub_navegacio
from dades.obstacles import RADI_COS_M
from dades import atmosfera
from basecode.cel import Cel
from basecode.mosaic import Mosaic
from basecode.detall import Detall
from basecode.mapes import Mapes
from basecode.vegetacio import Vegetacio
from dades import eclipse_data, eclipsis, geodesia, noms
import ui

MODELS_DIR = os.path.join(_CODE_DIR, 'models')  # models .obj (cada un a la seva carpeta), com al repte 4
VELOCITAT_GIR = 60.0               # graus/s amb les fletxes
ALCADA_ATMOSFERA_KM = 60.0         # per sobre, el cel ja es negre (aproximacio visual)
INCLINACIO_EN_ARRIBAR = 2.0        # graus: en tornar al punt d'observacio, la mirada just sobre l'horitzo
ALCADA_PRIMERA_PERSONA_KM = 0.1    # per sota d'aquesta altura sobre el terra, els edificis segueixen l'opcio "Edificis";
                                   # per sobre, "A la vista aeria" (panell, Que es dibuixa)
# mirada en arrencar (rumb i inclinacio, graus): des de la placa Civica de la UAB, cap al campus (est-sud-est), una
# direccio oberta; cap a l'oest (on es el Sol al maxim, azimut 286 i 4 graus) hi ha un edifici al davant
MIRADA_INICIAL = (100.0, 3.0)
HORA_ABANS_C1 = 1.0                # l'arrencada es aquest nombre d'hores abans de C1 (temps TU del model)
# Repos: si la imatge no canvia (mateixa camera i hora, en pausa) i no hi ha cap feina en segon pla durant REPOS_S,
# el bucle espera esdeveniments (teclat, ratoli, finestra) com a molt ESPERA_REPOS_S en lloc de tornar a dibuixar
# la mateixa imatge: la GPU i la CPU descansen. Qualsevol esdeveniment el desperta a l'instant, i cada
# ESPERA_REPOS_S es torna a dibuixar igualment (recull el que acabi en segon pla).
REPOS_S = 0.5
ESPERA_REPOS_S = 0.25


def suau(a, b, x):
    """smoothstep de GLSL: 0 per sota de a, 1 per sobre de b."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def v3(a):
    return glm.vec3(float(a[0]), float(a[1]), float(a[2]))


class GraphicsEngine(GraphicsEngineBase):
    def on_init(self):
        self.ctx.enable_only(mgl.DEPTH_TEST)  # sense CULL_FACE: el terreny es veu per sota tambe
        self.light = Sol()
        self.coef_log = COEF_LOG
        self.radi_sol_km, self.radi_lluna_km = RADI_SOL_KM, RADI_LLUNA_KM
        self.terra = self.peninsula = self.zona = self.sol_visible = self.halo = self.lluna = self.paret = None
        self.edificis = None          # edificis de la zona de detall (Catastro), si n'hi ha
        # edificis: es mostren a prop del terra (primera persona) i des de l'aire; cada cas es pot canviar al panell
        self.mostrar_edificis = True
        self.edificis_aeris = True    # (equip, 01/11/2026: tambe a la vista aeria per defecte; es poden amagar)
        self._clau_edificis = None
        self.mostrar_noms = True      # noms de lloc importants sobre el mapa, vist des de l'aire (ui.noms_al_mapa)
        self.noms_mapa = None         # [(nom, nivell, posicio ECEF)], es prepara el primer cop que es dibuixen
        self.usar_ortofoto = True     # color del terra de les zones de detall: fotografia aeria (si n'hi ha)
        # mapes de l'eclipsi (objectius O3 i O4): basecode/mapes.py (les dades es preparen en segon pla segons la
        # vista, per nivells de detall; el shader del terreny les llegeix)
        self.mapes = Mapes(self)
        self.consulta_nom, self.nom_punt = None, None   # nom del lloc del punt d'observacio (dades/noms.py)

        # --- territori: la peninsula sencera posada sobre la Terra; el detall (zones de 5 m, edificis) el
        # carrega basecode/detall.py segons el que es mira i el punt d'observacio
        t0 = time.time()
        cami = {n: c for n, c, _ in TERRENYS}
        self.peninsula = Terrain(self, cami['Peninsula'], globus=True)
        self.peninsula.exaggeration = 1.0
        self.peninsula.limits_totalitat = False   # capa tecnica: una opcio del selector de Mapes (ui.py)
        self.zona, self.nom_zona = None, None
        self.camera_exploracio = None
        self.ulls_fixats = None            # posicio on s'ha posat la camera als ulls (veure seguir_ulls)
        self.abans_espai = None            # tecla G: on era la camera abans d'anar a l'espai (per tornar-hi)
        self.detall = Detall(self)
        self.vegetacio = Vegetacio(self)   # vegetacio mesurada (LiDAR) amb un geometry shader; desactivada d'entrada
        self.terra = Terra(self)
        self.mosaic = Mosaic(self)         # fotografia aeria per al terreny i el globus (es baixa en segon pla)
        self.ombres = OmbresRelleu(self)   # ombres del relleu (shadow mapping) a la zona de 5 m
        print(f"Escena carregada en {time.time() - t0:.1f} s")

        # --- temps de l'eclipsi (hores TU): independent de la camera
        self.ef = efemerides()
        self.reproduint = False
        self.velocitat = 60
        self.velocitat_auto = True    # lent a la totalitat, rapid a les fases parcials
        self.tapada = 0.0
        self.marcador_fins = -1.0     # temps real (s) fins al qual es veu l'avis del punt triat
        self.ressaltar_ombra = False  # linies de l'ombra de la Lluna (didactic, opcional)
        self.camera = None

        # --- punt d'observacio (dada independent): la UAB, placa Civica (dades/observador.UBICACIO_INICIAL)
        nom, lat, lon = next(u for u in UBICACIONS if u[0] == UBICACIO_INICIAL)
        self.triar_punt(lat, lon, nom)
        # arrencada: pausat, una hora abans del primer contacte (C1) calculat pel model en aquest punt.
        # Nomes en arrencar: canviar d'ubicacio despres no toca el temps
        self.hora = max(self.model.hores['c1'] - HORA_ABANS_C1, self.ef.inici) if self.model.valid else self.ef.inici
        self.actualitzar_astres()

        # --- espai de navegacio: fix durant la sessio, calculat amb tot l'interval de les efemerides
        self.cub = cub_navegacio(self.ef, FOV_EXPLORACIO)
        self.ratoli = ControlRatoli(self)
        self.esc_premuda = False
        self.avis, self.avis_fins = '', -1.0   # avis temporal al panell Camera (p. ex. consulta desada)

        # --- camera: comencem als ulls de l'observador mirant cap al campus (MIRADA_INICIAL; cap al Sol, a la UAB,
        # hi ha un edifici al davant). El boto "Mirar el Sol" hi gira la mirada
        self.camera_exploracio = CameraExploracio(self, self.ulls(), *MIRADA_INICIAL)
        self.camera = self.camera_exploracio
        self.posar_als_ulls()

        self.lluna = Lluna(self)
        self.sol_visible = Esfera(self, color=(1.0, 0.96, 0.85), mode=SOL)
        self.halo = Esfera(self, color=(1.0, 0.95, 0.85), mode=HALO)
        self.paret = ParetCub(self, self.cub)
        self.cel = Cel(self)
        self.color_cel, self.densitat_boira = COLOR_CEL, 0.0

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.on_resize(self.window, *glfw.get_framebuffer_size(self.window))  # per si ja ha canviat
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0
        self.en_repos, self._signatura, self._quiet_des_de = False, None, 0.0

    def drawables(self):
        objectes = [self.terra, self.peninsula, self.zona, self.edificis, self.lluna, self.sol_visible, self.halo,
                    self.paret]
        return [obj for obj in objectes if obj is not None]

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera.aspect_ratio = amplada / alcada
        self.camera.update()

    # ------------------------------------------------------------ territori i observador

    def terrenys(self):
        """Els relleus que es dibuixen, del menys al mes detallat."""
        return [t for t in (self.peninsula, self.zona) if t is not None]

    def altitud_terra_km(self, lat, lon):
        """Altura (km) dels triangles que es dibuixen en aquest punt: els de la zona de detall si hi
        es, si no els de la peninsula, si no 0 (el globus)."""
        for t in reversed(self.terrenys()):
            h = t.altitud_latlon(lat, lon)
            if h is not None:
                return h / 1000.0 * t.exaggeration
        return 0.0

    def primera_persona(self):
        """La camera a prop del terra (menys d'ALCADA_PRIMERA_PERSONA_KM): els edificis fan l'horitzo."""
        cam = self.camera_exploracio
        return cam is not None and cam.alcada_sobre_terra() < ALCADA_PRIMERA_PERSONA_KM

    def actualitzar_edificis(self):
        """Edificis visibles segons la vista (primera persona o aeria) i les opcions del panell. Nomes actua quan
        alguna d'aquestes coses canvia: aixi un script (o una opcio de depuracio) els pot amagar sense que es
        tornin a mostrar al fotograma seguent."""
        e = self.edificis
        if e is None or getattr(self, 'camera_exploracio', None) is None:
            return
        pp = self.primera_persona()
        clau = (pp, self.mostrar_edificis, self.edificis_aeris)
        if clau != self._clau_edificis:
            self._clau_edificis = clau
            e.visible = self.mostrar_edificis if pp else self.edificis_aeris

    def obstacles_actius(self):
        """Els edificis que fan d'obstacle a la camera d'exploracio: els de la zona carregada, si es mostren
        (amagats, es pot passar a traves, com es veu)."""
        e = self.edificis
        return e.obstacles if e is not None and e.visible else None

    def triar_punt(self, lat, lon, nom=''):
        """Posa l'observador al punt (lat, lon) i hi calcula, tot alhora, el model del Sol i la Lluna
        i les dades del CNIG: aixi sempre corresponen al mateix punt.
        Si el punt cau dins d'un edifici (o a menys del radi del cos d'una facana), els ulls van al punt
        exterior mes proper (carrer o placa, no el terrat); el lloc triat es conserva com a referencia.
        No depen de si els edificis es mostren: el punt d'observacio es el mateix amb edificis i sense.
        Durant la reproduccio la ubicacio esta bloquejada: no canvia res i retorna False."""
        if self.reproduint:
            return False
        self.detall.situar(lat, lon, observador=True)
        lat_ref, lon_ref, desplacament = lat, lon, 0.0
        obs = self.edificis.obstacles if self.edificis is not None else None
        if obs is not None:
            x, y = obs.utm(lat, lon)
            if obs.separacio(x, y) < RADI_COS_M:
                exterior = obs.punt_exterior(x, y)
                if exterior is not None:
                    lat, lon = obs.latlon(exterior[0], exterior[1])
                    desplacament = exterior[2]
                    self.detall.situar(lat, lon, observador=True)    # el pegat dens, centrat als ulls
        alt_km = self.altitud_terra_km(lat, lon)
        self.observador = Observador(lat, lon, alt_km * 1000.0, nom,
                                     lat_ref if desplacament else None, lon_ref if desplacament else None,
                                     desplacament)
        self.model = ModelEclipsi(lat, lon, alt_km)
        # dades del CNIG: nomes les del 2026
        self.cnig = eclipse_data.punt(lat, lon) if eclipse_data.disponible() and eclipsis.actiu() == '2026' else None
        self.marcador_fins = glfw.get_time() + 2.5   # avis discret al panell durant uns segons
        # nom del lloc triat (nucli mes proper i municipi): en un fil, perque la xarxa no aturi res
        if self.nom_punt is None or self.nom_punt[0] != (round(lat_ref, 5), round(lon_ref, 5)):
            self.consulta_nom, self.nom_punt = noms.Consulta(lat_ref, lon_ref), None
        return True

    def reubicar_observador(self):
        """Quan arriben edificis nous (o les altures mesurades) a la zona de l'observador, el punt es torna a triar:
        si ara queda dins d'un edifici, els ulls van a l'exterior. En reproduir, la ubicacio no canvia. Si la camera
        era als ulls, s'hi queda (als ulls nous)."""
        o = self.observador
        if self.reproduint or o is None:
            return
        als_ulls = self.camera_als_ulls()
        lat, lon = (o.lat_ref, o.lon_ref) if o.lat_ref is not None else (o.lat, o.lon)
        nom_punt = self.nom_punt
        self.triar_punt(lat, lon, o.nom)
        self.nom_punt = nom_punt
        if als_ulls:
            self.posar_als_ulls()

    def actualitzar_nom(self):
        """Recull el nom del lloc quan la consulta acaba."""
        c = self.consulta_nom
        if c is not None and c.fet:
            self.consulta_nom = None
            self.nom_punt = (c.clau, c.resultat if c.resultat is not None else dict(nucli=None, municipi=None,
                                                                                     errors=[c.error]))

    def anar_al_punt(self, lat, lon, nom=''):
        """Doble clic al terreny (i desplegable d'ubicacions): el punt d'observacio va al punt i la camera als seus
        ulls (1,7 m sobre el terra), mirant cap al Sol. Es la mateixa camera: des d'alli es continua explorant.
        Durant la reproduccio, com triar_punt, no fa res (avis al panell)."""
        if not self.triar_punt(lat, lon, nom):
            self.avis, self.avis_fins = 'En reproduccio el punt no canvia (P per pausar)', glfw.get_time() + 3.0
            return False
        self.posar_als_ulls()
        self.mirar_el_sol()
        return True

    def text_mapa(self):
        """Estat del mapa (panell), o ''."""
        return self.mapes.text_estat() if self.mapes.quin else ''

    def triar_ubicacio(self, lat, lon, nom):
        """Desplegable del panell: com el doble clic (anar_al_punt), amb el nom de la ubicacio."""
        return self.anar_al_punt(lat, lon, nom)

    def ulls(self):
        """Posicio dels ulls de l'observador (ECEF, km): 1,7 m sobre els triangles que es dibuixen en
        aquell punt (es torna a calcular: l'exageracio de depuracio pot canviar el relleu)."""
        o = self.observador
        return geodesia.ecef(o.lat, o.lon, self.altitud_terra_km(o.lat, o.lon) + ALCADA_ULLS_KM)

    # ------------------------------------------------------------ camera i temps

    def posar_als_ulls(self):
        """La camera als ulls de l'observador (sense canviar la mirada). Mentre no es mogui, segueix els ulls si el
        relleu de sota canvia (seguir_ulls): p. ex. quan arriba el relleu de 5 m d'aquell lloc."""
        cam = self.camera
        cam.aturar_moviment()
        cam.posicio = self.ulls()
        self.ulls_fixats = cam.posicio.copy()

    def camera_als_ulls(self):
        """Si la camera es als ulls de l'observador i no s'ha mogut des que s'hi ha posat."""
        return self.ulls_fixats is not None and np.linalg.norm(self.camera.posicio - self.ulls_fixats) < 1e-6

    def seguir_ulls(self):
        """Cada fotograma: si la camera es als ulls (camera_als_ulls), s'hi torna a posar (el relleu dibuixat pot haver
        canviat). Si l'usuari l'ha moguda, deixa de seguir-los. Girar la mirada no la mou."""
        if self.ulls_fixats is None:
            return
        if not self.camera_als_ulls():
            self.ulls_fixats = None
            return
        self.camera.posicio = self.ulls()
        self.ulls_fixats = self.camera.posicio.copy()

    def mirar_el_sol(self):
        """Orienta la camera cap al Sol (on es dibuixa) des d'on es, sense moure-la. Es una accio puntual:
        despres la mirada torna a ser de l'usuari (el Sol no se segueix)."""
        cam = self.camera
        cam.aturar_moviment()
        lat, lon, _ = geodesia.geodesiques(cam.posicio)
        cam.orientar(*geodesia.azimut_elevacio(self.sol_ecef - cam.posicio, float(lat), float(lon)))

    def tornar_al_punt(self):
        """Boto del panell: la camera torna als ulls de l'observador, amb el mateix rumb i la mirada just sobre
        l'horitzo."""
        self.posar_als_ulls()
        self.camera.orientar(self.camera.rumb, INCLINACIO_EN_ARRIBAR)

    def commutar_espai(self):
        """Tecla G: la primera vegada, la camera va a 12.000 km, entre la vertical del lloc on l'ombra de la Lluna es
        mes fosca a l'hora actual i el Sol (veu la cara de dia), i mira aquell punt; un enquadrament, sense
        seguiment. La segona, torna on era (posicio i mirada, tambe als ulls si hi era). El temps no canvia."""
        cam = self.camera
        cam.aturar_moviment()
        if self.abans_espai is not None:
            posicio, rumb, inclinacio, als_ulls = self.abans_espai
            self.abans_espai = None
            cam.posicio = posicio
            cam.orientar(rumb, inclinacio)
            if als_ulls:
                self.posar_als_ulls()
            return
        self.abans_espai = (cam.posicio.copy(), cam.rumb, cam.inclinacio, self.camera_als_ulls())
        lat_o, lon_o, _ = punt_ombra(self.hora, self.ef)
        cap_al_sol = self.sol_ecef / np.linalg.norm(self.sol_ecef)
        _, _, amunt = geodesia.base_local(lat_o, lon_o)
        punt = geodesia.ecef(lat_o, lon_o, 0.0)
        direccio = amunt + cap_al_sol
        cam.posicio = punt + 12000.0 * direccio / np.linalg.norm(direccio)
        lat, lon, _ = cam.geodesiques()
        cam.orientar(*geodesia.azimut_elevacio(punt - cam.posicio, lat, lon))

    def anar_al_maxim(self):
        """L'hora del maxim de l'eclipsi al punt d'observacio, amb el temps pausat. La camera no es mou."""
        if self.model.valid:
            self.hora, self.reproduint = self.model.hores['maxim'], False

    def canviar_eclipsi(self, clau):
        """Canvia l'eclipsi (dades/eclipsis.py): efemerides, model del punt, espai de navegacio i hora (C1 - 1 h,
        com en arrencar). El punt d'observacio i la camera no canvien. Les capes del CNIG nomes son del 2026."""
        if clau == eclipsis.actiu() or self.reproduint:
            return
        eclipsis.triar(clau)
        self.ef = efemerides()
        o = self.observador
        self.triar_punt(o.lat_ref if o.lat_ref is not None else o.lat, o.lon_ref if o.lat_ref is not None else o.lon,
                        o.nom)
        self.hora = max(self.model.hores['c1'] - HORA_ABANS_C1, self.ef.inici) if self.model.valid else self.ef.inici
        self.cub = cub_navegacio(self.ef, FOV_EXPLORACIO)
        self.paret.destroy()
        self.paret = ParetCub(self, self.cub)
        if clau != '2026':
            for t in self.terrenys():
                t.overlay, t.limits_totalitat = 0, False
        self.camera_exploracio.posicio = self.camera_exploracio.posicio   # dins del cub nou
        self.actualitzar_astres()

    def reproduir_pausar(self):
        """Tecla P: nomes posa en marxa o atura el temps. Si ja s'ha arribat al final, no fa res."""
        if not self.reproduint and self.hora >= self.ef.final:
            return
        self.reproduint = not self.reproduint

    def avancar_temps(self, dt):
        if not self.reproduint:
            return
        v = self.velocitat
        if self.velocitat_auto:  # lent a prop de la totalitat del punt d'observacio
            m = self.model
            a_prop = (m.valid and m.durada is not None
                      and abs(self.hora - m.hores['maxim']) * 3600 < m.durada / 2 + 45)
            v = 5 if a_prop else 60
        self.hora += dt * v / 3600.0
        if self.hora >= self.ef.final:
            self.hora, self.reproduint = self.ef.final, False

    def teclat(self, dt):
        """P reproduir/pausar, G anar a l'espai a veure l'ombra de la Lluna / tornar, Tab capturar o alliberar el
        ratoli, fletxes girar la mirada (velocitat x dt). W A S D desplacen la camera en horitzontal i E / Q la
        pugen o baixen (Ctrl: mes rapid); la velocitat depen de l'altura (camera_exploracio.py)."""
        if imgui.get_io().want_capture_keyboard:
            return
        tecla = lambda k: glfw.get_key(self.window, k) == glfw.PRESS
        if imgui.is_key_pressed(imgui.Key.KEY_G, False):
            self.commutar_espai()
        if imgui.is_key_pressed(imgui.Key.KEY_TAB, False):
            self.ratoli.commutar()
        if imgui.is_key_pressed(imgui.Key.KEY_P, False):
            self.reproduir_pausar()
        cam = self.camera
        dreta, amunt = tecla(glfw.KEY_RIGHT) - tecla(glfw.KEY_LEFT), tecla(glfw.KEY_UP) - tecla(glfw.KEY_DOWN)
        if dreta or amunt:
            cam.girar(VELOCITAT_GIR * dt * dreta * cam.fov / 60.0, VELOCITAT_GIR * dt * amunt * cam.fov / 60.0)
        # desplacament: res si la finestra no te el focus (cap tecla enganxada) o si s'esta fent servir un
        # control del panell (p. ex. arrossegant la barra de temps)
        if not self.ratoli.focus or imgui.is_any_item_active():
            return
        endavant = tecla(glfw.KEY_W) - tecla(glfw.KEY_S)
        costat = tecla(glfw.KEY_D) - tecla(glfw.KEY_A)
        vertical = tecla(glfw.KEY_E) - tecla(glfw.KEY_Q)
        if endavant or costat or vertical:
            rapid = 5.0 if (tecla(glfw.KEY_LEFT_CONTROL) or tecla(glfw.KEY_RIGHT_CONTROL)) else 1.0
            cam.moure(endavant, costat, vertical, dt * rapid)

    # ------------------------------------------------------------ escena a cada instant

    def actualitzar_astres(self):
        """Posicions del Sol i la Lluna (ECEF) a l'hora de simulacio, i el Sol vist des del punt
        d'observacio (per al panell)."""
        self.sol_ecef, self.lluna_ecef = self.ef.posicions(self.hora)
        self.light.azimut, self.light.elevacio = self.model.sol(self.hora)
        self.tapada = self.model.fraccio_tapada(self.hora)

    def actualitzar_cel(self):
        """Atmosfera vista des de la camera: part del Sol tapada, altura, color de la boira cap al Sol i en sentit
        contrari (el color del cel a l'horitzo del mateix model que dibuixa el cel, dades/atmosfera.py) i color
        del disc del Sol (la llum que travessa l'atmosfera fins a la camera). La boira es mes densa a prop del
        terra: la densitat de l'aire decreix exponencialment amb l'altura."""
        cam = self.camera
        lat, lon, alt = geodesia.geodesiques(cam.posicio)
        lat, lon, alt = float(lat), float(lon), float(alt)
        s, l = self.sol_ecef - cam.posicio, self.lluna_ecef - cam.posicio
        az, el = geodesia.azimut_elevacio(s, lat, lon)
        rs = float(np.arcsin(RADI_SOL_KM / np.linalg.norm(s)))
        rl = float(np.arcsin(RADI_LLUNA_KM / np.linalg.norm(l)))
        self.tapada_camera = area_tapada(angle_entre(s, l), rs, rl)
        self.radi_sol_camera = rs
        self.alcada_camera_km = alt
        visible = 1.0 - self.tapada_camera
        self.atmosfera = (1.0 - suau(0.0, ALCADA_ATMOSFERA_KM, max(alt, 0.0))) ** 2
        self.boira_terra = 1.0 / 120.0          # 1/km a nivell del mar: la llum es redueix a 1/e cada 120 km
        # a l'altura de la camera (edificis); el terreny i el globus fan servir la mitjana del cami (terrain.vert)
        self.densitat_boira = math.exp(-max(alt, 0.0) / atmosfera.ESCALA_R_KM) * self.boira_terra
        # colors de la boira: el cel a 1,5 graus sobre l'horitzo, cap al Sol i al contrari. Es tornen a calcular
        # (a la CPU) si l'hora canvia o la camera es mou mes d'un 1 % de la seva altura (o 50 m)
        est, nord, amunt = geodesia.base_local(lat, lon)
        clau = (self.hora, cam.posicio)
        ant = getattr(self, '_clau_boira', None)
        if ant is None or ant[0] != self.hora or np.linalg.norm(ant[1] - cam.posicio) > max(0.05, 0.01 * max(alt, 0.0)):
            self._clau_boira = (self.hora, cam.posicio.copy())
            r = math.radians(az)
            horitzontal = math.sin(r) * est + math.cos(r) * nord
            e = math.radians(1.5)
            colors = [atmosfera.color_cel(cam.posicio, math.cos(e) * signe * horitzontal + math.sin(e) * amunt,
                                          self.sol_ecef, self.lluna_ecef, RADI_SOL_KM, RADI_LLUNA_KM, alt, visible)
                      for signe in (1.0, -1.0)]
            self.boira_sol, self.boira_contra = (tuple(float(v) for v in c) for c in colors)
            self.color_cel = tuple(0.5 * (a + b) for a, b in zip(self.boira_sol, self.boira_contra))
            # color del disc del Sol: la llum que travessa l'atmosfera fins a la camera (el disc no canvia de mida)
            t = atmosfera.color_llum_sol(math.sin(math.radians(el)), max(alt, 0.0))
            self.tint_sol = tuple(float(v) for v in t / max(float(t.max()), 1e-3))
        self.sol_horitzontal = glm.vec3(*(math.sin(math.radians(az)) * est + math.cos(math.radians(az)) * nord))
        self.amunt_camera = glm.vec3(*amunt)
        self.sol_visible.tint = self.halo.tint = self.tint_sol
        # halo: enlluernament de dia i corona a la totalitat (il·lustratiu). La corona es ~10^-6 vegades la brillantor
        # del disc: mentre en queda una mica (encara que sigui el 0,3 %, Cerdanyola) no es veu. Nomes apareix en els
        # ultims segons, amb menys del 0,05 % del disc visible
        corona = 1.0 - suau(0.0, 0.0005, visible)
        self.halo.intensitat = max(0.35 * visible, 0.9 * corona) * (0.4 + 0.6 * self.atmosfera)
        self.sol_visible.visible = self.halo.visible = el > -1.0 or alt > 50.0

    def situar_astres(self):
        """El Sol, el halo i la Lluna a la seva posicio i mida reals, relatives a la camera."""
        rel = self.camera.posicio
        sol_rel, lluna_rel = self.sol_ecef - rel, self.lluna_ecef - rel
        self.sol_visible.situar(v3(sol_rel), RADI_SOL_KM)
        self.halo.situar(v3(sol_rel), 4 * RADI_SOL_KM)
        # la Lluna, amb la cara de la textura (longitud 0) cap a la Terra i el nord cap amunt (aprox.)
        x = -self.lluna_ecef / np.linalg.norm(self.lluna_ecef)
        y = np.array([0.0, 0.0, 1.0]) - x[2] * x
        y /= np.linalg.norm(y)
        z = np.cross(x, y)
        rot = glm.mat4(glm.vec4(*x, 0), glm.vec4(*y, 0), glm.vec4(*z, 0), glm.vec4(0, 0, 0, 1))
        self.lluna.situar(v3(lluna_rel), RADI_LLUNA_KM, rot)
        self.lluna.sun_dir = v3((self.sol_ecef - self.lluna_ecef) / np.linalg.norm(self.sol_ecef - self.lluna_ecef))
        self.lluna.atmosfera = self.atmosfera > 0.3
        self.lluna.radi_sol = float(self.radi_sol_camera)

    def feina_en_curs(self):
        """Si alguna cosa pot canviar la imatge sense que l'usuari faci res: el temps avanca, o hi ha feines en
        segon pla (detall, mapes, teselles, nom del lloc)."""
        return (self.reproduint or bool(self.detall.feines) or self.mapes.ocupat() or bool(self.vegetacio.feines)
                or self.consulta_nom is not None
                or (self.mosaic.actiu and self.mosaic.descarregador.pendents() > 0))

    def signatura(self):
        """El que determina la imatge i pot canviar d'un fotograma al seguent: camera i hora."""
        cam = self.camera
        return (cam.posicio.tobytes(), bytes(cam.m_view), cam.fov, self.hora, self.mapes.quin,
                self.mapes.mode_actual(), len(self.mapes.peces), self.vegetacio.actiu, len(self.vegetacio.cel_les))

    def repos(self):
        """Despres de cada fotograma: si fa REPOS_S que la imatge no canvia i no hi ha feina, espera esdeveniments
        (veure REPOS_S). L'animacio de la camera (inercia, roda) canvia la signatura: no hi entra."""
        ara, s = glfw.get_time(), self.signatura()
        if s != self._signatura or self.feina_en_curs():
            self._signatura, self._quiet_des_de = s, ara
        self.en_repos = ara - self._quiet_des_de > REPOS_S
        if self.en_repos:
            glfw.wait_events_timeout(ESPERA_REPOS_S)

    def run(self):
        """El bucle de GraphicsEngineBase.run (basecode/engine.py, sense canvis) amb aquestes diferencies:
        - Esc primer allibera el ratoli si es capturat (amb el ratoli lliure, Esc tanca el programa, com abans).
        - Abans del panell, no queda cap shader actiu.
        - Sincronia vertical (glfw.swap_interval(1)): swap_buffers espera que la pantalla mostri el fotograma, i
          no se'n fan mes dels que la pantalla pot mostrar (~60 per segon). Sense, es dibuixaven tants com la GPU
          podia (centenars per segon) i l'ordinador s'escalfava. La imatge es la mateixa.
        - Repos quan no canvia res (repos())."""
        glfw.swap_interval(1)
        while not winmod.should_close(self.window):
            glfw.poll_events()
            if winmod.is_escape_pressed(self.window):
                if self.ratoli.capturat:
                    self.ratoli.alliberar()
                    self.esc_premuda = True      # cal deixar anar Esc abans que pugui tancar
                elif not self.esc_premuda:
                    break
            else:
                self.esc_premuda = False
            self.get_time()
            self.ui_renderer.new_frame()
            imgui.new_frame()
            self.render()
            imgui.set_next_window_pos((10, 10), imgui.Cond.FIRST_USE_EVER)
            # sense imgui.ini: en arrencar sempre al mateix lloc i desplegat (les proves, amb el mateix fitxer, el
            # podien deixar mogut o plegat)
            imgui.begin('Eclipsi', False, imgui.WindowFlags.NO_SAVED_SETTINGS)
            self.build_ui()
            imgui.end()
            imgui.render()
            # Cap shader actiu abans de dibuixar el panell: slimgui desa el que hi ha actiu i el reactiva en acabar.
            # Si el panell n'ha alliberat un (p. ex. el cub de navegacio en canviar d'eclipsi), seria un shader
            # esborrat (GLError 1281, invalid value) i el programa es tancava.
            GL.glUseProgram(0)
            self.ui_renderer.render(imgui.get_draw_data())
            glfw.swap_buffers(self.window)
            self.repos()
        self._shutdown()

    def render(self):
        dt = min(self.dt, 0.1)
        self.teclat(dt)
        self.seguir_ulls()          # als ulls de l'observador, la camera segueix el relleu que hi ha a sota
        self.detall.actualitzar()   # detall segons la vista: es prepara i es carrega en segon pla
        self.mapes.actualitzar()    # mapes de l'eclipsi (les peces que vol la vista, en segon pla)
        self.vegetacio.actualitzar()
        self.actualitzar_nom()
        self.actualitzar_edificis()
        self.avancar_temps(dt)
        self.actualitzar_astres()
        # ratoli: amb el ratoli capturat, el moviment gira la mirada (un cop per fotograma, sense dt). La resta del
        # ratoli (roda, arrossegar, doble clic) es processa despres de dibuixar (picking)
        dx, dy, roda = self.ratoli.fotograma()
        if dx or dy:
            self.camera.girar_ratoli(dx, dy)
        # si mai la camera queda dins d'un edifici (p. ex. s'han tornat a mostrar els edificis), surt al punt exterior
        # mes proper; i mai per sota dels ulls, encara que el relleu dibuixat canvii
        fora = self.camera.sortir_dels_edificis()
        if fora:
            self.avis, self.avis_fins = f'Fora de l\'edifici: {fora:.0f} m', glfw.get_time() + 4.0
        self.camera.no_sota_terra()
        self.camera.update()
        self.actualitzar_cel()
        self.situar_astres()
        self.mosaic.actualitzar()   # teselles d'imatge al voltant de la camera (les que ja han arribat)

        self.ombres.actualitzar()   # passada des del Sol (nomes si han canviat l'hora o el punt)
        self.cel.calcular()         # el cel a baixa resolucio (abans de comencar a dibuixar a la pantalla)
        self.ctx.clear(*self.color_cel)
        self.sol_visible.render()
        self.lluna.render()
        self.terra.render()
        for t in self.terrenys():
            t.render()
        if self.edificis is not None:
            self.edificis.render()   # opacs: escriuen la profunditat i tapen el Sol, el halo i el terreny
        self.vegetacio.render()      # opaca, com els edificis
        self.cel.render()    # nomes on no hi ha res dibuixat (no tapa el Sol ni la Lluna) i sense profunditat
        self.terra.render_atmosfera()   # des de l'espai, la resplendor blava al voltant del disc
        self.paret.render()  # translucides: despres dels objectes opacs
        self.halo.render()

        # el ratoli es processa just despres de dibuixar: el depth buffer ja es ple.
        # doble clic: si no s'esta reproduint, el punt d'observacio i la camera van al punt clicat (als ulls, cap al Sol)
        punt = self.camera.processar_ratoli(self.punt_sota_cursor, roda, self.ratoli.capturat)
        if punt is not None:
            lat, lon, _ = geodesia.geodesiques(punt)
            self.anar_al_punt(float(lat), float(lon))
        # FPS: mitjana de cada mig segon (self.dt el calcula GraphicsEngineBase)
        self.frames += 1
        self.temps_fps += self.dt
        if self.temps_fps >= 0.5:
            self.fps = self.frames / self.temps_fps
            self.frames, self.temps_fps = 0, 0.0

    def on_destroy(self):
        self.detall.destroy()
        self.mapes.destroy()
        self.vegetacio.destroy()
        self.mosaic.destroy()
        self.ombres.destroy()
        self.cel.destroy()

    def pixel_cursor(self):
        """(px, py, amplada, alcada): el pixel del framebuffer sota el cursor (origen a baix a l'esquerra), o None
        si el cursor es fora de la finestra."""
        io = imgui.get_io()
        escala_x, escala_y = io.display_framebuffer_scale       # retina: 2 pixels per punt
        _, _, amplada, alcada = self.ctx.viewport
        px = int(io.mouse_pos[0] * escala_x)
        py = alcada - 1 - int(io.mouse_pos[1] * escala_y)       # glfw: y cap avall; GL: y cap amunt
        if not (0 <= px < amplada and 0 <= py < alcada):
            return None
        return px, py, amplada, alcada

    def punt_sota_cursor(self, pixel=None):
        """Picking: llegeix la profunditat del pixel sota el cursor (o del pixel donat, (px, py) del framebuffer) i
        la desprojecta. Retorna el punt del mon (ECEF, km) o None si el cursor apunta al cel."""
        _, _, amplada, alcada = self.ctx.viewport
        if pixel is None:
            pixel = self.pixel_cursor()
            if pixel is None:
                return None
        px, py = pixel[0], pixel[1]
        dades = self.ctx.screen.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4')
        profunditat = float(np.frombuffer(dades, dtype='f4')[0])
        if not 0.0 < profunditat < 1.0:  # 1: no hi ha res dibuixat (cel); 0: sense profunditat (finestra sense buffer)
            return None
        return self.camera.desprojectar(px + 0.5, py + 0.5, profunditat, amplada, alcada)

    # ------------------------------------------------------------ panell

    def build_ui(self):
        ui.build_ui(self)   # el panell i la barra de temps son a ui.py


FITXER_ERROR = os.path.join(_CODE_DIR, 'data', 'cache', 'darrer_error.txt')   # carpeta ignorada pel Git

if __name__ == '__main__':
    app = GraphicsEngine(win_size=(1280, 860), title="EGRA - Eclipsi 12/08/2026", use_ui_panel=True)
    try:
        app.run()
    except Exception:
        # si el programa es tanca per un error, el detall queda desat (encara que s'hagi tancat el terminal)
        import datetime
        import traceback
        os.makedirs(os.path.dirname(FITXER_ERROR), exist_ok=True)
        with open(FITXER_ERROR, 'w') as f:
            f.write(f'{datetime.datetime.now():%d/%m/%Y %H:%M:%S}\n{traceback.format_exc()}')
        print(f'El programa s\'ha tancat per un error; detall desat a {FITXER_ERROR}')
        raise
