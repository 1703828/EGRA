"""
Prova del cel, de la llum de l'atmosfera i de l'aspecte dels edificis amb el programa real (finestra amagada).

1. El shader del cel (cel.frag) i el model de la CPU (dades/atmosfera.py) donen el mateix color en 40 direccions
   (diferencia per la interpolacio de la textura de baixa resolucio i el mig float).
2. El cel no tapa res: amb el cel i sense, els pixels on hi ha objectes (el Sol, la Lluna, el terreny, els edificis)
   son identics, i el disc del Sol te els mateixos pixels.
3. Continuitat: de C1 - 30 min fins a 20 min despres de la posta, minut a minut, cap salt de color del cel ni del
   terreny entre dos minuts seguits; cap pixel de cel amb un canal saturat i un altre fosc (color pur).
4. Eclipsi i posta: a Picos (totalitat), el zenit es fosc i l'horitzo encara te llum (l'atmosfera de fora de
   l'ombra); en una posta normal (el mateix lloc, el Sol a la mateixa elevacio sense Lluna) el zenit es clar.
5. Edificis (Vic): totes les cobertes miren amunt i les facanes cap a fora del contorn (es poden descartar les
   cares del darrere); colors de coberta de l'ortofoto.
6. Temps per fotograma a 1280 x 860 i a 2560 x 1720 (pantalla Retina), amb cel i edificis i sense.
Captures a captures/proves/cel_*.png.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_cel.py
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

errors = []


def ok(condicio, text):
    print(('OK    ' if condicio else 'FALLA ') + text)
    if not condicio:
        errors.append(text)


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades.observador import UBICACIONS_PROVES
    from dades import geodesia, atmosfera
    from PIL import Image

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova del cel', use_ui_panel=True)
    fbs = {}

    def fotograma(n=1, mida=(W, H)):
        if mida not in fbs:
            fbs[mida] = app.ctx.simple_framebuffer(mida)
        for _ in range(n):
            glfw.poll_events()
            app.dt = 1 / 60
            app.ui_renderer.new_frame()
            imgui.new_frame()
            fbs[mida].use()
            app.ctx.viewport = (0, 0, *mida)
            app.render()
            imgui.render()
        app.ctx.finish()
        fb = fbs[mida]
        color = np.frombuffer(fb.read(components=3), 'u1').reshape(mida[1], mida[0], 3)[::-1] / 255.0
        prof = np.frombuffer(fb.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(mida[1], mida[0])[::-1]
        return color, prof

    carpeta = os.path.join(ARREL, 'captures', 'proves')
    os.makedirs(carpeta, exist_ok=True)
    co = app.camera_observador
    nom, lat, lon = UBICACIONS_PROVES[1]                     # Vic
    app.triar_ubicacio(lat, lon, nom)
    app.canviar_vista(1)
    m = app.model

    # ------------------------------------------------------------ 1. GPU = CPU
    print('== Cel: shader contra el model de la CPU (Vic)')
    pitjor = 0.0
    for h in (14.5, m.hores['c1'] + 0.3, m.hores['maxim']):
        app.hora = h
        az, el = m.sol(h, refraccio=False)
        co.mirar(az + 30, max(el, 0) + 15)
        co.fov = 60.0
        color, prof = fotograma(2)
        rng = np.random.default_rng(3)
        cam = app.camera
        rot = np.array(cam.m_view.to_list())[:3, :3]       # files = columnes de la matriu glm
        for _ in range(40 // 3 + 1):
            px, py = int(rng.uniform(20, W - 20)), int(rng.uniform(20, H * 0.45))
            if prof[py, px] < 1.0:
                continue
            ndc = np.array([2 * (px + 0.5) / W - 1, 1 - 2 * (py + 0.5) / H])
            d_cam = np.array([ndc[0] / cam.m_proj[0][0], ndc[1] / cam.m_proj[1][1], -1.0])
            d = rot @ d_cam                                    # transposada de la rotacio de la vista
            d /= np.linalg.norm(d)
            cpu = atmosfera.color_cel(cam.posicio, d, app.sol_ecef, app.lluna_ecef, app.radi_sol_km,
                                      app.radi_lluna_km, app.alcada_camera_km, 1.0 - app.tapada_camera)
            pitjor = max(pitjor, float(np.abs(cpu - color[py, px]).max()))
    ok(pitjor < 0.04, f'el color del cel a la pantalla coincideix amb el model de la CPU (diferencia maxima '
                      f'{pitjor * 255:.1f}/255; textura de 1/4 interpolada)')

    # ------------------------------------------------------------ 2. el cel no tapa res
    app.hora = m.hores['maxim'] - 0.05
    az, el = m.sol(app.hora, refraccio=False)
    co.mirar(az, el)
    co.fov = 3.0                                               # el disc del Sol (amb la Lluna) gran
    amb, prof_amb = fotograma(2)
    app.cel.visible = False
    sense, prof_sense = fotograma(2)
    app.cel.visible = True
    objectes = prof_amb < 1.0
    ok(np.array_equal(prof_amb, prof_sense) and np.array_equal(amb[objectes], sense[objectes]),
       f'amb el cel i sense, els {objectes.sum()} pixels amb objectes (Sol, Lluna, terreny, edificis) son identics')

    # ------------------------------------------------------------ 3. continuitat
    co.fov = 60.0
    h0, h1 = m.hores['c1'] - 0.5, (m.hores['posta'] or m.hores['c4']) + 1 / 3
    salt_cel = salt_terra = 0.0
    ant, purs = None, 0
    for h in np.arange(h0, h1, 1 / 60):
        app.hora = float(h)
        az, el = m.sol(app.hora, refraccio=False)
        co.mirar(az, 8.0)
        color, prof = fotograma(1)
        cel = color[prof >= 1.0].mean(axis=0)
        terra = color[prof < 1.0].mean(axis=0)
        purs += int(((color.max(axis=2) > 0.999) & (color.min(axis=2) < 0.4) & (prof >= 1.0)).sum())
        if ant is not None:
            if float(np.abs(cel - ant[0]).max()) > salt_cel:
                on = (app.hora, el, 1.0 - app.tapada_camera, app.halo.visible, app.halo.intensitat)
            salt_cel = max(salt_cel, float(np.abs(cel - ant[0]).max()))
            salt_terra = max(salt_terra, float(np.abs(terra - ant[1]).max()))
        ant = (cel, terra)
    # el minut amb el canvi mes gran, en passos de 10 s: si el canvi es continu, cada pas en fa ~1/6
    passos = []
    ant_f = None
    for h in np.linspace(on[0] - 1 / 60, on[0], 7):
        app.hora = float(h)
        az, el = m.sol(app.hora, refraccio=False)
        co.mirar(az, 8.0)
        color, prof = fotograma(1)
        cel_f = color[prof >= 1.0].mean(axis=0)
        if ant_f is not None:
            passos.append(float(np.abs(cel_f - ant_f).max()))
        ant_f = cel_f
    continu = max(passos) <= 0.4 * max(sum(passos), 1e-9)
    ok(salt_terra < 0.04 and (salt_cel < 0.04 or continu),
       f'minut a minut durant {(h1 - h0) * 60:.0f} min: canvi maxim del color mitja del cel {salt_cel * 255:.1f}/255 '
       f'i del terreny {salt_terra * 255:.1f}/255; el canvi mes gran, en passos de 10 s: '
       f'{", ".join(f"{x * 255:.1f}" for x in passos)} (continu, no un salt)')
    print(f'   (salt mes gran del cel a {programa.eclipse_data.hora_local(on[0])}: Sol a {on[1]:.2f} graus, '
          f'visible {on[2]:.3f}, halo {on[3]} {on[4]:.3f})')
    ok(purs == 0, f'cap pixel de cel amb un canal saturat i un altre fosc ({purs})')

    # ------------------------------------------------------------ 4. totalitat contra posta (Picos)
    nom, lat, lon = UBICACIONS_PROVES[0]
    app.triar_ubicacio(lat, lon, nom)
    m = app.model
    t = (m.hores['c2'] + m.hores['c3']) / 2
    app.hora = t
    p = app.ulls()
    _, nord, amunt = geodesia.base_local(lat, lon)
    sol, lluna = app.ef.posicions(t)
    vis = 1.0 - m.fraccio_tapada(t)

    def lum(sol_, lluna_, d, visible):
        return float(atmosfera.color_cel(p, d, sol_, lluna_, app.radi_sol_km, app.radi_lluna_km,
                                         app.alcada_camera_km, visible) @ atmosfera.LUMA)
    az_s, el_s = m.sol(t, refraccio=False)
    contra = -(math.sin(math.radians(az_s)) * geodesia.base_local(lat, lon)[0] + math.cos(math.radians(az_s)) * nord)
    hor = math.cos(math.radians(3)) * contra + math.sin(math.radians(3)) * amunt
    lluny = sol + 1e9 * amunt                                       # la Lluna fora: una posta normal
    zen_t, hor_t = lum(sol, lluna, amunt, vis), lum(sol, lluna, hor, vis)
    zen_p, hor_p = lum(sol, lluny, amunt, 1.0), lum(sol, lluny, hor, 1.0)
    ok(zen_t < 0.5 * zen_p and hor_t > 1.5 * zen_t,
       f'Picos a la totalitat (Sol a {el_s:.1f} graus): zenit {zen_t:.3f}, horitzo oposat {hor_t:.3f}; posta normal amb '
       f'el Sol a la mateixa altura: zenit {zen_p:.3f}, horitzo {hor_p:.3f} (el zenit fosc i l\'horitzo encara amb llum: '
       'no es una posta)')
    for nom_c, gir, el_c in (('totalitat_sol', 0, el_s + 4), ('totalitat_contra', 180, 8)):
        co.mirar(az_s + gir, el_c)
        color, _ = fotograma(2)
        Image.fromarray((color * 255).astype('u1')).save(os.path.join(carpeta, f'cel_picos_{nom_c}.png'))

    # ------------------------------------------------------------ 5. edificis
    print('\n== Edificis (Vic)')
    nom, lat, lon = UBICACIONS_PROVES[1]
    app.triar_ubicacio(lat, lon, nom)
    from dades.edificis import preparar_malla
    from dades.data_io import ZONES_DETALL
    mm = preparar_malla('vic', next(c for _, c, z in ZONES_DETALL if z == 'vic'))
    tri, atr = mm['triangles'].astype(float), mm['atributs']
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    centre = tri.mean(axis=1) + mm['origen']
    amunt_t = centre / np.linalg.norm(centre, axis=1, keepdims=True)
    coberta = atr[:, 0, 2] < 0
    cob_ok = float(((n[coberta] * amunt_t[coberta]).sum(axis=1) > 0).mean())
    obs = app.edificis.obstacles
    rng = np.random.default_rng(5)
    mostra = rng.choice(np.where(~coberta & (np.linalg.norm(n, axis=1) > 1e-9))[0], 3000, replace=False)
    fora = 0
    for k in mostra:
        q = centre[k] + n[k] / np.linalg.norm(n[k]) * 0.00002             # 2 cm cap a la normal
        la, lo, _ = (float(v) for v in geodesia.geodesiques(q))
        x, y = obs.utm(la, lo)
        part = int(atr[k, 0, 3])
        fora += not obs.contorns[part].contains(__import__('shapely').Point(x, y))
    ok(cob_ok == 1.0 and fora == len(mostra),
       f'cobertes cap amunt: {cob_ok * 100:.2f} %; facanes cap a fora del contorn: {fora} de {len(mostra)} '
       '(les cares del darrere es poden descartar)')
    c = app.edificis.colors_coberta
    ok(c is not None and np.isfinite(c[:, 0]).mean() > 0.95,
       f'color de coberta de l\'ortofoto a {np.isfinite(c[:, 0]).mean() * 100:.1f} % de les parts de Vic' if c is not None
       else 'sense colors de coberta')

    # ------------------------------------------------------------ 6. temps
    print('\n== Temps per fotograma (ms, finestra amagada; mirant al nord des de la placa Major a les 16:30)')
    app.hora = 14.5
    co.mirar(0.0, 2.0)
    co.fov = 60.0
    for mida in ((1280, 860), (2560, 1720)):
        res = []
        for cel, edif in ((True, True), (False, True), (True, False)):
            app.cel.visible, app.edificis.visible = cel, edif
            fotograma(5, mida)
            t0 = time.perf_counter()
            fotograma(40, mida)
            res.append((time.perf_counter() - t0) / 40 * 1000)
        app.cel.visible = app.edificis.visible = True
        print(f'   {mida[0]} x {mida[1]}: tot {res[0]:.1f}; sense cel {res[1]:.1f}; sense edificis {res[2]:.1f}')
    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
