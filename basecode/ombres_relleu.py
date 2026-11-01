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
  - Dos mapes (F36): el gran (MIDA_KM, texels d'~8 m) per al relleu, i un de fi (MIDA_FI_KM, 3 x 3 km al voltant
    de l'ancora, texels de 0,7-0,9 m) quan hi ha edificis: els edificis hi fan ombra (tots, no nomes els de mes de
    ~12 m com amb el gran) i en reben (edifici.frag). El fi s'ajusta a les altures del quadrat (alcades_fi): amb el
    Sol baix, una caixa mes baixa fa els texels mes petits. Al mapa fi el marge contra l'acne creix amb la
    inclinacio de la llum sobre la superficie (ombres.glsl): amb el Sol rasant, els primers metres de l'ombra arran
    de l'obstacle es perden (alla el terra rep molt poca llum directa: un 5 % amb el Sol a 3 graus).
  - El mapa nomes es torna a calcular quan canvia l'hora (arrodonida al segon), el punt o el relleu.
"""
import math

import glm
import moderngl as mgl
import numpy as np

from .camera_exploracio import direccio_mirada
from .programes import carregar_programa
from dades import geodesia

RESOLUCIO = 4096       # texels per costat del mapa d'ombres gran
MIDA_KM = 16.0         # mig costat del quadrat de terreny cobert, al voltant de l'ancora (punt de detall)
# Mapa fi (F36, peticio de l'equip): els edificis fan ombra i en reben. 3 x 3 km amb texels de menys d'1 m.
RESOLUCIO_FI = 4096
MIDA_FI_KM = 1.5       # mig costat
ALCADA_EDIFICIS_KM = 0.25   # per sobre del terreny mes alt del quadrat fi: els edificis hi han de cabre
BIAIX_FI_KM = 0.0003   # marge fix del mapa fi (30 cm); el shader hi suma texel x tangent (ombres.glsl)
UNITAT_FI = 12
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
        self.textura_fi = self.ctx.depth_texture((RESOLUCIO_FI, RESOLUCIO_FI))
        self.textura_fi.repeat_x = self.textura_fi.repeat_y = False
        self.textura_fi.compare_func = '<='
        self.textura_fi.filter = (mgl.LINEAR, mgl.LINEAR)
        self.fbo_fi = self.ctx.framebuffer(depth_attachment=self.textura_fi)
        self.valid_fi, self.m_llum_fi, self.texel_fi_km = False, glm.mat4(), 2 * MIDA_FI_KM / RESOLUCIO_FI
        self.programa = carregar_programa(self.ctx, 'ombra')
        self.actiu = True             # interruptor de l'apartat Avancat
        self.depuracio = False        # scripts: el terreny es pinta amb el factor d'ombra (1 llum, 0 ombra)
        self.valid = False            # hi ha un mapa per a la zona actual
        self.m_llum = glm.mat4()
        self.ancora = np.zeros(3)
        self.clau = None              # (hora, punt, exageracio) del mapa calculat
        self.zona = self.pegat = self.edificis = None   # zona, pegat i edificis dels VAO (referencies)
        self.vaos = {}                # VAO de la passada des del Sol per a cada nivell de la zona
        self.texel_km = 2 * MIDA_KM / RESOLUCIO
        self.fbo.clear(depth=1.0)
        self.fbo_fi.clear(depth=1.0)

    def vao(self, clau, vbo, vbo_h, ibo):
        """VAO amb el programa de la passada des del Sol i els buffers del terreny (els mateixos que es
        dibuixen: no hi ha cap copia de la geometria)."""
        if clau not in self.vaos:
            self.vaos[clau] = self.ctx.vertex_array(
                self.programa, [(vbo, '2f 3f 3f 20x', 'in_uv', 'in_offset', 'in_amunt'), (vbo_h, '1f', 'in_h')],
                index_buffer=ibo)
        return self.vaos[clau]

    def oblidar_vaos(self):
        for v in self.vaos.values():
            v.release()
        self.vaos = {}

    def matriu_llum(self, lat, lon, zona, mida_km=MIDA_KM, alcades=None, resolucio=RESOLUCIO):
        """(m_llum, elevacio del Sol, texel en km): de posicio relativa a l'ancora (km) a coordenades de clip de la
        llum, per a un quadrat de mig costat mida_km entre les altures alcades (km; per defecte, de -50 m al mes
        alt de la zona). El texel es el costat mes llarg de la caixa vista des del Sol entre la resolucio."""
        app = self.app
        # Sol aparent (amb refraccio) vist des de l'ancora: pot ser lluny del punt d'observacio (explorant)
        az, el = geodesia.azimut_elevacio(app.sol_ecef - geodesia.ecef(lat, lon, 0.0), lat, lon)
        el += geodesia.refraccio_graus(el)
        cap_al_sol = direccio_mirada(lat, lon, az, el)
        est, nord, amunt = geodesia.base_local(lat, lon)
        vista = glm.lookAt(glm.vec3(*(cap_al_sol * DIST_SOL_KM)), glm.vec3(0.0), glm.vec3(*amunt))
        # cantonades del quadrat de terreny (de -50 m, per la curvatura, fins a l'altitud maxima de la zona)
        h0, h1 = alcades if alcades is not None else (-0.05, zona.max_height / 1000.0 * zona.exaggeration + 0.05)
        xs, ys = [], []
        for a in (-mida_km, mida_km):
            for b in (-mida_km, mida_km):
                for h in (h0, h1):
                    q = vista * glm.vec4(*(a * est + b * nord + h * amunt), 1.0)
                    xs.append(q.x)
                    ys.append(q.y)
        proj = glm.ortho(min(xs), max(xs), min(ys), max(ys), 1.0, 2 * DIST_SOL_KM)
        return proj * vista, el, max((max(xs) - min(xs)), (max(ys) - min(ys))) / resolucio

    def alcades_fi(self, lat, lon, zona):
        """(minima, maxima) en km del quadrat fi: el relleu en una graella de 9 x 9 punts (el que es dibuixa) i, a
        sobre, ALCADA_EDIFICIS_KM per als edificis. Amb el Sol baix, una caixa ajustada fa els texels mes petits."""
        hs = []
        dlat = MIDA_FI_KM / 111.32
        dlon = MIDA_FI_KM / (111.32 * math.cos(math.radians(lat)))
        for f in np.linspace(-1, 1, 9):
            for g in np.linspace(-1, 1, 9):
                h = zona.altitud_latlon(lat + f * dlat, lon + g * dlon)
                if h is not None:
                    hs.append(h / 1000.0 * zona.exaggeration)
        if not hs:
            return -0.05, ALCADA_EDIFICIS_KM
        return min(hs) - 0.05, max(hs) + ALCADA_EDIFICIS_KM

    def actualitzar(self):
        """Passada des del Sol, si ha canviat alguna cosa. Es crida abans de dibuixar el fotograma."""
        app, zona = self.app, self.app.zona
        # ancora: el centre del pegat dens de la zona (el punt de detall: el que es mira o el punt d'observacio)
        lat, lon = zona.pegat['centre'] if zona is not None and zona.pegat is not None else \
            (app.observador.lat, app.observador.lon)
        if not self.actiu or zona is None or not zona.conte(lat, lon):
            # sense mapa: cal oblidar la clau perque, en tornar-les a encendre (en pausa, la mateixa
            # hora), el mapa es torni a calcular i valid torni a ser True
            self.valid, self.valid_fi, self.clau = False, False, None
            return
        pegat, edificis = zona.pegat, app.edificis
        if zona is not self.zona or pegat is not self.pegat or edificis is not self.edificis:
            self.oblidar_vaos()          # zona, pegat o edificis nous: els buffers han canviat
            self.zona, self.pegat, self.edificis, self.clau = zona, pegat, edificis, None
        amb_edificis = edificis is not None and edificis.visible
        # l'hora, arrodonida al segon (de temps de l'eclipsi): en 1 s el Sol es mou 0,004 graus i l'ombra d'un edifici
        # de 20 m, menys d'1 m; a velocitat x1 el mapa es refa un cop per segon i no a cada fotograma
        clau = (round(app.hora * 3600.0), lat, lon, zona.exaggeration, amb_edificis)
        if clau == self.clau:
            return
        self.clau = clau
        self.ancora = geodesia.ecef(lat, lon, 0.0)
        self.m_llum, el, self.texel_km = self.matriu_llum(lat, lon, zona)
        self.valid = el > -1.0            # amb el Sol sota l'horitzo no hi ha ombres del relleu
        self.m_llum_fi, _, self.texel_fi_km = self.matriu_llum(lat, lon, zona, MIDA_FI_KM,
                                                               self.alcades_fi(lat, lon, zona), RESOLUCIO_FI)
        self.valid_fi = self.valid and amb_edificis and edificis.n_triangles > 0   # nomes on hi ha edificis

        anterior, viewport = self.ctx.fbo, self.ctx.viewport
        for fbo, m_llum, valid in ((self.fbo, self.m_llum, self.valid), (self.fbo_fi, self.m_llum_fi, self.valid_fi)):
            fbo.use()
            fbo.clear(depth=1.0)
            if valid:
                self.dibuixar(m_llum, zona, pegat, edificis if amb_edificis else None)
        anterior.use()
        self.ctx.viewport = viewport

    def dibuixar(self, m_llum, zona, pegat, edificis):
        """La passada des del Sol en el framebuffer actiu: el relleu de la zona (graella i pegat) i els edificis."""
        sp = self.programa
        sp['m_llum'].write(m_llum)
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
        if edificis is not None and edificis.vbo is not None:
            # els edificis tambe fan ombra: la seva posicio va a in_offset (relativa al seu origen); els
            # atributs que no es lliguen (in_amunt, in_h, in_uv) valen 0
            if 'edificis' not in self.vaos:
                self.vaos['edificis'] = self.ctx.vertex_array(self.programa, [(edificis.vbo, '3f 16x', 'in_offset')])
            sp['origen'].write(glm.vec3(*(edificis.origen_ecef - self.ancora)))
            sp['n_forats'].value = 0
            self.vaos['edificis'].render()

    def aplicar(self, sp, terreny):
        """Uniforms del mapa per a un terreny (terrain.frag). El mapa sempre es lliga a la seva unitat,
        encara que aquest terreny no el faci servir: un sampler sense textura fa avisar el controlador."""
        rep = self.valid and terreny is self.app.zona
        sp['depuracio_ombra'].value = self.depuracio
        self.uniforms(sp, rep)

    def aplicar_edificis(self, sp, edificis):
        """El mateix per als edificis (edifici.frag): reben les ombres si son els de la zona del mapa."""
        self.uniforms(sp, self.valid and edificis is self.edificis)

    def uniforms(self, sp, rep):
        """Uniforms d'ombres.glsl. Els dos mapes es lliguen sempre a la seva unitat (un sampler sense textura fa
        avisar el controlador)."""
        self.textura.use(UNITAT_TEXTURA)
        sp['tex_ombra'].value = UNITAT_TEXTURA
        self.textura_fi.use(UNITAT_FI)
        sp['tex_ombra_fi'].value = UNITAT_FI
        sp['ombres_relleu'].value = rep
        sp['ombres_fi'].value = rep and self.valid_fi
        if rep:
            escala = 1.0 / (2 * DIST_SOL_KM - 1.0)     # de km a unitats de profunditat (ortografica de 1 a 2 x DIST)
            sp['m_llum'].write(self.m_llum)
            sp['m_llum_fi'].write(self.m_llum_fi)
            sp['cam_menys_ancora'].write(glm.vec3(*(self.app.camera.posicio - self.ancora)))
            sp['desplacament_normal'].value = self.desplacament_km()
            sp['biaix_profunditat'].value = BIAIX_KM * escala
            sp['texel_fi'].value = self.texel_fi_km
            sp['biaix_fi'].value = BIAIX_FI_KM
            sp['km_a_profunditat'].value = escala

    def desplacament_km(self):
        return DESPLACAMENT_TEXELS * self.texel_km

    def destroy(self):
        self.oblidar_vaos()
        for obj in (self.fbo, self.textura, self.fbo_fi, self.textura_fi, self.programa):
            obj.release()
