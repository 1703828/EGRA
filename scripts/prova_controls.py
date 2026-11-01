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
     la mirada no canvia; el gir no depen dels FPS i es menor amb zoom; la inclinacio es queda a +-89 graus;
     el cursor continua desactivat fotograma rere fotograma. Tab captura i allibera; tornar a capturar, canviar
     de vista o recuperar el focus no fa saltar la mirada; perdre el focus allibera. El clic esquerre no
     captura (arrossegar gira, el doble clic tria el punt); el clic dret a l'escena captura a l'instant, sobre
     el panell no.
  4. Panell: arrossegar i fer rodar sobre el panell no mou ni gira la camera.
  5. P: nomes canvia reproduir/pausar (ni la vista, ni les cameres, ni el punt, ni l'hora en aquell moment).
  6. Roda: passos de roda per anar del terra (3 km) a 20.000 km; en observacio, la roda nomes canvia el camp
     de visio (els ulls no es mouen).
  7. Vista guiada: G hi entra mirant el punt; 40 passos de roda fins a la vista ampla sense acostar-se a menys
     de 20 m del terreny dibuixat ni a la Lluna, i els mateixos passos endavant tornen exactament al punt;
     passos fraccionaris i gestos rapids; la roda no toca la mirada de l'usuari; canviar l'hora o reproduir no
     mou la camera; Recentrar; Mirar l'eclipsi a les tres vistes; canviar d'ubicacio; el panell; V i G.
     Desa captures dels enquadraments a captures/proves/guiat_*.png.
Limitacio: no hi ha ratoli ni trackpad fisics. El moviment del ratoli es simula posant la posicio virtual
del cursor (glfw.set_cursor_pos), els clics i la roda com a esdeveniments; el gest de pessigar no arriba a
GLFW (pla, tasca 12.4).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_controls.py
"""
import math
import os
import sys

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
            imgui.set_next_window_collapsed(False, imgui.Cond.ALWAYS)   # i plegat (Collapsed=1)
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

    def tecla(k):
        io.add_key_event(k, True)
        fotograma()
        io.add_key_event(k, False)
        fotograma()

    tecla(imgui.Key.KEY_TAB)
    fotograma(5)
    ok(app.ratoli.capturat and glfw.get_input_mode(app.window, glfw.CURSOR) == glfw.CURSOR_DISABLED,
       'Tab captura el ratoli a l\'instant i el cursor continua desactivat (CURSOR_DISABLED) 5 fotogrames despres '
       '(abans, el panell el tornava a posar normal a cada fotograma)')
    r0, i0 = co.rumb, co.inclinacio
    cursor[0] += 50
    cursor[1] += 20
    fotograma()
    ok(app.ratoli.capturat and abs(co.rumb - (r0 + 50 * SENSIBILITAT)) < 1e-9
       and abs(co.inclinacio - (i0 - 20 * SENSIBILITAT)) < 1e-9 and (np.linalg.norm(app.ulls() - ulls) < 1e-9),
       f'capturat: 50 punts a la dreta i 20 avall giren {50 * SENSIBILITAT:.1f} graus a la dreta i '
       f'{20 * SENSIBILITAT:.1f} avall; els ulls no es mouen')
    mirada = (co.rumb, co.inclinacio)
    fotograma(60)
    ok((co.rumb, co.inclinacio) == mirada, 'sense moure el ratoli, la mirada no canvia en 60 fotogrames (cap inercia)')
    girs = []
    for dt in (1 / 30, 1 / 144):
        co.mirar(*mirada)
        cursor[0] += 40
        fotograma(dt=dt)
        girs.append(co.rumb - mirada[0])
    ok(abs(girs[0] - girs[1]) < 1e-12, f'el mateix moviment gira el mateix a 30 i a 144 FPS ({girs[0]:.2f} graus)')
    co.fov = 6.0
    co.mirar(*mirada)
    cursor[0] += 40
    fotograma()
    ok(abs(co.rumb - mirada[0] - 40 * SENSIBILITAT * 6.0 / 60.0) < 1e-9,
       'amb zoom x10 el mateix moviment gira 10 vegades menys (la imatge es desplaca igual)')
    co.fov = 60.0
    cursor[1] -= 5000
    fotograma()
    ok(co.inclinacio == 89.0, f'mirada amunt al limit: {co.inclinacio:.1f} graus (no es capgira)')
    cursor[1] += 10000
    fotograma()
    ok(co.inclinacio == -89.0 and np.isfinite(np.array(co.m_view)).all(),
       f'mirada avall al limit: {co.inclinacio:.1f} graus, matriu de vista finita')
    co.mirar(*mirada)
    fotograma()
    tecla(imgui.Key.KEY_TAB)
    cursor[:] = [100.0, 100.0]
    fotograma(3)
    ok(not app.ratoli.capturat and glfw.get_input_mode(app.window, glfw.CURSOR) == glfw.CURSOR_NORMAL
       and (co.rumb, co.inclinacio) == mirada, 'Tab allibera; moure el cursor lliure no gira la mirada')
    cursor[:] = [700.0, 500.0]
    tecla(imgui.Key.KEY_TAB)
    fotograma(3)
    ok((co.rumb, co.inclinacio) == mirada, 'tornar a capturar amb el cursor en un altre lloc no fa saltar la mirada')
    app.canviar_vista(0)
    fotograma(3)
    app.canviar_vista(1)
    fotograma(3)
    ok(app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada,
       'canviar de vista amb el ratoli capturat no fa saltar la mirada')
    app.ratoli.on_scroll(app.window, 0.0, 0.5)
    app.ratoli.on_focus(app.window, False)
    fotograma()
    ok(not app.ratoli.capturat and co.fov == 60.0, 'perdre el focus allibera el ratoli i descarta la roda pendent')
    app.ratoli.on_focus(app.window, True)
    cursor[:] = [300.0, 200.0]
    fotograma(3)
    ok(not app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada,
       'en tornar el focus, el ratoli continua lliure i la mirada no salta')

    def clic(px, py, boto=0, frames_despres=3):
        io.add_mouse_pos_event(px, py)
        fotograma()
        io.add_mouse_button_event(boto, True)
        fotograma()
        io.add_mouse_button_event(boto, False)
        fotograma(frames_despres)

    clic(700, 450, frames_despres=30)
    ok(not app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada,
       "un clic esquerre a l'escena no captura (cap espera ni conflicte amb arrossegar i el doble clic)")
    clic(700, 450, boto=1, frames_despres=1)
    ok(app.ratoli.capturat and (co.rumb, co.inclinacio) == mirada,
       "un clic dret a l'escena captura al mateix fotograma, sense girar la mirada")
    app.ratoli.alliberar()
    fotograma(5)
    clic(150, 18, boto=1)    # la barra del titol del panell
    ok(not app.ratoli.capturat and not app.reproduint, 'un clic dret sobre el panell no captura el ratoli')
    io.add_mouse_pos_event(700, 450)
    fotograma(2)
    io.add_mouse_button_event(0, True)
    for i in range(10):
        io.add_mouse_pos_event(700 + 5 * i, 450)
        fotograma()
    io.add_mouse_button_event(0, False)
    fotograma()
    ok(not app.ratoli.capturat and abs(co.rumb - mirada[0] - 45 * SENSIBILITAT) < 1e-6,
       f'arrossegar a l\'escena (cursor lliure) gira amb la mateixa sensibilitat ({45 * SENSIBILITAT:.2f} graus per 45 punts)')
    co.mirar(*mirada)
    # doble clic a l'exploracio: tria el punt i no captura. El picking del programa llegeix la profunditat
    # de la finestra (ctx.screen); aqui es dibuixa en un framebuffer propi, i es llegeix d'alla
    def punt_sota_cursor(pixel=None):
        mx, my = io.mouse_pos
        px, py = (int(mx), H - 1 - int(my)) if pixel is None else pixel[:2]
        d = float(np.frombuffer(objectiu.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'), 'f4')[0])
        return None if d >= 1.0 else app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
    app.punt_sota_cursor = punt_sota_cursor
    app.detall.preparar = False   # sense descarregues: el detall en navegar el prova prova_detall.py
    app.posar_exploracio_sobre_el_punt()
    app.canviar_vista(0)
    ce.orientar(ce.rumb, -45.0)
    fotograma(3)
    o = app.observador
    clic(W // 2, H // 2, frames_despres=0)
    clic(W // 2, H // 2, frames_despres=30)
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
    ok(abs(co.fov - 60.0 * 0.85) < 1e-9 and (np.linalg.norm(app.ulls() - ulls) < 1e-9),
       f'observacio: un pas de roda canvia el camp de visio de 60 a {co.fov:.1f} graus i els ulls no es mouen')

    # ------------------------------------------------------------ 7. vista guiada
    print("\n== Allunyar-se fins a l'espai (vista guiada)")
    from dades.efemerides import RADI_LLUNA_KM
    from dades.trajectoria import S2, S3, H0_KM
    from basecode.camera_guiada import PAS_RODA
    cg = app.camera_guiada
    if app.ratoli.capturat:
        app.ratoli.alliberar()
    nom, lat, lon = programa.UBICACIONS[1]
    app.triar_ubicacio(lat, lon, nom)
    app.canviar_vista(1)
    fotograma()
    io.add_mouse_pos_event(700, 450)
    tecla(imgui.Key.KEY_G)
    fotograma()
    d0 = cg.posicio - app.ulls()
    dir_ok = math.degrees(math.acos(min(1.0, -float(d0 @ cg.direccio()[0]) / np.linalg.norm(d0))))
    ok(app.vista == 2 and cg.progres == 0.0 and abs(np.linalg.norm(d0) - H0_KM) < 1e-6 and dir_ok < 1e-6,
       f'G entra a la vista guiada: a {np.linalg.norm(d0) * 1000:.0f} m del punt i mirant-lo (enquadrament inicial)')
    inici = cg.posicio.copy()
    marge_terra, marge_lluna, passos = 1e9, 1e9, 0
    estats = []
    while cg.progres < 1.0 and passos < 100:
        app.ratoli.on_scroll(app.window, 0.0, -1.0)
        fotograma()
        passos += 1
        la, lo, al = (float(v) for v in geodesia.geodesiques(cg.posicio))
        marge_terra = min(marge_terra, al - app.altitud_terra_km(la, lo))
        marge_lluna = min(marge_lluna, float(np.linalg.norm(cg.posicio - app.lluna_ecef)) / RADI_LLUNA_KM)
        estats.append(cg.posicio.copy())
    ok(passos == 40, f"roda enrere: del punt a la vista ampla amb {passos} passos (sense salts: un pas cada fotograma)")
    ok(marge_terra >= 0.0199 and marge_lluna > 50,
       f'pel cami, la camera es a {marge_terra * 1000:.0f} m o mes del terreny dibuixat i a {marge_lluna:.0f} radis '
       'lunars o mes de la Lluna')
    for _ in range(passos):
        app.ratoli.on_scroll(app.window, 0.0, 1.0)
        fotograma()
    ok(cg.progres == 0.0 and (np.linalg.norm(cg.posicio - inici) < 1e-9),
       'roda endavant el mateix nombre de passos: torna exactament al punt inicial (sense deriva)')
    for _ in range(20):
        app.ratoli.on_scroll(app.window, 0.0, -0.3)     # lliscar amb dos dits: passos fraccionaris
        fotograma()
    ok(abs(cg.progres - 20 * 0.3 * PAS_RODA) < 1e-12, f'trackpad: 20 passos de 0,3 avancen {cg.progres:.3f} del recorregut')
    p = cg.progres
    app.ratoli.on_scroll(app.window, 0.0, -25.0)
    fotograma()
    ok(abs(cg.progres - p - 3 * PAS_RODA) < 1e-12, 'un gest molt rapid (25 passos en un fotograma) es limita a 3 passos')
    # mirada de l'usuari independent del progres
    tecla(imgui.Key.KEY_TAB)
    cursor[0] += 100
    cursor[1] += 50
    fotograma()
    mirada = (cg.gir, cg.inclinacio)
    ok(abs(cg.gir - 100 * SENSIBILITAT) < 1e-9 and abs(cg.inclinacio + 50 * SENSIBILITAT) < 1e-9,
       f'vista guiada amb el ratoli capturat: gir {cg.gir:.1f} i inclinacio {cg.inclinacio:.1f} graus')
    for _ in range(4):
        app.ratoli.on_scroll(app.window, 0.0, -1.0)
        fotograma()
    fotograma(30)
    ok((cg.gir, cg.inclinacio) == mirada, 'la roda canvia la posicio pero no la mirada de l\'usuari (cap reenquadrament)')
    cursor[1] -= 10000
    fotograma()
    ok(cg.inclinacio == 89.0 and np.isfinite(np.array(cg.m_view)).all(), 'inclinacio al limit de +89 graus, matriu finita')
    tecla(imgui.Key.KEY_TAB)
    # el temps no mou la camera
    pos, h = cg.posicio.copy(), app.hora
    app.hora = h + 1.0
    fotograma(3)
    ok(np.array_equal(cg.posicio, pos) and (cg.gir, cg.inclinacio) == (mirada[0], 89.0),
       "canviar l'hora 1 h: la camera no es mou ni gira (la trajectoria es la de l'ancora)")
    app.reproduir_pausar()
    fotograma(10)
    app.reproduir_pausar()
    ok(np.array_equal(cg.posicio, pos), 'reproduir el temps tampoc mou la camera')
    cg.recentrar()
    fotograma()
    ok(cg.hora_ancora == app.hora and (cg.gir, cg.inclinacio) == (0.0, 0.0) and abs(cg.progres - p - 7 * PAS_RODA) < 1e-12,
       "Recentrar: trajectoria amb l'hora actual i mirada de referencia, sense canviar el progres")
    app.hora = h
    # Mirar l'eclipsi, a les tres vistes
    for vista in (2, 0, 1):
        app.canviar_vista(vista)
        fotograma()
        app.mirar_el_sol()
        fotograma()
        d = app.camera.m_view   # la mirada es la -z de la camera
        mirada_mon = -np.array([d[0][2], d[1][2], d[2][2]])
        error = math.degrees(math.acos(min(1.0, float(mirada_mon @ (app.sol_ecef - app.camera.posicio))
                                           / np.linalg.norm(app.sol_ecef - app.camera.posicio))))
        ok(error < 0.01, f"Mirar l'eclipsi ({programa.ui.VISTES[vista]}): el Sol al centre ({error:.4f} graus); "
                         'la camera no es mou')
    # canviar d'ubicacio a la vista guiada
    app.canviar_vista(2)
    cg.progres = S2
    fotograma()
    nom, lat, lon = programa.UBICACIONS[5]
    app.triar_ubicacio(lat, lon, nom)
    fotograma()
    f, _ = cg.trajectoria.marc(cg.progres)
    ok(cg.progres == S2 and abs(float((app.ulls() - cg.posicio) @ f) / np.linalg.norm(app.ulls() - cg.posicio) - 1) < 1e-9,
       "canviar d'ubicacio a la vista guiada: mateix tram, trajectoria recalculada per al punt nou")
    # sobre el panell la roda no mou la camera
    p = cg.progres
    io.add_mouse_pos_event(80, 80)
    fotograma()
    for _ in range(3):
        app.ratoli.on_scroll(app.window, 0.0, -1.0)
        fotograma()
    ok(cg.progres == p, 'fer rodar sobre el panell no mou la camera guiada')
    io.add_mouse_pos_event(700, 450)
    # V torna a observar; G hi torna amb el mateix progres
    tecla(imgui.Key.KEY_V)
    v_obs = app.vista
    tecla(imgui.Key.KEY_G)
    ok(v_obs == 1 and app.vista == 2 and cg.progres == p, 'V torna a observar; G torna a la vista guiada al mateix lloc')
    # captures dels enquadraments (inspeccio visual): captures/proves/guiat_*.png (carpeta ignorada pel Git)
    from PIL import Image
    carpeta = os.path.join(ARREL, 'captures', 'proves')
    os.makedirs(carpeta, exist_ok=True)
    nom, lat, lon = programa.UBICACIONS[1]
    app.triar_ubicacio(lat, lon, nom)
    app.hora = app.model.hores['maxim']
    cg.recentrar()
    for s, etiqueta in ((0.0, 'prop'), (0.3, 's1'), (S2, 'terra'), (S3, 'terra_lluna'), (1.0, 'sol')):
        cg.progres = s
        fotograma(2)
        img = Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)
        img.save(os.path.join(carpeta, f'guiat_{etiqueta}.png'))
    print(f'   captures a {carpeta}/guiat_*.png')

    glfw.get_key, glfw.get_cursor_pos = get_key, get_cursor_pos
    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
