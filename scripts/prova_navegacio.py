"""
Prova d'usabilitat de la navegacio amb el programa real (finestra amagada, fotogrames com els del bucle,
amb el panell construit). No nomes mira on acaba la camera: desa el recorregut fotograma a fotograma i
comprova que no hi ha salts, sobrepassaments, acceleracions brusques ni oscil·lacions.

Recorreguts:
  1. Des del terra (Vic), mirar cap al cel i mantenir E: passa a l'exploracio sense cap salt (la mateixa
     matriu de vista i el mateix camp de visio que als ulls), el punt d'observacio, l'hora i la reproduccio
     no canvien, la mirada no canvia mentre s'avanca i la velocitat creix de manera suau.
  2. Girar 90 graus: E avanca en la direccio nova; Q retrocedeix. Mirant a terra, E no el travessa.
  3. Triar el Sol, mirar-lo (F) i apropar-s'hi (G); el mateix amb la Lluna; tornar a la Terra. Per a cada
     viatge: la distancia al desti no oscil·la ni es passa del punt final, el pas per fotograma canvia de
     manera suau (sense acceleracions brusques), el cami no travessa cap astre, l'astre acaba sencer a la
     imatge i la camera queda quieta.
  4. Cancel·lar un viatge amb W: s'atura alla on es, sense salt.
  5. La mateixa sensibilitat del ratoli a prop del terra i a l'espai.
  6. Velocitat entre la Terra i la Lluna: sense salts quan canvia l'astre mes proper. Un fotograma molt
     llarg (0,1 s) amb Ctrl a prop de la Lluna: no la travessa.
  7. P no mou la camera; tornar al punt d'observacio: els ulls a 1,7 m.
  8. Les parets del cub no es veuen per defecte.
Limitacio: el teclat i el ratoli son simulats (glfw.get_key i esdeveniments d'imgui); el ratoli i el trackpad
fisics del Mac no es proven aqui.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_navegacio.py
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


def angle(a, b):
    return math.degrees(math.acos(float(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    from dades.observador import ALCADA_ULLS_KM
    from basecode.camera_exploracio import ALCADA_MINIMA_KM, DISTANCIA_MINIMA_KM

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de la navegacio', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    co, ce, io = app.camera_observador, app.camera_exploracio, imgui.get_io()
    errors = []
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(n=1, dt=1 / 60):
        for _ in range(n):
            app.dt = dt
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
            imgui.begin('Opcions')
            app.build_ui()
            imgui.end()
            imgui.render()

    def tecla_imgui(k):
        io.add_key_event(k, True)
        fotograma()
        io.add_key_event(k, False)
        fotograma()

    def suau(passos, text, ratio_max):
        """Els passos consecutius (longitud per fotograma) no canvien de cop: cada un es com a molt ratio_max
        vegades l'anterior (ni mes gran ni mes petit), sense comptar els passos gairebe nuls."""
        p = np.array(passos)
        p = p[p > 1e-12 * max(p.max(), 1e-30)]
        r = p[1:] / p[:-1]
        pitjor = float(max(r.max(), 1 / r.min())) if len(r) else 1.0
        ok(pitjor <= ratio_max, f'{text}: el pas per fotograma canvia com a molt x{pitjor:.3f} d\'un fotograma al seguent')

    # ------------------------------------------------------------ 1. del terra al cel amb E
    print('== 1. Del terra al cel amb E')
    nom, lat, lon = programa.UBICACIONS[1]
    app.triar_ubicacio(lat, lon, nom)
    app.canviar_vista(1)
    co.fov = 60.0
    co.mirar(250.0, 60.0)
    fotograma(2)
    vista_ulls, fov_ulls, ulls = np.array(co.m_view), co.fov, co.posicio.copy()
    observador, hora, reproduint = app.observador, app.hora, app.reproduint
    app.passar_a_exploracio()    # el que fa E al primer fotograma, sense moure encara
    ok(app.vista == 0 and np.allclose(np.array(ce.m_view), vista_ulls, atol=1e-6) and ce.fov == fov_ulls
       and np.allclose(ce.posicio, ulls, atol=1e-12),
       "E des de l'observacio: passa a explorar amb la mateixa posicio, matriu de vista i camp de visio")
    app.canviar_vista(1)
    premudes.add(glfw.KEY_E)
    posicions, davants = [ce.posicio.copy()], []
    for _ in range(600):      # 10 s
        fotograma()
        posicions.append(ce.posicio.copy())
        davants.append(ce.davant_ecef.copy())
    premudes.clear()
    passos = [float(np.linalg.norm(b - a)) for a, b in zip(posicions, posicions[1:])]
    alcades = [float(geodesia.geodesiques(p)[2]) for p in posicions]
    ok(app.vista == 0 and passos[0] < 0.001, f'mantenint E: es passa a explorar sense salt (primer pas {passos[0] * 1000:.1f} m)')
    ok(all(np.array_equal(d, davants[0]) for d in davants), 'la direccio de la mirada no canvia mentre s\'avanca')
    ok(all(b > a for a, b in zip(alcades, alcades[1:])) and alcades[-1] - alcades[0] > 50,
       f'mirant amunt, E puja sempre: en 10 s, de {alcades[0] * 1000:.1f} m a {alcades[-1]:,.1f} km d\'altitud')
    suau(passos, 'mantenint E', 1.05)
    ok(app.observador is observador and app.hora == hora and app.reproduint == reproduint,
       "el punt d'observacio, l'hora i la reproduccio no canvien")

    # ------------------------------------------------------------ 2. E i Q segueixen la camera
    print('\n== 2. E i Q segueixen la mirada')
    ce.girar(90.0, -60.0)
    fotograma()
    for k, signe, nom_t in ((glfw.KEY_E, 1, 'E'), (glfw.KEY_Q, -1, 'Q')):
        p0, davant = ce.posicio.copy(), ce.davant_ecef.copy()
        premudes.add(k)
        fotograma(10)
        premudes.clear()
        ok(angle(ce.posicio - p0, signe * davant) < 0.01,
           f"girat 90 graus: {nom_t} es mou {'endavant' if signe > 0 else 'enrere'} en la direccio nova de la mirada")
    ce.inclinacio = -80.0
    premudes.add(glfw.KEY_E)
    minim = math.inf
    for _ in range(600):
        fotograma()
        minim = min(minim, ce.alcada_sobre_terra())
    premudes.clear()
    ok(minim >= ALCADA_MINIMA_KM * 0.999, f'mirant a terra, E s\'hi acosta pero no el travessa (minim {minim * 1000:.2f} m)')

    # ------------------------------------------------------------ 3. viatges als astres
    print('\n== 3. Mirar i apropar-se als astres')

    def viatge(desti, text):
        app.desti = desti
        nom_a, centre, radi = app.astre()
        p0 = ce.posicio.copy()
        tecla_imgui(imgui.Key.KEY_F)
        ok(angle(ce.davant_ecef, app.astre()[1] - ce.posicio) < 0.2 and np.allclose(ce.posicio, p0),
           f'{text}: F orienta la camera cap a {nom_a} ({angle(ce.davant_ecef, app.astre()[1] - ce.posicio):.3f} graus) sense moure-la')
        io.add_key_event(imgui.Key.KEY_G, True)
        fotograma()
        io.add_key_event(imgui.Key.KEY_G, False)
        tr = ce.viatge['trajecte']
        posicions, distancies, n = [ce.posicio.copy()], [], 0
        obstacles = [(app.astre(k)[1], app.astre(k)[2]) for k in (1, 2)]
        minim_obstacles, alt_minima = math.inf, math.inf
        while ce.viatge is not None and n < 600:
            fotograma()
            n += 1
            posicions.append(ce.posicio.copy())
            distancies.append(float(np.linalg.norm(ce.posicio - app.astre()[1])))
            for c, r in obstacles:
                if r != radi:
                    minim_obstacles = min(minim_obstacles, float(np.linalg.norm(ce.posicio - c)) / r)
            alt_minima = min(alt_minima, float(geodesia.geodesiques(ce.posicio)[2]))
        final = ce.posicio.copy()
        fotograma(30)
        d = np.array(distancies)
        creix = tr.r1 > tr.r0
        monoton = np.all(np.diff(d) >= -1e-6 * d[1:]) if creix else np.all(np.diff(d) <= 1e-6 * d[1:])
        passat = (d.max() > tr.r1 * (1 + 1e-6)) if creix else (d.min() < tr.r1 * (1 - 1e-6))
        ok(n < 600 and monoton and not passat,
           f'{text}: G, viatge de {tr.durada:.1f} s ({n} fotogrames) de {tr.r0:,.0f} a {tr.r1:,.0f} km del centre, '
           f'sense oscil·lar ni passar-se')
        # suavitat en escala logaritmica: el canvi de log(distancia) per fotograma no salta
        lpas = np.abs(np.diff(np.log(d)))
        salt = float(np.abs(np.diff(lpas)).max() / lpas.max())
        ok(salt < 0.05 and lpas[0] < 0.05 * lpas.max() and lpas[-1] < 0.05 * lpas.max(),
           f'{text}: sense acceleracions brusques (canvi maxim del pas entre fotogrames: {salt * 100:.1f} % del pas maxim; '
           f'comenca i acaba a poc a poc)')
        ok(minim_obstacles > 1.0 and alt_minima > 0.0,
           f'{text}: el cami no travessa cap astre ni el terra (altitud minima {alt_minima:,.1f} km)')
        fov_v = math.radians(ce.fov)
        fov_min = min(fov_v, 2 * math.atan(math.tan(fov_v / 2) * ce.aspect_ratio))
        ocupa = 2 * math.asin(radi / np.linalg.norm(final - app.astre()[1])) / fov_min
        ok(0.6 < ocupa < 0.95 and angle(ce.davant_ecef, app.astre()[1] - ce.posicio) < 0.2
           and np.array_equal(ce.posicio, final),
           f"{text}: {nom_a} acaba sencer al centre de la imatge (ocupa el {ocupa * 100:.0f} % del camp mes estret) "
           f'i la camera queda quieta')
        return n

    viatge(2, 'Sol')
    viatge(1, 'Lluna')
    viatge(0, 'Terra')

    # ------------------------------------------------------------ 4. cancel·lar
    print('\n== 4. Cancel·lar un viatge')
    app.desti = 2
    tecla_imgui(imgui.Key.KEY_G)
    fotograma(20)
    abans = ce.posicio.copy()
    pas_viatge = float(np.linalg.norm(ce.posicio - abans))
    fotograma()
    pas_viatge = float(np.linalg.norm(ce.posicio - abans))
    abans, pas_w = ce.posicio.copy(), ce.velocitat() / 60
    premudes.add(glfw.KEY_W)
    fotograma()
    premudes.clear()
    pas_cancel = float(np.linalg.norm(ce.posicio - abans))
    despres = ce.posicio.copy()
    fotograma(20)
    ok(ce.viatge is None and np.array_equal(ce.posicio, despres) and abs(pas_cancel - pas_w) < 0.02 * pas_w,
       f'W durant el viatge el cancel·la: en aquell fotograma la camera nomes fa el pas de W ({pas_cancel:,.0f} km, '
       f'el pas del viatge era {pas_viatge:,.0f} km) i despres queda quieta')

    # ------------------------------------------------------------ 5. sensibilitat del ratoli
    print('\n== 5. Sensibilitat del ratoli')
    angles = []
    for alcada in (0.01, 1e7):
        ce.posicio = geodesia.ecef(lat, lon, alcada)
        ce.orientar(30.0, 0.0)
        d0 = ce.davant_ecef.copy()
        ce.girar_ratoli(50.0, 0.0)
        angles.append(angle(d0, ce.davant_ecef))
    ok(abs(angles[0] - angles[1]) < 1e-6, f'50 punts de ratoli giren {angles[0]:.4f} graus a 10 m i {angles[1]:.4f} a 10 milions de km')

    # ------------------------------------------------------------ 6. velocitat
    print('\n== 6. Velocitat entre la Terra i la Lluna')
    lluna = app.lluna_ecef.copy()
    ce.posicio = lluna * 0.3
    ce.mirar_cap_a(lluna)
    premudes.add(glfw.KEY_E)
    posicions = [ce.posicio.copy()]
    for _ in range(400):
        fotograma()
        posicions.append(ce.posicio.copy())
    premudes.clear()
    passos = [float(np.linalg.norm(b - a)) for a, b in zip(posicions, posicions[1:])]
    suau(passos, 'anant cap a la Lluna (passa de ser mes a prop de la Terra a ser-ho de la Lluna)', 1.05)
    d_lluna = float(np.linalg.norm(ce.posicio - app.lluna_ecef)) - programa.RADI_LLUNA_KM
    ok(d_lluna > DISTANCIA_MINIMA_KM * 0.999, f'acaba a {d_lluna:,.1f} km de la superficie de la Lluna, sense travessar-la')
    ce.posicio = app.lluna_ecef + (ce.posicio - app.lluna_ecef) / np.linalg.norm(ce.posicio - app.lluna_ecef) * (programa.RADI_LLUNA_KM + 100)
    ce.mirar_cap_a(app.lluna_ecef)
    premudes.update({glfw.KEY_E, glfw.KEY_LEFT_CONTROL})
    minim = math.inf
    for _ in range(50):
        fotograma(dt=0.1)
        minim = min(minim, float(np.linalg.norm(ce.posicio - app.lluna_ecef)) - programa.RADI_LLUNA_KM)
    premudes.clear()
    ok(minim > DISTANCIA_MINIMA_KM * 0.999, f'fotogrames de 0,1 s amb Ctrl cap a la Lluna: no la travessa (minim {minim:.2f} km)')
    d0 = float(np.linalg.norm(ce.posicio - app.lluna_ecef)) - programa.RADI_LLUNA_KM
    ce.posicio = app.lluna_ecef + (ce.posicio - app.lluna_ecef) / np.linalg.norm(ce.posicio - app.lluna_ecef) * (programa.RADI_LLUNA_KM + 1000)
    ce.mirar_cap_a(app.lluna_ecef)
    app.ratoli.on_scroll(app.window, 0.0, 1.0)
    fotograma()
    d1 = float(np.linalg.norm(ce.posicio - app.lluna_ecef)) - programa.RADI_LLUNA_KM
    ok(abs(d1 - 1000 / 1.35) < 5, f'roda a 1.000 km de la Lluna mirant-la: un pas la deixa a {d1:.0f} km (1000/1,35)')

    # ------------------------------------------------------------ 7. P i tornar al punt
    print("\n== 7. P i tornar al punt d'observacio")
    fotograma()
    p0, d0v = ce.posicio.copy(), ce.davant_ecef.copy()
    tecla_imgui(imgui.Key.KEY_P)
    fotograma(30)
    tecla_imgui(imgui.Key.KEY_P)
    ok(np.array_equal(ce.posicio, p0) and np.array_equal(ce.davant_ecef, d0v), 'P (reproduir i pausar) no mou ni gira la camera')
    app.tornar_al_punt()
    fotograma()
    o = app.observador
    alt_ulls = float(geodesia.geodesiques(co.posicio)[2]) - app.altitud_terra_km(o.lat, o.lon)
    ok(app.vista == 1 and app.observador is observador and abs(alt_ulls - ALCADA_ULLS_KM) < 1e-9,
       f"tornar al punt d'observacio: els ulls a {alt_ulls * 1000:.3f} m del terra dibuixat al punt original")

    # ------------------------------------------------------------ 8. parets amagades
    print('\n== 8. Parets del cub')
    app.canviar_vista(0)
    p = (app.cub.minim + app.cub.maxim) / 2
    p[0] = app.cub.minim[0]
    ce.posicio = p
    ce.mirar_cap_a(p - np.array([1.0, -0.5, -0.3]) * 1e6)
    imatges = []
    for mostrar in (False, True):
        app.mostrar_cub = mostrar
        fotograma(2)
        imatges.append(np.frombuffer(objectiu.read(components=3), 'u1').astype(int))
    app.mostrar_cub = False
    ok(imatges[0].max() < 30 and np.abs(imatges[1] - imatges[0]).max() > 30,
       'per defecte la paret no es veu (a la paret, mirant-la); amb l\'opcio de depuracio, si')

    glfw.get_key = get_key
    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
