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
Detall segons la vista (basecode/detall.py): el punt de detall es el que es mira a l'exploracio (o el punt
d'observacio a les altres vistes); el relleu de 5 m, els edificis (amb altures mesurades) i el mapa de visibilitat de
detall d'aquell lloc es preparen i es carreguen en segon pla, sense aturar el dibuix.

Espai de navegacio: un cub fix que conte la Terra, la Lluna i el Sol (dades/navegacio.py); la camera
d'exploracio no en pot sortir i, a prop, se'n veuen les parets (basecode/paret_cub.py).
Ratoli: Tab (o un clic dret a l'escena) captura el ratoli per mirar sense premer cap boto; Tab o Esc
l'alliberen (basecode/control_ratoli.py). GraphicsEngine.run() es el bucle del basecode amb un sol canvi per
a l'Esc.

Tres coses independents:
  - el temps de simulacio (self.hora, TU): nomes canvia quan es reprodueix (tecla P);
  - el punt d'observacio (self.observador): nomes canvia quan se'n tria un (i no durant la reproduccio);
  - la camera: la d'exploracio (lliure), la d'observacio (als ulls, 1,7 m sobre el terra) o la guiada
    (allunyar-se del punt fins a l'espai per una trajectoria fixa, dades/trajectoria.py).

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
    camera_exploracio.py             camera lliure (del terreny a l'espai)
    camera_observador.py             camera als ulls de l'observador
    camera_guiada.py                 camera que s'allunya per una trajectoria (roda = progres)
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
from basecode.camera_exploracio import CameraExploracio, COEF_LOG, direccio_mirada, FOV as FOV_EXPLORACIO
from basecode.camera_observador import CameraObservador
from basecode.camera_guiada import CameraGuiada, VELOCITAT_TECLAT as VELOCITAT_GUIADA
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
from dades.observador import Observador, ALCADA_ULLS_KM, UBICACIONS
from dades.navegacio import cub_navegacio
from dades.obstacles import RADI_COS_M
from dades import atmosfera
from basecode.cel import Cel
from basecode.mosaic import Mosaic
from basecode.detall import Detall
from dades import eclipse_data, eclipsis, geodesia, noms, visibilitat
import ui

MODELS_DIR = os.path.join(_CODE_DIR, 'models')  # models .obj (cada un a la seva carpeta), com al repte 4
VELOCITAT_GIR = 60.0               # graus/s amb les fletxes
ALCADA_ATMOSFERA_KM = 60.0         # per sobre, el cel ja es negre (aproximacio visual)
INCLINACIO_EN_ARRIBAR = 2.0        # graus: en arribar a un punt amb doble clic, la mirada just sobre l'horitzo
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
        # edificis: es mostren en primera persona (observacio i caminant), per veure l'horitzo que deixen, i no
        # a la vista aeria (vol lliure i guiada), on taparien la fotografia; cada cas es pot canviar al panell
        self.mostrar_edificis = True
        self.edificis_aeris = False
        self._clau_edificis = None
        self.mostrar_noms = True      # noms de lloc importants sobre el mapa a les vistes aeries (ui.noms_al_mapa)
        self.noms_mapa = None         # [(nom, nivell, posicio ECEF)], es prepara el primer cop que es dibuixen
        self.usar_ortofoto = True     # color del terra de les zones de detall: fotografia aeria (si n'hi ha)
        # mapa de visibilitat de l'eclipsi (objectiu O3; basecode/terrain.py MAPES): es calcula la primera vegada
        # que es demana per a cada terreny i eclipsi (dades/visibilitat.py, en un fil) i es desa
        self.mapa_visibilitat = 0
        self.calculs_mapa, self.mapes_fallats = {}, set()   # cami del MDT -> visibilitat.Calcul del relleu
        self.calcul_detall = None     # mapa de detall (edificis i vegetacio mesurats) de la cel·la del punt de detall
        self.consulta_nom, self.nom_punt = None, None   # nom del lloc del punt d'observacio (dades/noms.py)

        # --- territori: la peninsula sencera posada sobre la Terra; el detall (zones de 5 m, edificis) el
        # carrega basecode/detall.py segons el que es mira i el punt d'observacio
        t0 = time.time()
        cami = {n: c for n, c, _ in TERRENYS}
        self.peninsula = Terrain(self, cami['Peninsula'], globus=True)
        self.peninsula.exaggeration = 1.0
        self.peninsula.limits_totalitat = False   # les capes tecniques, nomes des de l'apartat Avancat
        self.zona, self.nom_zona = None, None
        self.vista = 1                     # index a ui.VISTES: 0 exploracio, 1 observador, 2 guiada
        self.camera_exploracio = None
        self.detall = Detall(self)
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
        self.avis_caminar, self.avis_caminar_fins = '', -1.0   # resultat de passar a caminar (panell)

        # --- cameres: comencem mirant cap al Sol des del terra
        az, el = self.model.sol(self.hora)
        self.camera_observador = CameraObservador(self)
        self.camera_observador.mirar(az, el)
        self.camera_exploracio = CameraExploracio(self, self.ulls())
        self.posar_exploracio_sobre_el_punt()
        self.camera_guiada = CameraGuiada(self)
        self.camera = self.camera_observador

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
        for cam in (self.camera_exploracio, self.camera_observador, self.camera_guiada):
            cam.aspect_ratio = amplada / alcada
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
        """Observacio des del terra o caminant: la vista on els edificis fan l'horitzo."""
        return self.vista == 1 or (self.vista == 0 and self.camera_exploracio is not None and self.camera_exploracio.caminar)

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

    def altitud_caminable_km(self, lat, lon):
        """Com altitud_terra_km, pero nomes on hi ha relleu de terra dibuixat (el del terreny mes detallat que
        conte el punt): None al mar, fora d'Espanya o fora de tots els terrenys. Per caminar."""
        for t in reversed(self.terrenys()):
            if t.conte(lat, lon):
                if not t.es_terra(lat, lon):
                    return None
                return t.altitud_latlon(lat, lon) / 1000.0 * t.exaggeration
        return None

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
        si ara queda dins d'un edifici, els ulls van a l'exterior. En reproduir, la ubicacio no canvia."""
        o = self.observador
        if self.reproduint or o is None:
            return
        lat, lon = (o.lat_ref, o.lon_ref) if o.lat_ref is not None else (o.lat, o.lon)
        nom_punt = self.nom_punt
        self.triar_punt(lat, lon, o.nom)
        self.nom_punt = nom_punt

    def actualitzar_nom(self):
        """Recull el nom del lloc quan la consulta acaba."""
        c = self.consulta_nom
        if c is not None and c.fet:
            self.consulta_nom = None
            self.nom_punt = (c.clau, c.resultat if c.resultat is not None else dict(nucli=None, municipi=None,
                                                                                     errors=[c.error]))

    def anar_al_punt(self, lat, lon):
        """Doble clic a l'exploracio: l'observador va al punt i la vista passa directament a primera persona
        (observacio des del terra, amb els edificis), mirant cap on mirava la camera, en horitzontal: es veu
        l'horitzo d'aquell lloc. La camera d'exploracio no es mou (V hi torna). Caminant, el doble clic nomes
        tria el punt (ja s'es en primera persona). Durant la reproduccio, com triar_punt, no fa res."""
        ce = self.camera_exploracio
        if not self.triar_punt(lat, lon):
            return False
        if self.vista == 0 and not ce.caminar:
            self.camera_observador.mirar(ce.rumb, INCLINACIO_EN_ARRIBAR)
            self.canviar_vista(1)
        return True

    def actualitzar_mapa(self):
        """Mapa de visibilitat: si es mostra, cada terreny que es dibuixa ha de tenir el de l'eclipsi actiu (relleu) i
        la zona activa, el de detall de la cel·la del punt de detall si n'hi ha (edificis i vegetacio mesurats,
        basecode/detall.py). Es llegeixen o es calculen en fils (dades/visibilitat.Calcul), un de relleu i un de
        detall alhora; les textures es creen aqui (fil principal). Si no es mostra, s'alliberen (memoria de la GPU)."""
        clau = eclipsis.actiu()
        for cami, c in list(self.calculs_mapa.items()):
            if not c.fet:
                continue
            del self.calculs_mapa[cami]
            if c.cancelat:
                continue                                   # el terreny ja no es veia: es tornara a demanar si cal
            if c.error or c.resultat is None:
                self.mapes_fallats.add((c.cami, c.clau))   # no es torna a provar a cada fotograma
            if c.resultat is not None and c.clau == clau:
                for t in self.terrenys():
                    if t.cami == c.cami:
                        t.posar_visibilitat(c.resultat)
        # llegir un mapa ja calculat es pot fer sempre; calcular-ne un, d'un en un (cada calcul fa servir tota la CPU) i
        # despres del detall del punt (mes petit i mes util). Un calcul d'un terreny que ja no es veu acaba igualment
        # (queda desat) pero no impedeix llegir els altres
        visibles = {t.cami for t in self.terrenys()} if self.mapa_visibilitat else set()
        for c in self.calculs_mapa.values():
            if not c.fet and not c.nomes_llegir and c.cami not in visibles and not c.cancelat:
                c.cancel()                                 # deixa lloc al del terreny que es veu ara
        calculant = any(not c.fet and not c.nomes_llegir and not c.cancelat for c in self.calculs_mapa.values())
        for t in self.terrenys():
            if self.mapa_visibilitat == 0:
                if t.visibilitat is not None:
                    t.posar_visibilitat(None)
                continue
            if (t.visibilitat is not None and t.visibilitat['clau'] == clau) or t.cami in self.calculs_mapa \
                    or (t.cami, clau) in self.mapes_fallats:
                continue
            if visibilitat.vigent(t.cami, clau):
                self.calculs_mapa[t.cami] = visibilitat.Calcul(t.cami, clau, nomes_llegir=True)
            elif not calculant and not self.detall.detall_en_curs():
                self.calculs_mapa[t.cami] = visibilitat.Calcul(t.cami, clau, self.peninsula.cami)
                calculant = True
        # detall: nomes es fa servir si encara es el de la cel·la del punt i cap dins de la zona activa
        z = self.zona
        d = self.detall.detall_mapa if self.mapa_visibilitat else None
        cd = self.calcul_detall
        if cd is not None and not cd.fet and not cd.cancelat and (d is None or d[0] != cd.cami or cd.clau != clau):
            cd.cancel()   # ja no cal (mapa tret, un altre eclipsi o una altra cel·la): no ha d'aturar els altres
        if cd is not None and cd.fet:
            self.calcul_detall = None
            if cd.cancelat:
                cd = None
            elif cd.error or cd.resultat is None:
                self.mapes_fallats.add((cd.cami, cd.clau))
            elif cd.clau == clau and z is not None and d is not None and d[0] == cd.cami:
                z.posar_visibilitat_detall(cd.resultat, d[1])
                z.vis_detall.update(cami=d[0], descripcio=d[3])
        if z is None:
            return
        if d is None:
            if z.vis_detall is not None:
                z.posar_visibilitat_detall(None, None)
            return
        if z.vis_detall is not None and z.vis_detall.get('cami') == d[0] and z.vis_detall['clau'] == clau:
            return
        if self.calcul_detall is None and (d[0], clau) not in self.mapes_fallats:
            self.calcul_detall = visibilitat.Calcul(d[0], clau, lluny=[d[4] or z.cami, self.peninsula.cami],
                                                    cami_ulls=d[2])

    def text_mapa(self):
        """Estat del calcul del mapa (panell), o ''."""
        return self.detall.estat['mapa'] if self.mapa_visibilitat else ''

    def triar_ubicacio(self, lat, lon, nom):
        """Desplegable del panell: l'observador va a la ubicacio i la camera d'exploracio se situa a sobre,
        perque en passar a explorar (V) es parteixi del lloc triat. La mirada als ulls es conserva.
        (El doble clic explorant crida nomes triar_punt: la camera es queda on es.)
        A la vista guiada, la trajectoria es torna a calcular per al punt nou (amb el mateix progres i la
        mateixa mirada): la camera salta al lloc triat, que es el que s'ha demanat."""
        if self.triar_punt(lat, lon, nom):
            self.posar_exploracio_sobre_el_punt()
            if self.vista == 2:
                self.camera_guiada.ancorar()
            return True
        return False

    def ulls(self):
        """Posicio dels ulls de l'observador (ECEF, km): 1,7 m sobre els triangles que es dibuixen en
        aquell punt (es torna a calcular: l'exageracio de depuracio pot canviar el relleu)."""
        o = self.observador
        return geodesia.ecef(o.lat, o.lon, self.altitud_terra_km(o.lat, o.lon) + ALCADA_ULLS_KM)

    # ------------------------------------------------------------ vistes i temps

    def canviar_vista(self, vista):
        """Les cameres d'exploracio i d'observacio conserven la seva posicio i orientacio. En entrar a la
        guiada, la trajectoria es calcula amb l'hora actual i es mira la referencia del tram (enquadrament
        inicial); el progres es conserva."""
        if vista == 2 and self.vista != 2:
            self.camera_guiada.recentrar()
        self.camera_exploracio.aturar_moviment()   # el zoom o la inercia pendents no continuen en tornar-hi
        if vista != 0 and self.vista == 0:
            # el relleu i els edificis del punt d'observacio (son carregats: la zona de l'observador no es descarrega)
            o = self.observador
            abans = self.detall.cami_obs
            self.detall.situar(o.lat, o.lon, observador=True)
            if self.detall.cami_obs != abans:
                self.reubicar_observador()     # el relleu de 5 m hi ha arribat mentre s'explorava
        self.vista = vista
        self.camera = (self.camera_exploracio, self.camera_observador, self.camera_guiada)[vista]
        self.actualitzar_edificis()

    def mirar_el_sol(self):
        """Mirar l'eclipsi: orienta la camera activa cap al Sol (on es dibuixa) des d'on es, sense moure-la.
        Es una accio puntual: despres la mirada torna a ser de l'usuari."""
        cam = self.camera
        if self.vista == 2:
            cam.mirar_cap_a(self.sol_ecef)
            return
        if self.vista == 0:
            cam.aturar_moviment()
        lat, lon, _ = geodesia.geodesiques(cam.posicio)
        cam.orientar(*geodesia.azimut_elevacio(self.sol_ecef - cam.posicio, float(lat), float(lon)))

    def tornar_al_punt(self):
        """Vista d'observacio al punt triat (amb la mirada que tenia)."""
        self.canviar_vista(1)

    def posar_exploracio_sobre_el_punt(self):
        """Camera d'exploracio a 6 km del punt d'observacio, d'esquena al Sol i mirant cap al punt. Si s'esta
        caminant, en canvi, la camera es posa als ulls del punt (mateixa mirada que l'observador)."""
        if self.camera_exploracio.caminar:
            self.caminar_des_del_punt()
            return
        o = self.observador
        az, _ = self.model.sol(self.hora)
        darrere = direccio_mirada(o.lat, o.lon, az + 180.0, 0.0)
        _, _, amunt = geodesia.base_local(o.lat, o.lon)
        self.camera_exploracio.posicio = self.ulls() + 6.0 * darrere + 3.0 * amunt
        self.camera_exploracio.orientar(az, -25.0)

    def veure_ombra_des_de_lespai(self):
        """Enquadrament (una sola vegada, sense seguiment): la camera d'exploracio a 12.000 km, entre la
        vertical del lloc i el Sol (veu la cara de dia), mirant el punt on l'ombra de la Lluna es mes fosca
        a l'hora actual. El temps no canvia. Si es caminava, passa a vol lliure (es un boto explicit)."""
        self.camera_exploracio.caminar = False
        lat_o, lon_o, _ = punt_ombra(self.hora, self.ef)
        cap_al_sol = self.sol_ecef / np.linalg.norm(self.sol_ecef)
        _, _, amunt = geodesia.base_local(lat_o, lon_o)
        punt = geodesia.ecef(lat_o, lon_o, 0.0)
        cam = self.camera_exploracio
        direccio = amunt + cap_al_sol
        cam.posicio = punt + 12000.0 * direccio / np.linalg.norm(direccio)
        lat, lon, _ = cam.geodesiques()
        az, el = geodesia.azimut_elevacio(punt - cam.posicio, lat, lon)
        cam.orientar(az, el)
        self.canviar_vista(0)

    def passar_a_caminar(self):
        """Selector del panell: caminar des d'on es la camera d'exploracio (baixant en vertical al terra) o, si
        no es pot, deixar-ho dit al panell (cap teletransport)."""
        fet, text = self.camera_exploracio.entrar_caminar()
        self.avis_caminar, self.avis_caminar_fins = text, glfw.get_time() + (4.0 if fet else 1e9)
        return fet

    def caminar_des_del_punt(self):
        """Accio explicita: la camera d'exploracio als ulls de l'observador, amb la seva mirada, caminant."""
        ce, co = self.camera_exploracio, self.camera_observador
        ce.posicio = self.ulls()
        ce.orientar(co.rumb, co.inclinacio)
        ce.caminar = True
        self.avis_caminar_fins = -1.0
        self.canviar_vista(0)

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
        if self.vista == 2:
            self.camera_guiada.ancorar()

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
        """P reproduir/pausar, V explorar / observar, G allunyar-se (guiat), Tab capturar o alliberar el
        ratoli, fletxes girar la mirada (velocitat x dt). A l'exploracio en vol lliure, W A S D desplacen la
        camera i E / Q la pugen o baixen (Ctrl: mes rapid); caminant, W A S D caminen sobre el relleu (Shift:
        correr) i E / Q no fan res; a la guiada, W / S s'acosten o s'allunyen per la trajectoria."""
        if imgui.get_io().want_capture_keyboard:
            return
        tecla = lambda k: glfw.get_key(self.window, k) == glfw.PRESS
        if imgui.is_key_pressed(imgui.Key.KEY_V, False):
            self.canviar_vista(0 if self.vista == 1 else 1)
        if imgui.is_key_pressed(imgui.Key.KEY_G, False):
            self.canviar_vista(1 if self.vista == 2 else 2)
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
        if self.vista == 0:
            endavant = tecla(glfw.KEY_W) - tecla(glfw.KEY_S)
            costat = tecla(glfw.KEY_D) - tecla(glfw.KEY_A)
            if cam.caminar:     # E / Q no separen la camera del terra
                if endavant or costat:
                    correr = tecla(glfw.KEY_LEFT_SHIFT) or tecla(glfw.KEY_RIGHT_SHIFT)
                    cam.caminar_pas(endavant, costat, dt, correr)
                return
            vertical = tecla(glfw.KEY_E) - tecla(glfw.KEY_Q)
            if endavant or costat or vertical:
                rapid = 5.0 if (tecla(glfw.KEY_LEFT_CONTROL) or tecla(glfw.KEY_RIGHT_CONTROL)) else 1.0
                cam.moure(endavant, costat, vertical, dt * rapid)
        elif self.vista == 2:
            endavant = tecla(glfw.KEY_W) - tecla(glfw.KEY_S)
            if endavant:
                rapid = 3.0 if (tecla(glfw.KEY_LEFT_CONTROL) or tecla(glfw.KEY_RIGHT_CONTROL)) else 1.0
                cam.moure_progres(-endavant * VELOCITAT_GUIADA * dt * rapid)

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
        return (self.reproduint or bool(self.detall.feines) or bool(self.calculs_mapa)
                or self.calcul_detall is not None or self.consulta_nom is not None
                or (self.mosaic.actiu and self.mosaic.descarregador.pendents() > 0))

    def signatura(self):
        """El que determina la imatge i pot canviar d'un fotograma al seguent: vista, camera i hora."""
        cam = self.camera
        return (self.vista, cam.posicio.tobytes(), bytes(cam.m_view), cam.fov, self.hora, self.mapa_visibilitat)

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
            imgui.begin('Eclipsi')
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
        self.detall.actualitzar()   # detall segons la vista: es prepara i es carrega en segon pla
        self.actualitzar_mapa()     # mapa de visibilitat (es calcula o es llegeix en segon pla)
        self.actualitzar_nom()
        self.actualitzar_edificis()
        self.avancar_temps(dt)
        self.actualitzar_astres()
        # ratoli: amb el ratoli capturat, el moviment gira la mirada (un cop per fotograma, sense dt); la roda
        # va a la camera activa. L'exploracio processa el ratoli despres de dibuixar (picking)
        dx, dy, roda = self.ratoli.fotograma()
        if dx or dy:
            self.camera.girar_ratoli(dx, dy)
        if self.vista != 0:
            self.camera.processar_ratoli(roda, self.ratoli.capturat)
        else:
            # si mai la camera queda dins d'un edifici (p. ex. s'han tornat a mostrar els edificis), surt al
            # punt exterior mes proper; caminant, els ulls sobre el relleu encara que el relleu canvii
            fora = self.camera.sortir_dels_edificis()
            if fora:
                self.avis_caminar, self.avis_caminar_fins = f'Fora de l\'edifici: {fora:.0f} m', glfw.get_time() + 4.0
            if self.camera.caminar:
                self.camera.seguir_terra()
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
        self.cel.render()    # nomes on no hi ha res dibuixat (no tapa el Sol ni la Lluna) i sense profunditat
        self.terra.render_atmosfera()   # des de l'espai, la resplendor blava al voltant del disc
        self.paret.render()  # translucides: despres dels objectes opacs
        self.halo.render()

        if self.vista == 0:
            # el ratoli es processa just despres de dibuixar: el depth buffer ja es ple.
            # doble clic: si no s'esta reproduint, l'observador va al punt clicat i es passa a mirar des d'alli
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
