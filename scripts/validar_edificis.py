"""
Comprova els edificis (Catastro INSPIRE) separant tres coses: la correccio del renderitzador, la precisio
geografica dels contorns i la incertesa de les altures.

1. Dades: parts per zona, plantes i altures estimades, versions; si els punts d'observacio son dins d'un
   edifici (i, si ho son, el punt exterior mes proper a 3 m de qualsevol facana, nomes com a proposta).
2. Precisio geografica (UAB): els contorns del Catastro comparats amb els d'OpenStreetMap (una altra
   cartografia, independent) en 400 m al voltant de la placa Civica: desplacament dels centres i solapament.
3. Altures: (a) les plantes del GML original contra les preparades; (b) la coberta dibuixada: una camera a
   sobre de l'edifici mirant avall llegeix la profunditat de la coberta i ha de ser la cota calculada;
   (c) OpenStreetMap, on hi ha building:levels (independent; la incertesa de les altures queda aqui).
4. Renderitzador: per a casos de Sol visible, parcialment tapat i totalment tapat (a la UAB i a Vic), la
   fraccio del disc visible llegida de la imatge (pixels del Sol identificats per la profunditat: el Sol es
   a ~1,5e8 km, la Lluna a ~3,8e5 km i els edificis a menys de 3 km) contra el calcul geometric de
   dades/edificis.py (perfil d'horitzo dels edificis i el disc mostrejat), des dels ulls i des de la camera
   d'exploracio posada al mateix lloc. El halo no travessa les facanes. Mostrar/amagar edificis
   repetidament en pausa dona les mateixes imatges i no mou la camera ni el temps.
5. Rendiment: temps de carrega, triangles, memoria de GPU i temps per fotograma amb edificis i sense.

Punts de prova (no son ubicacions del programa): a la UAB, 41,50220, 2,10416, en espai obert a 40 m de la
placa Civica (el punt de la placa cau dins d'un edifici del Catastro); a Vic, la placa Major; a l'Escala,
Cerdanyola i Montmelo, els punts exteriors proposats (els ajuntaments son dins d'un edifici).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/validar_edificis.py
"""
import json
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from pyproj import Transformer  # noqa: E402
from slimgui import imgui  # noqa: E402

SORTIDA = os.path.join(ARREL, 'captures', 'proves')
FOV_SOL = 2.0                  # graus: el Sol (0,53 graus) fa ~170 pixels de diametre a 640 pixels d'alt
TOLERANCIA_FRACCIO = 0.04      # pixels de la vora del disc (2/r ~ 2,4 %) i intervals de 0,01 graus del perfil (~2 %)
PROVA_UAB = (41.50220, 2.10416)


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    import geopandas as gpd
    import requests
    from basecode.camera_exploracio import COEF_LOG, direccio_mirada
    from dades import edificis, geodesia, eclipse_data
    from dades.observador import UBICACIONS

    W, H = 640, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - edificis', use_ui_panel=True)
    app.edificis_aeris = True   # aqui la camera d'exploracio fa de referencia: tambe amb els edificis
    app.mosaic.actiu = False    # sense la fotografia aeria, que arriba a mesura que es baixa: escena quieta
    objectiu = app.ctx.simple_framebuffer((W, H))
    co, ce = app.camera_observador, app.camera_exploracio
    errors = []
    a_utm = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True)
    a_latlon = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
    os.makedirs(SORTIDA, exist_ok=True)

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(n=2):
        for _ in range(n):
            app.dt = 0.0
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.render()

    def distancies():
        d = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        w = 2.0 ** (d.astype(float) * 2.0 / COEF_LOG) - 1.0
        w[d >= 1.0] = np.inf
        return w

    def imatge():
        return Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    # ------------------------------------------------------------ 1. dades
    print('== 1. Dades (Catastro INSPIRE, parts d\'edifici a menys de 2 km dels punts)')
    for zona in ('valles', 'vic', 'escala', 'picos'):
        parts = edificis.llegir_zona(zona)
        if parts is None or len(parts) == 0:
            print(f'   {zona}: cap edifici a l\'area (zona sense cobertura d\'edificis)')
            continue
        p = parts['plantes']
        print(f'   {zona}: {len(parts)} parts; plantes: mediana {p.median():.0f}, maxim {p.max()} '
              f'(altura estimada fins a {p.max() * edificis.ALCADA_PLANTA_M:.0f} m); versions {parts.versio.min()} a {parts.versio.max()}')
    for nom, lat, lon in UBICACIONS:
        parts = edificis.llegir_zona(edificis.ZONA_DE_LA_UBICACIO[nom])
        if parts is None or len(parts) == 0:
            continue
        x, y = a_utm.transform(lon, lat)
        pid = edificis.dins_dun_edifici(parts, x, y)
        print(f"   {nom}: {'DINS de la part ' + pid if pid else 'fora dels edificis'}")

    # ------------------------------------------------------------ 2. precisio geografica (OSM)
    print('\n== 2. Contorns del Catastro contra OpenStreetMap (UAB, 400 m)')
    cache_osm = os.path.join(edificis.DIR_EDIFICIS, 'osm_uab.json')
    if not os.path.exists(cache_osm):
        consulta = f'[out:json][timeout:60];way["building"](around:400,{PROVA_UAB[0]},{PROVA_UAB[1]});out tags geom;'
        r = requests.post('https://overpass-api.de/api/interpreter', data={'data': consulta}, timeout=120,
                          headers={'User-Agent': 'EGRA-projecte-universitari (validacio d\'edificis)'})
        r.raise_for_status()
        with open(cache_osm, 'w') as f:
            f.write(r.text)
    osm = json.load(open(cache_osm))['elements']
    pol_osm, nivells_osm = [], []
    for e in osm:
        c = [a_utm.transform(g['lon'], g['lat']) for g in e.get('geometry', [])]
        if len(c) >= 4:
            pol_osm.append(shapely.Polygon(c).buffer(0))
            nivells_osm.append(e['tags'].get('building:levels'))
    parts = edificis.llegir_zona('valles')
    x0, y0 = a_utm.transform(PROVA_UAB[1], PROVA_UAB[0])
    prop = parts[parts.distance(shapely.Point(x0, y0)) < 400]
    # es compara a nivell de part: per a cada edifici d'OSM, la unio de les parts del Catastro que hi cauen
    # majoritariament a dins (a la UAB, tot el campus es un sol edifici cadastral amb centenars de parts)
    desplacaments, ious, nivells = [], [], []
    for po, nv in zip(pol_osm, nivells_osm):
        cand = prop[prop.intersects(po)]
        if len(cand) == 0:
            continue
        dins = cand[cand.geometry.intersection(po).area > 0.5 * cand.geometry.area]
        if len(dins) == 0:
            continue
        gc = shapely.union_all(dins.geometry.values)
        iou = gc.intersection(po).area / gc.union(po).area
        if iou > 0.3:
            ious.append(iou)
            desplacaments.append(np.array(po.centroid.coords[0]) - np.array(gc.centroid.coords[0]))
            if nv:
                nivells.append((int(float(nv)), int(dins['plantes'].max())))
    desplacaments = np.array(desplacaments)
    mitja = desplacaments.mean(0) if len(desplacaments) else np.zeros(2)
    # OSM es tracat sobre ortofotos (precisio de pocs metres); el Catastro declara 0,1 m: es demana que els
    # centres coincideixin a menys de 3 m (mediana) i que no hi hagi un desplacament sistematic de mes d'1,5 m
    ok(len(ious) >= 10 and np.median(np.linalg.norm(desplacaments, axis=1)) < 3.0 and np.linalg.norm(mitja) < 1.5,
       f'{len(ious)} edificis coincidents (de {len(pol_osm)} a OSM): solapament (IoU) mediana {np.median(ious):.2f}; '
       f'distancia entre centres mediana {np.median(np.linalg.norm(desplacaments, axis=1)):.2f} m; '
       f'desplacament mitja (est, nord) ({mitja[0]:+.2f}, {mitja[1]:+.2f}) m')

    # ------------------------------------------------------------ 3. altures
    print('\n== 3. Altures')
    import zipfile
    import io
    with zipfile.ZipFile(os.path.join(edificis.DIR_EDIFICIS, 'catastro', 'A.ES.SDGC.BU.08266.zip')) as z:
        original = gpd.read_file(io.BytesIO(z.read('A.ES.SDGC.BU.08266.buildingpart.gml')))
    mostra = prop[prop['id'].isin(original['localId'])].sample(10, random_state=1)
    orig = dict(zip(original['localId'], original['numberOfFloorsAboveGround'].astype(int)))
    ok(all(orig[i] == pl for i, pl in zip(mostra['id'], mostra['plantes'])),
       '(a) 10 parts a l\'atzar: les plantes preparades son les del GML original del Catastro')
    if nivells:
        n = np.array(nivells)
        print(f'      (c) OpenStreetMap amb building:levels: {len(n)} edificis; iguals {int((n[:, 0] == n[:, 1]).sum())}, '
              f'diferencia mediana {np.median(np.abs(n[:, 0] - n[:, 1])):.0f} plantes, maxima {np.abs(n[:, 0] - n[:, 1]).max()} '
              f'(OSM compta plantes del cos principal; no es una mesura d\'altura)')
    else:
        print('      (c) cap edifici d\'OpenStreetMap a la zona te building:levels: no hi ha referencia independent')

    # (b) la coberta dibuixada: triar el punt de prova a la UAB carrega la zona i els edificis
    app.triar_punt(*PROVA_UAB, 'prova UAB')
    e = app.edificis
    m = np.load(os.path.join(ARREL, 'data', 'cache', 'edificis_valles.npz'))
    tots = edificis.llegir_zona('valles')
    errs = []
    for pid in mostra['id'][:5]:
        i = int(np.flatnonzero(tots['id'].values == pid)[0])
        geom = tots.geometry.iloc[i]
        pt = shapely.maximum_inscribed_circle(geom).coords[0]   # el punt mes lluny de les vores
        lon, lat = a_latlon.transform(*pt)
        ce.posicio = geodesia.ecef(lat, lon, m['cota_coberta'][i] / 1000 + 0.05)   # 50 m per sobre
        ce.rumb, ce.inclinacio = 0.0, -89.9
        app.canviar_vista(0)
        fotograma()
        dist = distancies()[H // 2, W // 2]
        errs.append(abs(0.05 - dist) * 1000)      # m
    app.canviar_vista(1)
    ok(max(errs) < 0.01, f'(b) 5 cobertes: la superficie dibuixada es a la cota calculada (error maxim {max(errs) * 1000:.1f} mm, '
                         f'mirant avall des de 50 m al centre del cercle inscrit mes gran)')
    print(f'      altura estimada = plantes x {edificis.ALCADA_PLANTA_M:.0f} m; cota de referencia = mediana del MDT sota el contorn; '
          f'desnivell del terra sota les parts: mediana {np.median(m["desnivell"]):.1f} m, percentil 95 {np.percentile(m["desnivell"], 95):.1f} m')

    # ------------------------------------------------------------ 4. ocultacio del Sol (renderitzador)
    print('\n== 4. Ocultacio del Sol: imatge contra calcul geometric')
    halo = app.halo

    def pixels_sol(cam):
        """Pixels del disc del Sol que es veuen: profunditat entre 1e8 i 1e9 km (el cel no en te: infinit)."""
        fotograma()
        d = distancies()
        return int(((d > 1e8) & np.isfinite(d)).sum())

    def cas(nom_cas, lat, lon, hora):
        app.reproduint = False
        app.triar_punt(lat, lon, nom_cas)
        app.hora = hora
        app.actualitzar_astres()
        ulls = app.ulls()
        e = app.edificis
        lluna_f, edif_f, vis_f = e.fraccions(ulls)
        lat_u, lon_u, _ = (float(c) for c in geodesia.geodesiques(ulls))
        az, el = geodesia.azimut_elevacio(app.sol_ecef - ulls, lat_u, lon_u)
        res = {}
        for nom_cam in ('ulls', 'exploracio'):
            if nom_cam == 'ulls':
                app.canviar_vista(1)
                co.mirar(az, el)
                co.fov = FOV_SOL
            else:
                app.canviar_vista(0)
                ce.posicio = ulls
                ce.rumb, ce.inclinacio = az, el
                ce.fov = FOV_SOL
            e.visible, app.lluna.visible = False, False
            total = pixels_sol(None)
            app.lluna.visible = True
            sense = pixels_sol(None)
            e.visible = True
            amb = pixels_sol(None)
            res[nom_cam] = (total, sense, amb)
            if nom_cam == 'ulls':
                im = imatge()
                e.visible = False
                fotograma()
                im_sense = imatge()
                e.visible = True
                fotograma()
                # el halo no travessa les facanes: amb halo i sense, els pixels d'edifici son iguals
                edifici = np.flipud(distancies() < 10.0)        # en l'ordre de la imatge (fila 0 a dalt)
                a = np.asarray(imatge()).astype(int)
                halo.visible = False
                fotograma()
                b = np.asarray(imatge()).astype(int)
                halo.visible = True
                halo_ok = None
                if edifici.any():
                    halo_ok = np.abs(a - b)[edifici].max() == 0
                captura = (im, im_sense)
        ce.fov = 50.0
        co.fov = 60.0
        total, sense, amb = res['ulls']
        vis_img = amb / total
        lluna_img = 1 - sense / total
        t2, s2, a2 = res['exploracio']
        estat = 'visible' if edif_f == 0 else ('parcial' if vis_f > 0 or lluna_f + edif_f < 0.999 else 'total')
        ok(abs(vis_img - vis_f) < TOLERANCIA_FRACCIO and abs(lluna_img - lluna_f) < TOLERANCIA_FRACCIO
           and abs(a2 / t2 - vis_img) < 0.01,
           f'{nom_cas} {eclipse_data.hora_local(hora)} (Sol a {el:.2f} graus, {estat}): visible a la imatge {vis_img * 100:.1f} % '
           f'/ calcul {vis_f * 100:.1f} %; Lluna {lluna_img * 100:.1f} % / {lluna_f * 100:.1f} %; edificis (calcul) '
           f'{edif_f * 100:.1f} %; camera d\'exploracio {a2 / t2 * 100:.1f} %')
        if halo_ok is not None:
            ok(halo_ok, f'{nom_cas} {eclipse_data.hora_local(hora)}: el halo no canvia cap pixel de les facanes')
        return captura, f'{nom_cas} {eclipse_data.hora_local(hora)} CEST, azimut {az:.1f}, elevacio {el:.2f} graus: visible {vis_img * 100:.0f} %'

    captures = []
    hores_uab = [('visible', -40 / 60), ('parcial', None), ('total', 0.0)]
    app.triar_punt(*PROVA_UAB, 'prova UAB')
    maxim = app.model.hores['maxim']
    # el moment parcial: el primer minut amb una part tapada (calcul geometric)
    t_parcial = None
    for t in np.arange(maxim - 20 / 60, maxim, 10 / 3600):
        app.hora = t
        app.actualitzar_astres()
        f = app.edificis.fraccions(app.ulls())
        if 0.15 < f[1] < 0.85:
            t_parcial = t
            break
    for nom_cas, desfas in hores_uab:
        hora = t_parcial if desfas is None else maxim + desfas
        if hora is None:
            ok(False, 'UAB: no s\'ha trobat cap moment parcial')
            continue
        captures.append(cas(f'UAB (prova) {nom_cas}', *PROVA_UAB, hora))
    nom_v, lat_v, lon_v = UBICACIONS[1]
    for nom_cas, hora_local in (('visible', 20 + 10 / 60), ('parcial', 20 + 18 / 60), ('total', 20 + 25 / 60)):
        captures.append(cas(f'Vic {nom_cas}', lat_v, lon_v, hora_local - 2))
    # una comprovacio a cada una de les altres zones, des dels punts exteriors proposats (a 3 m de les facanes:
    # el Sol hi queda tapat per edificis a l'hora del maxim)
    for nom_cas, lat, lon in (("L'Escala (punt exterior)", 42.12479, 3.13237), ('Cerdanyola (punt exterior)', 41.49092, 2.14077),
                              ('Montmelo (punt exterior)', 41.55163, 2.24796)):
        app.triar_punt(lat, lon, nom_cas)
        captures.append(cas(nom_cas, lat, lon, app.model.hores['maxim'] - 30 / 60))
    full = Image.new('RGB', (W, H * len(captures) // 2))
    dib = ImageDraw.Draw(full)
    for i, ((im, im_sense), text) in enumerate(captures):
        y = i * H // 2
        full.paste(im.resize((W // 2, H // 2)), (0, y))
        full.paste(im_sense.resize((W // 2, H // 2)), (W // 2, y))
        dib.text((6, y + 6), text + '  (amb / sense edificis)', fill=(255, 255, 0))
    full.save(os.path.join(SORTIDA, 'edificis_sol.png'))

    # interruptor repetit en pausa: mateix enquadrament
    app.triar_punt(*PROVA_UAB, 'prova UAB')
    app.hora = maxim - 40 / 60
    app.canviar_vista(1)
    co.mirar(270.0, 3.0)
    imatges, estats = [], []
    for visible in (True, False, True, False):
        app.edificis.visible = visible
        fotograma()
        imatges.append(np.asarray(imatge()))
        estats.append((co.posicio.copy(), co.rumb, co.inclinacio, app.hora))
    ok(np.array_equal(imatges[0], imatges[2]) and np.array_equal(imatges[1], imatges[3])
       and not np.array_equal(imatges[0], imatges[1]) and all(np.array_equal(s[0], estats[0][0]) and s[1:] == estats[0][1:] for s in estats),
       'mostrar/amagar edificis 4 vegades en pausa: les mateixes imatges cada vegada; la camera i l\'hora no canvien')

    # ------------------------------------------------------------ 5. rendiment
    print('\n== 5. Rendiment')
    app.edificis.visible = True
    co.mirar(270.0, 3.0)
    co.fov = 60.0
    temps = {}
    for visible in (False, True):
        app.edificis.visible = visible
        fotograma(5)
        app.ctx.finish()
        t = time.time()
        for _ in range(60):
            fotograma(1)
        objectiu.read(viewport=(0, 0, 1, 1))
        temps[visible] = (time.time() - t) / 60 * 1000
    e = app.edificis
    t = time.time()
    e.perfil, e.ull_perfil = None, None
    e.fraccions(app.ulls())
    t_perfil = time.time() - t
    print(f'   Valles: {e.n_parts} parts, {e.n_triangles:,} triangles, {e.memoria_gpu / 1e6:.0f} MB de GPU; carrega des de la memoria cau '
          f'{e.temps_carrega:.2f} s; perfil des dels ulls {t_perfil:.2f} s (un cop per punt)')
    print(f'   temps per fotograma (finestra amagada {W}x{H}): sense edificis {temps[False]:.1f} ms, amb {temps[True]:.1f} ms')

    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
