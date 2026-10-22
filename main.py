"""
Projecte EGRA -- Simulacio de l'eclipsi total del 12/08/2026 sobre terreny real.
Programa principal: GraphicsEngine (subclasse de GraphicsEngineBase del basecode de classe) i panell.

Segueix l'estructura del repte 4: on_init crea la llum (el Sol), les cameres, els eixos i l'escena
(el terreny, el personatge, la Lluna i el Sol); drawables() son els objectes als quals la camera
escriu m_proj i m_view; render() els dibuixa i build_ui() fa el panell "Opcions" i la barra de temps.

Es com un videojoc (model de la plantilla de joc d'Spline): un personatge camina pel terreny.
  Tercera persona  la camera el segueix (orbital, camera.py)
  Primera persona  la camera son els seus ulls (camera_primera_persona.py)
  Tecla P          primera persona mirant el Sol i l'eclipsi reproduit des d'aquell punt

Moduls:
  sol.py                    el Sol: Light del basecode amb azimut i elevacio (self.light)
  model_eclipsi.py          on son el Sol i la Lluna a cada hora, vistos des d'un punt
  camera.py                 camera orbital (tercera persona)
  camera_primera_persona.py camera dels ulls del personatge
  personatge.py             el personatge (camina i salta)
  astres.py                 esferes de la Lluna i el Sol + basecode/shaders/esfera.vert i .frag
  terrain.py                terreny (textures, graella, faldilles) + basecode/shaders/terrain.vert i .frag
  data_io.py                lectura dels MDT (data/mdt/), mascares, derivats i cache .npz (data/cache/)
  eclipse_data.py           dataset de l'eclipsi del CNIG (overlays i valors en un punt)

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
from camera import Camera
from camera_primera_persona import CameraPrimeraPersona
from basecode.personatge import Personatge
from basecode.astres import Esfera, Lluna, EMISSIVA, HALO
from dades.model_eclipsi import ModelEclipsi, RADI_ANGULAR_SOL, RADI_ANGULAR_LLUNA
from basecode.sol import Sol
from dades.data_io import TERRENYS
from basecode.terrain import (Terrain, COLOR_CEL, OVERLAYS, ENFOSQUIMENT_MIN,
                     COLORS_ENFOSQUIMENT, COLOR_TOTALITAT, COLORS_DURADA, COLORS_OMBRES)
from dades import eclipse_data

MODELS_DIR = os.path.join(_CODE_DIR, 'models')  # models .obj (cada un a la seva carpeta), com al repte 4
REGIO = 'Picos'           # de moment, una sola regio (data_io.TERRENYS)
VISTES = ['Tercera persona', 'Primera persona']

COLOR_NIT = (0.02, 0.03, 0.08)     # cel a la totalitat / de nit
COLOR_POSTA = (0.93, 0.70, 0.55)   # to del cel amb el Sol baix
VELOCITATS = [1, 10, 60, 300]      # x temps real ('Auto' a mes: lent a la totalitat)
VELOCITAT_CAMINAR = 0.02           # km/s en primera persona (72 km/h: un "heroi" de videojoc)
VELOCITAT_GIR = 60.0               # graus/s amb les fletxes
COLOR_FASE = {'TOTALITAT': (1.0, 0.45, 0.9, 1.0), 'Eclipsi parcial': (1.0, 0.8, 0.3, 1.0)}


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
        self.axis = self.lluna = self.sol_visible = self.halo = self.personatge = None

        cami = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else next(c for n, c, _ in TERRENYS if n == REGIO)
        self.nom_regio = os.path.basename(cami) if len(sys.argv) > 1 else 'Picos de Europa (MDT 5 m)'
        t0 = time.time()
        self.terrain = Terrain(self, cami)
        self.terrain.exaggeration = 1.0   # relleu real (a la vista de joc es camina per sobre)
        print(f"Terreny carregat en {time.time() - t0:.1f} s")

        # el personatge comenca al centre del terreny i la camera el mira des de darrere, cap al Sol
        self.personatge = Personatge(self)
        self.actualitzar_model(forcar=True)
        self.hora = self.model.interval()[0]   # una mica abans de l'inici de l'eclipsi
        self.light.azimut, self.light.elevacio = self.model.sol(self.hora)
        self.camera_tercera = Camera(self, self.terrain)
        self.camera_tercera.inicial = (0.0, 6.0, 0.6)   # gir, inclinacio, distancia (km)
        self.camera_tercera.reset()
        self.camera_tercera.mirar_azimut(self.light.azimut)
        self.camera_primera = CameraPrimeraPersona(self, self.personatge)
        self.camera = self.camera_tercera
        self.vista = 0   # index a VISTES

        self.axis = Axis(self, length=1.0)
        self.axis.visible = False
        self.lluna = Lluna(self)
        self.sol_visible = Esfera(self, color=(1.0, 0.96, 0.85), mode=EMISSIVA)
        self.halo = Esfera(self, color=(1.0, 0.95, 0.85), mode=HALO)
        self.distancia_lluna = 2.0 * max(self.terrain.mida)  # km (la real, ~364000, no cap a l'escena)

        # temps de l'eclipsi (hores TU)
        self.reproduint = False
        self.velocitat = 60
        self.velocitat_auto = False
        self.tapada = 0.0

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.on_resize(self.window, *glfw.get_framebuffer_size(self.window))  # per si ja ha canviat
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0

    def drawables(self):
        # els objectes que encara no existeixen (mentre es creen les cameres) son None
        objectes = [self.axis, self.terrain, self.lluna, self.sol_visible, self.halo]
        if self.personatge is not None:
            objectes += self.personatge.objectes()
        return [obj for obj in objectes if obj is not None]

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera_tercera.aspect_ratio = self.camera_primera.aspect_ratio = amplada / alcada
        self.camera.update()

    # ------------------------------------------------------------ joc

    def info_aqui(self):
        """Coordenades i altitud del punt on es el personatge."""
        return self.terrain.info_punt(self.personatge.x, self.personatge.z)

    def actualitzar_model(self, forcar=False):
        """Model de l'eclipsi al punt del personatge; es refa quan s'ha mogut mes de 500 m."""
        p = self.personatge
        if not forcar and glm.length(glm.vec2(p.x, p.z) - self.punt_model) < 0.5:
            return
        info = self.info_aqui()
        self.model = ModelEclipsi(info['lat'], info['lon'])
        self.punt_model = glm.vec2(p.x, p.z)
        self.cnig = eclipse_data.punt(info['lat'], info['lon']) if eclipse_data.disponible() else None

    def canviar_vista(self, vista):
        if vista == self.vista:
            return
        self.vista = vista
        if vista == 1:  # mirant cap on mirava la camera en tercera persona
            self.camera_primera.mirar(self.camera_tercera.azimut_vista(), 5.0)
            self.camera = self.camera_primera
        else:
            self.camera_tercera.mirar_azimut(self.camera_primera.azimut_vista())
            self.camera = self.camera_tercera
        self.personatge.visible = vista == 0

    def eclipsi_des_d_aqui(self):
        """Tecla P: primera persona mirant el Sol i l'eclipsi reproduit des d'aquest punt."""
        self.actualitzar_model(forcar=True)
        self.canviar_vista(1)
        self.camera_primera.seguir_sol = True
        self.camera_primera.fov = 20.0   # una mica de zoom: el Sol i el relleu del voltant
        if self.model.valid:
            self.hora = self.model.hores['c1'] - 1 / 60
        self.reproduint = True
        self.velocitat_auto = True

    def teclat(self, dt):
        """WASD per caminar, Espai per saltar, fletxes per mirar, Ctrl per correr, V i P."""
        if imgui.get_io().want_capture_keyboard:
            return
        tecla = lambda k: glfw.get_key(self.window, k) == glfw.PRESS
        if imgui.is_key_pressed(imgui.Key.KEY_V, False):
            self.canviar_vista(1 - self.vista)
        if imgui.is_key_pressed(imgui.Key.KEY_P, False):
            self.eclipsi_des_d_aqui()

        cam, p, t = self.camera, self.personatge, self.terrain
        moviment = cam.endavant() * (tecla(glfw.KEY_W) - tecla(glfw.KEY_S)) \
            + cam.dreta() * (tecla(glfw.KEY_D) - tecla(glfw.KEY_A))
        if glm.length(moviment) > 0:
            # en tercera persona la velocitat va amb el zoom: de lluny es corre mes
            v = VELOCITAT_CAMINAR if self.vista == 1 else max(VELOCITAT_CAMINAR, 0.5 * cam.distance)
            if tecla(glfw.KEY_LEFT_CONTROL) or tecla(glfw.KEY_RIGHT_CONTROL):
                v *= 5
            pas = glm.normalize(moviment) * v * dt
            mx, mz = 0.499 * t.mida.x, 0.499 * t.mida.y
            p.x = min(max(p.x + pas.x, -mx), mx)
            p.z = min(max(p.z + pas.z, -mz), mz)
        if tecla(glfw.KEY_SPACE):
            p.saltar()
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
        """La Lluna a la seva direccio des de l'observador (els ulls o el cap del personatge)."""
        p = self.personatge
        if self.vista == 1:
            observador = p.peus(p.ALCADA_REAL) + glm.vec3(0, p.ALCADA_REAL, 0)
        else:
            observador = p.peus() + glm.vec3(0, 0.9 * p.alcada, 0)
        d = self.distancia_lluna
        self.lluna.situar(observador + d * self.model.direccio_lluna(self.hora), d * RADI_ANGULAR_LLUNA)

    def render(self):
        dt = min(self.dt, 0.1)
        p = self.personatge
        self.teclat(dt)
        if not self.reproduint:
            self.actualitzar_model()
        self.avancar_temps(dt)
        self.actualitzar_llum()
        p.actualitzar(dt)

        if self.vista == 0:
            cam = self.camera
            # marcador visible des de lluny (com als videojocs), pero no gegant
            p.alcada = max(p.ALCADA_REAL, min(0.1 * cam.distance, 0.3))
            cam.alcada_objectiu = (0.6 + p.salt) * p.alcada
            cam.target.x, cam.target.z = p.x, p.z
        else:
            self.camera.processar_ratoli()
        self.situar_lluna()   # abans de la camera: el far l'ha d'incloure
        self.camera.update()
        cam = self.camera
        # el Sol i el halo "a l'infinit": a la direccio del Sol des de la camera, darrere de tot
        s = self.light.direccio()
        self.sol_visible.situar(cam.position + cam.dist_sol * s, cam.dist_sol * RADI_ANGULAR_SOL)
        self.halo.situar(self.sol_visible.centre, 4 * cam.dist_sol * RADI_ANGULAR_SOL)

        self.ctx.clear(color=self.color_cel)
        self.terrain.render()
        p.render()
        self.lluna.render()
        self.sol_visible.render()
        # eixos al personatge, amb una llargada proporcional al terreny
        self.axis.m_model = glm.translate(cam.target) * glm.scale(glm.vec3(0.1 * max(self.terrain.mida)))
        self.axis.shader_program['m_model'].write(self.axis.m_model)
        self.axis.render()
        self.halo.render()   # l'ultim: es transparent

        if self.vista == 0:
            # el ratoli es processa just despres de dibuixar: el depth buffer ja es ple.
            # doble clic: el personatge hi va; arrossegar amb el boto dret: el personatge es desplaca
            cam.processar_ratoli(self.punt_sota_cursor)
            p.x, p.z = cam.target.x, cam.target.z
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
        imgui.set_window_size((340, 0), imgui.Cond.ALWAYS)   # amplada fixa, alcada segons el contingut
        imgui.text_colored((1.0, 0.85, 0.4, 1.0), 'ECLIPSI TOTAL - 12/08/2026')
        imgui.text_disabled(self.nom_regio)

        imgui.separator_text('Vista  (tecla V)')
        for i, nom in enumerate(VISTES):
            if i > 0:
                imgui.same_line()
            if imgui.radio_button(nom, self.vista == i):
                self.canviar_vista(i)
        if imgui.collapsing_header('Controls', None, imgui.TreeNodeFlags.DEFAULT_OPEN)[0]:
            self.panell_controls()

        imgui.separator_text('Ara mateix')
        self.panell_ara()

        if imgui.collapsing_header('Aquest punt (dades del CNIG)')[0]:
            self.panell_punt()
        if imgui.collapsing_header('Capes sobre el terreny')[0]:
            self.panell_overlays()
        if imgui.collapsing_header('Avancat')[0]:
            self.panell_avancat()
        imgui.spacing()
        imgui.text_disabled('MDT i eclipsi (c) IGN / CNIG (CC BY 4.0)')

        self.barra_temps()

    def panell_controls(self):
        linies = ['W A S D: caminar', 'Espai: saltar   Ctrl: correr']
        if self.vista == 0:
            linies += ['Arrossegar o fletxes: girar', 'Roda: zoom   Doble clic: anar-hi']
        else:
            linies += ['Arrossegar o fletxes: mirar', f'Roda: zoom (ara x{self.camera.zoom():.1f})']
        linies += ["P: l'eclipsi des d'aqui"]
        for linia in linies:
            imgui.bullet_text(linia)

    def panell_ara(self):
        m = self.model
        fase = m.fase(self.hora)
        imgui.text(f'{eclipse_data.hora_local(self.hora)} CEST')
        imgui.same_line()
        imgui.text_colored(COLOR_FASE.get(fase, (0.8, 0.8, 0.8, 1.0)), fase)
        imgui.progress_bar(self.tapada, (-1.0, 0.0), f'Sol tapat: {self.tapada * 100:.1f} %')
        el = self.light.elevacio
        estat = "sota l'horitzo" if el < 0 else f'a {el:.1f} graus'
        imgui.text(f'Sol: azimut {self.light.azimut:.0f}, {estat}')
        if self.vista == 1 and self.camera.seguir_sol:
            imgui.text_disabled('Seguint el Sol (gira per deixar-ho)')
        if imgui.button("Veure l'eclipsi des d'aqui (P)", (-1.0, 0.0)):
            self.eclipsi_des_d_aqui()

    def panell_punt(self):
        i = self.info_aqui()
        imgui.text(f"{i['lat']:.4f}, {i['lon']:.4f}   {i['altitud']:.0f} m")
        e = self.cnig
        if e is None:
            imgui.text_disabled("Sense dades de l'eclipsi en aquest punt")
            return
        if imgui.begin_table('fases', 2, imgui.TableFlags.ROW_BG | imgui.TableFlags.BORDERS_INNER_H):
            files = [(nom, hora if visible else f'{hora} (Sol post)') for nom, hora, visible in e['fases']]
            files += [('Posta del Sol', e['posta']),
                      ('Durada totalitat', f"{e['durada']:.1f} s" if e['durada'] else 'no n\'hi ha'),
                      ('Enfosquiment max.', f"{e['enfosquiment'] * 100:.2f} %")]
            for nom, valor in files:
                imgui.table_next_row()
                imgui.table_next_column()
                imgui.text(nom)
                imgui.table_next_column()
                imgui.text(valor)
            imgui.end_table()
        imgui.text_wrapped(f"Relleu (CNIG): {e['text_ombres']}")
        imgui.text_disabled('Hores en CEST (TU + 2)')

    def panell_overlays(self):
        """Overlays de l'eclipsi (un de cada vegada), opacitat i llegenda dels colors."""
        t = self.terrain
        for i, nom in enumerate(OVERLAYS):
            if imgui.radio_button(nom, t.overlay == i):
                t.overlay = i
        if t.overlay:
            _, t.opacitat = imgui.slider_float('Opacitat', t.opacitat, 0, 1)
        _, t.limits_totalitat = imgui.checkbox('Limits de la totalitat', t.limits_totalitat)

        def llegenda(color, text):
            imgui.color_button(f'##{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (14, 14))
            imgui.same_line()
            imgui.text(text)

        if t.overlay == 1:
            passos = [ENFOSQUIMENT_MIN + (1 - ENFOSQUIMENT_MIN) * k / 3 for k in range(4)]
            for color, valor in zip(COLORS_ENFOSQUIMENT, passos):
                llegenda(color, f'{valor * 100:.1f} %')
            llegenda(COLOR_TOTALITAT, 'totalitat (100 %)')
        elif t.overlay == 2:
            for k, color in enumerate(COLORS_DURADA):
                llegenda(color, f'{t.durada_min + (t.durada_max - t.durada_min) * k / 4:.0f} s')
            imgui.text_disabled('  linies cada 10 s; nomes dins la franja')
        elif t.overlay == 3:
            for classe, color in enumerate(COLORS_OMBRES):
                llegenda(color, f'{classe}: {eclipse_data.CLASSES_OMBRES[classe]}')
            imgui.text_disabled('  sense color: sense dades')

    def panell_avancat(self):
        t, cam = self.terrain, self.camera
        imgui.text(f'FPS: {self.fps:.0f} ({1000 / max(self.fps, 1e-6):.1f} ms)   '
                   f'triangles: {t.n_triangles / 1e6:.2f} M')
        _, t.exaggeration = imgui.slider_float('Exageracio Y', t.exaggeration, 1, 20)
        _, t.boira = imgui.slider_float('Boira', t.boira, 0, 1)
        mida = max(t.mida)
        _, self.distancia_lluna = imgui.slider_float('Distancia Lluna (km)', self.distancia_lluna,
                                                     0.5 * mida, 364200, '%.0f', imgui.SliderFlags.LOGARITHMIC)
        imgui.text_disabled('  real ~364200 km (la mida aparent\n  sempre es la real)')
        _, t.wireframe = imgui.checkbox('Filferros', t.wireframe)
        imgui.same_line()
        _, t.curvatura = imgui.checkbox('Curvatura', t.curvatura)
        imgui.same_line()
        _, self.axis.visible = imgui.checkbox('Eixos', self.axis.visible)
        if self.vista == 0:
            _, cam.distance = imgui.slider_float('Zoom (km)', cam.distance, cam.dist_min, cam.dist_max,
                                                 '%.2f', imgui.SliderFlags.LOGARITHMIC)
            if imgui.button('Mirar des de darrere la Lluna', (-1.0, 0.0)):
                # la camera a la banda del Sol, mes lluny que la Lluna i una mica mes amunt
                cam.yaw = (180.0 - self.light.azimut + 180.0) % 360.0 - 180.0
                cam.pitch = self.light.elevacio + 3.0
                cam.distance = min(1.3 * self.distancia_lluna, cam.dist_max)
        imgui.text(f'near {cam.near * 1000:.1f} m  far {cam.far:.0f} km')

    def barra_temps(self):
        """Finestra de la barra de temps, a baix al mig (com un reproductor de video)."""
        m = self.model
        io = imgui.get_io()
        w, h = io.display_size
        imgui.set_next_window_pos((w / 2, h - 12), imgui.Cond.ALWAYS, (0.5, 1.0))
        imgui.set_next_window_size((min(w - 40, 760), 0), imgui.Cond.ALWAYS)
        imgui.set_next_window_bg_alpha(0.85)
        flags = (imgui.WindowFlags.NO_TITLE_BAR | imgui.WindowFlags.NO_RESIZE | imgui.WindowFlags.NO_MOVE
                 | imgui.WindowFlags.NO_COLLAPSE | imgui.WindowFlags.NO_SAVED_SETTINGS)
        imgui.begin('Temps', False, flags)
        inici, final = m.interval()
        if imgui.button('Pausa' if self.reproduint else 'Play', (70, 0)):
            self.reproduint = not self.reproduint
            if self.reproduint and self.hora >= final:
                self.hora = inici
        imgui.same_line()
        if imgui.button('-5 min'):
            self.hora -= 5 / 60
        imgui.same_line()
        if imgui.button('+5 min'):
            self.hora += 5 / 60
        imgui.same_line()
        imgui.text('   Velocitat:')
        for v in VELOCITATS:
            imgui.same_line()
            if imgui.radio_button(f'x{v}', not self.velocitat_auto and self.velocitat == v):
                self.velocitat, self.velocitat_auto = v, False
        imgui.same_line()
        if imgui.radio_button('Auto', self.velocitat_auto):
            self.velocitat_auto = True

        self.hora = min(max(self.hora, inici), final)
        imgui.push_item_width(-1.0)
        text = f'{eclipse_data.hora_local(self.hora)} CEST  -  {m.fase(self.hora)}'
        canviat, minuts = imgui.slider_float('##hora', (self.hora - inici) * 60, 0, (final - inici) * 60,
                                             text.replace('%', '%%'))
        imgui.pop_item_width()
        if canviat:
            self.hora = inici + minuts / 60
        if m.valid:
            hh, hl = m.hores, eclipse_data.hora_local
            text = f"Inici {hl(hh['c1'])[:5]}"
            if hh['c2'] is not None:
                text += f"   |   Totalitat {hl(hh['c2'])} - {hl(hh['c3'])}"
            text += f"   |   Final {hl(hh['c4'])[:5]}"
            if hh['posta'] is not None:
                text += f"   |   Posta {hl(hh['posta'])[:5]}"
            imgui.text_disabled(text)
        imgui.end()


if __name__ == '__main__':
    app = GraphicsEngine(win_size=(1280, 860), title="EGRA - Eclipsi 12/08/2026", use_ui_panel=True)
    app.run()
