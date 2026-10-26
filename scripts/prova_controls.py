"""
Prova dels controls i de l'espai de navegacio amb el programa real (finestra amagada). Cada fotograma es
com els del bucle del programa: amb el panell construit, perque imgui sapiga quan el cursor es a sobre.

  1. Cub de navegacio: escriu les dades (costat, limits, marge) i comprova que conte la Terra, la Lluna i el
     Sol tot l'interval. A les sis cares: el teclat (W, E/Q), la roda i una posicio posada directament (com
     fan els botons) no deixen sortir la camera; a la paret, la coordenada de la cara es queda exacta (sense
     rebots ni tremolors) i el moviment paral·lel continua. Els botons d'enquadrament deixen la camera dins.
  2. Enquadrar el Sol: per a cada cara, amb el Sol a l'instant en que hi es mes a prop, la camera a la paret
     de darrere mirant-lo: el Sol sencer cap a la imatge (cap pixel del disc a la vora).
  3. Ratoli capturat: el moviment relatiu (posicio virtual del cursor de GLFW) gira la mirada; sense moviment
     la mirada no canvia; alliberar i tornar a capturar en un altre lloc no fa saltar la mirada; perdre el
     focus allibera. Un clic a l'escena captura (despres del temps del doble clic); un doble clic no
     captura i tria el punt; un clic sobre el panell no captura.
  4. Panell: arrossegar i fer rodar sobre el panell no mou ni gira la camera.
  5. P: nomes canvia reproduir/pausar (ni la vista, ni les cameres, ni el punt, ni l'hora en aquell moment).
  6. Roda: passos de roda per anar del terra (3 km) a 20.000 km; en observacio, la roda nomes canvia el camp
     de visio (els ulls no es mouen).
Limitacio: no hi ha ratoli ni trackpad fisics. El moviment del ratoli es simula posant la posicio virtual
del cursor (glfw.set_cursor_pos), els clics i la roda com a esdeveniments; el gest de pessigar no arriba a
GLFW (pla, tasca 12.4).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_controls.py
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
from slimgui import imgui  # noqa: E402


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    from dades.navegacio import UA_KM, DISTANCIA_PARET_KM
    from dades.efemerides import RADI_SOL_KM
    from basecode.camera_exploracio import direccio_mirada, FOV as FOV_EXPLORACIO
    from basecode.control_ratoli import SENSIBILITAT

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova dels controls', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    co, ce, cub, io = app.camera_observador, app.camera_exploracio, app.cub, imgui.get_io()
    errors = []
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)
    # posicio virtual del cursor: la finestra amagada no te el focus i macOS no hi aplica el cursor
    # desactivat; es simula la posicio que retornaria GLFW (glfw.get_cursor_pos)
    cursor = [400.0, 300.0]
    get_cursor_pos = glfw.get_cursor_pos
    glfw.get_cursor_pos = lambda finestra: tuple(cursor)

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(n=1, dt=1 / 60):
        for _ in range(n):
            glfw.poll_events()
            app.dt = dt
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)   # imgui.ini pot tenir-lo en un altre lloc
            imgui.begin('Opcions')
            app.build_ui()
            imgui.end()
            imgui.render()

    # ------------------------------------------------------------ 1. cub de navegacio
    print('== Cub de navegacio (coordenades terrestres ECEF, km: X cap a la longitud 0, Y cap a 90 E, Z cap al nord)')
    print(f'   costat {cub.costat_km:,.0f} km = {cub.costat_km / UA_KM:.4f} UA; radi solar {RADI_SOL_KM:,.0f} km; '
          f'marge {cub.marge_km:,.0f} km = {cub.marge_km / RADI_SOL_KM:.3f} radis solars')
    for k, eix in enumerate('XYZ'):
        print(f'   {eix}: de {cub.minim[k]:,.0f} a {cub.maxim[k]:,.0f} km  (astres: de {cub.extrems_min[k]:,.0f} '
              f'a {cub.extrems_max[k]:,.0f})')
    hores = np.linspace(app.ef.inici, app.ef.final, 451)
    sols = np.array([app.ef.posicions(h)[0] for h in hores])
    llunes = np.array([app.ef.posicions(h)[1] for h in hores])
    dins = (np.all(sols - RADI_SOL_KM >= cub.minim) and np.all(sols + RADI_SOL_KM <= cub.maxim)
            and np.all(llunes >= cub.minim) and np.all(llunes <= cub.maxim))
    ok(dins and abs(np.ptp([cub.maxim - cub.minim])) < 1e-6 * cub.costat_km,
       'el cub conte el Sol (amb el radi), la Lluna i la Terra a tot l\'interval i els tres costats son iguals')

    app.canviar_vista(0)
    centre = (cub.minim + cub.maxim) / 2
    for k, eix in enumerate('XYZ'):
        for signe, nom_cara in ((-1, 'min'), (1, 'max')):
            limit = cub.minim[k] if signe < 0 else cub.maxim[k]
            normal = np.zeros(3)
            normal[k] = signe
            cara = f'{eix} {nom_cara}'
            # teclat: la camera a 1.000 km de la paret mirant cap a fora; W (endavant) i E (amunt) premudes
            p = centre.copy()
            p[k] = limit - signe * 20000.0
            ce.posicio = p
            lat, lon, _ = ce.geodesiques()
            ce.rumb, ce.inclinacio = geodesia.azimut_elevacio(normal + 0.3 * np.roll(normal, 1), lat, lon)
            premudes.update({glfw.KEY_W, glfw.KEY_E})
            coords, altres = [], []
            for _ in range(40):
                fotograma()
                coords.append(ce.posicio[k])
                altres.append(np.delete(ce.posicio, k).copy())
            premudes.clear()
            limit = limit - signe * DISTANCIA_PARET_KM      # la camera s'atura a aquesta distancia
            arribat = coords.index(limit) if limit in coords else None
            ok(arribat is not None and all(c == limit for c in coords[arribat:])
               and np.linalg.norm(altres[-1] - altres[arribat]) > 0,
               f'cara {cara}, teclat: la camera arriba a la paret, s\'hi queda exactament i es continua movent en paral·lel')
            # roda cap a fora, mirant la paret
            ce.posicio = p
            lat, lon, _ = ce.geodesiques()
            ce.rumb, ce.inclinacio = geodesia.azimut_elevacio(normal, lat, lon)
            for _ in range(10):
                app.ratoli.on_scroll(app.window, 0.0, 3.0)
                fotograma()
            ok(ce.posicio[k] == limit and np.all(ce.posicio > cub.minim) and np.all(ce.posicio < cub.maxim),
               f'cara {cara}, roda: s\'atura a la paret')
            # posicio posada directament (com els botons): fora del cub -> a la paret
            q = centre.copy()
            q[k] = limit + signe * 5e7
            ce.posicio = q
            ok(ce.posicio[k] == limit, f'cara {cara}, posicio directa fora del cub: es queda a la paret '
                                       f'(a {DISTANCIA_PARET_KM:.0f} km)')
    for nom_boto, boto in (("Veure l'ombra des de l'espai", app.veure_ombra_des_de_lespai),
                           ('triar una ubicacio', lambda: app.triar_ubicacio(*programa.UBICACIONS[1][1:], programa.UBICACIONS[1][0]))):
        boto()
        fotograma()
        ok(np.all(ce.posicio >= cub.minim) and np.all(ce.posicio <= cub.maxim), f'boto "{nom_boto}": la camera es dins del cub')

    # ------------------------------------------------------------ 2. enquadrar el Sol
    print('\n== Enquadrar el Sol des de la paret de darrere')
    ce.fov = FOV_EXPLORACIO
    for k, eix in enumerate('XYZ'):
        for signe, nom_cara in ((-1, 'min'), (1, 'max')):
            i = int(np.argmin(sols[:, k]) if signe < 0 else np.argmax(sols[:, k]))
            app.hora = hores[i]
            sol = sols[i]
            p = sol.copy()
            p[k] = cub.minim[k] if signe < 0 else cub.maxim[k]
            ce.posicio = p
            lat, lon, _ = ce.geodesiques()
            ce.rumb, ce.inclinacio = geodesia.azimut_elevacio(sol - ce.posicio, lat, lon)
            fotograma(2)
            prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
            disc = prof < 1.0
            d = float(np.linalg.norm(sol - ce.posicio))
            diametre = 2 * math.degrees(math.asin(RADI_SOL_KM / d))
            vora = disc[0].any() or disc[-1].any() or disc[:, 0].any() or disc[:, -1].any()
            ok(disc.any() and not vora,
               f'cara {eix} {nom_cara}: Sol a {d / RADI_SOL_KM:.2f} radis, diametre {diametre:.1f} graus de '
               f'{FOV_EXPLORACIO:.0f}; el disc sencer cap a la imatge ({disc.mean() * 100:.0f} % dels pixels)')

    # ------------------------------------------------------------ 3. ratoli capturat
    print('\n== Ratoli capturat')
    nom, lat, lon = programa.UBICACIONS[1]
    app.triar_ubicacio(lat, lon, nom)
    app.hora = app.model.hores['maxim'] - 0.5
    app.canviar_vista(1)
    co.mirar(200.0, 5.0)
    co.fov = 60.0
    fotograma()
    ulls = app.ulls()
    app.ratoli.capturar()
    fotograma()
    r0, i0 = co.rumb, co.inclinacio
    cursor[0] += 50
    cursor[1] += 20
    fotograma()
    ok(app.ratoli.capturat and abs(co.rumb - (r0 + 50 * SENSIBILITAT)) < 1e-9
       and abs(co.inclinacio - (i0 - 20 * SENSIBILITAT)) < 1e-9 and np.allclose(app.ulls(), ulls),
       f'capturat: 50 i 20 punts de moviment giren {50 * SENSIBILITAT:.1f} i {20 * SENSIBILITAT:.1f} graus; els ulls no es mouen')
    mirada = (co.rumb, co.inclinacio)
    fotograma(60)
    ok((co.rumb, co.inclinacio) == mirada, 'sense moure el ratoli, la mirada no canvia en 60 fotogrames (cap inercia)')
    cursor[1] -= 5000
    fotograma()
    ok(co.inclinacio <= 89.0, f'la mirada vertical es limita a {co.inclinacio:.1f} graus (no es capgira)')
    co.mirar(*mirada)
    app.ratoli.alliberar()
    cursor[:] = [100.0, 100.0]
    fotograma(3)
    ok(not app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada, 'alliberat: moure el cursor no gira la mirada')
    cursor[:] = [700.0, 500.0]
    app.ratoli.capturar()
    fotograma(3)
    ok((co.rumb, co.inclinacio) == mirada, 'tornar a capturar amb el cursor en un altre lloc no fa saltar la mirada')
    app.ratoli.on_focus(app.window, False)
    ok(not app.ratoli.capturat, 'perdre el focus de la finestra allibera el ratoli')

    def clic(px, py, esperar=True):
        io.add_mouse_pos_event(px, py)
        fotograma()
        io.add_mouse_button_event(0, True)
        fotograma()
        io.add_mouse_button_event(0, False)
        fotograma()
        if esperar:
            t = time.time()
            while time.time() - t < 0.45:
                fotograma()
                time.sleep(0.02)

    clic(700, 450)
    ok(app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada,
       "un clic a l'escena captura el ratoli (passat el temps del doble clic), sense girar la mirada")
    app.ratoli.alliberar()
    fotograma(5)
    clic(150, 18)    # la barra del titol del panell (no hi ha cap boto)
    ok(not app.ratoli.capturat and not app.reproduint, 'un clic sobre el panell no captura el ratoli')
    # doble clic a l'exploracio: tria el punt i no captura. El picking del programa llegeix la profunditat
    # de la finestra (ctx.screen); aqui es dibuixa en un framebuffer propi, i es llegeix d'alla
    def punt_sota_cursor():
        mx, my = io.mouse_pos
        px, py = int(mx), H - 1 - int(my)
        d = float(np.frombuffer(objectiu.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'), 'f4')[0])
        return None if d >= 1.0 else ce.desprojectar(px + 0.5, py + 0.5, d, W, H)
    app.punt_sota_cursor = punt_sota_cursor
    app.posar_exploracio_sobre_el_punt()
    app.canviar_vista(0)
    ce.inclinacio = -45.0
    fotograma(3)
    o = app.observador
    clic(W // 2, H // 2, esperar=False)
    clic(W // 2, H // 2)
    ok(not app.ratoli.capturat and app.observador is not o,
       "doble clic a l'exploracio (ratoli lliure): tria el punt d'observacio i no captura")

    # ------------------------------------------------------------ 4. panell
    print('\n== Panell')
    fotograma(5)
    cam, mirada_ce = ce.posicio.copy(), (ce.rumb, ce.inclinacio)
    io.add_mouse_pos_event(80, 80)
    fotograma()
    io.add_mouse_button_event(0, True)
    for i in range(10):
        io.add_mouse_pos_event(80 + 10 * i, 80 + 3 * i)
        fotograma()
    io.add_mouse_button_event(0, False)
    fotograma()
    for _ in range(5):
        app.ratoli.on_scroll(app.window, 0.0, -2.0)
        fotograma()
    ok(np.array_equal(ce.posicio, cam) and (ce.rumb, ce.inclinacio) == mirada_ce and not app.ratoli.capturat,
       'arrossegar i fer rodar sobre el panell no mou ni gira la camera')
    io.add_mouse_pos_event(700, 450)
    fotograma(3)

    # ------------------------------------------------------------ 5. P
    print('\n== Tecla P')
    for vista in (0, 1):
        app.canviar_vista(vista)
        fotograma()
        estat = (app.vista, ce.posicio.copy(), (ce.rumb, ce.inclinacio), co.rumb, co.inclinacio, app.observador, app.hora)
        reproduint = app.reproduint
        io.add_key_event(imgui.Key.KEY_P, True)
        app.dt = 0.0
        fotograma(dt=0.0)
        io.add_key_event(imgui.Key.KEY_P, False)
        fotograma(dt=0.0)
        despres = (app.vista, ce.posicio.copy(), (ce.rumb, ce.inclinacio), co.rumb, co.inclinacio, app.observador, app.hora)
        ok(app.reproduint != reproduint and estat[0] == despres[0] and np.array_equal(estat[1], despres[1])
           and estat[2:] == despres[2:],
           f"P ({'explorar' if vista == 0 else 'observar'}): nomes canvia reproduir/pausar")
        app.reproduir_pausar() if app.reproduint else None

    # ------------------------------------------------------------ 6. roda
    print('\n== Roda')
    for inclinacio in (-25.0, -60.0):
        app.posar_exploracio_sobre_el_punt()
        app.canviar_vista(0)
        ce.inclinacio = inclinacio
        fotograma()
        a0, passos = ce.alcada_sobre_terra(), 0
        while ce.alcada_sobre_terra() < 20000 and passos < 200:
            app.ratoli.on_scroll(app.window, 0.0, -1.0)
            fotograma()
            passos += 1
        ok(passos <= 40, f'mirant a {inclinacio:.0f} graus, de {a0:.1f} km a 20.000 km amb {passos} passos de roda')
    app.posar_exploracio_sobre_el_punt()
    ce.inclinacio = -60.0
    fotograma()
    a0 = ce.alcada_sobre_terra()
    app.ratoli.on_scroll(app.window, 0.0, 25.0)     # un gest molt rapid
    fotograma()
    esperat = a0 * 1.35 ** -3
    # el terra de sota tambe canvia (la camera es mou en la direccio de la mirada): factor 2 de marge.
    # Amb 25 passos sense limit, l'altura quedaria multiplicada per 1,35^-25 = 0,0006
    ok(0.5 * esperat < ce.alcada_sobre_terra() < 2 * esperat,
       f'un gest molt rapid (25 passos en un fotograma) es limita a 3 passos: de {a0:.1f} a '
       f'{ce.alcada_sobre_terra():.2f} km (sense travessar el terra)')
    app.canviar_vista(1)
    co.fov = 60.0
    fotograma()
    ulls = app.ulls()
    app.ratoli.on_scroll(app.window, 0.0, 1.0)
    fotograma()
    ok(abs(co.fov - 60.0 * 0.85) < 1e-9 and np.allclose(app.ulls(), ulls),
       f'observacio: un pas de roda canvia el camp de visio de 60 a {co.fov:.1f} graus i els ulls no es mouen')

    glfw.get_key, glfw.get_cursor_pos = get_key, get_cursor_pos
    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
