"""
Prova dels edificis com a obstacles (dades/obstacles.py) i dels punts d'observacio exteriors.

1. Geometries de prova (m): contra una paret el cos s'atura a 0,3 m; en diagonal hi llisca; un pas de 100 m no
   la travessa; passa una cantonada convexa sense quedar-s'hi enganxat; en una cantonada concava, empenyent
   60 fotogrames, la posicio no canvia (cap vibracio); no passa per una escletxa de 0,2 m ni per dos edificis
   que es toquen per una cantonada; el punt exterior d'un edifici amb pati es al carrer, no al pati tancat.
2. Contorns reals del Valles: 3.000 moviments a l'atzar (fins a 50 m d'un sol cop, com un fotograma molt llarg)
   des de punts exteriors a prop de la UAB, Cerdanyola i Montmelo: cap acaba dins d'un edifici ni a menys de
   0,3 m d'una facana. Temps per moviment.
3. Programa real (finestra amagada): a les sis ubicacions els ulls son a l'exterior i, mirant amunt, es veu el
   cel; la coordenada de referencia dels quatre punts desplacats es dins d'un edifici. Caminant cap a l'ajuntament de Cerdanyola
   (de cara, en diagonal, corrent i amb un pas de 30 s) no s'hi entra; en vol lliure no s'entra per la facana
   pero es pot baixar sobre la coberta i passar-hi per sobre; recuperacio si la camera queda dins; passar a
   caminar damunt d'un edifici; doble clic sobre un terrat; edificis amagats i tornats a mostrar.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_obstacles.py
"""
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import shapely  # noqa: E402

from dades.obstacles import Obstacles, RADI_COS_M  # noqa: E402

R = RADI_COS_M
errors = []


def ok(condicio, text):
    print(('OK    ' if condicio else 'FALLA ') + text)
    if not condicio:
        errors.append(text)


def geometries():
    print('== Geometries de prova (m)')
    o = Obstacles([shapely.box(0, 0, 10, 10)], [100.0])
    x, y, xoc = o.moure(-5, 5, 5, 5)
    ok(abs(x + R) < 1e-6 and abs(y - 5) < 1e-9 and xoc, f'de cara a la paret: s\'atura a {-x:.3f} m (radi {R})')
    x, y, _ = o.moure(-5, 2, 0, 7)
    ok(abs(x + R) < 1e-6 and y > 6.9, f'en diagonal (45 graus): llisca per la paret fins a y = {y:.2f}')
    x, y, _ = o.moure(-5, 5, 95, 5)
    ok(abs(x + R) < 1e-6, 'un sol pas de 100 m contra la paret: no la travessa')
    x, y, _ = o.moure(-R, 5, -R, 15)
    ok(abs(x + R) < 1e-6 and abs(y - 15) < 1e-6, 'resseguint la paret passa la cantonada convexa sense enganxar-se')
    # cantonada concava: dos edificis en L
    o = Obstacles([shapely.box(0, 0, 10, 10), shapely.box(-10, 10, 0, 20)], [100.0, 100.0])
    p, posicions = (-3.0, 7.0), []
    for _ in range(120):                         # ~54 fotogrames per arribar-hi i 66 empenyent
        x, y, _ = o.moure(*p, p[0] + 0.05, p[1] + 0.05)
        p = (x, y)
        posicions.append(p)
    final = np.array(posicions[-60:])
    ok(np.abs(final - final[0]).max() < 1e-9 and abs(p[0] + R) < 1e-6 and abs(p[1] - 10 + R) < 1e-6,
       f'cantonada concava, 60 fotogrames empenyent-hi: quiet a ({p[0]:.3f}, {p[1]:.3f}), cap vibracio')
    o = Obstacles([shapely.box(0, 0, 10, 10), shapely.box(10.2, 0, 20, 10)], [100.0, 100.0])
    x, y, _ = o.moure(10.1, -5, 10.1, 15)
    ok(y < 0, f'escletxa de 0,2 m entre dos edificis: no hi passa (s\'atura a y = {y:.2f})')
    o = Obstacles([shapely.box(0, 0, 10, 10), shapely.box(10, 10, 20, 20)], [100.0, 100.0])
    x, y, _ = o.moure(12, 8, 8, 12)
    ok(math.hypot(x - 8, y - 12) > 1.0 and o.dins(x, y) is None, 'dos edificis que es toquen per la cantonada: no s\'hi passa en diagonal')
    pati = shapely.Polygon(shapely.box(0, 0, 30, 30).exterior.coords, [shapely.box(10, 10, 20, 20).exterior.coords])
    o = Obstacles([pati], [100.0])
    x, y, d, marge = o.punt_exterior(9, 15)
    ok(x <= -marge + 1e-6, f'punt dins d\'un edifici amb pati tancat: el punt exterior es al carrer ({x:.1f}, {y:.1f}), '
                           f'no al pati (marge {marge} m)')


def contorns_reals():
    print('\n== Contorns reals del Valles (Catastro)')
    from dades.edificis import llegir_zona
    from dades.observador import UBICACIONS
    parts = llegir_zona('valles')
    if parts is None:
        print('   (sense dades del Valles: python scripts/descarregar_edificis.py)')
        return
    o = Obstacles(parts.geometry.values, (parts['plantes'] * 3.0).values)
    rng = np.random.default_rng(7)
    dolents, temps, xocs = 0, [], 0
    for nom, lat, lon in UBICACIONS[3:]:
        cx, cy = o.utm(lat, lon)
        n = 0
        while n < 1000:
            x0, y0 = cx + rng.uniform(-250, 250), cy + rng.uniform(-250, 250)
            if o.separacio(x0, y0) < R:
                continue
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.1, 50.0)
            t = time.perf_counter()
            x, y, xoc = o.moure(x0, y0, x0 + d * math.cos(a), y0 + d * math.sin(a))
            temps.append(time.perf_counter() - t)
            xocs += xoc
            if o.dins(x, y) is not None or o.separacio(x, y) < R - 1e-3:
                dolents += 1
            n += 1
    ok(dolents == 0, f'3.000 moviments a l\'atzar (fins a 50 m d\'un cop, {xocs} contra edificis): cap acaba dins '
                     f'ni a menys de {R} m d\'una facana')
    t = np.array(temps) * 1000
    print(f'   temps per moviment: mediana {np.median(t):.2f} ms, percentil 95 {np.percentile(t, 95):.1f} ms '
          f'(caminant, un fotograma avanca com a molt 0,45 m)')


def programa_real():
    print('\n== Programa real')
    import glfw
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    from dades.observador import ALCADA_ULLS_KM
    from basecode.camera_exploracio import RADI_VOL_M, MARGE_COBERTA_M

    W, H = 640, 480
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova dels obstacles', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    co, ce = app.camera_observador, app.camera_exploracio

    def fotograma(n=1, dt=1 / 60):
        for _ in range(n):
            glfw.poll_events()
            app.dt = dt
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.begin('Opcions')
            app.build_ui()
            imgui.end()
            imgui.render()

    def cel_amunt():
        """Fraccio de pixels de cel (sense res dibuixat) mirant amunt des dels ulls de l'observador."""
        app.canviar_vista(1)
        co.mirar(0.0, 89.0)
        co.fov = 60.0
        fotograma(2)
        prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4')
        return float((prof >= 1.0).mean())

    for nom, lat, lon in programa.UBICACIONS:
        app.triar_ubicacio(lat, lon, nom)
        o = app.observador
        obs = app.edificis.obstacles if app.edificis is not None else None
        sep = obs.separacio(*obs.utm(o.lat, o.lon)) if obs else float('inf')
        cel = cel_amunt()
        text = f'{nom}: ulls a {o.desplacament_m:.1f} m del lloc triat, a {min(sep, 99):.1f} m de la facana mes propera; ' \
               f'mirant amunt, {cel * 100:.0f} % de cel'
        if o.desplacament_m > 0:
            # la referencia es dins d'un edifici. (Abans de la F20, des d'alla mirant amunt es veia la coberta per
            # dins, 0 % de cel; ara les cares del darrere es descarten i des de dins no es veu: la camera ja no hi
            # pot quedar.)
            dins_ref = obs.dins(*obs.utm(o.lat_ref, o.lon_ref)) is not None
            text += f' (la referencia es dins d\'un edifici: {dins_ref})'
            ok(sep >= 2.99 and cel > 0.5 and dins_ref and o.desplacament_m < 30, text)
        else:
            ok(sep >= RADI_COS_M and cel > 0.5, text)

    # caminar cap a l'ajuntament de Cerdanyola
    nom, lat, lon = programa.UBICACIONS[3]
    app.triar_ubicacio(lat, lon, nom)
    app.caminar_des_del_punt()
    fotograma()
    obs = app.edificis.obstacles
    o = app.observador
    az, _ = geodesia.azimut_elevacio(geodesia.ecef(o.lat_ref, o.lon_ref, 0) - geodesia.ecef(o.lat, o.lon, 0), o.lat, o.lon)
    inici = ce.posicio.copy()

    def estat():
        la, lo, _ = ce.geodesiques()
        x, y = obs.utm(la, lo)
        return obs.separacio(x, y), obs.dins(x, y) is not None

    for gir, nom_cas in ((0.0, 'de cara'), (40.0, 'en diagonal (40 graus)')):
        ce.posicio = inici
        ce.orientar(az + gir, 0.0)
        pitjor, dins, xoc = 99.0, False, False
        for _ in range(300):                      # 30 s corrent amb fotogrames lents (dt = 0,1 s)
            ce.caminar_pas(1.0, 0.0, 0.1, correr=True)
            s, d = estat()
            pitjor, dins, xoc = min(pitjor, s), dins or d, xoc or ce.contra_edifici
        ok(xoc and not dins and pitjor >= RADI_COS_M - 1e-3,
           f'caminant {nom_cas} cap a l\'ajuntament, 30 s corrent: topa i no hi entra (minim {pitjor:.3f} m de la facana)')
    ce.posicio = inici
    ce.orientar(az, 0.0)
    cami = ce.caminar_pas(1.0, 0.0, 30.0, correr=True)
    seps = [obs.separacio(*obs.utm(*(float(v) for v in geodesia.geodesiques(p)[:2]))) for p in cami]
    ok(min(seps) >= RADI_COS_M - 1e-3, f'un sol pas de 30 s (135 m) cap a la facana: cap punt del cami a menys de '
                                       f'{RADI_COS_M} m ({min(seps):.3f} m)')

    # vol lliure: per la facana no, per sobre de la coberta si
    ce.caminar = False
    ce.posicio = inici + 0.001 * geodesia.base_local(o.lat, o.lon)[2]        # 2,7 m sobre el terra
    ce.orientar(az, 0.0)
    for _ in range(120):
        ce.moure(1, 0, 0, 1 / 60)
    la, lo, al = ce.geodesiques()
    x, y = obs.utm(la, lo)
    ok(obs.dins(x, y) is None and obs.separacio(x, y, al * 1000 - MARGE_COBERTA_M) >= RADI_VOL_M - 1e-3,
       'vol lliure a 2,7 m del terra cap a la facana: no hi entra')
    x_r, y_r = obs.utm(o.lat_ref, o.lon_ref)
    i = obs.dins(x_r, y_r)
    sostre = obs.coberta[i] / 1000.0
    ce.posicio = geodesia.ecef(o.lat_ref, o.lon_ref, sostre + 0.02)          # 20 m sobre la coberta
    for _ in range(120):
        ce.moure(0, 0, -1, 1 / 60)                                          # Q
    _, _, al = ce.geodesiques()
    ok(abs(al * 1000 - (obs.coberta[i] + MARGE_COBERTA_M)) < 0.01,
       f'vol lliure baixant (Q) sobre la coberta: s\'atura a {(al - sostre) * 1000:.2f} m del terrat')
    p0 = ce.posicio.copy()
    for _ in range(30):
        ce.moure(1, 0, 0, 1 / 60)
    _, _, al2 = ce.geodesiques()
    ok(np.linalg.norm(ce.posicio - p0) > 0.005 and abs(al2 - al) < 1e-5,
       'i hi pot passar per sobre en horitzontal (sense que la coberta el faci fora)')

    # recuperacio, passar a caminar damunt d'un edifici, doble clic sobre un terrat
    ce.caminar = True
    ce.posicio = geodesia.ecef(o.lat_ref, o.lon_ref, app.altitud_terra_km(o.lat_ref, o.lon_ref) + ALCADA_ULLS_KM)
    app.canviar_vista(0)
    fotograma()
    s, d = estat()
    ok(not d and s >= RADI_COS_M - 1e-3, f'camera caminant dins de l\'edifici: al fotograma seguent, fora ({app.avis_caminar})')
    ce.caminar = False
    ce.posicio = geodesia.ecef(o.lat_ref, o.lon_ref, sostre + 0.05)
    app.passar_a_caminar()
    s, d = estat()
    ok(ce.caminar and not d and s >= RADI_COS_M - 1e-3, f'passar a caminar damunt de l\'edifici: {app.avis_caminar}')
    app.triar_punt(o.lat_ref, o.lon_ref)
    o2 = app.observador
    ok(o2.desplacament_m > 0 and obs.separacio(*obs.utm(o2.lat, o2.lon)) >= 2.99,
       f'doble clic sobre el terrat (o un punt dins): els ulls al carrer, a {o2.desplacament_m:.1f} m')

    # edificis amagats: es poden travessar (com es veu); en tornar-los a mostrar, recuperacio
    app.caminar_des_del_punt()
    ce.orientar(az, 0.0)
    app.edificis.visible = False
    d_amagats = False
    for _ in range(200):                          # fins que es dins de l'edifici
        ce.caminar_pas(1.0, 0.0, 0.1, correr=True)
        _, d_amagats = estat()
        if d_amagats:
            break
    app.edificis.visible = True
    fotograma()
    s, d = estat()
    ok(d_amagats and not d and s >= RADI_COS_M - 1e-3,
       'edificis amagats: es poden travessar; en tornar-los a mostrar, la camera surt a fora')
    app._shutdown()


if __name__ == '__main__':
    geometries()
    contorns_reals()
    programa_real()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    sys.exit(1 if errors else 0)
