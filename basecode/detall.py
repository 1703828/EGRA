"""
Detall segons la vista: quin relleu de 5 m, quins edificis i quin mapa de visibilitat de detall calen on es mira, i
la seva preparacio i carrega en segon pla, sense aturar el dibuix.

Punt de detall (punt_referencia): a la vista d'exploracio, el punt del terra que es mira (el raig del centre de la
pantalla) o, a prop del terra o caminant, el de sota la camera; a les altres vistes, el punt d'observacio. Per sobre
d'ALCADA_DETALL_KM no es demana res (de lluny, el relleu de 200 m de la peninsula n'hi ha prou).

Per a aquest punt, a cada fotograma (com a molt cada REVISIO_S):
  1. Zona: la zona de detall que el conte (les fetes a ma, data_io.ZONES_DETALL, o un lloc preparat,
     dades/llocs.py). Si s'hi volen edificis i la zona no en te en aquell punt, la que en tingui. Si cap no hi
     serveix i el punt es a terra a Espanya, es prepara el lloc de la quadricula (relleu i, si es volen, edificis).
     La zona activa es la que es dibuixa i la que fan servir les ombres, els edificis, els obstacles i el mapa.
  2. Carrega: llegir les dades (CPU) es fa en un fil (Terrain.preparar, Edificis.preparar) i el fil principal nomes
     crea els objectes OpenGL. Es guarden carregades fins a MAX_CARREGADES zones (la del punt d'observacio, fixada, i
     les ultimes de la vista): tornar-hi es instantani.
  3. Pegats: el pegat dens de la zona (5 m, ~2,5 km) i el de la peninsula (200 m, ~100 km) es tornen a centrar,
     tambe en un fil, quan el punt se n'allunya.
  4. Altures mesurades dels edificis (dades/alcaries.py): quan els edificis es veuen i encara son estimats.
  5. Mapa de visibilitat de detall (dades/alcaries.preparar_superficie i dades/visibilitat): quan el mapa es mostra,
     per a la cel·la de la quadricula del punt, amb els edificis i la vegetacio mesurats.
Cada feina guarda que s'ha demanat (clau). Quan acaba, el resultat queda al disc; nomes es fa servir si encara es el
que cal per al punt actual (una descarrega antiga no canvia el que es veu despres de moure's).

Estat per al panell (estat): una linia per al terreny, la fotografia, els edificis i el mapa.
"""
import math
import os
import time

import numpy as np
import rasterio
from pyproj import Transformer

from dades import alcaries, geodesia, llocs, teselles
from dades.data_io import ZONES_DETALL
from dades.edificis import ZONA_DE_LA_UBICACIO, RADI_ZONA_M, fitxer_zona
from dades.alcaries import centre_cel
from dades.feines import Feina, FeinaProces
from dades.observador import UBICACIONS_PROVES
from .edificis import Edificis
from .terrain import Terrain, MIDA_PEGAT

ALCADA_DETALL_KM = 15.0      # per sobre, no es prepara ni es canvia el detall
ALCADA_SOTA_KM = 0.3         # per sota (o caminant), el punt de detall es el de sota la camera
REVISIO_S = 0.15
ESPERA_PREPARAR_S = 1.0      # el punt ha de ser a la mateixa cel·la aquesta estona abans de baixar-hi res (en volar per
                             # sobre d'un lloc no es prepara)
MAX_CARREGADES = 3
MARGE_ZONA_M = 1000.0        # el punt ha de ser a aixo de la vora del relleu de la zona
HISTERESI_M = 300.0          # la zona activa es conserva fins que el punt en surt aixo mes enlla
LLINDAR_PEGAT = 0.25         # el pegat es torna a centrar quan el punt se n'allunya aquesta fraccio del costat
LLINDAR_PEGAT_PENINSULA_KM = 25.0
RES_SUPERFICIE_M = {'icgc': 2.0, 'ign': 2.5}   # mapa de detall: l'ICGC (1 m) es redueix a 2 m (objecte mes alt)
_A_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True)


class Detall:
    def __init__(self, app):
        self.app = app
        self.max_textura = app.ctx.info['GL_MAX_TEXTURE_SIZE']
        self.carregades = {}      # cami del MDT -> dict(terreny, edificis, clau, nom, us)
        self.cami_obs = None      # zona del punt d'observacio (no es descarrega)
        self.feines = {}          # tipus -> Feina
        self.fallades = {}        # (tipus, clau) -> missatge: no es torna a provar en aquesta sessio
        self.punt = None          # (lat, lon) de referencia de l'ultima revisio
        self.ultima = -1e9
        self._limits = {}
        self.estat = dict(terreny='', foto='', edificis='', mapa='')
        self.detall_mapa = None   # (cami, limits, ulls, descripcio, mdt) del mapa de detall que toca, si n'hi ha
        self.preparar = True      # False: nomes es fa servir el que ja hi ha al disc (proves sense xarxa)
        self.cel_les_mesurades = {}   # zona -> cel·les on ja s'han mesurat les altures dels edificis
        self.desitjat = (None, 0.0)   # (cel·la del punt, des de quan hi es): per a ESPERA_PREPARAR_S
        self._situant = False

    # ------------------------------------------------------------ zones disponibles

    def limits(self, cami):
        if cami not in self._limits:
            with rasterio.open(cami) as f:
                self._limits[cami] = f.bounds
        return self._limits[cami]

    def zones(self):
        """Zones de detall al disc: dicts (nom, cami, clau, estatica)."""
        z = [dict(nom=nom, cami=cami, clau=clau, estatica=True) for nom, cami, clau in ZONES_DETALL
             if os.path.exists(cami)]
        z += [dict(nom=llocs.nom(c), cami=llocs.cami_mdt(c), clau=c, estatica=False) for c in llocs.existents()]
        return z

    @staticmethod
    def te_edificis(clau, x, y, extra=0.0):
        """Si la zona te edificis preparats que cobreixen el punt (x, y, EPSG:25830)."""
        if not os.path.exists(fitxer_zona(clau)):
            return False
        if clau.startswith('lloc_'):
            cx, cy = llocs.centre(clau)
            marge = 0.0 if llocs.de_quadricula(clau) else llocs.MARGE_M
            return max(abs(x - cx), abs(y - cy)) < llocs.meitat_edificis(clau) - marge + extra
        # els punts al voltant dels quals es van baixar els edificis de les zones fetes a ma (tots sis, encara que el
        # panell ara en mostri quatre: descriuen les dades que hi ha)
        punts = [_A_UTM.transform(lon, lat) for nom, lat, lon in UBICACIONS_PROVES
                 if ZONA_DE_LA_UBICACIO.get(nom) == clau]
        return any(math.hypot(x - px, y - py) < RADI_ZONA_M - llocs.MARGE_M + extra for px, py in punts)

    def conte(self, z, x, y, marge):
        b = self.limits(z['cami'])
        return b.left + marge < x < b.right - marge and b.bottom + marge < y < b.top - marge

    def triar_zona(self, x, y, edificis, actual=None):
        """La zona per al punt: (zona o None, falta) on falta diu si caldria preparar-ne una (cap zona conte el punt
        o, si es volen edificis, cap no en te alli). La zona actual es conserva amb una mica d'histeresi."""
        candidates = []
        for z in self.zones():
            es_actual = actual is not None and z['cami'] == actual
            extra = HISTERESI_M if es_actual else 0.0
            if not self.conte(z, x, y, MARGE_ZONA_M - extra):
                continue
            amb = self.te_edificis(z['clau'], x, y, extra)
            # preferencia: amb edificis (si es volen), l'actual, les fetes a ma (mes grans), la mes recent
            candidates.append(((amb if edificis else True), es_actual, z['estatica'], z))
        if not candidates:
            return None, True
        candidates.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
        millor = candidates[0]
        return millor[3], (edificis and not millor[0])

    # ------------------------------------------------------------ punt de detall

    def punt_vista(self):
        """El punt (lat, lon) que es mira a l'exploracio, o None si la camera es massa amunt."""
        cam = self.app.camera_exploracio
        alcada = cam.alcada_sobre_terra()
        if alcada > ALCADA_DETALL_KM:
            return None
        lat, lon, _ = cam.geodesiques()
        if cam.caminar or alcada < ALCADA_SOTA_KM:
            return float(lat), float(lon)
        # raig del centre de la pantalla contra l'el·lipsoide aixecat fins a l'altura del terra de sota la camera
        h = self.app.altitud_terra_km(float(lat), float(lon))
        o, d = cam.posicio, cam.davant()
        a_, b_ = geodesia.A_KM + h, geodesia.B_KM + h
        k = np.array([1.0, 1.0, a_ / b_])
        oo, dd = o * k, d * k
        aa, bb, cc = dd @ dd, 2 * (oo @ dd), oo @ oo - a_ ** 2
        disc = bb * bb - 4 * aa * cc
        if disc > 0:
            t = (-bb - math.sqrt(disc)) / (2 * aa)
            if 0 < t < 6.0 * alcada + 1.0:
                la, lo, _ = geodesia.geodesiques(o + t * d)
                return float(la), float(lo)
        return float(lat), float(lon)

    def punt_referencia(self):
        app = self.app
        if app.vista == 0:
            return self.punt_vista()
        return app.observador.lat, app.observador.lon

    def edificis_volguts(self):
        """Si a la vista actual es mostren els edificis (opcions del panell)."""
        app = self.app
        return app.mostrar_edificis if app.primera_persona() else app.edificis_aeris

    # ------------------------------------------------------------ carregar i activar

    @staticmethod
    def _carregar_cpu(cami, clau, nom, max_textura, mesurades, avis):
        avis(f'Llegint el relleu de {nom}...')
        t = Terrain.preparar(cami, max_textura)
        # (l'ortofoto feta a ma de Vic, F18, ja no es fa servir: el color del terra es el de les teselles del PNOA, com
        # a tot arreu; peticio de l'equip de l'1/11)
        e = None
        if os.path.exists(fitxer_zona(clau)):
            avis(f'Llegint els edificis de {nom}...')
            # nomes llegir: si la malla no hi es, es fara en un proces (recollir) i els edificis arribaran despres
            e = Edificis.preparar(clau, cami, mesurades=mesurades, nomes_llegir=True)
        from dades.edificis import preparar_malla
        falta = os.path.exists(fitxer_zona(clau)) and (
            e is None or (mesurades and preparar_malla(clau, cami, mesurades=True, nomes_llegir=True) is None))
        return dict(terreny=t, edificis=e, falta_malla=falta)

    def _crear(self, cami, clau, nom, cpu):
        """Objectes OpenGL de la zona llegida (cpu, de _carregar_cpu). Si li falta la malla dels edificis, es fa en un
        proces i els edificis arriben despres (carregar_edificis)."""
        app = self.app
        if cpu.get('falta_malla') and self.lliure('malla', clau):
            self.feines['malla'] = FeinaProces(clau, _preparar_malla, clau, cami, descripcio='malla dels edificis')
        t = Terrain(app, cami, globus=True, preparat=cpu['terreny'])
        t.pare, t.dibuixar_mar = app.peninsula, True
        for atribut in ('exaggeration', 'overlay', 'opacitat', 'limits_totalitat', 'wireframe'):
            setattr(t, atribut, getattr(app.peninsula, atribut))
        e = None
        if cpu['edificis'] is not None:
            e = Edificis(app, clau, cami, preparat=cpu['edificis'])
            if not e.n_triangles:
                e.destroy()
                e = None
        self.carregades[cami] = dict(terreny=t, edificis=e, clau=clau, nom=nom, us=time.time())
        self.alliberar_sobrants()

    def alliberar_sobrants(self):
        actiu = self.app.zona.cami if self.app.zona is not None else None
        while len(self.carregades) > MAX_CARREGADES:
            lliures = [c for c in self.carregades if c not in (actiu, self.cami_obs)]
            if not lliures:
                break
            c = min(lliures, key=lambda k: self.carregades[k]['us'])
            z = self.carregades.pop(c)
            z['terreny'].destroy()
            if z['edificis'] is not None:
                z['edificis'].destroy()

    def activar(self, cami):
        """La zona carregada (o None: nomes la peninsula) passa a ser la que es dibuixa."""
        app = self.app
        if app.zona is not None and (cami is None or app.zona.cami != cami):
            app.zona.treure_pegat()           # el pegat es torna a fer al voltant del punt nou
            if app.zona.visibilitat is not None:
                app.zona.posar_visibilitat(None)
            if app.zona.vis_detall is not None:
                app.zona.posar_visibilitat_detall(None, None)
        if cami is None:
            app.zona, app.edificis, app.nom_zona, app.peninsula.fills = None, None, None, []
            return
        z = self.carregades[cami]
        z['us'] = time.time()
        # la configuracio actual (exageracio, capes del CNIG, filferros...) es la de la peninsula
        for atribut in ('exaggeration', 'overlay', 'opacitat', 'limits_totalitat', 'wireframe'):
            setattr(z['terreny'], atribut, getattr(app.peninsula, atribut))
        app.zona, app.edificis, app.nom_zona = z['terreny'], z['edificis'], z['nom']
        llocs.tocar(z['clau'])
        app.peninsula.fills = [app.zona]
        app.zona.actualitzar_transicio()
        app._clau_edificis = None
        app.actualitzar_edificis()
        if app.camera is not None:
            app.camera.update()      # la zona nova tambe ha de rebre les matrius de la camera
        # una zona que arriba despres d'haver triat el punt d'observacio (preparada en segon pla) i el conte: el punt es
        # torna a triar, perque l'altitud dels ulls, el model i els edificis siguin els d'aquest relleu
        o = getattr(app, 'observador', None)
        if not self._situant and o is not None and cami != self.cami_obs and app.zona.conte(o.lat, o.lon) \
                and app.vista != 0:
            app.reubicar_observador()

    def situar(self, lat, lon, observador=False):
        """Ara mateix (sense fil): la zona del punt carregada i activa, i els pegats centrats al punt. El fan servir
        triar_punt (el punt d'observacio ha de quedar sobre el relleu que es dibuixara) i els scripts."""
        app = self.app
        self._situant = True
        try:
            self._situar(lat, lon, observador)
        finally:
            self._situant = False

    def _situar(self, lat, lon, observador):
        app = self.app
        x, y = _A_UTM.transform(lon, lat)
        actual = app.zona.cami if app.zona is not None else None
        z, _ = self.triar_zona(x, y, self.edificis_volguts() or observador, actual)
        if z is not None and z['cami'] not in self.carregades:
            self._crear(z['cami'], z['clau'], z['nom'],
                        self._carregar_cpu(z['cami'], z['clau'], z['nom'], self.max_textura,
                                           self.mesurades_disponibles(z['clau']), lambda t: None))
        self.activar(z['cami'] if z is not None else None)
        if observador:
            self.cami_obs = z['cami'] if z is not None else None
        # pegats: nomes si el punt se n'ha allunyat (el mateix criteri que en segon pla): tornar al punt d'observacio
        # amb la seva zona carregada no costa res
        pen, zona = app.peninsula, app.zona
        if pen.pegat is None or _distancia_km(pen.pegat['centre'], (lat, lon)) > LLINDAR_PEGAT_PENINSULA_KM \
                or not pen.conte(*pen.pegat['centre']):
            pen.posar_pegat(lat, lon)
            self.feines.pop('pegat_pen', None)
            if zona is not None:
                zona.actualitzar_transicio()
                zona.reajustar_pegat()
        if zona is not None and (zona.pegat is None or _distancia_km(zona.pegat['centre'], (lat, lon))
                                 > LLINDAR_PEGAT * MIDA_PEGAT * zona.mida.x / zona.alt.shape[1]):
            zona.posar_pegat(lat, lon)
            self.feines.pop('pegat', None)
        self.punt = (lat, lon)

    @staticmethod
    def mesurades_disponibles(clau):
        return os.path.exists(alcaries.cami_alcades(clau))

    # ------------------------------------------------------------ cada fotograma

    def actualitzar(self):
        app = self.app
        self.recollir()
        self.preparar_cobertes()
        ara = time.time()
        if ara - self.ultima < REVISIO_S:
            return
        self.ultima = ara
        p = self.punt_referencia()
        self.actualitzar_estat(p)
        if p is None:
            return
        self.punt = p
        lat, lon = p
        x, y = _A_UTM.transform(lon, lat)
        volguts = self.edificis_volguts()
        actual = app.zona.cami if app.zona is not None else None
        z, falta = self.triar_zona(x, y, volguts, actual)
        bloquejat = app.reproduint and app.vista == 1   # el relleu sota l'observador no canvia en reproduir
        cel = alcaries.centre_cel(x, y)
        if self.desitjat[0] != cel:
            self.desitjat = (cel, ara)
        estable = ara - self.desitjat[1] >= ESPERA_PREPARAR_S or app.vista != 0
        if falta and not bloquejat and estable:
            self.preparar_lloc(lat, lon, x, y, volguts)
        if z is not None and z['cami'] != actual and not bloquejat:
            if z['cami'] in self.carregades:
                self.activar(z['cami'])
            elif self.lliure('zona', z['cami']):
                self.feines['zona'] = Feina(z['cami'], self._carregar_cpu, z['cami'], z['clau'], z['nom'],
                                            self.max_textura, self.mesurades_disponibles(z['clau']),
                                            descripcio=f'carregar {z["nom"]}')
        elif z is None and actual is not None and app.vista == 0 and not app.peninsula.es_terra(lat, lon):
            pass      # al mar o fora d'Espanya, la zona d'abans es continua veient
        self.recentrar_pegats(lat, lon)
        if estable:
            self.preparar_alcades(volguts, x, y)
        if app.mapa_visibilitat:
            self.preparar_mapa_detall(x, y, estable)

    def lliure(self, tipus, clau):
        """Si es pot comencar una feina d'aquest tipus per a la clau: cap altra en curs i no ha fallat abans. Les que
        preparen dades noves (xarxa), nomes si preparar es True."""
        if not self.preparar and tipus in ('relleu', 'edificis', 'alcades', 'superficie'):
            return False
        return tipus not in self.feines and (tipus, clau) not in self.fallades

    def preparar_lloc(self, lat, lon, x, y, volguts):
        """Prepara el lloc de la quadricula del punt (relleu i, si es volen, edificis), si es a terra a Espanya."""
        app = self.app
        if not (app.peninsula.conte(lat, lon) and app.peninsula.es_terra(lat, lon)):
            return
        c = llocs.clau_per_punt(x, y)
        if not llocs.te_relleu(c):
            if self.lliure('relleu', c):
                protegits = {z['clau'] for z in self.carregades.values()}
                self.feines['relleu'] = FeinaProces(c, _preparar_relleu, c, self.max_textura, protegits,
                                                    descripcio='relleu del lloc')
        elif volguts and not llocs.edificis_fets(c) and self.lliure('edificis', c):
            self.feines['edificis'] = FeinaProces(c, llocs.preparar_edificis, c, descripcio='edificis del lloc')

    def recentrar_pegats(self, lat, lon):
        app = self.app
        pen = app.peninsula
        if 'pegat_pen' not in self.feines:
            c = pen.pegat['centre'] if pen.pegat is not None else None
            if c is None or _distancia_km(c, (lat, lon)) > LLINDAR_PEGAT_PENINSULA_KM:
                self.feines['pegat_pen'] = Feina(id(pen), lambda la, lo, avis: pen.calcular_pegat(la, lo, fil=True),
                                                 lat, lon, descripcio='pegat de la peninsula')
        z = app.zona
        if z is not None and 'pegat' not in self.feines:
            c = z.pegat['centre'] if z.pegat is not None else None
            costat_km = MIDA_PEGAT * z.mida.x / z.alt.shape[1]
            if (c is None or _distancia_km(c, (lat, lon)) > LLINDAR_PEGAT * costat_km) and z.conte(lat, lon):
                self.feines['pegat'] = Feina(z.cami, lambda la, lo, avis: z.calcular_pegat(la, lo, fil=True),
                                             lat, lon, descripcio='pegat de la zona')

    def preparar_alcades(self, volguts, x, y):
        """Altures mesurades dels edificis de la zona activa a la cel·la del punt (3 x 3 km), quan es veuen i aquella
        cel·la encara no s'ha mesurat (dades/alcaries.py). Cada cel·la es mesura un cop."""
        app = self.app
        e = app.edificis
        if not volguts or e is None:
            return
        cel = centre_cel(x, y)
        if e.zona not in self.cel_les_mesurades:
            self.cel_les_mesurades[e.zona] = alcaries.cel_les_fetes(e.zona)
        if cel in self.cel_les_mesurades[e.zona]:
            return
        clau = (e.zona, cel)
        if self.lliure('alcades', clau):
            self.feines['alcades'] = FeinaProces(clau, _mesurar_alcades, e.zona, cel, app.zona.cami,
                                                 descripcio='altures mesurades')

    def preparar_cobertes(self):
        """Si els edificis de la zona activa encara no tenen el color de les cobertes, es calcula en un proces (la
        primera vegada que es veu la zona; despres es llegeix del disc en carregar-los)."""
        e = self.app.edificis
        if e is None or not e.n_parts or e.colors_coberta is not None or not self.lliure('cobertes', e.zona):
            return
        cami = next((c for c, z in self.carregades.items() if z['clau'] == e.zona), None)
        if cami is not None:
            self.feines['cobertes'] = FeinaProces(e.zona, _preparar_cobertes, e.zona, cami,
                                                  descripcio='color de les cobertes')

    def carregar_edificis(self, zona):
        """Llegeix (en un fil) els edificis d'una zona carregada, amb les altures mesurades si n'hi ha: quan s'acaben
        de preparar o de mesurar. Es posen a la zona a recollir()."""
        cami = next((c for c, z in self.carregades.items() if z['clau'] == zona), None)
        if cami is None:
            return
        f = self.feines.pop('carregar_edificis', None)     # una de mes antiga queda substituida
        self.feines['carregar_edificis'] = Feina(zona, _llegir_edificis, zona, cami, self.mesurades_disponibles(zona),
                                                 descripcio='llegir els edificis')

    # ------------------------------------------------------------ mapa de visibilitat de detall

    def detall_en_curs(self):
        """Si s'esta preparant el detall del punt (superficie, altures o mapa de detall)."""
        return 'superficie' in self.feines or 'alcades' in self.feines or \
            (self.app.calcul_detall is not None and not self.app.calcul_detall.fet
             and not self.app.calcul_detall.cancelat)

    def candidats_mapa(self):
        """Superficies de detall al disc (dades/alcaries.py, per cel·les): [(cami, limits UTM, cami dels ulls,
        descripcio, MDT del relleu proper o None)]. Totes es fan de la mateixa manera a tot arreu (peticio de l'equip
        de l'1/11): el nuvol de punts de la UAB (scripts/visibilitat_lidar.py) ja no s'hi fa servir; es conserva per
        validar les altures (scripts/validar_alcaries.py: model d'alcaries - nuvol de punts, +0,10 m de mediana)."""
        import glob
        import json
        out = []
        for meta in sorted(glob.glob(os.path.join(alcaries.DIR_ALCARIES, 'cel_*.json'))):
            with open(meta) as f:
                m = json.load(f)
            cami = alcaries.cami_superficie(m['clau'], 'superficie')
            if os.path.exists(cami):
                font = alcaries.FONTS[m['font']]['curt']
                out.append((cami, tuple(self.limits(cami)), alcaries.cami_superficie(m['clau'], 'ulls'),
                            f'{font}, a {m["res_m"]:g} m', m['mdt'] if os.path.exists(m['mdt']) else None))
        return out

    def mapa_detall(self, x, y):
        """El mapa de detall que conte el punt i cap dins de la zona activa: (cami, limits, ulls, descripcio, mdt)."""
        z = self.app.zona
        if z is None:
            return None
        for cami, (x0, y0, x1, y1), ulls, desc, mdt in self.candidats_mapa():
            if not (x0 < x < x1 and y0 < y < y1):
                continue
            (u0, v1), (u1, v0) = z.uv_de_utm(x0, y0), z.uv_de_utm(x1, y1)
            if 0 <= u0 and u1 <= 1 and 0 <= v0 and v1 <= 1:
                return cami, (x0, y0, x1, y1), ulls, desc, mdt
        return None

    def preparar_mapa_detall(self, x, y, estable=True):
        """Si no hi ha mapa de detall al punt, prepara la superficie de la cel·la i en calcula la visibilitat. Es fa
        servir el relleu del lloc de la quadricula de la cel·la (cobreix la cel·la amb 1,5 km de marge)."""
        app = self.app
        self.detall_mapa = self.mapa_detall(x, y)
        if self.detall_mapa is not None or app.zona is None or not estable:
            return
        cx, cy = centre_cel(x, y)
        clau = f'cel_{cx:.0f}_{cy:.0f}'
        if os.path.exists(alcaries.cami_superficie(clau, 'superficie')):
            return      # ja es al disc: es fara servir quan la zona activa la contingui (la del lloc de la cel·la)
        lloc = llocs.clau(cx, cy)
        if not llocs.te_relleu(lloc):
            if self.lliure('relleu', lloc):
                protegits = {z['clau'] for z in self.carregades.values()}
                self.feines['relleu'] = FeinaProces(lloc, _preparar_relleu, lloc, self.max_textura, protegits,
                                                    descripcio='relleu de la cel·la del mapa')
            return
        if not self.lliure('superficie', clau) or app.calcul_detall is not None:
            return
        # contorns dels edificis (per posar els ulls sobre els terrats): els de la zona que en tingui a la cel·la
        parts_zona = next((z['clau'] for z in self.zones() if self.te_edificis(z['clau'], cx, cy)), None)
        self.feines['superficie'] = FeinaProces(clau, _preparar_superficie, (cx, cy), llocs.cami_mdt(lloc),
                                                parts_zona, descripcio='superficie del mapa de detall')

    # ------------------------------------------------------------ resultats de les feines

    def recollir(self):
        app = self.app
        for tipus in list(self.feines):
            # en recollir-ne una, se'n pot haver tret una altra (p. ex. tornar a situar l'observador quan arriben els
            # edificis treu la feina del pegat): llavors ja no hi es i se salta (abans: KeyError i el programa es tancava)
            f = self.feines.get(tipus)
            if f is None or not f.fet:
                continue
            del self.feines[tipus]
            if f.error:
                self.fallades[(tipus, f.clau)] = f.error
                continue
            if tipus == 'zona':
                self._crear(f.clau, *self._dades_zona(f.clau), f.resultat)
                # nomes s'activa si encara es la zona que toca al punt (si no, queda carregada per si s'hi torna)
                if self.punt is not None:
                    x, y = _A_UTM.transform(self.punt[1], self.punt[0])
                    actual = app.zona.cami if app.zona is not None else None
                    z, _ = self.triar_zona(x, y, self.edificis_volguts(), actual)
                    if z is not None and z['cami'] == f.clau and not (app.reproduint and app.vista == 1):
                        self.activar(f.clau)
            elif tipus == 'pegat':
                # nomes si es de la zona activa i el punt no s'ha mogut massa mentrestant (si no, se'n demana un altre)
                z = app.zona
                if z is not None and z.cami == f.clau and f.resultat is not None and self.punt is not None and \
                        _distancia_km(f.resultat['centre'], self.punt) < LLINDAR_PEGAT * MIDA_PEGAT * z.mida.x / z.alt.shape[1]:
                    z.aplicar_pegat(f.resultat)
            elif tipus == 'pegat_pen':
                app.peninsula.aplicar_pegat(f.resultat)
                if app.zona is not None:
                    app.zona.actualitzar_transicio()
                    app.zona.reajustar_pegat()   # la vora del pegat de la zona passa a la graella nova
            elif tipus == 'relleu':
                self._limits.clear()
            elif tipus == 'malla':
                self.carregar_edificis(f.clau)
            elif tipus == 'edificis':
                self._limits.clear()
                self.carregar_edificis(f.clau)       # si el lloc ja es veu, els seus edificis nous
            elif tipus == 'alcades':
                zona, cel = f.clau
                self.cel_les_mesurades.setdefault(zona, set()).add(cel)
                if f.resultat:
                    self.carregar_edificis(zona)
            elif tipus == 'carregar_edificis' and f.resultat is not None:
                self._canviar_edificis(f.clau, f.resultat)
            elif tipus == 'superficie':
                pass        # el mapa es calcula a main.actualitzar_mapa, que ara ja troba la superficie
            elif tipus == 'cobertes':
                for z in self.carregades.values():
                    if z['clau'] == f.clau and z['edificis'] is not None:
                        z['edificis'].posar_cobertes(f.resultat)

    def _dades_zona(self, cami):
        z = next(z for z in self.zones() if z['cami'] == cami)
        return z['clau'], z['nom']

    def _canviar_edificis(self, clau, preparat):
        """Els edificis amb les altures mesurades substitueixen els estimats de la mateixa zona (si es carregada)."""
        app = self.app
        for cami, z in self.carregades.items():
            if z['clau'] != clau:
                continue
            ant = z['edificis']
            if not preparat.n_triangles:
                return
            if ant is not None and preparat.colors_coberta is None:
                # mateixos contorns: el color de les cobertes no canvia
                preparat.colors_coberta = ant.colors_coberta
            nou = Edificis(app, clau, cami, preparat=preparat)
            nou.visible = ant.visible if ant is not None else True
            if ant is not None:
                ant.destroy()
            z['edificis'] = nou
            if app.zona is not None and app.zona.cami == cami:
                app.edificis = nou
                app._clau_edificis = None
                app.actualitzar_edificis()
                if cami == self.cami_obs:
                    app.reubicar_observador()

    # ------------------------------------------------------------ estat per al panell

    def actualitzar_estat(self, p):
        app = self.app
        f = self.feines
        z = app.zona

        def en_curs(*tipus):
            for t in tipus:
                if t in f:
                    return f'{f[t].estat} ({f[t].segons():.0f} s)'
            return None
        # terreny
        if en_curs('relleu', 'zona'):
            t = 'preparant 5 m: ' + en_curs('relleu', 'zona')
        elif z is not None:
            t = f'5 m ({app.nom_zona})'
        elif p is None and app.vista == 0:
            t = f'200 m (peninsula); el detall es prepara a menys de {ALCADA_DETALL_KM:.0f} km d\'altura'
        elif p is not None and not app.peninsula.es_terra(*p):
            t = '200 m: aqui no hi ha MDT de 5 m (mar o fora d\'Espanya)'
        else:
            fall = next((v for (tt, _), v in self.fallades.items() if tt in ('relleu', 'zona')), None)
            t = '200 m (peninsula)' + (f'; error: {fall[:60]}' if fall else '')
        # fotografia aeria (mosaic)
        m = app.mosaic
        if not m.actiu:
            ft = 'desactivada'
        else:
            pendents, _, _, fallades = m.estat()
            zoom = m.zoom_fi
            lat = p[0] if p is not None else 40.0
            res = teselles.CIRCUMFERENCIA_M * math.cos(math.radians(lat)) / (teselles.MIDA * 2 ** zoom)
            font = 'Sentinel-2 (10 m)' if zoom < teselles.ZOOM_MIN_PNOA else 'PNOA (vol a 0,25 m)'
            ft = f'{font}, z{zoom} ~{res:.2f} m/px' + (f', {pendents} teselles baixant' if pendents else '') + \
                (f', {fallades} fallades' if fallades else '')
        # edificis
        volguts = self.edificis_volguts()
        e = app.edificis
        if en_curs('edificis', 'malla', 'carregar_edificis'):
            et = 'preparant: ' + en_curs('edificis', 'malla', 'carregar_edificis')
        elif not volguts:
            et = 'amagats a aquesta vista (panell: Edificis)'
        elif e is not None:
            et = e.resum_alcades()
            if en_curs('alcades'):
                et += '; mesurant: ' + en_curs('alcades')
            elif any(t == 'alcades' and k[0] == e.zona for t, k in self.fallades):
                et += '; mesura fallada'
            if en_curs('cobertes'):
                et += '; ' + en_curs('cobertes')
        elif p is not None and z is not None and z.cami in self.carregades and \
                self.te_edificis(self.carregades[z.cami]['clau'], *_A_UTM.transform(p[1], p[0])):
            et = 'llegint...'
        else:
            c = llocs.clau_latlon(*p) if p is not None else None
            info = llocs.meta(c).get('edificis') if c is not None else None
            if info is not None and not info.get('municipis'):
                et = 'no disponibles: el Catastro estatal no hi te cap municipi (Navarra i el Pais Basc tenen cadastre propi)'
            elif info is not None:
                et = 'cap edifici al Catastro en aquest lloc'
            elif ('edificis', c) in self.fallades:
                et = f'error: {self.fallades[("edificis", c)][:60]}'
            else:
                et = 'pendents (primer el relleu de 5 m)'
        # mapa
        if not app.mapa_visibilitat:
            mt = 'no es mostra'
        else:
            parts = []
            c = app.calculs_mapa.get(z.cami if z is not None else app.peninsula.cami)
            c_altre = next((c for c in app.calculs_mapa.values() if not c.fet), None)
            if c is not None and not c.fet:
                parts.append(f'relleu: {c.estat}')
            elif z is not None and z.visibilitat is not None:
                parts.append('relleu 5 m')
            elif app.peninsula.visibilitat is not None:
                parts.append('relleu 200 m' + (' (5 m en espera: es calcula un altre mapa)' if c_altre else ''))
            cd = app.calcul_detall
            if en_curs('superficie'):
                parts.append('detall: ' + en_curs('superficie'))
            elif cd is not None and not cd.fet:
                parts.append(f'detall: {cd.estat}')
            elif z is not None and z.vis_detall is not None:
                parts.append(f'detall amb edificis i vegetacio ({z.vis_detall.get("descripcio", "")})')
            elif any(t == 'superficie' for t, _ in self.fallades):
                parts.append('detall no disponible (sense LiDAR)')
            mt = '; '.join(parts) or 'esperant el relleu'
        self.estat = dict(terreny=t, foto=ft, edificis=et, mapa=mt)

    def destroy(self):
        for z in self.carregades.values():
            if z['terreny'] is not self.app.zona:
                z['terreny'].destroy()
            if z['edificis'] is not None and z['edificis'] is not self.app.edificis:
                z['edificis'].destroy()


def _distancia_km(a, b):
    from dades.noms import distancia_km
    return distancia_km(a[0], a[1], b[0], b[1])


# ------------------------------------------------------------ feines (funcions de modul: es poden executar en un proces)

def _preparar_relleu(c, max_textura, protegits, avis):
    """Relleu d'un lloc i la memoria cau per dibuixar-lo (FeinaProces)."""
    llocs.preparar_relleu(c, avis, protegits)
    avis('Preparant el relleu per dibuixar-lo...')
    Terrain.preparar(llocs.cami_mdt(c), max_textura)      # deixa la memoria cau feta (derivats i atributs)
    return c


def _mesurar_alcades(zona, cel, cami, avis):
    """Altures mesurades d'una cel·la i la malla amb aquestes altures (FeinaProces). True si n'hi ha cap."""
    from dades.edificis import preparar_malla
    r = alcaries.preparar_alcades(zona, cel, avis)
    if not np.isfinite(r['alcada']).any():
        return False          # cap mesura: es queden les estimades
    avis('Malla dels edificis amb les altures mesurades...')
    preparar_malla(zona, cami, mesurades=True)
    return True


def _preparar_malla(zona, cami, avis):
    """La malla dels edificis d'una zona (estimades i, si n'hi ha, mesurades), quan no es a la memoria cau
    (FeinaProces)."""
    from dades.edificis import preparar_malla
    avis('Preparant la malla dels edificis...')
    preparar_malla(zona, cami)
    if os.path.exists(alcaries.cami_alcades(zona)):
        preparar_malla(zona, cami, mesurades=True)
    return True


def _preparar_cobertes(zona, cami, avis):
    """Color de les cobertes d'una zona a partir de la fotografia aeria (FeinaProces): els contorns, de la malla."""
    from dades.edificis import preparar_malla, contorns_de_bytes, colors_cobertes
    m = preparar_malla(zona, cami, nomes_llegir=True)
    return colors_cobertes(zona, contorns_de_bytes(m), avis) if m is not None else None


def _llegir_edificis(zona, cami, mesurades, avis):
    """Edificis d'una zona llegits de la memoria cau (Feina, en un fil: nomes llegeix)."""
    avis('Llegint els edificis...')
    return Edificis.preparar(zona, cami, mesurades=mesurades, nomes_llegir=True)   # la malla ja es feta (proces)


def _preparar_superficie(cel, cami_mdt, parts_zona, avis):
    """Superficie dels obstacles d'una cel·la per al mapa de detall (FeinaProces)."""
    cx, cy = cel
    m = llocs.PAS_GRAELLA_M / 2
    parts = None
    if parts_zona is not None:
        import geopandas as gpd
        parts = gpd.read_file(fitxer_zona(parts_zona), layer='parts', bbox=(cx - m, cy - m, cx + m, cy + m))
    a = alcaries.alcaria_cel(cx, cy, avis)
    if a is None:
        raise RuntimeError('cap model d\'alcaries (LiDAR) no cobreix aquest lloc')
    return alcaries.preparar_superficie(cel, cami_mdt, parts, RES_SUPERFICIE_M[a['font']], avis)
