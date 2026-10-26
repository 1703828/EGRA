"""
Projecte EGRA -- Simulacio de l'eclipsi total del 12/08/2026 sobre terreny real.
Programa principal: GraphicsEngine (subclasse de GraphicsEngineBase del basecode de classe), que
coordina l'escena: crea els objectes, fa avancar el temps i els dibuixa.

L'escena es un model geometric coherent en coordenades terrestres (ECEF, km): la Terra (el·lipsoide
WGS84 amb textura), el relleu de la peninsula (MDT de 200 m), una zona de detall (MDT de 5 m) al
voltant del punt d'observacio (Picos, Vic, l'Escala o el Valles) i el Sol i la Lluna a les seves
posicions reals (efemerides de JPL Horizons). L'ombra de la Lluna es calcula per a cada punt.

Nivells de detall del relleu, de lluny a prop: la graella general de la peninsula (~1 km entre
vertexs), un pegat de la peninsula al voltant de l'observador (200 m, ~100 km), la zona de 5 m
(~20 m entre vertexs) i un pegat de la zona al voltant de l'observador (5 m, ~2,5 km). Cada nivell
fa un forat al de sota i, a la vora, la seva altura passa suaument a la del de sota.

Espai de navegacio: un cub fix que conte la Terra, la Lluna i el Sol (dades/navegacio.py); la camera
d'exploracio no en pot sortir i, a prop, se'n veuen les parets (basecode/paret_cub.py).
Ratoli: un clic a l'escena captura el ratoli per mirar sense premer cap boto; Esc l'allibera
(basecode/control_ratoli.py). GraphicsEngine.run() es el bucle del basecode amb un sol canvi per a l'Esc.

Tres coses independents:
  - el temps de simulacio (self.hora, TU): nomes canvia quan es reprodueix (tecla P);
  - el punt d'observacio (self.observador): nomes canvia quan se'n tria un (i no durant la reproduccio);
  - la camera: la d'exploracio (lliure) o la d'observacio (als ulls, 1,7 m sobre el terra).

Segueix l'estructura del repte 4: on_init crea la llum, les cameres i l'escena; drawables() son els
objectes als quals la camera escriu m_proj i m_view; render() els dibuixa i build_ui() crida ui.py.

On es cada cosa:
  ui.py                            panell i barra de temps (slimgui)
  basecode/                        codi de classe (sense canvis) + els nostres objectes grafics:
    terra.py                         la Terra (globus)
    terrain.py                       relleu d'un MDT (mode globus: posat sobre la Terra)
    astres.py                        el Sol, el seu halo i la Lluna
    sol.py                           la llum (Light del basecode)
    camera_exploracio.py             camera lliure (del terreny a l'espai)
    camera_observador.py             camera als ulls de l'observador
    camera_orbital.py                camera del mode pla (nomes per als scripts)
    programes.py                     carrega shaders amb opcions (#define)
  dades/                           sense OpenGL: efemerides, geodesia, model de l'eclipsi, observador,
                                   lectura dels MDT i dades del CNIG

Executa:  python main.py
"""
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
import rasterio
from slimgui import imgui

from basecode.engine import GraphicsEngineBase
from basecode.camera_exploracio import CameraExploracio, COEF_LOG, direccio_mirada, FOV as FOV_EXPLORACIO
from basecode.camera_observador import CameraObservador
from basecode.astres import Esfera, Lluna, SOL, HALO
from basecode.sol import Sol
from basecode.terra import Terra
from basecode.terrain import Terrain, COLOR_CEL
from basecode.ombres_relleu import OmbresRelleu
from basecode.paret_cub import ParetCub
from basecode.control_ratoli import ControlRatoli
from basecode import window as winmod
from dades.data_io import TERRENYS, ZONES_DETALL
from dades.model_eclipsi import ModelEclipsi, area_tapada, angle_entre, efemerides, punt_ombra
from dades.efemerides import RADI_SOL_KM, RADI_LLUNA_KM
from dades.observador import Observador, ALCADA_ULLS_KM, UBICACIONS
from dades.navegacio import cub_navegacio
from dades import eclipse_data, geodesia
import ui

MODELS_DIR = os.path.join(_CODE_DIR, 'models')  # models .obj (cada un a la seva carpeta), com al repte 4
COLOR_NIT = (0.02, 0.03, 0.08)     # cel a la totalitat / de nit
COLOR_POSTA = (0.93, 0.70, 0.55)   # to del cel amb el Sol baix
VELOCITAT_GIR = 60.0               # graus/s amb les fletxes
ALCADA_ATMOSFERA_KM = 60.0         # per sobre, el cel ja es negre (aproximacio visual)
HORA_ABANS_C1 = 1.0                # l'arrencada es aquest nombre d'hores abans de C1 (temps TU del model)


def suau(a, b, x):
    """smoothstep de GLSL: 0 per sota de a, 1 per sobre de b."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def barreja(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def v3(a):
    return glm.vec3(float(a[0]), float(a[1]), float(a[2]))


class GraphicsEngine(GraphicsEngineBase):
    def on_init(self):
        self.ctx.enable_only(mgl.DEPTH_TEST)  # sense CULL_FACE: el terreny es veu per sota tambe
        self.light = Sol()
        self.coef_log = COEF_LOG
        self.radi_sol_km, self.radi_lluna_km = RADI_SOL_KM, RADI_LLUNA_KM
        self.terra = self.peninsula = self.zona = self.sol_visible = self.halo = self.lluna = self.paret = None

        # --- territori: la peninsula sencera posada sobre la Terra; la zona de detall de 5 m es
        # carrega quan es tria un punt d'observacio que hi es (triar_punt)
        t0 = time.time()
        cami = {n: c for n, c, _ in TERRENYS}
        self.peninsula = Terrain(self, cami['Peninsula'], globus=True)
        self.peninsula.exaggeration = 1.0
        self.peninsula.limits_totalitat = False   # les capes tecniques, nomes des de l'apartat Avancat
        # zones de detall disponibles (fitxers descarregats) i el rectangle que ocupen (UTM, m)
        self.zones = []
        for nom, cami_zona, ordre in ZONES_DETALL:
            if os.path.exists(cami_zona):
                with rasterio.open(cami_zona) as f:
                    self.zones.append((nom, cami_zona, f.bounds))
            else:
                print(f"AVIS: falta la zona de detall '{nom}': python scripts/descarregar_mdt.py {ordre}")
        self.nom_zona = None
        self.terra = Terra(self)
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

        # --- punt d'observacio (dada independent): Picos de Europa
        nom, lat, lon = UBICACIONS[0]
        self.triar_punt(lat, lon, nom)
        # arrencada: pausat, una hora abans del primer contacte (C1) calculat pel model en aquest punt.
        # Nomes en arrencar: canviar d'ubicacio despres no toca el temps
        self.hora = max(self.model.hores['c1'] - HORA_ABANS_C1, self.ef.inici) if self.model.valid else self.ef.inici
        self.actualitzar_astres()

        # --- espai de navegacio: fix durant la sessio, calculat amb tot l'interval de les efemerides
        self.cub = cub_navegacio(self.ef, FOV_EXPLORACIO)
        self.ratoli = ControlRatoli(self)
        self.esc_premuda = False

        # --- cameres: comencem mirant cap al Sol des del terra
        az, el = self.model.sol(self.hora)
        self.camera_observador = CameraObservador(self)
        self.camera_observador.mirar(az, el)
        self.camera_exploracio = CameraExploracio(self, self.ulls())
        self.posar_exploracio_sobre_el_punt()
        self.camera = self.camera_observador
        self.vista = 1   # index a ui.VISTES: 0 exploracio, 1 observador

        self.lluna = Lluna(self)
        self.sol_visible = Esfera(self, color=(1.0, 0.96, 0.85), mode=SOL)
        self.halo = Esfera(self, color=(1.0, 0.95, 0.85), mode=HALO)
        self.paret = ParetCub(self, self.cub)
        self.color_cel, self.densitat_boira = COLOR_CEL, 0.0

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.on_resize(self.window, *glfw.get_framebuffer_size(self.window))  # per si ja ha canviat
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0

    def drawables(self):
        objectes = [self.terra, self.peninsula, self.zona, self.lluna, self.sol_visible, self.halo, self.paret]
        return [obj for obj in objectes if obj is not None]

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera_exploracio.aspect_ratio = self.camera_observador.aspect_ratio = amplada / alcada
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

    def posar_detall(self, lat, lon):
        """Carrega la zona de 5 m que conte el punt (si n'hi ha) i posa els pegats densos al voltant del
        punt. Nomes es mante carregada una zona: la de l'observador (cada una ocupa uns 200 MB)."""
        x, y = self.peninsula.de_latlon.transform(lon, lat)
        nom = next((n for n, _, b in self.zones if b.left < x < b.right and b.bottom < y < b.top), None)
        if nom != self.nom_zona:
            if self.zona is not None:
                self.zona.destroy()
                self.zona, self.peninsula.fills = None, []
            if nom is not None:
                t0 = time.time()
                cami = next(c for n, c, _ in self.zones if n == nom)
                self.zona = Terrain(self, cami, globus=True)
                self.zona.pare, self.zona.dibuixar_mar = self.peninsula, True
                for atribut in ('exaggeration', 'overlay', 'opacitat', 'limits_totalitat', 'wireframe'):
                    setattr(self.zona, atribut, getattr(self.peninsula, atribut))
                self.peninsula.fills = [self.zona]
                print(f"Zona de detall '{nom}' carregada en {time.time() - t0:.1f} s")
            self.nom_zona = nom
        # de lluny a prop: cada nivell depen de la superficie del de sota
        self.peninsula.posar_pegat(lat, lon)
        if self.zona is not None:
            self.zona.actualitzar_transicio()
            self.zona.posar_pegat(lat, lon)
        if self.camera is not None:
            self.camera.update()   # la zona nova tambe ha de rebre les matrius de la camera

    def triar_punt(self, lat, lon, nom=''):
        """Posa l'observador al punt (lat, lon) i hi calcula, tot alhora, el model del Sol i la Lluna
        i les dades del CNIG: aixi sempre corresponen al mateix punt.
        Durant la reproduccio la ubicacio esta bloquejada: no canvia res i retorna False."""
        if self.reproduint:
            return False
        self.posar_detall(lat, lon)
        alt_km = self.altitud_terra_km(lat, lon)
        self.observador = Observador(lat, lon, alt_km * 1000.0, nom)
        self.model = ModelEclipsi(lat, lon, alt_km)
        self.cnig = eclipse_data.punt(lat, lon) if eclipse_data.disponible() else None
        self.marcador_fins = glfw.get_time() + 2.5   # avis discret al panell durant uns segons
        return True

    def triar_ubicacio(self, lat, lon, nom):
        """Desplegable del panell: l'observador va a la ubicacio i la camera d'exploracio se situa a sobre,
        perque en passar a explorar (V) es parteixi del lloc triat. La mirada als ulls es conserva.
        (El doble clic explorant crida nomes triar_punt: la camera es queda on es.)"""
        if self.triar_punt(lat, lon, nom):
            self.posar_exploracio_sobre_el_punt()
            return True
        return False

    def ulls(self):
        """Posicio dels ulls de l'observador (ECEF, km): 1,7 m sobre els triangles que es dibuixen en
        aquell punt (es torna a calcular: l'exageracio de depuracio pot canviar el relleu)."""
        o = self.observador
        return geodesia.ecef(o.lat, o.lon, self.altitud_terra_km(o.lat, o.lon) + ALCADA_ULLS_KM)

    # ------------------------------------------------------------ vistes i temps

    def canviar_vista(self, vista):
        """Cada camera conserva la seva posicio i orientacio: canviar de vista no les modifica."""
        self.vista = vista
        self.camera = self.camera_observador if vista == 1 else self.camera_exploracio

    def tornar_al_punt(self):
        """Vista d'observacio al punt triat (amb la mirada que tenia)."""
        self.canviar_vista(1)

    def posar_exploracio_sobre_el_punt(self):
        """Camera d'exploracio a 6 km del punt d'observacio, d'esquena al Sol i mirant cap al punt."""
        o = self.observador
        az, _ = self.model.sol(self.hora)
        darrere = direccio_mirada(o.lat, o.lon, az + 180.0, 0.0)
        _, _, amunt = geodesia.base_local(o.lat, o.lon)
        self.camera_exploracio.posicio = self.ulls() + 6.0 * darrere + 3.0 * amunt
        self.camera_exploracio.rumb, self.camera_exploracio.inclinacio = az, -25.0

    def veure_ombra_des_de_lespai(self):
        """Enquadrament (una sola vegada, sense seguiment): la camera d'exploracio a 12.000 km, entre la
        vertical del lloc i el Sol (veu la cara de dia), mirant el punt on l'ombra de la Lluna es mes fosca
        a l'hora actual. El temps no canvia."""
        lat_o, lon_o, _ = punt_ombra(self.hora, self.ef)
        cap_al_sol = self.sol_ecef / np.linalg.norm(self.sol_ecef)
        _, _, amunt = geodesia.base_local(lat_o, lon_o)
        punt = geodesia.ecef(lat_o, lon_o, 0.0)
        cam = self.camera_exploracio
        direccio = amunt + cap_al_sol
        cam.posicio = punt + 12000.0 * direccio / np.linalg.norm(direccio)
        lat, lon, _ = cam.geodesiques()
        az, el = geodesia.azimut_elevacio(punt - cam.posicio, lat, lon)
        cam.rumb, cam.inclinacio = az, el
        self.canviar_vista(0)

    def anar_al_maxim(self):
        """L'hora del maxim de l'eclipsi al punt d'observacio, amb el temps pausat. La camera no es mou."""
        if self.model.valid:
            self.hora, self.reproduint = self.model.hores['maxim'], False

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
        """P reproduir/pausar, V canviar de vista, fletxes girar la mirada; a l'exploracio, W A S D
        desplacen la camera i E / Q la pugen o baixen (Ctrl: mes rapid)."""
        if imgui.get_io().want_capture_keyboard:
            return
        tecla = lambda k: glfw.get_key(self.window, k) == glfw.PRESS
        if imgui.is_key_pressed(imgui.Key.KEY_V, False):
            self.canviar_vista(1 - self.vista)
        if imgui.is_key_pressed(imgui.Key.KEY_P, False):
            self.reproduir_pausar()
        cam = self.camera
        dreta, amunt = tecla(glfw.KEY_RIGHT) - tecla(glfw.KEY_LEFT), tecla(glfw.KEY_UP) - tecla(glfw.KEY_DOWN)
        if dreta or amunt:
            cam.girar(VELOCITAT_GIR * dt * dreta * cam.fov / 60.0, VELOCITAT_GIR * dt * amunt * cam.fov / 60.0)
        if self.vista == 0:
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
        """Color del cel i boira segons on es la camera: el Sol que hi veu (altura i part tapada) i
        l'altura de la camera (per sobre de l'atmosfera el cel es negre). Aproximacio visual."""
        cam = self.camera
        lat, lon, alt = geodesia.geodesiques(cam.posicio)
        lat, lon, alt = float(lat), float(lon), float(alt)
        s, l = self.sol_ecef - cam.posicio, self.lluna_ecef - cam.posicio
        _, el = geodesia.azimut_elevacio(s, lat, lon)
        rs = float(np.arcsin(RADI_SOL_KM / np.linalg.norm(s)))
        rl = float(np.arcsin(RADI_LLUNA_KM / np.linalg.norm(l)))
        self.tapada_camera = area_tapada(angle_entre(s, l), rs, rl)
        self.radi_sol_camera = rs
        visible = 1.0 - self.tapada_camera
        dia = suau(-6.0, 4.0, el)           # crepuscle: el cel s'apaga quan el Sol baixa de -6 graus
        llum_cel = max(0.03, dia * (0.04 + 0.96 * visible ** 0.4))
        color_dia = barreja(COLOR_CEL, COLOR_POSTA, 0.45 * (1.0 - suau(0.0, 15.0, el)))
        cel = barreja(COLOR_NIT, color_dia, llum_cel)
        self.atmosfera = (1.0 - suau(0.0, ALCADA_ATMOSFERA_KM, max(alt, 0.0))) ** 2
        self.color_cel = tuple(c * self.atmosfera for c in cel)
        self.densitat_boira = self.atmosfera / 250.0     # visibilitat d'uns 250 km a nivell del terra
        # halo: enlluernament de dia i corona a la totalitat (il·lustratiu)
        corona = 1.0 - suau(0.0, 0.004, visible)
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

    def run(self):
        """El bucle de GraphicsEngineBase.run (basecode/engine.py, sense canvis) amb una sola diferencia: Esc
        primer allibera el ratoli si es capturat; amb el ratoli lliure, Esc tanca el programa, com abans."""
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
            imgui.begin('Opcions')
            self.build_ui()
            imgui.end()
            imgui.render()
            self.ui_renderer.render(imgui.get_draw_data())
            glfw.swap_buffers(self.window)
        self._shutdown()

    def render(self):
        dt = min(self.dt, 0.1)
        self.teclat(dt)
        self.avancar_temps(dt)
        self.actualitzar_astres()
        # ratoli: amb el ratoli capturat, el moviment gira la mirada; la roda va a la camera activa
        dx, dy, roda = self.ratoli.fotograma(glfw.get_time())
        if dx or dy:
            self.camera.girar_ratoli(dx, dy)
        if self.vista == 1:
            self.camera.processar_ratoli(roda, self.ratoli.capturat)
        self.camera.update()
        self.actualitzar_cel()
        self.situar_astres()

        self.ombres.actualitzar()   # passada des del Sol (nomes si han canviat l'hora o el punt)
        self.ctx.clear(*self.color_cel)
        self.sol_visible.render()
        self.lluna.render()
        self.terra.render()
        for t in self.terrenys():
            t.render()
        self.paret.render()  # translucides: despres dels objectes opacs
        self.halo.render()

        if self.vista == 0:
            # el ratoli es processa just despres de dibuixar: el depth buffer ja es ple.
            # doble clic: si no s'esta reproduint, l'observador va al punt clicat
            punt = self.camera.processar_ratoli(self.punt_sota_cursor, roda, self.ratoli.capturat)
            if punt is not None:
                lat, lon, _ = geodesia.geodesiques(punt)
                self.triar_punt(float(lat), float(lon))
        # FPS: mitjana de cada mig segon (self.dt el calcula GraphicsEngineBase)
        self.frames += 1
        self.temps_fps += self.dt
        if self.temps_fps >= 0.5:
            self.fps = self.frames / self.temps_fps
            self.frames, self.temps_fps = 0, 0.0

    def on_destroy(self):
        self.ombres.destroy()

    def punt_sota_cursor(self):
        """Picking: llegeix la profunditat del pixel sota el cursor i la desprojecta.
        Retorna el punt del mon (ECEF, km) o None si el cursor apunta al cel."""
        io = imgui.get_io()
        escala_x, escala_y = io.display_framebuffer_scale       # retina: 2 pixels per punt
        _, _, amplada, alcada = self.ctx.viewport
        px = int(io.mouse_pos[0] * escala_x)
        py = alcada - 1 - int(io.mouse_pos[1] * escala_y)       # glfw: y cap avall; GL: y cap amunt
        if not (0 <= px < amplada and 0 <= py < alcada):
            return None
        dades = self.ctx.screen.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4')
        profunditat = float(np.frombuffer(dades, dtype='f4')[0])
        if profunditat >= 1.0:  # no hi ha res dibuixat (cel)
            return None
        return self.camera.desprojectar(px + 0.5, py + 0.5, profunditat, amplada, alcada)

    # ------------------------------------------------------------ panell

    def build_ui(self):
        ui.build_ui(self)   # el panell i la barra de temps son a ui.py


if __name__ == '__main__':
    app = GraphicsEngine(win_size=(1280, 860), title="EGRA - Eclipsi 12/08/2026", use_ui_panel=True)
    app.run()
