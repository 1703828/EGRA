"""
Auditoria del temps des que s'arriba a un lloc fins que s'hi veuen els edificis (programa real, finestra amagada).
No canvia res del programa: observa a cada fotograma les feines en segon pla de basecode/detall.py (quan comencen,
cada canvi del seu estat, que dona les subfases, i quan acaben), quan s'activa el relleu de 5 m, quan es dibuixen els
primers edificis (estimats) i els mesurats (Catastro + LiDAR), i els fotogrames lents del fil principal.

Us:  python scripts/auditar_edificis.py <lat> <lon> --mode clic|camera [--reproduir] [--tornar] [--max 600]
  --mode clic     doble clic (anar_al_punt): punt d'observacio i camera als ulls (nomes en pausa: en reproduccio el
                  punt no es pot canviar)
  --mode camera   nomes la camera als ulls d'aquell lloc (el punt d'observacio no canvia): serveix en pausa i en
                  reproduccio
  --reproduir     l'eclipsi en reproduccio a x1 (amb Auto o x60, el temps arribaria al final abans d'acabar)
  --tornar        despres, anar a la UAB i tornar al lloc (reutilitzacio dins de la mateixa sessio)
  --cache DIR     memoria cau de proves (EGRA_CACHE_PROVES, dades/data_io.py): els llocs, edificis, ZIP del Catastro,
                  alcaries i caches van a DIR i els de l'usuari no es toquen. Els fitxers base del territori (derivats
                  de la peninsula i del Valles) s'hi enllacen (enllacos durs: no ocupen mes disc)
  --lidar MODE    nomes amb --cache: 'falla' o 'lent:N' (s) simula un LiDAR absent o lent (EGRA_PROVA_LIDAR)
Escriu un resum i la llista d'esdeveniments; desa captures a captures/auditoria/.
Atencio: un lloc nou baixa dades (relleu, Catastro, LiDAR) i, com el programa, pot esborrar els llocs mes antics
(dades/llocs.MAX_LLOCS): amb --cache, nomes els de la carpeta de proves.
"""
import argparse
import json
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA = os.path.join(ARREL, 'captures', 'auditoria')
BASE = ['peninsula_200m.derivats.npz', 'peninsula_200m.globus3_7428_1024x833.npz',
        'peninsula_200m.globus3_852992_1024x833.npz', 'valles_5m.derivats.npz', 'valles_5m.globus3_7780_1024x921.npz',
        'valles_5m.globus3_943104_1024x921.npz']


def preparar_cache(carpeta):
    """La carpeta de proves amb els fitxers base enllacats (si no hi son)."""
    desti = os.path.join(carpeta, 'cache')
    os.makedirs(desti, exist_ok=True)
    for nom in BASE:
        origen = os.path.join(ARREL, 'data', 'cache', nom)
        if os.path.exists(origen) and not os.path.exists(os.path.join(desti, nom)):
            os.link(origen, os.path.join(desti, nom))


def main():
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    ap = argparse.ArgumentParser()
    ap.add_argument('lat', type=float)
    ap.add_argument('lon', type=float)
    ap.add_argument('--mode', choices=('clic', 'camera'), default='clic')
    ap.add_argument('--reproduir', action='store_true')
    ap.add_argument('--tornar', action='store_true')
    ap.add_argument('--max', type=float, default=600.0)
    ap.add_argument('--nom', default='lloc')
    ap.add_argument('--cache')
    ap.add_argument('--lidar')
    a = ap.parse_args()
    if a.cache:                       # abans d'importar el programa: els moduls llegeixen la variable en carregar-se
        a.cache = os.path.abspath(a.cache)
        preparar_cache(a.cache)
        os.environ['EGRA_CACHE_PROVES'] = a.cache
        if a.lidar:
            os.environ['EGRA_PROVA_LIDAR'] = a.lidar

    import glfw
    from OpenGL import GL
    from PIL import Image
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import catastro, geodesia, llocs
    from dades.observador import ALCADA_ULLS_KM
    from dades.edificis import fitxer_zona

    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='auditoria', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    obj = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    os.makedirs(CARPETA, exist_ok=True)
    c = llocs.clau_latlon(a.lat, a.lon)
    print(f'lloc {a.nom}: {a.lat}, {a.lon}  clau {c}  cache {a.cache or "data/ (usuari)"}'
          + (f'  LiDAR simulat: {a.lidar}' if a.lidar else ''))
    print(f'  al disc abans: relleu {llocs.te_relleu(c)}, edificis {llocs.edificis_fets(c)}, '
          f'gpkg {os.path.exists(fitxer_zona(c))}', flush=True)

    ultim = [time.perf_counter()]
    lents = []

    def fotograma():
        ara = time.perf_counter()
        espera = 1 / 60 - (ara - ultim[0])          # com amb la sincronia vertical: com a molt ~60 per segon
        if espera > 0:
            time.sleep(espera)
        ara = time.perf_counter()
        app.dt = ara - ultim[0]
        ultim[0] = ara
        glfw.poll_events()
        app.ui_renderer.new_frame()
        io.display_size, io.display_framebuffer_scale = (W, H), (1.0, 1.0)
        imgui.new_frame()
        obj.use()
        t = time.perf_counter()
        app.render()
        imgui.begin('Eclipsi')
        app.build_ui()
        imgui.end()
        imgui.render()
        GL.glUseProgram(0)
        app.ui_renderer.render(imgui.get_draw_data())
        # sense ctx.finish(): retindria el GIL mentre la GPU acaba (el programa no ho fa)
        ms = (time.perf_counter() - t) * 1000
        if ms > 100:
            lents.append((ara, ms))

    def captura(nom):
        Image.frombytes('RGB', (W, H), obj.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(CARPETA, nom))

    def anar(lat, lon):
        if a.mode == 'clic':
            ok = app.anar_al_punt(lat, lon, a.nom)
            print(f'  doble clic: {"fet" if ok else "NO (en reproduccio el punt no canvia)"}')
        else:
            app.camera.aturar_moviment()
            app.camera.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + ALCADA_ULLS_KM)
        app.camera.orientar(200.0, 2.0)

    def seguir(etiqueta, t0, maxim):
        """Fotogrames fins que els edificis mesurats es veuen i no hi ha feines (o maxim s). Retorna els
        esdeveniments [(s des de t0, text)]."""
        ev = []
        vistes, estats = {}, {}
        zona, primer, mesurats, fi = app.nom_zona, None, None, None
        quiet = None
        while time.perf_counter() - t0 < maxim:
            fotograma()
            ara = time.perf_counter() - t0
            f = app.detall.feines
            for k, v in f.items():
                if k not in vistes:
                    vistes[k] = ara
                    ev.append((ara, f'comenca {k}'))
                if estats.get(k) != v.estat:
                    estats[k] = v.estat
                    ev.append((ara, f'  {k}: {v.estat}'))
            for k in [k for k in vistes if k not in f]:
                ev.append((ara, f'acaba {k} ({ara - vistes.pop(k):.1f} s)'))
                estats.pop(k, None)
            if app.nom_zona != zona:
                zona = app.nom_zona
                ev.append((ara, f'zona activa: {zona}'))
            e = app.edificis
            dins = e is not None and e.visible and e.vao is not None and app.zona is not None and \
                app.zona.conte(*app.camera.geodesiques()[:2]) and e.zona == llocs.clau_latlon(*app.camera.geodesiques()[:2])
            if dins and primer is None:
                primer = ara
                ev.append((ara, f'PRIMERS EDIFICIS A PANTALLA ({e.n_parts} parts; {app.detall.estat["edificis"]})'))
                captura(f'{a.nom}_{etiqueta}_primers.png')
            text = app.detall.estat.get('edificis', '')
            if dins and mesurats is None and text.startswith('mesurades'):
                mesurats = ara
                ev.append((ara, f'EDIFICIS MESURATS A PANTALLA ({text})'))
            if mesurats is not None and not f:
                quiet = quiet or ara
                if ara - quiet > 3.0:
                    fi = ara
                    break
            else:
                quiet = None
            if primer is not None and not f and text.startswith(('cap ', 'no disponibles')):
                break
        captura(f'{a.nom}_{etiqueta}_final.png')
        return ev, primer, mesurats, fi

    def informe(etiqueta, ev, primer, mesurats, t0):
        print(f'\n== {etiqueta}')
        for t, text in ev:
            print(f'  {t:7.2f} s  {text}')
        l = [ms for t, ms in lents if t >= t0]
        print(f'  primers edificis: {primer if primer is None else round(primer, 1)} s; mesurats: '
              f'{mesurats if mesurats is None else round(mesurats, 1)} s; fotogrames > 100 ms: {len(l)}'
              + (f' (maxim {max(l):.0f} ms)' if l else ''), flush=True)
        return dict(etiqueta=etiqueta, primers_s=primer, mesurats_s=mesurats, lents=len(l),
                    lent_max_ms=max(l) if l else 0, esdeveniments=ev)

    for _ in range(10):
        fotograma()
    if a.reproduir:
        app.velocitat_auto, app.velocitat = False, 1
        app.reproduir_pausar()
    resultats = []
    t0 = time.perf_counter()
    anar(a.lat, a.lon)
    ev, primer, mesurats, _ = seguir('primera', t0, a.max)
    resultats.append(informe(f'{a.nom}: primera visita ({a.mode}, {"reproduint" if app.reproduint else "pausa"})',
                             ev, primer, mesurats, t0))
    if a.tornar:
        lents.clear()
        t1 = time.perf_counter()
        app.camera.posicio = geodesia.ecef(41.5018, 2.1041, app.altitud_terra_km(41.5018, 2.1041) + ALCADA_ULLS_KM)
        while time.perf_counter() - t1 < 15:
            fotograma()
        print(f'\n  (a la UAB: zona {app.nom_zona})')
        t0 = time.perf_counter()
        anar(a.lat, a.lon)
        ev, primer, mesurats, _ = seguir('tornada', t0, min(a.max, 180))
        resultats.append(informe(f'{a.nom}: tornada a la mateixa sessio', ev, primer, mesurats, t0))
    print(f'\n  al disc despres: relleu {llocs.te_relleu(c)}, edificis {llocs.edificis_fets(c)}; zips del Catastro: '
          f'{len([f for f in os.listdir(catastro.DIR_ZIPS) if f.endswith(".zip")]) if os.path.isdir(catastro.DIR_ZIPS) else 0}')
    with open(os.path.join(CARPETA, f'{a.nom}_{a.mode}{"_repr" if a.reproduir else ""}.json'), 'w') as fj:
        json.dump(resultats, fj, indent=1, default=str)
    app._shutdown()


if __name__ == '__main__':
    main()
