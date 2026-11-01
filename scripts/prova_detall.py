"""
Prova del detall segons la vista (basecode/detall.py) amb el programa real (finestra amagada, mateix bucle i panell):
el relleu, la fotografia, els edificis (altures mesurades) i el mapa de visibilitat es preparen en navegar, sense
doble clic ni punt d'observacio, i la navegacio continua mentre es preparen.

Parts (es poden triar amb arguments; per defecte totes, en ordre):
  vic       Vic, placa Major (llista del panell): conserva la zona de 5 m i els edificis (sense ortofoto feta a ma); els
            edificis passen a altures mesurades (ICGC); nom del lloc.
  uab       UAB (llista): zona del Valles, mapa de detall del model d'alcaries de l'ICGC (2 m), com a tot Catalunya.
  valencia  Des de la UAB, nomes navegant: pujar (E), girar cap a Valencia (fletxes), avancar (W) i baixar amb la roda
            fins a un carrer. S'hi espera el relleu de 5 m, s'hi activen els edificis (a la vista aeria) i el mapa, i
            es tria un punt amb doble clic (nom del lloc). Es mesura el temps de cada fotograma mentre tot es prepara.
  antiga    Una preparacio que encara no ha acabat quan la camera ja es en un altre lloc: en acabar, no canvia el
            que es veu.
  tornar    Tornar al mateix lloc de Valencia (navegant): tot surt del disc (cap feina de xarxa nova).
Captures a captures/proves/detall_*.png. Resultats amb OK / FALLA i un resum de fonts i resolucions.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_detall.py [vic] [uab] [valencia] [antiga] [tornar]
La primera vegada a Valencia baixa ~10 MB de relleu, el Catastro del municipi i l'alcaria de l'IGN (uns minuts).
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from slimgui import imgui  # noqa: E402

SORTIDA = os.path.join(ARREL, 'captures', 'proves')
VALENCIA = (39.4745, -0.3768)          # Ciutat Vella (plaça de la Reina), destinacio de la navegacio
VALENCIA_LLUNY = (39.4699, -0.3200)    # un altre lloc de Valencia (el Cabanyal, a 5 km), per a la prova "antiga"
W, H = 1100, 760


def main():
    parts = [a for a in sys.argv[1:] if not a.startswith('-')] or ['vic', 'uab', 'valencia', 'antiga', 'tornar']
    os.makedirs(SORTIDA, exist_ok=True)
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia, llocs
    from dades.observador import UBICACIONS_PROVES as UBICACIONS

    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova del detall', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    errors, temps = [], []
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)
    app.ratoli.focus = True       # la finestra amagada no te el focus: sense aixo, W A S D no fan res

    def punt_sota_cursor(pixel=None):
        mx, my = io.mouse_pos
        px, py = (int(mx), H - 1 - int(my)) if pixel is None else pixel[:2]
        d = float(np.frombuffer(objectiu.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'),
                                'f4')[0])
        return None if not 0.0 < d < 1.0 else app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
    app.punt_sota_cursor = punt_sota_cursor

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text, flush=True)
        if not condicio:
            errors.append(text)
        return condicio

    def fotograma(n=1, dt=1 / 30):
        for _ in range(n):
            t0 = time.perf_counter()
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
            app.ui_renderer.render(imgui.get_draw_data())
            app.ctx.finish()
            temps.append(time.perf_counter() - t0)

    def desa(nom):
        Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(SORTIDA, f'detall_{nom}.png'))

    def esperar(condicio, maxim_s, text=''):
        """Fotogrames fins que condicio() es certa (o maxim_s segons). Retorna els segons."""
        t0 = time.time()
        ultim = -1
        while not condicio() and time.time() - t0 < maxim_s:
            fotograma()
            time.sleep(0.02)
            if text and int(time.time() - t0) // 15 != ultim:
                ultim = int(time.time() - t0) // 15
                e = app.detall.estat
                print(f'   ... {time.time() - t0:4.0f} s  terreny: {e["terreny"][:70]} | edificis: {e["edificis"][:70]}'
                      f' | mapa: {e["mapa"][:70]}', flush=True)
        return time.time() - t0

    def resum_estat(lloc):
        e = app.detall.estat
        print(f'   [{lloc}] terreny: {e["terreny"]}\n   [{lloc}] foto: {e["foto"]}\n   [{lloc}] edificis: {e["edificis"]}'
              f'\n   [{lloc}] mapa: {e["mapa"]}', flush=True)

    def ubicacio(nom_part):
        nom, lat, lon = next(u for u in UBICACIONS if nom_part in u[0])
        app.triar_ubicacio(lat, lon, nom)
        return lat, lon

    def nom_del_punt():
        esperar(lambda: app.consulta_nom is None and app.nom_punt is not None, 60)
        return app.nom_punt[1] if app.nom_punt else None

    def text_nom(r):
        if r is None:
            return 'cap'
        n, m = r['nucli'], r['municipi']
        nn = 'cap' if n is None else (f'dins de {n[0]}' if n[1] == 'dins del nucli' else f'{n[0]} a {n[2]:.1f} km')
        return f'nucli: {nn}; municipi: {m[0] + " (" + m[1] + ")" if m else "no disponible"}'

    def feines_xarxa():
        return {t for t in app.detall.feines if t in ('relleu', 'edificis', 'alcades', 'superficie')}

    resultats = {}
    fotograma(5)

    # ------------------------------------------------------------ Vic
    if 'vic' in parts:
        print('== Vic, placa Major (llista del panell)')
        ubicacio('Vic')
        app.canviar_vista(1)
        fotograma(5)
        z = app.zona
        ok(z is not None and app.nom_zona == 'Vic' and z.alt.shape == (4000, 4000),
           'Vic: la zona de 5 m (20 x 20 km, 4000 x 4000 px) es la que es dibuixa')
        ok(z is not None and z.orto is None and z.orto_detall is None,
           'Vic: sense l\'ortofoto feta a ma (el terra, de les teselles del PNOA, com a tot arreu)')
        ok(app.edificis is not None and app.edificis.n_parts > 1000, f'Vic: edificis del Catastro '
           f'({app.edificis.n_parts if app.edificis else 0} parts)')
        s = esperar(lambda: app.edificis is not None and app.edificis.mesurades, 400, 'Vic')
        e = app.edificis
        # nomes es mesura la cel·la de 3 x 3 km del punt (la resta, quan s'hi miri): s'hi comprova la part on son els ulls
        prop = e.obstacles.contorns if e is not None else []
        o = app.observador
        x, y = e.obstacles.utm(o.lat, o.lon) if e is not None else (0, 0)
        import shapely
        a_prop = np.array([g.distance(shapely.Point(x, y)) < 300 for g in prop]) if e is not None else np.zeros(0, bool)
        frac = float(e.origen_alcada[a_prop].mean()) if e is not None and a_prop.any() else 0.0
        ok(e is not None and e.mesurades and e.font_alcada == 'icgc' and frac > 0.8,
           f'Vic: altures mesurades (ICGC 1 m) a {e.n_mesurades if e else 0} de {e.n_parts if e else 0} parts (la '
           f'cel·la del punt); a menys de 300 m dels ulls, el {frac * 100:.0f} % ({s:.0f} s)')
        r = nom_del_punt()
        print(f'   nom: {text_nom(r)}')
        ok(r is not None and r['nucli'] is not None and 'Vic' in r['nucli'][0], 'Vic: el nucli del punt es Vic')
        # color de les cobertes (fotografia aeria del PNOA): totes les parts, a tot arreu; s'espera el calcul
        s = esperar(lambda: app.edificis is not None and app.edificis.colors_coberta is not None, 300, 'Vic')
        cc = app.edificis.colors_coberta if app.edificis is not None else None
        amb = int((~np.isnan(cc[:, 0])).sum()) if cc is not None else 0
        ok(cc is not None and amb > 0.99 * len(cc), f'Vic: color de les cobertes de la foto a {amb} de '
           f'{len(cc) if cc is not None else 0} parts ({s:.0f} s)')
        app.camera_observador.mirar(250, 3)
        fotograma(20)
        desa('vic_terra')
        app.edificis_aeris = True
        app.posar_exploracio_sobre_el_punt()
        app.camera_exploracio.posicio = app.ulls() + 0.4 * (app.camera_exploracio.posicio - app.ulls()) / \
            np.linalg.norm(app.camera_exploracio.posicio - app.ulls())
        app.canviar_vista(0)
        fotograma(20)
        desa('vic_aeria_cobertes')
        app.canviar_vista(1)
        app.edificis_aeris = False
        resum_estat('Vic')
        resultats['vic'] = dict(app.detall.estat)

    # ------------------------------------------------------------ UAB
    if 'uab' in parts:
        print('== UAB, placa Civica (llista del panell)')
        ubicacio('UAB')
        app.canviar_vista(1)
        app.mapa_visibilitat = 1
        fotograma(3)
        ok(app.zona is not None and app.nom_zona.startswith('Valles'), 'UAB: la zona del Valles es la que es dibuixa')
        s = esperar(lambda: app.zona is not None and app.zona.vis_detall is not None, 600, 'UAB')
        vd = app.zona.vis_detall if app.zona is not None else None
        ok(vd is not None and 'ICGC' in vd.get('descripcio', ''),
           f'UAB: el mapa de detall es el del model d\'alcaries de l\'ICGC, com a la resta de Catalunya '
           f'({vd.get("descripcio") if vd else "-"}, {s:.0f} s)')
        s = esperar(lambda: app.edificis is not None and app.edificis.mesurades, 600, 'UAB')
        ok(app.edificis is not None and app.edificis.mesurades, f'UAB: altures mesurades ({s:.0f} s): '
           f'{app.edificis.resum_alcades() if app.edificis else ""}')
        app.camera_observador.mirar(285, 2)
        fotograma(10)
        desa('uab_terra_mapa')
        # a 400 m del punt (com a Vic): el centre de la imatge (el punt de detall) queda dins de la cel·la del mapa
        app.posar_exploracio_sobre_el_punt()
        app.camera_exploracio.posicio = app.ulls() + 0.4 * (app.camera_exploracio.posicio - app.ulls()) / \
            np.linalg.norm(app.camera_exploracio.posicio - app.ulls())
        app.canviar_vista(0)
        fotograma(10)
        desa('uab_aeria_mapa')
        resum_estat('UAB')
        resultats['uab'] = dict(app.detall.estat)
        app.mapa_visibilitat = 0

    # ------------------------------------------------------------ Valencia, navegant
    if 'valencia' in parts:
        print('== Valencia: des de la UAB, nomes navegant (tecles i roda)')
        ubicacio('UAB')
        app.posar_exploracio_sobre_el_punt()
        app.canviar_vista(0)
        ce = app.camera_exploracio
        ce.caminar = False
        fotograma(3)
        temps.clear()
        # 1. pujar amb E (i Ctrl, rapid) fins a ~150 km
        premudes.update({glfw.KEY_E, glfw.KEY_LEFT_CONTROL})
        esperar(lambda: ce.alcada_sobre_terra() > 150.0, 60)
        premudes.clear()
        # 2. girar amb les fletxes fins a mirar cap a Valencia (rumb) i una mica cap avall
        lat0, lon0, _ = ce.geodesiques()
        x0, y0, z0 = geodesia.ecef(float(lat0), float(lon0), 0.0)
        rumb = geodesia.azimut_elevacio(geodesia.ecef(*VALENCIA, 0.0) - geodesia.ecef(float(lat0), float(lon0), 0.0),
                                        float(lat0), float(lon0))[0]
        print(f'   rumb cap a Valencia: {rumb:.1f} graus')
        for _ in range(2000):
            d = (rumb - ce.rumb + 540) % 360 - 180
            if abs(d) < 1.0:
                break
            premudes.clear()
            premudes.add(glfw.KEY_RIGHT if d > 0 else glfw.KEY_LEFT)
            fotograma()
        premudes.clear()
        for _ in range(600):
            if ce.inclinacio < -20:
                break
            premudes.add(glfw.KEY_DOWN)
            fotograma()
        premudes.clear()

        def distancia_km():
            la, lo, _ = ce.geodesiques()
            from dades.noms import distancia_km as d
            return d(float(la), float(lo), *VALENCIA)
        # 3. avancar amb W (Ctrl: rapid), corregint el rumb amb les fletxes, fins que Valencia es davant (a ~1,5
        #    vegades l'altura)
        t0 = time.time()
        while distancia_km() > 1.5 * ce.alcada_sobre_terra() and time.time() - t0 < 120:
            la, lo, _ = ce.geodesiques()
            rumb = geodesia.azimut_elevacio(geodesia.ecef(*VALENCIA, 0.0) - geodesia.ecef(float(la), float(lo), 0.0),
                                            float(la), float(lo))[0]
            d = (rumb - ce.rumb + 540) % 360 - 180
            premudes.clear()
            premudes.update({glfw.KEY_W, glfw.KEY_LEFT_CONTROL})
            if abs(d) > 0.5:
                premudes.add(glfw.KEY_RIGHT if d > 0 else glfw.KEY_LEFT)
            fotograma()
        premudes.clear()
        print(f'   davant de Valencia: a {distancia_km():.0f} km, altura {ce.alcada_sobre_terra():.0f} km '
              f'({time.time() - t0:.0f} s)')
        desa('valencia_arribant')
        # 4. baixar amb la roda cap al punt del centre de la pantalla, que es Valencia (el cursor al mig)
        io.add_mouse_pos_event(W / 2, H / 2)
        fotograma()
        t0 = time.time()
        while ce.alcada_sobre_terra() > 0.35 and time.time() - t0 < 180:
            # el punt sota el cursor ha de ser Valencia: es corregeix el rumb i la inclinacio amb les fletxes
            la, lo, h = ce.geodesiques()
            v = geodesia.ecef(*VALENCIA, 0.01) - ce.posicio
            rumb, el = geodesia.azimut_elevacio(v, float(la), float(lo))
            d = (rumb - ce.rumb + 540) % 360 - 180
            premudes.clear()
            if abs(d) > 0.3:
                premudes.add(glfw.KEY_RIGHT if d > 0 else glfw.KEY_LEFT)
            if abs(el - ce.inclinacio) > 0.3:
                premudes.add(glfw.KEY_UP if el > ce.inclinacio else glfw.KEY_DOWN)
            app.ratoli.on_scroll(app.window, 0.0, 1.0)
            fotograma(3)
        premudes.clear()
        fotograma(20)
        la, lo, _ = ce.geodesiques()
        print(f'   al carrer: altura {ce.alcada_sobre_terra() * 1000:.0f} m, a {distancia_km():.2f} km de la placa '
              f'de la Reina ({time.time() - t0:.0f} s de roda)')
        desa('valencia_baixant')
        # 5. el relleu de 5 m arriba sol (sense doble clic ni punt d'observacio)
        clau_obs = app.detall.cami_obs
        s = esperar(lambda: app.zona is not None and app.nom_zona.startswith('Lloc') and app.zona.conte(*VALENCIA),
                    300, 'Valencia')
        ok(app.zona is not None and app.nom_zona.startswith('Lloc') and app.zona.conte(*VALENCIA),
           f'Valencia: el relleu de 5 m del lloc arriba navegant ({s:.0f} s): {app.nom_zona}')
        ok(app.detall.cami_obs == clau_obs and 'UAB' in app.observador.nom,
           'Valencia: el punt d\'observacio no ha canviat (continua a la UAB)')
        fotograma(30)
        desa('valencia_relleu')
        # 6. edificis a la vista aeria (el panell: "A la vista aeria") i mapa de visibilitat ("Al maxim")
        app.edificis_aeris = True
        app.mapa_visibilitat = 1
        s = esperar(lambda: app.edificis is not None, 900, 'Valencia')
        ok(app.edificis is not None and app.edificis.n_parts > 0,
           f'Valencia: edificis del Catastro ({app.edificis.n_parts if app.edificis else 0} parts, {s:.0f} s)')
        fotograma(10)
        desa('valencia_edificis_estimats')
        s = esperar(lambda: app.edificis is not None and app.edificis.mesurades, 900, 'Valencia')
        e = app.edificis
        ok(e is not None and e.mesurades and e.font_alcada == 'ign',
           f'Valencia: altures mesurades amb el MDSn de l\'IGN ({s:.0f} s): {e.resum_alcades() if e else ""}')
        s = esperar(lambda: app.zona is not None and app.zona.visibilitat is not None, 900, 'Valencia')
        ok(app.zona is not None and app.zona.visibilitat is not None, f'Valencia: mapa del relleu de 5 m ({s:.0f} s)')
        s = esperar(lambda: app.zona is not None and app.zona.vis_detall is not None, 1800, 'Valencia')
        vd = app.zona.vis_detall if app.zona is not None else None
        ok(vd is not None and 'IGN' in vd.get('descripcio', ''),
           f'Valencia: mapa de detall amb edificis i vegetacio de l\'IGN ({s:.0f} s): '
           f'{vd.get("descripcio") if vd else ""}')
        fotograma(10)
        desa('valencia_mapa_aeria')
        resultats['vista'] = (ce.posicio.copy(), ce.rumb, ce.inclinacio)     # per tornar-hi exactament
        # 7. punt amb doble clic al centre de la pantalla: primera persona i nom del lloc
        io.add_mouse_pos_event(W / 2, H / 2 + 60)
        fotograma()
        for _ in range(2):
            io.add_mouse_button_event(0, True)
            fotograma()
            io.add_mouse_button_event(0, False)
            fotograma()
        fotograma(5)
        o = app.observador
        from dades.noms import distancia_km as dk
        ok(app.vista == 1 and dk(o.lat, o.lon, *VALENCIA) < 3.0,
           f'Valencia: el doble clic posa el punt d\'observacio a {o.lat:.5f}, {o.lon:.5f} i passa a primera persona')
        r = nom_del_punt()
        print(f'   nom: {text_nom(r)}')
        ok(r is not None and r['municipi'] is not None and 'Val' in r['municipi'][0],
           'Valencia: el municipi del punt es Valencia')
        app.camera_observador.mirar(285, 2)
        fotograma(20)
        desa('valencia_terra')
        resum_estat('Valencia')
        resultats['valencia'] = dict(app.detall.estat)
        t = np.array(temps)
        print(f'   temps per fotograma durant tot el cami (preparant dades): mediana {np.median(t) * 1000:.0f} ms, '
              f'p99 {np.percentile(t, 99) * 1000:.0f} ms, maxim {t.max() * 1000:.0f} ms ({len(t)} fotogrames)')
        ok(np.percentile(t, 99) < 0.25, 'la navegacio continua responent mentre es prepara el detall '
           '(99 % dels fotogrames per sota de 250 ms)')
        resultats['temps'] = (float(np.median(t)), float(np.percentile(t, 99)), float(t.max()))

    # ------------------------------------------------------------ una preparacio antiga no canvia el que es veu
    if 'antiga' in parts:
        print("== Preparacio antiga: la camera se'n va abans que acabi")
        ce = app.camera_exploracio
        app.canviar_vista(0)
        ce.caminar = False
        _, _, amunt = geodesia.base_local(*VALENCIA_LLUNY)
        ce.posicio = geodesia.ecef(*VALENCIA_LLUNY, 0.25)
        ce.orientar(0.0, -89.0)
        clau_lluny = llocs.clau_latlon(*VALENCIA_LLUNY)
        nou = not llocs.te_relleu(clau_lluny)
        esperar(lambda: 'relleu' in app.detall.feines or app.nom_zona == llocs.nom(clau_lluny), 10)
        f = app.detall.feines.get('relleu')
        # tornar de seguida a la placa de la Reina
        ce.posicio = geodesia.ecef(*VALENCIA, 0.25)
        ce.orientar(0.0, -89.0)
        fotograma(10)
        zona_vista = app.nom_zona
        if f is not None:
            esperar(lambda: f.fet, 300)
            fotograma(20)
        ok(app.nom_zona == zona_vista and app.nom_zona != llocs.nom(clau_lluny),
           f'en acabar la preparacio del Cabanyal ({"nova" if nou else "ja hi era"}), la zona que es veu continua sent '
           f'la de la placa de la Reina ({app.nom_zona})')

    # ------------------------------------------------------------ tornar-hi: tot del disc
    if 'tornar' in parts:
        print('== Tornar al mateix lloc de Valencia')
        ce = app.camera_exploracio
        ubicacio('UAB')
        app.canviar_vista(0)
        ce.caminar = False
        app.edificis_aeris = True
        app.mapa_visibilitat = 1
        ce.posicio = geodesia.ecef(*VALENCIA, 400.0)      # lluny (per sobre del detall): res de Valencia
        fotograma(5)
        baixades = app.mosaic.descarregador.baixades
        t0 = time.time()
        # la mateixa vista aeria que la primera vegada (si aquesta execucio no hi ha passat, la placa de la Reina)
        posicio, rumb, inclinacio = resultats.get('vista', (geodesia.ecef(*VALENCIA, 0.25), 0.0, -60.0))
        ce.posicio = posicio
        ce.orientar(rumb, inclinacio)
        llest = lambda: (app.zona is not None and app.nom_zona.startswith('Lloc') and app.edificis is not None
                         and app.edificis.mesurades and app.zona.vis_detall is not None
                         and app.zona.visibilitat is not None)
        vistes = set()
        while not llest() and time.time() - t0 < 120:
            fotograma()
            vistes |= feines_xarxa()
        s = time.time() - t0
        ok(llest() and not vistes, f'tornar-hi: relleu, edificis mesurats, mapa del relleu i mapa de detall en {s:.1f} s, '
           f'sense cap feina de xarxa (relleu, edificis, altures, superficie): {sorted(vistes) or "cap"}')
        print(f'   fotografia: {app.mosaic.descarregador.baixades - baixades} teselles noves de la xarxa '
              f'(la resta del disc)')
        fotograma(20)
        desa('valencia_tornar')
        resum_estat('Valencia, segona vegada')

    print(f'\n{len(errors)} errors' if errors else '\nTot correcte')
    for e in errors:
        print('  FALLA', e)
    glfw.set_window_should_close(app.window, True)
    app._shutdown()
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
