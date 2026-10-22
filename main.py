"""
Projecte EGRA -- Simulacio de l'eclipsi total del 12/08/2026 sobre terreny real.
Programa principal: GraphicsEngine (subclasse de GraphicsEngineBase del basecode de classe), que
coordina l'escena: crea els objectes, fa avancar el temps i la llum i els dibuixa.

Segueix l'estructura del repte 4: on_init crea la llum (el Sol), les cameres, els eixos i l'escena
(el terreny, el marcador del punt d'observacio, la Lluna i el Sol); drawables() son els objectes als
quals la camera escriu m_proj i m_view; render() els dibuixa i build_ui() crida el panell de ui.py.

Dues vistes:
  Exploracio   camera lliure per inspeccionar el terreny; doble clic: triar el punt d'observacio
  Observador   els ulls de l'observador, 1,7 m sobre el terra: mirar al voltant i zoom
  Tecla P      vista d'observador mirant el Sol i l'eclipsi reproduit des del punt triat
La ubicacio de l'observador (dades/observador.py) es una dada: el marcador nomes la mostra. Durant la
reproduccio esta bloquejada, perque el model, el panell i la vista siguin sempre del mateix punt.

On es cada cosa:
  ui.py                            panell "Opcions" i barra de temps (slimgui)
  basecode/                        codi de classe (sense canvis) + els nostres objectes grafics:
    sol.py                           el Sol: Light del basecode amb azimut i elevacio (self.light)
    terrain.py                       terreny (textures, graella, faldilles) + shaders/terrain.*
    astres.py                        esferes de la Lluna, el Sol i el halo + shaders/esfera.*
    camera_exploracio.py             camera orbital per explorar el terreny
    camera_observador.py             camera als ulls de l'observador
  dades/                           sense OpenGL:
    observador.py                    la ubicacio de l'observador (nomes dades)
    model_eclipsi.py                 on son el Sol i la Lluna a cada hora, vistos des d'un punt
    data_io.py                       lectura dels MDT (data/mdt/), mascares, derivats i cache (data/cache/)
    eclipse_data.py                  dataset de l'eclipsi del CNIG (overlays i valors en un punt)

Executa:  python main.py                    (Picos de Europa, data/mdt/picos_5m.tif)
          python main.py data/mdt/xxx.tif   (un altre MDT en EPSG:25830)
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
from slimgui import imgui

from basecode.engine import GraphicsEngineBase
from basecode.axis import Axis
from basecode.camera_exploracio import CameraExploracio
from basecode.camera_observador import CameraObservador
from basecode.astres import Esfera, Lluna, EMISSIVA, HALO
from dades.model_eclipsi import ModelEclipsi, RADI_ANGULAR_SOL, RADI_ANGULAR_LLUNA
from dades.observador import Observador, ALCADA_ULLS_KM
from basecode.sol import Sol
from dades.data_io import TERRENYS
from basecode.terrain import Terrain, COLOR_CEL
from dades import eclipse_data
import ui

MODELS_DIR = os.path.join(_CODE_DIR, 'models')  # models .obj (cada un a la seva carpeta), com al repte 4
REGIO = 'Picos'           # de moment, una sola regio (data_io.TERRENYS)

COLOR_NIT = (0.02, 0.03, 0.08)     # cel a la totalitat / de nit
COLOR_POSTA = (0.93, 0.70, 0.55)   # to del cel amb el Sol baix
VELOCITAT_DESPLACAMENT = 0.02      # km/s minims de la camera d'exploracio amb WASD (de lluny va mes rapid)
VELOCITAT_GIR = 60.0               # graus/s amb les fletxes
COLOR_MARCADOR = (0.95, 0.35, 0.15)


def suau(a, b, x):
    """smoothstep de GLSL: 0 per sota de a, 1 per sobre de b."""
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def barreja(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


class GraphicsEngine(GraphicsEngineBase):
    def on_init(self):
        self.ctx.enable_only(mgl.DEPTH_TEST)  # sense CULL_FACE: el terreny es veu per sota tambe
        self.light = Sol()
        self.axis = self.lluna = self.sol_visible = self.halo = self.marcador = None

        cami = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else next(c for n, c, _ in TERRENYS if n == REGIO)
        self.nom_regio = os.path.basename(cami) if len(sys.argv) > 1 else 'Picos de Europa (MDT 5 m)'
        t0 = time.time()
        self.terrain = Terrain(self, cami)
        self.terrain.exaggeration = 1.0   # relleu real
        print(f"Terreny carregat en {time.time() - t0:.1f} s")

        # temps de l'eclipsi (hores TU)
        self.reproduint = False
        self.velocitat = 60
        self.velocitat_auto = False
        self.tapada = 0.0

        # l'observador comenca al centre del terreny; d'alla surten el model i les dades del CNIG
        self.triar_punt(0.0, 0.0)
        self.hora = self.model.interval()[0]   # una mica abans de l'inici de l'eclipsi
        self.light.azimut, self.light.elevacio = self.model.sol(self.hora)
        self.camera_exploracio = CameraExploracio(self, self.terrain)
        self.camera_exploracio.inicial = (0.0, 6.0, 0.6)   # gir, inclinacio, distancia (km)
        self.camera_exploracio.reset()
        self.camera_exploracio.mirar_azimut(self.light.azimut)
        self.camera_observador = CameraObservador(self)
        self.camera = self.camera_exploracio
        self.vista = 0   # index a ui.VISTES: 0 exploracio, 1 observador

        self.axis = Axis(self, length=1.0)
        self.axis.visible = False
        self.marcador = Esfera(self, color=COLOR_MARCADOR)   # mostra on es l'observador (nomes dibuix)
        self.marcador.ambient = 4.0                          # que no quedi negre a contrallum
        self.lluna = Lluna(self)
        self.sol_visible = Esfera(self, color=(1.0, 0.96, 0.85), mode=EMISSIVA)
        self.halo = Esfera(self, color=(1.0, 0.95, 0.85), mode=HALO)
        self.distancia_lluna = 2.0 * max(self.terrain.mida)  # km (la real, ~364000, no cap a l'escena)

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.on_resize(self.window, *glfw.get_framebuffer_size(self.window))  # per si ja ha canviat
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0

    def drawables(self):
        # els objectes que encara no existeixen (mentre es creen les cameres) son None
        objectes = [self.axis, self.terrain, self.marcador, self.lluna, self.sol_visible, self.halo]
        return [obj for obj in objectes if obj is not None]

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera_exploracio.aspect_ratio = self.camera_observador.aspect_ratio = amplada / alcada
        self.camera.update()

    # ------------------------------------------------------------ observador i vistes

    def triar_punt(self, x, z):
        """Posa l'observador al punt (x, z) del terreny (km) i hi calcula, tot alhora, el model del Sol
        i la Lluna i les dades del CNIG: aixi sempre corresponen al mateix punt.
        Durant la reproduccio la ubicacio esta bloquejada: no canvia res i retorna False."""
        if self.reproduint:
            return False
        mx, mz = 0.499 * self.terrain.mida.x, 0.499 * self.terrain.mida.y
        x, z = min(max(x, -mx), mx), min(max(z, -mz), mz)
        i = self.terrain.info_punt(x, z)
        self.observador = Observador(x, z, i['lat'], i['lon'], i['altitud'])
        self.model = ModelEclipsi(i['lat'], i['lon'])
        self.cnig = eclipse_data.punt(i['lat'], i['lon']) if eclipse_data.disponible() else None
        return True

    def ulls(self):
        """Posicio dels ulls de l'observador al mon (km): 1,7 m sobre la superficie dibuixada."""
        o = self.observador
        return glm.vec3(o.x, self.terrain.altitud_mon(o.x, o.z) + ALCADA_ULLS_KM, o.z)

    def canviar_vista(self, vista):
        if vista == self.vista:
            return
        self.vista = vista
        if vista == 1:  # mirant cap on mirava la camera d'exploracio
            self.camera_observador.mirar(self.camera_exploracio.azimut_vista(), 5.0)
            self.camera = self.camera_observador
        else:
            self.camera_exploracio.mirar_azimut(self.camera_observador.azimut_vista())
            self.camera = self.camera_exploracio
        self.marcador.visible = vista == 0

    def eclipsi_des_d_aqui(self):
        """Tecla P: vista d'observador mirant el Sol i l'eclipsi reproduit des del punt triat."""
        self.canviar_vista(1)
        self.camera_observador.seguir_sol = True
        self.camera_observador.fov = 20.0   # una mica de zoom: el Sol i el relleu del voltant
        if self.model.valid:
            self.hora = self.model.hores['c1'] - 1 / 60
        self.reproduint = True
        self.velocitat_auto = True

    def teclat(self, dt):
        """Exploracio: WASD desplacen la camera (Ctrl, mes rapid). Les dues vistes: fletxes per
        mirar, V per canviar de vista i P per veure l'eclipsi des del punt triat."""
        if imgui.get_io().want_capture_keyboard:
            return
        tecla = lambda k: glfw.get_key(self.window, k) == glfw.PRESS
        if imgui.is_key_pressed(imgui.Key.KEY_V, False):
            self.canviar_vista(1 - self.vista)
        if imgui.is_key_pressed(imgui.Key.KEY_P, False):
            self.eclipsi_des_d_aqui()

        cam = self.camera
        if self.vista == 0:
            moviment = cam.endavant() * (tecla(glfw.KEY_W) - tecla(glfw.KEY_S)) \
                + cam.dreta() * (tecla(glfw.KEY_D) - tecla(glfw.KEY_A))
            if glm.length(moviment) > 0:
                v = max(VELOCITAT_DESPLACAMENT, 0.5 * cam.distance)   # de lluny es va mes rapid
                if tecla(glfw.KEY_LEFT_CONTROL) or tecla(glfw.KEY_RIGHT_CONTROL):
                    v *= 5
                cam.target += glm.normalize(moviment) * v * dt   # update() el mante dins del terreny
        dreta, amunt = tecla(glfw.KEY_RIGHT) - tecla(glfw.KEY_LEFT), tecla(glfw.KEY_UP) - tecla(glfw.KEY_DOWN)
        if dreta or amunt:
            cam.girar(VELOCITAT_GIR * dt * dreta, VELOCITAT_GIR * dt * amunt)

    def avancar_temps(self, dt):
        if not self.reproduint:
            return
        v = self.velocitat
        if self.velocitat_auto:  # lent a prop de la totalitat, rapid a les fases parcials
            m = self.model
            a_prop = m.valid and abs(self.hora - m.hores['maxim']) * 3600 < (m.durada or 0) / 2 + 45
            v = 5 if a_prop else 150
        self.hora += dt * v / 3600.0
        final = self.model.interval()[1]
        if self.hora >= final:
            self.hora, self.reproduint = final, False

    def actualitzar_llum(self):
        """Sol a l'hora actual, i la llum del terreny i del cel segons l'eclipsi."""
        m, h = self.model, self.hora
        self.light.azimut, self.light.elevacio = m.sol(h)
        el = self.light.elevacio
        self.tapada = m.fraccio_tapada(h)
        visible = 1.0 - self.tapada
        sol_sobre = suau(-1.0, 1.0, el)     # el Sol per sobre de l'horitzo
        dia = suau(-6.0, 4.0, el)           # crepuscle: el cel s'apaga quan el Sol baixa de -6 graus
        llum_cel = max(0.03, dia * (0.04 + 0.96 * visible ** 0.4))
        color_dia = barreja(COLOR_CEL, COLOR_POSTA, 0.45 * (1.0 - suau(0.0, 15.0, el)))
        self.color_cel = barreja(COLOR_NIT, color_dia, llum_cel)

        t = self.terrain
        t.llum_sol, t.llum_cel, t.color_cel = visible * sol_sobre, llum_cel, self.color_cel
        self.lluna.atmosfera = self.vista == 1
        self.sol_visible.visible = self.halo.visible = el > -0.6
        # halo: enlluernament de dia i corona a la totalitat
        corona = 1.0 - suau(0.0, 0.004, visible)
        self.halo.intensitat = max(0.35 * visible, 0.9 * corona)

    def situar_lluna(self):
        """La Lluna a la seva direccio vista des dels ulls de l'observador."""
        d = self.distancia_lluna
        self.lluna.situar(self.ulls() + d * self.model.direccio_lluna(self.hora), d * RADI_ANGULAR_LLUNA)

    def situar_marcador(self):
        """Esfera al punt de l'observador. Es dibuixa mes gran quan la camera s'allunya, perque es
        vegi des de lluny (entre 1,7 m i 300 m de radi); no forma part de la dada de l'observador."""
        o = self.observador
        radi = min(max(0.04 * self.camera_exploracio.distance, ALCADA_ULLS_KM), 0.3)
        terra = glm.vec3(o.x, self.terrain.altitud_mon(o.x, o.z), o.z)
        self.marcador.situar(terra + glm.vec3(0, radi, 0), radi)

    def render(self):
        dt = min(self.dt, 0.1)
        self.teclat(dt)
        self.avancar_temps(dt)
        self.actualitzar_llum()
        if self.vista == 1:
            self.camera.processar_ratoli()
        self.situar_lluna()   # abans de la camera: el far l'ha d'incloure
        self.camera.update()
        cam = self.camera
        self.situar_marcador()
        # el Sol i el halo "a l'infinit": a la direccio del Sol des de la camera, darrere de tot
        s = self.light.direccio()
        self.sol_visible.situar(cam.position + cam.dist_sol * s, cam.dist_sol * RADI_ANGULAR_SOL)
        self.halo.situar(self.sol_visible.centre, 4 * cam.dist_sol * RADI_ANGULAR_SOL)

        self.ctx.clear(color=self.color_cel)
        self.terrain.render()
        self.marcador.render()
        self.lluna.render()
        self.sol_visible.render()
        # eixos a l'objectiu de la camera, amb una llargada proporcional al terreny
        self.axis.m_model = glm.translate(cam.target) * glm.scale(glm.vec3(0.1 * max(self.terrain.mida)))
        self.axis.shader_program['m_model'].write(self.axis.m_model)
        self.axis.render()
        self.halo.render()   # l'ultim: es transparent

        if self.vista == 0:
            # el ratoli es processa just despres de dibuixar: el depth buffer ja es ple.
            # doble clic: la camera s'hi centra i, si no s'esta reproduint, l'observador hi va
            punt = cam.processar_ratoli(self.punt_sota_cursor)
            if punt is not None:
                self.triar_punt(punt.x, punt.z)
        # FPS: mitjana de cada mig segon (self.dt el calcula GraphicsEngineBase)
        self.frames += 1
        self.temps_fps += self.dt
        if self.temps_fps >= 0.5:
            self.fps = self.frames / self.temps_fps
            self.frames, self.temps_fps = 0, 0.0

    def punt_sota_cursor(self):
        """Picking: llegeix la profunditat del pixel sota el cursor i la desprojecta.
        Retorna el punt del mon (glm.vec3, km) o None si el cursor apunta al cel."""
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
