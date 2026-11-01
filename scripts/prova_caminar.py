"""
Prova del mode "Caminar" de l'exploracio amb el programa real (finestra amagada; el teclat se simula substituint
glfw.get_key i cada fotograma es com els del bucle del programa, amb el panell construit).

  1. Direccio: amb diferents rumbs, W avanca cap al rumb; S enrere; A / D de costat; la mirada no canvia.
  2. Mirar amunt o avall no fa volar ni canvia el desplacament; W+D no es mes rapid que W.
  3. La mateixa distancia a 30, 60 i 144 FPS; un fotograma llarg al programa es limita a 0,1 s.
  4. Seguiment del relleu: pujant i baixant pel pendent mes fort a prop de Picos, els ulls sempre a 1,7 m del
     relleu dibuixat (sense penetrar ni flotar). Per comparar, el vol lliure en baixada queda flotant.
  5. Un pas molt llarg (30 s corrent en una sola crida) es subdivideix: el cami no travessa el relleu, encara
     que la recta entre l'inici i el final si que el travessaria.
  6. Vora de la zona de 5 m (transicio cap al relleu de 200 m): sense esglaons. Mar (l'Escala): la camera
     s'atura a la vora i no hi entra.
  7. Entrar a caminar: des de l'exploracio a ~3 km, baixa en vertical; des de l'espai, no fa res i ho diu;
     "Caminar des del punt d'observacio" posa la camera als ulls.
  8. Sense moviment residual en deixar les tecles, canviar de mode o d'ubicacio, o perdre el focus; E / Q i la
     roda no mouen la camera caminant; si el relleu canvia (exageracio), els ulls el segueixen.
  9. Panell: amb un control del panell actiu, W no mou la camera.
Limitacio: no hi ha teclat ni ratoli fisics; la finestra real l'ha de provar l'equip.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_caminar.py
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
    from dades.observador import UBICACIONS_PROVES
    from dades import geodesia
    from basecode.camera_exploracio import VELOCITAT_CAMINAR_M_S, FACTOR_CORRER

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de caminar', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    ce, io = app.camera_exploracio, imgui.get_io()
    errors = []
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)
    v_km_s = VELOCITAT_CAMINAR_M_S / 1000.0

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
            imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
            imgui.set_next_window_collapsed(False, imgui.Cond.ALWAYS)
            imgui.begin('Opcions')
            app.build_ui()
            imgui.end()
            imgui.render()

    def alcada_ulls_m(p=None):
        p = ce.posicio if p is None else p
        lat, lon, alt = (float(v) for v in geodesia.geodesiques(p))
        return (alt - app.altitud_caminable_km(lat, lon)) * 1000.0

    def horitzontal(p0, p1):
        """(distancia horitzontal en m, azimut en graus) de p0 a p1, al pla horitzontal de p0."""
        lat, lon, _ = (float(v) for v in geodesia.geodesiques(p0))
        est, nord, amunt = geodesia.base_local(lat, lon)
        d = p1 - p0
        h = d - (d @ amunt) * amunt
        return float(np.linalg.norm(h)) * 1000.0, math.degrees(math.atan2(h @ est, h @ nord)) % 360.0

    def amb_tecles(tecles, n, dt=1 / 60):
        premudes.update(tecles)
        fotograma(n, dt)
        premudes.difference_update(tecles)

    def dif_angle(a, b):
        return abs((a - b + 180.0) % 360.0 - 180.0)

    # ------------------------------------------------------------ 1-2. direccio
    print('== Direccio i velocitat (Picos)')
    app.caminar_des_del_punt()
    fotograma(2)
    inici = ce.posicio.copy()
    ok(ce.caminar and app.vista == 0 and (np.linalg.norm(inici - app.ulls()) < 1e-9),
       "Caminar des del punt d'observacio: la camera als ulls de l'observador, caminant")
    pitjor_az, pitjor_d = 0.0, 0.0
    for rumb in (0.0, 37.0, 90.0, 180.0, 263.0, 315.0):
        for tecla, gir in ((glfw.KEY_W, 0.0), (glfw.KEY_S, 180.0), (glfw.KEY_A, -90.0), (glfw.KEY_D, 90.0)):
            ce.posicio = inici
            ce.orientar(rumb, 10.0)
            p0 = ce.posicio.copy()
            amb_tecles({tecla}, 60)
            d, az = horitzontal(p0, ce.posicio)
            pitjor_az = max(pitjor_az, dif_angle(az, rumb + gir))
            pitjor_d = max(pitjor_d, abs(d - VELOCITAT_CAMINAR_M_S))
            if (ce.rumb, ce.inclinacio) != (rumb, 10.0):
                pitjor_az = 999.0
    ok(pitjor_az < 0.05, f'6 rumbs x W/S/A/D: el moviment va cap al rumb, enrere i de costat (error maxim '
                         f'{pitjor_az:.3f} graus) i la mirada no canvia')
    ok(pitjor_d < 0.002, f'1 s caminant = {VELOCITAT_CAMINAR_M_S} m en horitzontal (error maxim {pitjor_d * 1000:.2f} mm)')
    desplacaments = []
    for inc in (-80.0, 0.0, 80.0):
        ce.posicio = inici
        ce.orientar(120.0, inc)
        amb_tecles({glfw.KEY_W}, 60)
        desplacaments.append(ce.posicio - inici)
    ok(max(np.linalg.norm(d - desplacaments[1]) for d in desplacaments) < 1e-12,
       'mirant a -80, 0 i +80 graus el desplacament es identic (no es vola)')
    ce.posicio = inici
    ce.orientar(120.0, 0.0)
    amb_tecles({glfw.KEY_W, glfw.KEY_D}, 60)
    d_diag, az_diag = horitzontal(inici, ce.posicio)
    ok(abs(d_diag - VELOCITAT_CAMINAR_M_S) < 0.002 and dif_angle(az_diag, 165.0) < 0.05,
       f'W+D: {d_diag:.3f} m en 1 s (com W) a 45 graus a la dreta')
    ce.posicio = inici
    amb_tecles({glfw.KEY_W, glfw.KEY_LEFT_SHIFT}, 60)
    d_correr, _ = horitzontal(inici, ce.posicio)
    ok(abs(d_correr - VELOCITAT_CAMINAR_M_S * FACTOR_CORRER) < 0.005, f'Shift: correr a {d_correr:.2f} m/s')

    # ------------------------------------------------------------ 3. FPS
    finals = []
    for fps in (30, 60, 144):
        ce.posicio = inici
        ce.orientar(200.0, 0.0)
        amb_tecles({glfw.KEY_W}, 2 * fps, dt=1 / fps)
        finals.append(ce.posicio.copy())
    dists = [horitzontal(inici, p)[0] for p in finals]
    ok(max(dists) - min(dists) < 0.005 and max(np.linalg.norm(p - finals[1]) for p in finals) < 5e-6,
       f'2 s a 30, 60 i 144 FPS: {dists[0]:.4f}, {dists[1]:.4f} i {dists[2]:.4f} m (finals a < 5 mm)')
    ce.posicio = inici
    amb_tecles({glfw.KEY_W}, 1, dt=5.0)
    d_llarg, _ = horitzontal(inici, ce.posicio)
    ok(d_llarg <= 0.1 * VELOCITAT_CAMINAR_M_S + 1e-6,
       f'un fotograma de 5 s al programa avanca {d_llarg * 100:.0f} cm (dt limitat a 0,1 s: cap salt)')

    # ------------------------------------------------------------ 4. pendent
    print('\n== Seguiment del relleu')
    lat0, lon0 = app.observador.lat, app.observador.lon
    h0 = app.altitud_caminable_km(lat0, lon0)
    pendents = []
    for rumb in range(0, 360, 10):
        q = inici + 0.03 * ce.direccions(lat0, lon0)[0] * 0 + 0.03 * geodesia.base_local(lat0, lon0)[1] * math.cos(math.radians(rumb)) \
            + 0.03 * geodesia.base_local(lat0, lon0)[0] * math.sin(math.radians(rumb))
        la, lo, _ = (float(v) for v in geodesia.geodesiques(q))
        pendents.append(((app.altitud_caminable_km(la, lo) - h0) / 0.03, rumb))
    pendent, rumb_amunt = max(pendents)
    for nom, rumb in (('pujant', rumb_amunt), ('baixant', rumb_amunt + 180.0)):
        ce.posicio = inici
        ce.orientar(rumb, 0.0)
        alcades, z0 = [], float(geodesia.geodesiques(inici)[2])
        for _ in range(int(25 / (1 / 60))):        # 25 s corrent, cada fotograma del programa
            ce.caminar_pas(1.0, 0.0, 1 / 60, correr=True)
            alcades.append(alcada_ulls_m())
        desnivell = (float(geodesia.geodesiques(ce.posicio)[2]) - z0) * 1000.0
        ok(max(abs(a - 1.7) for a in alcades) < 1e-6,
           f'{nom} ({desnivell:+.0f} m en {len(alcades)} fotogrames): els ulls sempre a 1,7 m del relleu dibuixat '
           f'(de {min(alcades):.6f} a {max(alcades):.6f} m)')
    # comparacio: el vol lliure (sense seguiment) en baixada
    ce.caminar = False
    ce.posicio = inici
    ce.orientar(rumb_amunt + 180.0, 0.0)
    for _ in range(60):
        ce.moure(1, 0, 0, 1 / 60)
    flota = alcada_ulls_m()
    ok(flota > 3.0, f'per comparar, el vol lliure en baixada: {horitzontal(inici, ce.posicio)[0]:.0f} m '
                    f'i queda a {flota:.0f} m del terra (flota: per aixo cal el mode Caminar)')
    ce.caminar = True

    # ------------------------------------------------------------ 5. pas llarg
    triat = None
    for rumb in range(0, 360, 15):
        ce.posicio = inici
        ce.orientar(float(rumb), 0.0)
        p_ini = ce.posicio.copy()
        cami = ce.caminar_pas(1.0, 0.0, 30.0, correr=True)
        recta = [p_ini + t * (cami[-1] - p_ini) for t in np.linspace(0, 1, 201)[1:-1]]
        if min(alcada_ulls_m(p) for p in recta) < 0:
            triat = (rumb, cami, min(alcada_ulls_m(p) for p in recta))
            break
    if triat is None:
        ok(False, 'no s\'ha trobat cap direccio amb una carena per a la prova del pas llarg')
    else:
        rumb, cami, sota = triat
        mitjos = [(a + b) / 2 for a, b in zip(cami[:-1], cami[1:])]
        minim = min(alcada_ulls_m(p) for p in mitjos)
        ok(minim > 1.0, f'un pas de 30 s corrent ({horitzontal(cami[0], cami[-1])[0]:.0f} m, rumb {rumb}) es fa en '
                        f'{len(cami) - 1} passos; el cami queda a {minim:.2f} m o mes del relleu (la recta directa '
                        f'hi quedaria {-sota:.0f} m per sota)')

    # ------------------------------------------------------------ 6. vora de la zona i mar
    zona = app.zona
    lon_v, lat_v = zona.a_latlon.transform(*zona.utm_de_uv(0.995, 0.5))
    h_v = app.altitud_caminable_km(lat_v, lon_v)
    ce.posicio = geodesia.ecef(lat_v, lon_v, h_v + 0.0017)
    ce.orientar(90.0, 0.0)
    alcades, dins = [], []
    for _ in range(400):                       # 180 m cap a l'est (des de ~100 m de la vora): surt de la zona
        p_ant = ce.posicio.copy()
        ce.caminar_pas(1.0, 0.0, 0.1, correr=True)
        alcades.append(alcada_ulls_m())
        la, lo, _ = (float(v) for v in geodesia.geodesiques(ce.posicio))
        dins.append((zona.conte(la, lo), p_ant, ce.posicio.copy()))
    creuament = next(((a, b) for (z, a, b) in dins if not z), None)
    # salt a la frontera: s'hi arriba per biseccio (0,1 mm) i es compara l'altura dibuixada a +-5 mm
    def h_a(q):
        la, lo, _ = (float(v) for v in geodesia.geodesiques(q))
        return app.altitud_caminable_km(la, lo), zona.conte(la, lo)
    a, b = creuament
    for _ in range(40):
        m = (a + b) / 2
        a, b = (m, b) if h_a(m)[1] else (a, m)
    u = (b - a) / np.linalg.norm(b - a) if np.linalg.norm(b - a) > 0 else (creuament[1] - creuament[0]) / np.linalg.norm(creuament[1] - creuament[0])
    (h1, z1), (h2, z2) = h_a(a - 5e-6 * u), h_a(a + 5e-6 * u)
    salt_cm = abs(h2 - h1) * 1e5
    ok(z1 and not z2 and max(abs(x - 1.7) for x in alcades) < 1e-6 and salt_cm < 1.0,
       f'sortint de la zona de 5 m cap al relleu de 200 m: ulls sempre a 1,7 m i, just a la frontera, '
       f'{salt_cm:.3f} cm de diferencia en 1 cm (cap esglao)')

    nom, lat, lon = UBICACIONS_PROVES[2]       # l'Escala, a la costa
    app.triar_ubicacio(lat, lon, nom)
    fotograma(2)
    ok((np.linalg.norm(ce.posicio - app.ulls()) < 1e-9) and ce.caminar,
       "caminant, triar una ubicacio de la llista posa la camera als ulls del punt nou")
    ce.orientar(90.0, 0.0)
    recorregut = 0.0
    app.edificis.visible = False          # aqui es prova la vora del relleu (els edificis, a prova_obstacles.py)
    for _ in range(200):                       # fins a 2,7 km cap al mar (est)
        p0 = ce.posicio.copy()
        ce.caminar_pas(1.0, 0.0, 3.0, correr=True)
        recorregut += horitzontal(p0, ce.posicio)[0]
        if ce.a_la_vora:
            break
    p_vora = ce.posicio.copy()
    ce.caminar_pas(1.0, 0.0, 1.0, correr=True)
    la, lo, _ = (float(v) for v in geodesia.geodesiques(ce.posicio))
    app.edificis.visible = True
    ok(ce.a_la_vora and (np.linalg.norm(ce.posicio - p_vora) < 1e-9) and app.altitud_caminable_km(la, lo) is not None
       and abs(alcada_ulls_m() - 1.7) < 1e-6,
       f"l'Escala cap a l'est: s'atura a la costa despres de {recorregut:.0f} m, sobre terra, i no entra al mar")

    # ------------------------------------------------------------ 7. entrar a caminar
    print('\n== Entrar i sortir del mode Caminar')
    nom, lat, lon = UBICACIONS_PROVES[1]
    ce.caminar = False
    app.triar_ubicacio(lat, lon, nom)
    fotograma()
    p0 = ce.posicio.copy()
    alt0 = alcada_ulls_m() / 1000.0
    fet = app.passar_a_caminar()
    fotograma()
    ok(fet and horitzontal(p0, ce.posicio)[0] < 1e-3 and abs(alcada_ulls_m() - 1.7) < 1e-6,
       f'des de {alt0:.1f} km sobre el terra: baixa en vertical (0 mm en horitzontal) fins als ulls ({app.avis_caminar})')
    ce.caminar = False
    app.veure_ombra_des_de_lespai()
    fotograma()
    p0 = ce.posicio.copy()
    fet = app.passar_a_caminar()
    fotograma()
    ok(not fet and not ce.caminar and np.array_equal(ce.posicio, p0) and 'Massa amunt' in app.avis_caminar,
       f"des de l'espai no passa a caminar ni es mou: \"{app.avis_caminar}\"")
    app.caminar_des_del_punt()
    fotograma()
    ok(ce.caminar and (np.linalg.norm(ce.posicio - app.ulls()) < 1e-9),
       "accio explicita \"Caminar des del punt d'observacio\": als ulls de l'observador")

    # ------------------------------------------------------------ 8. sense moviment residual
    inici = ce.posicio.copy()
    amb_tecles({glfw.KEY_W}, 30)
    p = ce.posicio.copy()
    fotograma(30)
    ok((np.linalg.norm(ce.posicio - p) < 1e-9), 'deixar anar W: la camera s\'atura al mateix fotograma (cap inercia)')
    ce.caminar = False
    fotograma(10)
    ok((np.linalg.norm(ce.posicio - p) < 1e-9), 'passar a vol lliure: la camera no es mou')
    app.passar_a_caminar()
    fotograma(10)
    ok((np.linalg.norm(ce.posicio - p) < 1e-9), 'tornar a caminar al mateix lloc: tampoc')
    premudes.add(glfw.KEY_W)
    app.ratoli.on_focus(app.window, False)
    fotograma(30)
    sense_focus = ce.posicio.copy()
    app.ratoli.on_focus(app.window, True)
    fotograma(30)
    premudes.discard(glfw.KEY_W)
    ok((np.linalg.norm(sense_focus - p) < 1e-9) and not (np.linalg.norm(ce.posicio - p) < 1e-9),
       'sense el focus, W (encara que sembli premuda) no mou la camera; amb el focus, si')
    p = ce.posicio.copy()
    amb_tecles({glfw.KEY_E}, 30)
    amb_tecles({glfw.KEY_Q}, 30)
    for _ in range(3):
        app.ratoli.on_scroll(app.window, 0.0, -2.0)
        fotograma()
    ok((np.linalg.norm(ce.posicio - p) < 1e-9), 'caminant, E / Q i la roda no separen la camera del terra')
    for t in app.terrenys():
        t.exaggeration = 3.0
    fotograma(2)
    alcada_exag = alcada_ulls_m()
    for t in app.terrenys():
        t.exaggeration = 1.0
    fotograma(2)
    ok(abs(alcada_exag - 1.7) < 1e-6 and abs(alcada_ulls_m() - 1.7) < 1e-6,
       "si el relleu canvia (exageracio x3 i tornar a 1), els ulls el segueixen")
    app.canviar_vista(1)
    amb_tecles({glfw.KEY_W}, 30)
    app.canviar_vista(0)
    ok((np.linalg.norm(ce.posicio - p) < 1e-9), 'a la vista d\'observacio, W no mou la camera d\'exploracio')

    # ------------------------------------------------------------ 9. panell
    io.add_mouse_pos_event(150, 18)            # barra del titol del panell
    fotograma()
    io.add_mouse_button_event(0, True)
    fotograma()
    actiu = imgui.is_any_item_active()
    amb_tecles({glfw.KEY_W}, 30)
    io.add_mouse_button_event(0, False)
    fotograma()
    ok(actiu and (np.linalg.norm(ce.posicio - p) < 1e-9), 'amb un control del panell actiu, W no mou la camera')
    io.add_mouse_pos_event(700, 450)
    fotograma()

    glfw.get_key = get_key
    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
