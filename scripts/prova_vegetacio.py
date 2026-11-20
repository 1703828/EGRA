"""
Prova de la vegetacio (basecode/vegetacio.py, F53) amb el programa real (finestra amagada) i una memoria cau de proves
(EGRA_CACHE_PROVES): els llocs de l'usuari no es toquen.

  1. Lloc nou sense res preparat (Mataro): s'activa nomes la casella de vegetacio (cap mapa de visibilitat obert).
     La superficie dels obstacles es demana sola, en segon pla, i surt a Descarregues amb el nom del lloc.
  2. La vegetacio es carrega i, a 300 m del terra, el panell no dona cap motiu per no veure-la.
  3. Coherencia amb el calcul de visibilitat (D94): cada columna es exactament una cel·la de la superficie dels
     obstacles (mateix nombre de punts que cel·les amb objecte > 1,5 m fora dels edificis i mateixa alcaria, al mm), i
     el fitxer es el mateix que llegeix el mapa de detall (N3).
  4. Motius: camera a 3 km (massa lluny); i, simulats (injectant l'estat), sense cobertura LiDAR i sense relleu.
  5. Cap fotograma de mes de 0,25 s per la vegetacio (el treball pesat va en processos; es diu a quina carrega es deu
     cada fotograma lent).
Necessita xarxa (un lloc nou: relleu, Catastro i LiDAR). Executa:  python scripts/prova_vegetacio.py <carpeta de proves>
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ARREL, 'scripts'))


def main():
    from auditar_edificis import preparar_cache
    carpeta = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'proves_vegetacio')
    preparar_cache(carpeta)
    os.environ['EGRA_CACHE_PROVES'] = carpeta
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    import glfw
    import numpy as np
    import rasterio
    from OpenGL import GL
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    import ui
    from basecode import vegetacio as modul
    from dades import alcaries, geodesia
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='prova', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    obj = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    errors, textos, lents, abans_edificis = [], set(), [], []
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
        abans = (len(app.vegetacio.cel_les), sorted(app.detall.feines), app.edificis.zona if app.edificis else None)
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
        linies = [t for t, _ in ui.descarregues(app)]
        for (tipus, c), f in app.vegetacio.feines.items():
            # la linia d'aquesta feina, amb el nom del lloc (ui.nom_proper: el nom del mapa o, sense, les coordenades)
            textos.add((tipus, c, any('vegetacio' in t and ui.nom_proper(*f.lloc) in t for t in linies)))
            # i abans dels edificis del lloc, mai (la superficie es desa amb els contorns del Catastro)
            if tipus == 'superficie' and c == c_lloc and not llocs.edificis_fets(llocs.clau_per_punt(*cel_xy)):
                abans_edificis.append(c)
        d = time.perf_counter() - ara
        if d > 0.25:     # (amb el que ha canviat en aquell fotograma: quina carrega l'ha allargat)
            despres = (len(app.vegetacio.cel_les), sorted(app.detall.feines), app.edificis.zona if app.edificis else None)
            lents.append((round(d, 2), 'vegetacio pujada' if despres[0] != abans[0] else
                          f'detall {abans[1]} -> {despres[1]}' if despres[1:] != abans[1:] else 'altres'))

    def camera(lat, lon, alt_km, incl):
        app.camera.aturar_moviment()
        app.camera.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + alt_km)
        app.camera.orientar(30.0, incl)

    def esperar(condicio, maxim):
        t = time.perf_counter()
        while time.perf_counter() - t < maxim and not condicio():
            fotograma()
        return time.perf_counter() - t

    lat, lon = 41.5390, 2.4440                      # Mataro
    from dades import llocs
    cel_xy = alcaries.centre_cel(*modul._A_UTM.transform(lon, lat))
    c_lloc = f'cel_{cel_xy[0]:.0f}_{cel_xy[1]:.0f}'
    for _ in range(5):
        fotograma()
    ok(app.mapes.mode_actual() in (None, 'cap', 0) or not app.mapes.feines, f'cap mapa de visibilitat obert '
       f'({app.mapes.mode_actual()})')
    app.vegetacio.actiu = True
    camera(lat, lon, 0.3, -35.0)
    t0 = time.perf_counter()
    motius_espera = {}

    def preparant():
        motius_espera.update(app.vegetacio.esperant)
        return ('superficie', c_lloc) in app.vegetacio.feines
    s = esperar(preparant, 400)
    ok(('superficie', c_lloc) in app.vegetacio.feines and not abans_edificis,
       f'1. sense obrir cap mapa, la vegetacio demana la superficie dels obstacles de {c_lloc} ({s:.0f} s: abans, '
       f'el relleu i els edificis del lloc; motiu d\'espera: {sorted(set(motius_espera.values())) or "cap"})')
    s2 = esperar(lambda: not app.vegetacio.feines and app.vegetacio.cel_les, 600)
    ok(all(v for _, _, v in textos) and ('superficie', c_lloc, True) in textos,
       f'1. cada feina de vegetacio surt a Descarregues amb el seu lloc ({ui.nom_proper(lat, lon)}): {sorted(textos)}')
    c = app.vegetacio.volgudes[0] if app.vegetacio.volgudes else None
    carregada = c in app.vegetacio.cel_les
    n = app.vegetacio.cel_les[c]['n'] if carregada else 0
    ok(carregada and n > 0, f'2. vegetacio carregada a {c}: {n} punts ({s2:.0f} s mes; {time.perf_counter() - t0:.0f} s '
                            'des de l\'arribada)')
    for _ in range(30):
        fotograma()
    ok(app.vegetacio.motiu() == '', f'2. a 300 m, cap motiu al panell ("{app.vegetacio.motiu()}")')

    # 3. coherencia amb la superficie del calcul
    if carregada:
        capes = {}
        for capa in ('superficie', 'ulls', 'edifici'):
            with rasterio.open(alcaries.cami_superficie(c, capa)) as f:
                capes[capa] = f.read(1)
        alt = capes['superficie'] - capes['ulls']
        sel = np.isfinite(alt) & (alt > modul.MIN_M) & (capes['edifici'] == 0)
        origen, v, res, trossos = modul.punts_cel(c)
        alt_v = np.sort(v['a'][:, 3] * 1000.0)
        alt_r = np.sort(alt[sel].astype('f4'))
        ok(len(v) == int(sel.sum()) and np.abs(alt_v - alt_r).max() < 1e-3 and sum(k for _, k, _, _ in trossos) == len(v),
           f'3. {len(v)} columnes = {int(sel.sum())} cel·les de la superficie amb objecte; diferencia d\'alcaria maxima '
           f'{np.abs(alt_v - alt_r).max() * 1000:.3f} mm; {len(trossos)} trossos de {modul.TROS_M:.0f} m')
        # el mapa de detall (N3) llegeix el mateix fitxer (basecode/mapes.py, _preparar nivell 3)
        import inspect
        from basecode import mapes
        font = inspect.getsource(mapes.Mapes._preparar)
        ok("alcaries.cami_superficie(cel, 'superficie')" in font and 'cami_superficie(c, ' in inspect.getsource(modul),
           '3. el mapa de detall i la vegetacio fan servir el mateix fitxer (alcaries.cami_superficie)')

    # 4. motius
    camera(lat, lon, 3.0, -35.0)
    for _ in range(20):
        fotograma()
    m = app.vegetacio.motiu()
    ok('massa lluny' in m, f'4. camera a 3 km: "{m}"')
    camera(lat, lon, 0.3, -35.0)
    for _ in range(20):
        fotograma()
    if c is not None:
        dades = app.vegetacio.cel_les.pop(c)
        app.vegetacio.fallades[('superficie', c)] = 'RuntimeError: cap model d\'alcaries (LiDAR) no cobreix aquest lloc'
        m = app.vegetacio.motiu()
        ok('sense cobertura LiDAR' in m, f'4. (simulat) sense LiDAR: "{m}"')
        del app.vegetacio.fallades[('superficie', c)]
        app.vegetacio.esperant[c] = 'falta el relleu de 5 m del lloc'
        m = app.vegetacio.motiu()
        ok('relleu' in m, f'4. (simulat) sense relleu: "{m}"')
        del app.vegetacio.esperant[c]
        app.vegetacio.cel_les[c] = dades
    veg = [l for l in lents if l[1] != 'altres' and not l[1].startswith('detall')]
    ok(not veg, f'5. fotogrames de mes de 0,25 s per la vegetacio: {veg or "cap"} (altres, de la carrega del relleu i '
                f'dels edificis, ja existents: {[l for l in lents if l not in veg][:5] or "cap"})')
    print(f'\n{"Tot correcte" if not errors else f"{len(errors)} errors"}')
    app._shutdown()
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
