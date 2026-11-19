"""
Prova de la navegacio unificada (una sola camera) i del panell "Camera" simplificat, amb el programa real (finestra
amagada). Cada fotograma es com els del bucle del programa, amb el panell construit i dibuixat.

  1. Arrencada: una sola camera (la d'exploracio), als ulls de l'observador (1,7 m sobre el terra dibuixat).
  2. Teclat: W A S D mouen la posicio (a pas de caminar a prop del terra) i la camera deixa de seguir els ulls;
     E puja i Q baixa, mai per sota dels ulls; les fletxes nomes giren la mirada (la posicio no canvia).
  3. Doble clic al terreny des de l'aire: el punt d'observacio va al punt clicat i la camera als seus ulls, mirant
     cap al Sol; despres, W la continua movent (la mateixa camera).
  4. G: a l'espai (milers de km) i, un altre cop, torna exactament on era (posicio i mirada, als ulls).
  5. P: nomes reproduir / pausar (la camera no es mou ni gira).
  6. Panell: les linies de "Descarregues en segon pla" surten de les feines (es posa una feina d'espera amb el lloc de
     Cadis: comprova el text, no una descarrega real); el selector de Mapes ja no te els limits de totalitat; es desa una
     captura del panell amb els desplegables oberts a captures/proves/panell_camera.png.
Limitacio: no hi ha ratoli fisic; els clics es simulen com a esdeveniments d'imgui. No demostra que els controls
siguin intuitius: aixo ho ha de provar l'equip amb la finestra.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_navegacio.py
"""
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from OpenGL import GL  # noqa: E402
from PIL import Image  # noqa: E402
from slimgui import imgui  # noqa: E402

CARPETA = os.path.join(ARREL, 'captures', 'proves')


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    import ui
    from dades import geodesia
    from dades.feines import Feina
    from dades.observador import ALCADA_ULLS_KM

    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de la navegacio', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    app.mosaic.actiu = False          # sense xarxa: la prova no depen de les teselles
    app.detall.preparar = False
    objectiu = app.ctx.simple_framebuffer((W, H))
    ce, io = app.camera, imgui.get_io()
    errors = []
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)
    app.ratoli.focus = True

    def pixel_cursor():
        mx, my = io.mouse_pos
        px, py = int(mx), H - 1 - int(my)
        return (px, py, W, H) if 0 <= px < W and 0 <= py < H else None
    app.pixel_cursor = pixel_cursor

    def punt_sota_cursor(pixel=None):   # el picking llegeix el framebuffer de la prova (el programa, la pantalla)
        mx, my = io.mouse_pos
        px, py = (int(mx), H - 1 - int(my)) if pixel is None else pixel[:2]
        d = float(np.frombuffer(objectiu.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'), 'f4')[0])
        return None if d >= 1.0 else app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
    app.punt_sota_cursor = punt_sota_cursor
    obrir = [False]
    capcalera = imgui.collapsing_header

    def capcalera_oberta(*a, **k):
        if obrir[0]:
            imgui.set_next_item_open(True, imgui.Cond.ALWAYS)
        return capcalera(*a, **k)
    imgui.collapsing_header = capcalera_oberta

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(n=1, dt=1 / 60):
        for _ in range(n):
            glfw.poll_events()
            app.dt = dt
            app.ui_renderer.new_frame()
            io.display_size, io.display_framebuffer_scale = (W, H), (1.0, 1.0)   # captura: un pixel per punt
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
            imgui.begin('Eclipsi')
            app.build_ui()
            imgui.end()
            imgui.render()
            GL.glUseProgram(0)
            objectiu.use()
            app.ui_renderer.render(imgui.get_draw_data())

    def alcada():
        return ce.alcada_sobre_terra()

    def angle_al_sol():
        s = app.sol_ecef - ce.posicio
        return math.degrees(math.acos(float(np.clip(s @ ce.davant() / np.linalg.norm(s), -1, 1))))

    # ------------------------------------------------------------ 1. arrencada
    fotograma(3)
    ok(not hasattr(app, 'camera_observador') and not hasattr(app, 'camera_guiada') and not hasattr(app, 'vista'),
       'una sola camera: no hi ha camera d\'observacio, ni guiada, ni selector de vista')
    ok(app.camera is app.camera_exploracio and app.camera_als_ulls() and abs(alcada() - ALCADA_ULLS_KM) < 1e-6,
       f'arrencada als ulls de l\'observador ({app.observador.nom}): {alcada() * 1000:.2f} m sobre el terra')

    # ------------------------------------------------------------ 2. teclat
    p0, rumb0, incl0 = ce.posicio.copy(), ce.rumb, ce.inclinacio
    premudes.add(glfw.KEY_W)
    fotograma(60)
    premudes.clear()
    fotograma()
    d = np.linalg.norm(ce.posicio - p0) * 1000
    ok(0.5 < d < 5.0 and abs(alcada() - ALCADA_ULLS_KM) < 0.01 and not app.camera_als_ulls(),
       f'W durant 1 s als ulls: {d:.2f} m (pas de caminar), a {alcada() * 1000:.2f} m del terra; deixa de seguir els ulls')
    for k, nom in ((glfw.KEY_A, 'A'), (glfw.KEY_D, 'D'), (glfw.KEY_S, 'S')):
        p = ce.posicio.copy()
        premudes.add(k)
        fotograma(30)
        premudes.clear()
        ok(np.linalg.norm(ce.posicio - p) > 2e-4, f'{nom}: la camera es mou ({np.linalg.norm(ce.posicio - p) * 1000:.2f} m)')
    h = alcada()
    premudes.add(glfw.KEY_E)
    fotograma(120)
    premudes.clear()
    pujat = alcada()
    premudes.add(glfw.KEY_Q)
    fotograma(400)
    premudes.clear()
    fotograma()
    ok(pujat > h + 0.002 and abs(alcada() - ALCADA_ULLS_KM) < 1e-4,
       f'E puja ({h * 1000:.1f} -> {pujat * 1000:.1f} m) i Q baixa fins als ulls, no mes ({alcada() * 1000:.2f} m)')
    p, rumb, incl = ce.posicio.copy(), ce.rumb, ce.inclinacio
    premudes.update({glfw.KEY_RIGHT, glfw.KEY_UP})
    fotograma(20)
    premudes.clear()
    ok(np.linalg.norm(ce.posicio - p) < 1e-9 and ce.rumb != rumb and ce.inclinacio > incl,
       f'fletxes: giren la mirada (rumb {rumb:.0f} -> {ce.rumb:.0f}, inclinacio {incl:.0f} -> {ce.inclinacio:.0f}) '
       'sense moure la camera')

    # ------------------------------------------------------------ 3. doble clic
    app.hora = 14.5                     # Sol alt
    o0 = (app.observador.lat, app.observador.lon)
    ce.posicio = geodesia.ecef(41.50, 2.10, 3.0)
    ce.orientar(0.0, -60.0)
    fotograma(3)
    clicat = app.punt_sota_cursor((W // 2, H // 2))
    for _ in range(2):
        io.add_mouse_pos_event(W / 2, H / 2)
        io.add_mouse_button_event(0, True)
        fotograma()
        io.add_mouse_button_event(0, False)
        fotograma()
    fotograma(3)
    lat_c, lon_c, _ = geodesia.geodesiques(clicat)
    dist = math.hypot(app.observador.lat - float(lat_c), (app.observador.lon - float(lon_c)) * math.cos(math.radians(41.5)))
    ok((app.observador.lat, app.observador.lon) != o0 and dist * 111.0 < 0.05,
       f'doble clic: el punt d\'observacio va al punt clicat ({app.observador.lat:.4f}, {app.observador.lon:.4f}; '
       f'{dist * 111000:.0f} m)')
    ok(app.camera_als_ulls() and abs(alcada() - ALCADA_ULLS_KM) < 1e-6 and angle_al_sol() < 0.5,
       f'doble clic: la camera als ulls ({alcada() * 1000:.2f} m) mirant el Sol (a {angle_al_sol():.2f} graus del centre)')
    p = ce.posicio.copy()
    premudes.add(glfw.KEY_W)
    fotograma(30)
    premudes.clear()
    ok(app.camera is app.camera_exploracio and np.linalg.norm(ce.posicio - p) > 2e-4,
       'des del punt es continua explorant amb la mateixa camera (W la mou)')
    coords, _, _ = ui.dades_punt(app)
    ok(coords == f'{app.observador.lat:.5f} N, {app.observador.lon:.5f} E',
       f'panell Eclipsi: les coordenades son les del punt del doble clic ({coords})')
    if app.consulta_nom is not None:
        ok(ui.dades_punt(app)[1:] == ('-', '-'), 'mentre es consulta el nom: nucli i municipi "-"')
    t = time.time()
    while app.consulta_nom is not None and time.time() - t < 20:
        fotograma()
    print(f'   nucli i municipi (servei IGN, si hi ha xarxa): {ui.dades_punt(app)[1:]}')
    app.tornar_al_punt()
    fotograma()

    # ------------------------------------------------------------ 4. G
    p, rumb, incl = ce.posicio.copy(), ce.rumb, ce.inclinacio
    io.add_key_event(imgui.Key.KEY_G, True)
    fotograma()
    io.add_key_event(imgui.Key.KEY_G, False)
    fotograma(2)
    lluny = alcada()
    t = time.time()
    while time.time() - t < 0.4:          # el detall revisa l'estat cada 0,15 s
        fotograma()
    motiu = ui.motiu_sense_edificis(app)
    ok('massa amunt' in motiu, f'a l\'espai, el panell diu per que no hi ha edificis: "{motiu}"')
    io.add_key_event(imgui.Key.KEY_G, True)
    fotograma()
    io.add_key_event(imgui.Key.KEY_G, False)
    fotograma(2)
    ok(lluny > 5000 and np.linalg.norm(ce.posicio - p) < 1e-6 and abs(ce.rumb - rumb) < 1e-6
       and abs(ce.inclinacio - incl) < 1e-6 and app.camera_als_ulls(),
       f'G: a l\'espai ({lluny:,.0f} km sobre el terra) i, un altre cop, torna on era (als ulls, mateixa mirada)')

    # ------------------------------------------------------------ 5. P
    p, rumb = ce.posicio.copy(), ce.rumb
    io.add_key_event(imgui.Key.KEY_P, True)
    fotograma()
    io.add_key_event(imgui.Key.KEY_P, False)
    fotograma(10)
    ok(app.reproduint and np.linalg.norm(ce.posicio - p) < 1e-6 and ce.rumb == rumb,
       'P: reprodueix sense moure ni girar la camera')
    app.reproduir_pausar()

    # ------------------------------------------------------------ 6. panell
    ok(not ui.descarregues(app), f'sense feines: cap linia de descarrega ({ui.descarregues(app)})')
    t = time.time()
    while time.time() - t < 0.4:
        fotograma()
    ok(ui.motiu_sense_edificis(app) == '' and app.edificis is not None,
       f'als ulls amb edificis carregats, cap avis ({app.detall.estat["edificis"]})')
    desat = (app.detall.estat, app.edificis)
    app.detall.estat, app.edificis = dict(terreny='5 m (Lloc)', edificis='error: ConnectionError: timeout'), None
    app.detall.fallades[('edificis', 'prova')] = 'ConnectionError: timeout'
    ok(ui.motiu_sense_edificis(app) == 'error: ConnectionError: timeout', 'descarrega fallada: el panell en mostra l\'error')
    fotograma()
    app.detall.fallades.pop(('edificis', 'prova'))
    app.detall.estat, app.edificis = desat
    cadis = (36.5271, -6.2886)
    f = Feina('prova', lambda avis: (avis('Edificis de Cadiz (3/4, Catastro)...'), time.sleep(3.0)), descripcio='prova')
    f.lloc = cadis
    time.sleep(0.1)
    app.detall.feines['cadastre'] = f
    linies = ui.descarregues(app)
    ok(linies == [('Descarregant edificis de Cadiz...', 0.5)],
       f'feina d\'edificis a Cadis, municipi 3 de 4: {linies} (progres: 2 de 4 acabats)')
    g = Feina('prova', lambda avis: time.sleep(3.0), descripcio='prova')
    app.detall.feines['relleu'] = g
    linies = ui.descarregues(app)
    ok(linies[0][1] is None, f'feina sense comptador: barra indeterminada ({linies[0]})')
    app.detall.feines.pop('relleu')
    app.mosaic.actiu = True
    dsc = app.mosaic.descarregador
    en_curs = set(dsc.en_curs)
    dsc.baixant, dsc.lot = 2, 3
    dsc.en_curs.update({(99, 0, 0), (99, 0, 1)})
    app.detall.punt = cadis
    linies = ui.descarregues(app)
    ok(('Descarregant fotografies de Cadiz...', 0.6) in linies, f'teselles: 3 acabades, 2 pendents: {linies}')
    obrir[0] = True
    fotograma(3)
    os.makedirs(CARPETA, exist_ok=True)
    dades = objectiu.read(components=3)
    Image.frombytes('RGB', (W, H), dades).transpose(Image.FLIP_TOP_BOTTOM).save(os.path.join(CARPETA, 'panell_camera.png'))
    print(f'   captura: {os.path.join(CARPETA, "panell_camera.png")}')
    app.detall.feines.pop('cadastre', None)
    dsc.baixant, dsc.en_curs = 0, en_curs
    app.mosaic.actiu = False
    import inspect
    ok('limits_totalitat' not in inspect.getsource(ui) and not any(t.limits_totalitat for t in app.terrenys()),
       'el selector de Mapes ja no te els limits de totalitat i la capa no es dibuixa')

    # ------------------------------------------------------------ 7. barra de temps
    from dades.observador import UBICACIONS_PROVES
    obrir[0] = False

    def captura_barra(nom):
        fotograma(2)
        im = Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)
        im.crop((240, H - 150, W - 240, H)).save(os.path.join(CARPETA, nom))
        print(f'   captura: {os.path.join(CARPETA, nom)}')
    captura_barra('barra_temps_uab.png')
    nom, lat, lon = next(u for u in UBICACIONS_PROVES if u[0].startswith('Picos'))
    app.triar_ubicacio(lat, lon, nom)
    app.hora = app.model.hores['c2'] - 0.05
    hora = app.hora
    io.add_key_event(imgui.Key.KEY_P, True)
    fotograma()
    io.add_key_event(imgui.Key.KEY_P, False)
    captura_barra('barra_temps_picos.png')
    ok(app.reproduint and app.hora > hora and app.model.hores['c2'] is not None,
       f'barra de temps a {nom} (totalitat), reproduint: l\'hora avanca ({ui.eclipse_data.hora_local(app.hora)})')
    app.reproduir_pausar()

    print(f'\n{"Tot correcte" if not errors else f"{len(errors)} errors"}')
    app._shutdown()
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
