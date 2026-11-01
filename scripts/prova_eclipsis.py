"""
Prova dels tres eclipsis (2026, 2027 i 2028) amb el programa real (main.py) i el panell dibuixat (slimgui),
com quan l'equip el fa servir: el canvi d'eclipsi es fa des del panell, entre el dibuix de l'escena i el del panell.

Per a cada eclipsi:
  1. Canviar-hi (i tornar-ne) sense errors d'OpenGL: abans, en canviar d'eclipsi el programa es tancava
     (GLError 1281 a glUseProgram: slimgui reactivava el shader del cub de navegacio, ja esborrat).
  2. Les hores del model al punt d'observacio: C1 < maxim < C4 i dins de l'interval de les efemerides.
  3. "Anar al maxim": l'hora es la del maxim i el temps queda en pausa.
  4. Coherencia de l'escena amb el model: la separacio entre el Sol i la Lluna dibuixats, vista des dels ulls,
     es la que calcula el model en aquell instant (tolerancia 0,001 graus).
  5. Les capes del CNIG (nomes 2026) no queden actives en un altre eclipsi.
  6. Captures: des del terra mirant el Sol al maxim, i l'ombra de la Lluna des de l'espai.
  7. El mapa de visibilitat: en demanar-lo, se'n llegeix o se'n comenca a calcular un per a l'eclipsi actiu (quan
     acaben les lectures i el detall que hi hagi en curs; com a molt ESPERA_MAPA_S) i el dibuix continua (el calcul
     es en un fil). Despres es treu i el calcul s'atura.

Les captures es desen a captures/proves/eclipsi_<any>_*.png (carpeta ignorada pel Git).

Executa (des de l'arrel del projecte, amb l'entorn egra):
    python scripts/prova_eclipsis.py
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
SORTIDA = os.path.join(ARREL, 'captures', 'proves')

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from OpenGL import GL  # noqa: E402
from PIL import Image  # noqa: E402
from slimgui import imgui  # noqa: E402

TOLERANCIA_GRAUS = 0.001
ESPERA_MAPA_S = 90.0    # com a molt, el que es pot esperar que acabin les lectures i el detall en curs


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import eclipsis, geodesia
    from dades.model_eclipsi import angle_entre

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova dels eclipsis', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    os.makedirs(SORTIDA, exist_ok=True)
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(accio_panell=None, n=1):
        """El fotograma de main.GraphicsEngine.run: escena, panell (accio_panell s'executa dins del panell, com un
        clic) i dibuix del panell amb slimgui. Retorna l'error d'OpenGL que hi hagi hagut, o None."""
        for _ in range(n):
            glfw.poll_events()
            app.dt = 1 / 60
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.begin('Opcions')
            app.build_ui()
            if accio_panell is not None:
                accio_panell()
                accio_panell = None
            imgui.end()
            imgui.render()
            GL.glUseProgram(0)   # el que fa main.py abans del panell
            try:
                app.ui_renderer.render(imgui.get_draw_data())
            except GL.GLError as e:
                return e
        return None

    def imatge():
        return Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    fotograma(n=3)
    disponibles = eclipsis.disponibles()
    ok(set(disponibles) == {'2026', '2027', '2028'}, f'efemerides dels tres eclipsis: {disponibles}')
    for clau in disponibles + ['2026']:
        titol = eclipsis.dades(clau)['titol']
        print(f'== {titol} ({clau})')
        error = fotograma(lambda c=clau: app.canviar_eclipsi(c))
        error = error or fotograma(n=3)
        ok(error is None and eclipsis.actiu() == clau, f'canviar a {clau} des del panell, sense error d\'OpenGL'
           + (f': {error}' if error else ''))
        m, ef = app.model, app.ef
        ok(m.valid, f'model valid al punt d\'observacio ({app.observador.nom or "punt"})')
        if not m.valid:
            continue
        h = m.hores
        ok(ef.inici <= h['c1'] < h['maxim'] < h['c4'] <= ef.final,
           f"C1 {eclipsis.hora_local(h['c1'])}, maxim {eclipsis.hora_local(h['maxim'])}, "
           f"C4 {eclipsis.hora_local(h['c4'])} ({eclipsis.dades()['nom_hora']}), dins de les efemerides")
        fotograma(app.anar_al_maxim)
        fotograma(n=2)
        ok(abs(app.hora - h['maxim']) < 1e-9 and not app.reproduint, 'Anar al maxim: hora del maxim, en pausa')
        # separacio Sol - Lluna a l'escena (posicions dibuixades) i al model, vistes des dels ulls
        ulls = app.ulls()
        escena = angle_entre(app.sol_ecef - ulls, app.lluna_ecef - ulls)
        sol, lluna = ef.posicions(app.hora)
        o = app.observador
        p = geodesia.ecef(o.lat, o.lon, o.altitud_m / 1000.0 + programa.ALCADA_ULLS_KM)
        model = angle_entre(sol - p, lluna - p)
        ok(abs(escena - model) < TOLERANCIA_GRAUS,
           f'separacio Sol - Lluna al maxim: escena {escena:.4f} graus, model {model:.4f} graus; '
           f'part del Sol tapada {m.tapat * 100:.1f} %' if hasattr(m, 'tapat') else
           f'separacio Sol - Lluna al maxim: escena {escena:.4f} graus, model {model:.4f} graus')
        if clau != '2026':
            ok(all(t.overlay == 0 and not t.limits_totalitat for t in app.terrenys()),
               'capes i limits del CNIG desactivats (nomes son del 2026)')
        # captures: des del terra mirant el Sol, i l'ombra des de l'espai
        fotograma(lambda: app.canviar_vista(1))
        fotograma(app.mirar_el_sol, n=4)
        imatge().save(os.path.join(SORTIDA, f'eclipsi_{clau}_terra_maxim.png'))
        fotograma(app.veure_ombra_des_de_lespai, n=6)
        imatge().save(os.path.join(SORTIDA, f'eclipsi_{clau}_ombra_espai.png'))
        # mapa de visibilitat: se'n llegeix o se'n comenca a calcular un de l'eclipsi actiu i el dibuix continua
        fotograma(lambda: app.canviar_vista(1))
        app.mapa_visibilitat = 1
        t0, n = time.time(), 0
        while time.time() - t0 < ESPERA_MAPA_S:   # primer acaben les lectures i el detall que hi hagi en curs
            fotograma()
            n += 1
            calculs = [c for c in app.calculs_mapa.values() if c.clau == clau] + \
                [c for c in (app.calcul_detall,) if c is not None and c.clau == clau]   # el de detall va primer
            mostrat = any(t.visibilitat is not None and t.visibilitat['clau'] == clau for t in app.terrenys())
            if calculs or mostrat:
                break
        ok(calculs or mostrat, f'mapa de visibilitat: {"mostrat" if mostrat else "calculant-se"} per al {clau} '
           f'(al cap de {time.time() - t0:.1f} s, {n / (time.time() - t0):.0f} fotogrames/s mentrestant)')
        app.mapa_visibilitat = 0
        fotograma(n=3)
    print()
    print('Captures a captures/proves/eclipsi_*.png')
    print('Tot correcte' if not errors else f'{len(errors)} errors')
    app._shutdown() if hasattr(app, '_shutdown') else None
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
