"""
Prova del canvi de lloc amb feines en curs (basecode/detall.py, F51), amb el programa real (finestra amagada) i una
memoria cau de proves (EGRA_CACHE_PROVES): els llocs de l'usuari no es toquen.

  1. La camera es a Igualada (amb edificis) i va a un lloc nou (Martorell). Abans de la F51, la zona d'Igualada encara
     activa feia una feina d'altures per a una cel·la sense cap part seva i refeia la seva malla (~17 s): ara no s'ha de
     demanar cap feina d'altures per a una zona que no te parts a la cel·la del punt.
  2. Mentre Martorell es prepara, la camera va a un altre lloc nou (Sant Sadurni d'Anoia) i s'hi queda. A cada
     fotograma: els edificis que es dibuixen son els de la zona activa. Al final, la zona i els edificis son els de
     Sant Sadurni, encara que les feines de Martorell acabin despres.
Necessita xarxa (dos llocs nous). Executa:  python scripts/prova_canvi_lloc.py <carpeta de proves>
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ARREL, 'scripts'))


def main():
    from auditar_edificis import preparar_cache
    carpeta = os.path.abspath(sys.argv[1])
    preparar_cache(carpeta)
    os.environ['EGRA_CACHE_PROVES'] = carpeta
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    import glfw
    from OpenGL import GL
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia, llocs
    from dades.observador import ALCADA_ULLS_KM
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='prova', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    obj = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    errors, incoherents, feines_vistes = [], [], []
    ultim = [time.perf_counter()]

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text, flush=True)
        if not condicio:
            errors.append(text)

    def fotograma():
        espera = 1 / 60 - (time.perf_counter() - ultim[0])
        if espera > 0:
            time.sleep(espera)
        ara = time.perf_counter()
        app.dt, ultim[0] = ara - ultim[0], ara
        glfw.poll_events()
        app.ui_renderer.new_frame()
        io.display_size, io.display_framebuffer_scale = (W, H), (1.0, 1.0)
        imgui.new_frame()
        obj.use()
        app.render()
        imgui.begin('Eclipsi')
        app.build_ui()
        imgui.end()
        imgui.render()
        GL.glUseProgram(0)
        app.ui_renderer.render(imgui.get_draw_data())
        for k, f in app.detall.feines.items():
            if (k, f.clau) not in feines_vistes:
                feines_vistes.append((k, f.clau))
        e, z = app.edificis, app.zona
        if e is not None:
            clau_zona = app.detall.carregades[z.cami]['clau'] if z is not None and z.cami in app.detall.carregades else None
            if e.zona != clau_zona:
                incoherents.append((round(time.perf_counter(), 1), e.zona, clau_zona))

    def camera(lat, lon):
        app.camera.aturar_moviment()
        app.camera.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + ALCADA_ULLS_KM)
        app.camera.orientar(200.0, 2.0)

    def esperar(condicio, maxim):
        t = time.perf_counter()
        while time.perf_counter() - t < maxim and not condicio():
            fotograma()
        return time.perf_counter() - t

    igualada, martorell, sadurni = (41.5786, 1.6172), (41.4746, 1.9306), (41.4262, 1.7853)
    c_ig, c_ma, c_sa = (llocs.clau_latlon(*p) for p in (igualada, martorell, sadurni))
    print(f'Igualada {c_ig} (preparat: {llocs.edificis_fets(c_ig)}), Martorell {c_ma} '
          f'({llocs.te_relleu(c_ma)}), Sant Sadurni {c_sa} ({llocs.te_relleu(c_sa)})', flush=True)
    for _ in range(10):
        fotograma()
    camera(*igualada)
    s = esperar(lambda: app.edificis is not None and app.edificis.zona == c_ig and not app.detall.feines, 240)
    ok(app.edificis is not None and app.edificis.zona == c_ig, f'camera a Igualada: edificis d\'Igualada ({s:.1f} s)')

    # 1. Martorell
    feines_vistes.clear()
    camera(*martorell)
    s = esperar(lambda: 'cadastre' in app.detall.feines and app.detall.feines['cadastre'].clau == c_ma, 30)
    esperar(lambda: False, 6.0)
    alcades = [c for k, c in feines_vistes if k == 'alcades']
    ok(not alcades, f'a Martorell, amb la zona d\'Igualada activa: cap feina d\'altures ({alcades or "cap"}); feines: '
                    f'{sorted({k for k, _ in feines_vistes})}')

    # 2. Sant Sadurni amb Martorell a mitges
    en_curs = sorted(app.detall.feines)
    camera(*sadurni)
    s = esperar(lambda: app.edificis is not None and app.edificis.zona == c_sa and not app.detall.feines, 300)
    ok(app.edificis is not None and app.edificis.zona == c_sa and
       app.detall.carregades[app.zona.cami]['clau'] == c_sa,
       f'canvi a Sant Sadurni amb feines de Martorell en curs ({en_curs}): zona i edificis de Sant Sadurni '
       f'({s:.1f} s; edificis: {app.detall.estat["edificis"]})')
    esperar(lambda: False, 5.0)
    ok(app.edificis.zona == c_sa, 'les feines de Martorell que acaben despres no canvien el que es veu')
    ok(not incoherents, f'a cada fotograma, els edificis dibuixats son de la zona activa ({len(incoherents)} incoherencies'
                        + (f': {incoherents[:3]})' if incoherents else ')'))
    print(f'\n{"Tot correcte" if not errors else f"{len(errors)} errors"}')
    app._shutdown()
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
