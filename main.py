"""
Projecte EGRA -- Simulacio d'un eclipsi sobre terreny real (12/08/2026).
Programa principal: GraphicsEngine (subclasse de GraphicsEngineBase del basecode de classe) i panell.

Moduls:
  camera.py        camera orbital amb ratoli, enganxada al terreny
  terrain.py       terreny (textures, graella, faldilles) + shaders/terrain.vert i .frag
  data_io.py       lectura dels MDT (data/mdt/), mascares, derivats i cache .npz (data/cache/)
  eclipse_data.py  dataset de l'eclipsi del CNIG (overlays i punt d'observacio)

Executa:  python main.py                         (selector amb els terrenys de data/mdt/)
          python main.py data/mdt05/PNOA_...tif  (afegeix un altre MDT en EPSG:25830)
"""
import os
import sys
import time

import glfw
import numpy as np
import moderngl as mgl
from slimgui import imgui

from basecode.engine import GraphicsEngineBase
from camera import Camera
from data_io import TERRENYS
from terrain import (Terrain, limits_utm, zones_de_detall, COLOR_CEL, OVERLAYS, ENFOSQUIMENT_MIN,
                     COLORS_ENFOSQUIMENT, COLOR_TOTALITAT, COLORS_DURADA, COLORS_OMBRES)
import eclipse_data


class GraphicsEngine(GraphicsEngineBase):
    def on_init(self):
        self.ctx.enable_only(mgl.DEPTH_TEST)  # sense CULL_FACE: el terreny es veu per sota tambe
        self.llista = [t for t in TERRENYS if os.path.exists(t[1])]
        for nom, cami, _ in TERRENYS:
            if not os.path.exists(cami):
                print(f"AVIS: no hi ha {cami}; el terreny '{nom}' no surt al selector")
        if len(sys.argv) > 1:  # un MDT passat per la linia de comandes
            self.llista.append(('Fitxer', os.path.abspath(sys.argv[1]), False))
        self.limits = limits_utm(self.llista)  # per als rectangles de les zones de detall

        self.terrenys = {}           # nom -> Terrain, es carreguen la primera vegada que es trien
        self.terrain = None
        self.camera = None
        self.curvatura = False
        self.punt_observacio = None  # ultim punt triat amb doble clic (es fara servir a la T6)
        self.seleccionar(self.llista[-1][0] if len(sys.argv) > 1 else self.llista[0][0])

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0

    def seleccionar(self, nom):
        """Canvia al terreny 'nom' (el carrega si es la primera vegada). Si l'objectiu de la camera
        tambe cau dins del terreny nou, es mante el mateix punt geografic (via coordenades UTM)."""
        anterior = self.terrain
        info = anterior.info_punt(self.camera.target.x, self.camera.target.z) if anterior else None

        if nom not in self.terrenys:
            t0 = time.time()
            cami = next(c for n, c, _ in self.llista if n == nom)
            self.terrenys[nom] = Terrain(self, cami)
            print(f"Terreny '{nom}' carregat en {time.time() - t0:.1f} s")
        t = self.terrain = self.terrenys[nom]
        self.nom_terreny = nom

        es_detall = any(n == nom and detall for n, _, detall in self.llista)
        t.zones = [] if es_detall else zones_de_detall(t, self.llista, self.limits)

        punt = None
        if info is not None and anterior.crs == t.crs:
            punt = t.mon_de_utm(info['x_utm'], info['y_utm'])
        if self.camera is None:
            self.camera = Camera(self, t)
        else:
            self.camera.canviar_terreny(t, punt)

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera.aspect_ratio = amplada / alcada
        self.camera.update()

    def drawables(self):
        return [self.terrain]

    def on_destroy(self):
        # el terreny actual l'allibera GraphicsEngineBase (es a drawables); aqui, la resta
        for t in self.terrenys.values():
            if t is not self.terrain:
                t.destroy()

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

    def triar_punt(self, x, z):
        """Punt d'observacio: coordenades del punt (x, z) del terreny actual i, si hi ha el dataset,
        els valors de l'eclipsi llegits dels GeoTIFF originals en aquell punt."""
        p = self.terrain.info_punt(x, z)
        p['eclipsi'] = eclipse_data.punt(p['lat'], p['lon']) if eclipse_data.disponible() else None
        self.punt_observacio = p

    def render(self):
        self.terrain.curvatura = self.curvatura
        self.camera.update()  # l'objectiu segueix el terreny si canvia l'exageracio o la curvatura
        self.ctx.clear(color=COLOR_CEL)
        self.terrain.render()
        # el ratoli es processa just despres de dibuixar el terreny: el depth buffer ja es ple
        punt = self.camera.processar_ratoli(self.punt_sota_cursor)
        if punt is not None:
            self.triar_punt(punt.x, punt.z)
        # FPS: mitjana de cada mig segon (self.dt el calcula GraphicsEngineBase)
        self.frames += 1
        self.temps_fps += self.dt
        if self.temps_fps >= 0.5:
            self.fps = self.frames / self.temps_fps
            self.frames, self.temps_fps = 0, 0.0

    def build_ui(self):
        imgui.text(f'FPS: {self.fps:.0f} ({1000 / max(self.fps, 1e-6):.1f} ms)')
        imgui.text(f'Triangles: {self.terrain.n_triangles / 1e6:.2f} M')
        imgui.separator()
        imgui.text('Terreny (la primera vegada es carrega)')
        for i, (nom, _, _) in enumerate(self.llista):
            if i > 0:
                imgui.same_line()
            if imgui.radio_button(nom, nom == self.nom_terreny) and nom != self.nom_terreny:
                self.seleccionar(nom)
        t, cam = self.terrain, self.camera
        if t.zones:
            _, t.mostrar_zones = imgui.checkbox('Zones de detall', t.mostrar_zones)
        _, self.curvatura = imgui.checkbox('Curvatura de la Terra', self.curvatura)
        imgui.separator()
        imgui.text('Camera')
        _, cam.yaw = imgui.slider_float('Gir', cam.yaw, -180, 180)
        _, cam.pitch = imgui.slider_float('Inclinacio', cam.pitch, 1, 89)
        _, cam.distance = imgui.slider_float('Distancia (km)', cam.distance, cam.dist_min, cam.dist_max,
                                             '%.2f', imgui.SliderFlags.LOGARITHMIC)
        if imgui.button('Reiniciar camera'):
            cam.reset()
        cam.update()
        objectiu = t.info_punt(cam.target.x, cam.target.z)
        imgui.text(f"Objectiu: {objectiu['lat']:.4f}, {objectiu['lon']:.4f}  {objectiu['altitud']:.0f} m")
        imgui.text(f'near {cam.near * 1000:.1f} m  far {cam.far:.0f} km')
        imgui.separator()
        imgui.text('Punt d\'observacio (doble clic)')
        p = self.punt_observacio
        if p is None:
            imgui.text('  cap punt seleccionat')
        else:
            imgui.text(f"  UTM {p['x_utm']:.0f} E  {p['y_utm']:.0f} N ({t.crs})")
            imgui.text(f"  lat {p['lat']:.5f}  lon {p['lon']:.5f}")
            imgui.text(f"  altitud {p['altitud']:.0f} m")
            self.panell_eclipsi_punt(p.get('eclipsi'))
        imgui.separator()
        self.panell_overlays()
        imgui.separator()
        imgui.text('Terreny')
        _, t.exaggeration = imgui.slider_float('Exageracio Y', t.exaggeration, 1, 20)
        _, t.boira = imgui.slider_float('Boira', t.boira, 0, 1)
        _, t.wireframe = imgui.checkbox('Filferros', t.wireframe)
        imgui.separator()
        imgui.text('Sol')
        _, t.sun_azimuth = imgui.slider_float('Azimut', t.sun_azimuth, 0, 360)
        _, t.sun_elevation = imgui.slider_float('Elevacio', t.sun_elevation, -5, 90)
        imgui.separator()
        imgui.text_disabled('Eclipsi: informacio astronomica oficial')
        imgui.text_disabled('IGN / Observatori Astronomic Nacional (CC BY 4.0)')
        imgui.text_disabled('MDT (c) IGN / CNIG')

    def panell_eclipsi_punt(self, e):
        """Valors de l'eclipsi al punt d'observacio (hores en CEST = TU + 2)."""
        if e is None:
            imgui.text('  (sense dades de l\'eclipsi en aquest punt)')
            return
        imgui.text(f"  Sol al maxim: azimut {e['azimut']:.1f}  elevacio {e['elevacio']:.1f} graus")
        imgui.text(f"  Enfosquiment maxim: {e['enfosquiment'] * 100:.2f} %")
        for nom, hora, visible in e['fases']:
            if visible:
                imgui.text(f"  {nom}: {hora}")
            else:
                imgui.text_colored((1.0, 0.6, 0.3, 1.0), f"  {nom}: {hora} (no visible: el Sol ja s'ha post)")
        if e['durada'] is not None:
            imgui.text(f"  Durada de la totalitat: {e['durada']:.1f} s")
        else:
            imgui.text('  Fora de la franja de totalitat')
        imgui.text(f"  Posta del Sol: {e['posta']}   (hores CEST = TU+2)")
        imgui.text(f"  Ombres CNIG: {e['text_ombres']}")
        if imgui.button("Sol al maxim de l'eclipsi"):
            self.terrain.sun_azimuth, self.terrain.sun_elevation = e['azimut'], e['elevacio']

    def panell_overlays(self):
        """Overlays de l'eclipsi (un de cada vegada), opacitat i llegenda dels colors."""
        t = self.terrain
        imgui.text("Eclipsi sobre el terreny")
        for i, nom in enumerate(OVERLAYS):
            if i % 2 == 1:
                imgui.same_line()
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


if __name__ == '__main__':
    app = GraphicsEngine(win_size=(1200, 900), title="EGRA - Terreny MDT", use_ui_panel=True)
    app.run()
