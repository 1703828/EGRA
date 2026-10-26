"""
Ombres del relleu (shadow mapping): on una muntanya tapa el Sol a un punt del terreny.

Es diferent de l'ombra de la Lluna (la part del Sol que tapa la Lluna, terrain.frag: tapat_des_de) i
de l'ocultacio del Sol pel relleu vista des de l'observador (scripts/validar_horitzo.py).

Dues passades:
  1. Des del Sol (actualitzar): el relleu de la zona de detall de 5 m es dibuixa amb una projeccio
     ortografica (raigs paral·lels) en una textura de profunditat. Cada texel guarda a quina distancia
     del Sol es la primera superficie que troba aquell raig.
  2. Fotograma normal (aplicar, terrain.frag: llum_relleu): cada fragment de la zona es passa al mateix
     espai de la llum. Si es mes lluny del Sol que el que guarda el mapa, una altra superficie li tapa el
     Sol i nomes rep la llum del cel.

Decisions:
  - El mapa s'ancora al punt d'observacio: les posicions son relatives a l'ancora (km, float32), com la
    resta de l'escena es relativa a la camera.
  - La caixa de la llum s'ajusta al quadrat de terreny (MIDA_KM al voltant de l'observador) vist des del
    Sol. Amb el Sol baix, una caixa quadrada estiraria molt cada texel sobre el terra.
  - La llum ve del Sol aparent (azimut i elevacio amb refraccio, com el CNIG i D18): es la direccio de
    la qual arriba la llum al terra. El terreny es geometric.
  - Nomes la zona de 5 m projecta i rep ombres (primera versio, zona controlada). La peninsula no.
  - El mapa nomes es torna a calcular quan canvia l'hora, el punt o el relleu.
"""
import glm
import moderngl as mgl
import numpy as np

from .camera_exploracio import direccio_mirada
from .programes import carregar_programa
from dades import geodesia

RESOLUCIO = 4096       # texels per costat del mapa d'ombres
MIDA_KM = 16.0         # mig costat del quadrat de terreny cobert, al voltant de l'observador
DIST_SOL_KM = 150.0    # on es posa la "camera" de la llum, cap al Sol (ha de ser mes enlla de les muntanyes)
UNITAT_TEXTURA = 6     # unitat de textura del mapa (terrain.frag en fa servir de la 0 a la 5)
DESPLACAMENT_TEXELS = 1.0   # el punt es mira 1 texel fora de la superficie (amb 0,5 apareix acne)
BIAIX_KM = 0.003       # i 3 m mes a prop del Sol. Junts: obstacles mes baixos que ~11 m no fan ombra


class OmbresRelleu:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        self.textura = self.ctx.depth_texture((RESOLUCIO, RESOLUCIO))
        self.textura.repeat_x = self.textura.repeat_y = False
        # comparacio per maquinari (sampler2DShadow) amb filtre lineal: cada lectura ja barreja 2 x 2 texels
        self.textura.compare_func = '<='
        self.textura.filter = (mgl.LINEAR, mgl.LINEAR)
        self.fbo = self.ctx.framebuffer(depth_attachment=self.textura)
        self.programa = carregar_programa(self.ctx, 'ombra')
        self.actiu = True             # interruptor de l'apartat Avancat
        self.depuracio = False        # scripts: el terreny es pinta amb el factor d'ombra (1 llum, 0 ombra)
        self.valid = False            # hi ha un mapa per a la zona actual
        self.m_llum = glm.mat4()
        self.ancora = np.zeros(3)
        self.clau = None              # (hora, punt, exageracio) del mapa calculat
        self.zona = self.pegat = None # zona i pegat dels VAO (referencies, no copies)
        self.vaos = {}                # VAO de la passada des del Sol per a cada nivell de la zona
        self.texel_km = 2 * MIDA_KM / RESOLUCIO
        self.fbo.clear(depth=1.0)

    def vao(self, clau, vbo, vbo_h, ibo):
        """VAO amb el programa de la passada des del Sol i els buffers del terreny (els mateixos que es
        dibuixen: no hi ha cap copia de la geometria)."""
        if clau not in self.vaos:
            self.vaos[clau] = self.ctx.vertex_array(
                self.programa, [(vbo, '2f 3f 3f 12x', 'in_uv', 'in_offset', 'in_amunt'), (vbo_h, '1f', 'in_h')],
                index_buffer=ibo)
        return self.vaos[clau]

    def oblidar_vaos(self):
        for v in self.vaos.values():
            v.release()
        self.vaos = {}

    def matriu_llum(self, lat, lon, zona):
        """m_llum: de posicio relativa a l'ancora (km) a coordenades de clip de la llum."""
        app = self.app
        az, el = app.model.sol(app.hora)                    # Sol aparent (amb refraccio)
        cap_al_sol = direccio_mirada(lat, lon, az, el)
        est, nord, amunt = geodesia.base_local(lat, lon)
        vista = glm.lookAt(glm.vec3(*(cap_al_sol * DIST_SOL_KM)), glm.vec3(0.0), glm.vec3(*amunt))
        # cantonades del quadrat de terreny (de -50 m, per la curvatura, fins a l'altitud maxima de la zona)
        alt_max = zona.max_height / 1000.0 * zona.exaggeration + 0.05
        xs, ys = [], []
        for a in (-MIDA_KM, MIDA_KM):
            for b in (-MIDA_KM, MIDA_KM):
                for h in (-0.05, alt_max):
                    q = vista * glm.vec4(*(a * est + b * nord + h * amunt), 1.0)
                    xs.append(q.x)
                    ys.append(q.y)
        proj = glm.ortho(min(xs), max(xs), min(ys), max(ys), 1.0, 2 * DIST_SOL_KM)
        self.texel_km = max((max(xs) - min(xs)), (max(ys) - min(ys))) / RESOLUCIO
        return proj * vista, el

    def actualitzar(self):
        """Passada des del Sol, si ha canviat alguna cosa. Es crida abans de dibuixar el fotograma."""
        app, zona = self.app, self.app.zona
        o = app.observador
        if not self.actiu or zona is None or not zona.conte(o.lat, o.lon):
            self.valid = False
            return
        pegat = zona.pegat
        if zona is not self.zona or pegat is not self.pegat:
            self.oblidar_vaos()          # zona o pegat nous: els buffers han canviat
            self.zona, self.pegat, self.clau = zona, pegat, None
        clau = (app.hora, o.lat, o.lon, zona.exaggeration)
        if clau == self.clau:
            return
        self.clau = clau
        self.ancora = geodesia.ecef(o.lat, o.lon, 0.0)
        self.m_llum, el = self.matriu_llum(o.lat, o.lon, zona)
        self.valid = el > -1.0            # amb el Sol sota l'horitzo no hi ha ombres del relleu

        anterior, viewport = self.ctx.fbo, self.ctx.viewport
        self.fbo.use()
        self.fbo.clear(depth=1.0)
        if self.valid:
            sp = self.programa
            sp['m_llum'].write(self.m_llum)
            sp['origen'].write(glm.vec3(*(zona.origen_ecef - self.ancora)))
            sp['exaggeration'].value = zona.exaggeration
            nivells = [(self.vao('graella', zona.vbo, zona.vbo_h, zona.ibo), [pegat['finestra']] if pegat else [])]
            if pegat is not None:
                vao, _, vbo, _, vbo_h, _, ibo, _ = pegat['recursos']
                nivells.append((self.vao('pegat', vbo, vbo_h, ibo), []))
            for vao, forats in nivells:
                sp['n_forats'].value = len(forats)
                sp['forats'].write(np.array(forats + [(0, 0, 0, 0)] * (4 - len(forats)), 'f4').tobytes())
                vao.render()
        anterior.use()
        self.ctx.viewport = viewport

    def aplicar(self, sp, terreny):
        """Uniforms del mapa per a un terreny (terrain.frag). El mapa sempre es lliga a la seva unitat,
        encara que aquest terreny no el faci servir: un sampler sense textura fa avisar el controlador."""
        self.textura.use(UNITAT_TEXTURA)
        sp['tex_ombra'].value = UNITAT_TEXTURA
        rep = self.valid and terreny is self.app.zona
        sp['ombres_relleu'].value = rep
        sp['depuracio_ombra'].value = self.depuracio
        if rep:
            sp['m_llum'].write(self.m_llum)
            sp['cam_menys_ancora'].write(glm.vec3(*(self.app.camera.posicio - self.ancora)))
            sp['desplacament_normal'].value = self.desplacament_km()
            sp['biaix_profunditat'].value = BIAIX_KM / (2 * DIST_SOL_KM - 1.0)   # en unitats de profunditat

    def desplacament_km(self):
        return DESPLACAMENT_TEXELS * self.texel_km

    def destroy(self):
        self.oblidar_vaos()
        for obj in (self.fbo, self.textura, self.programa):
            obj.release()
