"""
Prova del mosaic d'imatges aeries (basecode/mosaic.py, dades/teselles.py) i dels controls de la vista aeria.

1. Sense finestra:
   - coordenades Web Mercator: la tesella de la placa Major de Vic a z = 17 es la que dona l'IGN;
   - la coordenada relativa a l'origen del terreny (float32, com la GPU) conserva la diferencia amb la camera amb un
     error molt menor que un pixel de z = 19;
   - reduccions de les teselles (mipmaps) i el zoom triat per a cada altura;
   - sense xarxa (servidor inexistent): no hi ha cap excepcio, la tesella compta com a fallada i no es torna a
     demanar fins passat ESPERA_ERROR_S.
2. Programa real (finestra amagada, 1280 x 860; necessita xarxa el primer cop, despres llegeix data/cache/teselles):
   - alineacio: a Vic, la fotografia del mosaic contra l'ortofoto descarregada de la zona (F18, la mateixa font
     pero un altre cami: WMS en UTM): desplacament per correlacio de fase;
   - a l'Escala, des de dalt, la foto sobre el pegat de 5 m contra la mateixa foto sense el pegat (graella general):
     bloc a bloc al centre de la imatge, no s'ha de moure (la F21 la movia ~1 m per vertex: es veia esmicolada);
   - globus contra terreny: a la costa (delta de l'Ebre, relleu ~0 m), la imatge del globus (Mercator calculada per
     fragment) contra la del terreny (Mercator per vertex);
   - temps de carrega i per fotograma, amb el mosaic i sense;
   - controls de la vista aeria: arrossegar deixa el punt agafat sota el cursor; la roda s'hi acosta sense que es
     mogui de la pantalla; orbitar el deixa al mateix pixel i no passa per sota del terra; la inercia s'atura;
   - doble clic: primera persona al punt, mirant cap on mirava la camera, amb edificis; a la vista aeria, sense.
3. Captures a captures/proves/mosaic_*.png.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_mosaic.py
"""
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402

CARPETA = os.path.join(ARREL, 'captures', 'proves')
errors = []


def ok(condicio, text):
    print(('   OK    ' if condicio else '   ERROR ') + text)
    if not condicio:
        errors.append(text)


def desplacament(a, b):
    """Desplacament (dx, dy) en pixels de la imatge b respecte de a (correlacio de fase, amb precisio de subpixel
    per l'ajust d'una parabola al maxim) i la qualitat del maxim (1 = imatges identiques)."""
    a = a - a.mean()
    b = b - b.mean()
    finestra = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa, fb = np.fft.fft2(a * finestra), np.fft.fft2(b * finestra)
    r = fa.conj() * fb
    c = np.real(np.fft.ifft2(r / np.maximum(np.abs(r), 1e-9)))
    i, j = np.unravel_index(np.argmax(c), c.shape)

    def fi(v, k, n):
        e, d = v[(k - 1) % n], v[(k + 1) % n]
        den = e - 2 * v[k] + d
        return k + (0.5 * (e - d) / den if abs(den) > 1e-12 else 0.0)
    y = fi(c[:, j], i, c.shape[0])
    x = fi(c[i, :], j, c.shape[1])
    y = y - c.shape[0] if y > c.shape[0] / 2 else y
    x = x - c.shape[1] if x > c.shape[1] / 2 else x
    return x, y, float(c.max())


def sense_finestra():
    from dades import teselles
    print('== Coordenades i teselles (sense finestra)')
    x, y = teselles.mercator(41.93, 2.255)
    ok((int(x * 2 ** 17), int(y * 2 ** 17)) == (66357, 48690), f'Vic (41,93 N, 2,255 E) a z = 17: tesella '
       f'({int(x * 2 ** 17)}, {int(y * 2 ** 17)}) (la que serveix l\'IGN: 66357, 48690)')
    # la camera i un vertex a 3 km, en una zona de 40 km (origen al centre): diferencia en float64 contra la de la GPU
    # (vertex i camera relatius a l'origen, en float32)
    origen = np.array(teselles.mercator(41.90, 2.20))
    cam = np.array(teselles.mercator(41.93, 2.25))
    vertex = np.array(teselles.mercator(41.95, 2.28))
    gpu = ((vertex - origen).astype('f4') - (cam - origen).astype('f4')).astype(float)
    err_px = np.abs(gpu - (vertex - cam)).max() * 2 ** 19 * 256
    ingenu = np.abs((vertex.astype('f4') - cam.astype('f4')).astype(float) - (vertex - cam)).max() * 2 ** 19 * 256
    ok(err_px < 0.01, f'Mercator relativa a l\'origen del terreny: error {err_px:.1e} pixels de z = 19 (restant directament en float32 '
       f'seria {ingenu:.1f} pixels)')
    zooms = {h: teselles.zoom_per_resolucio(h * 1000 * math.radians(50) / 860, 42.0) for h in (0.0017, 1.45, 25, 8000)}
    ok(zooms[0.0017] == 19 and 16 <= zooms[1.45] <= 18 and zooms[8000] <= 6,
       'zoom per altura (camp de 50 graus, 860 px): ' + ', '.join(f'{h} km -> z{z}' for h, z in zooms.items()))
    rgb = np.random.default_rng(1).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    nivells = teselles.reduccions(rgb)
    ok([n.shape[0] for n in nivells] == [256 >> k for k in range(9)] and
       abs(float(nivells[8][0, 0, 0]) - rgb[..., 0].mean()) < 1.0 and (nivells[3][..., 3] == 255).all(),
       'reduccions: 9 nivells (256 ... 1 px), mitjanes 2 x 2, opaques')
    # sense xarxa: un servidor que no existeix
    fonts = dict(teselles.FONTS)
    teselles.FONTS['pnoa'] = 'http://servidor-inexistent.invalid/{z}/{x}/{y}.jpg'
    teselles.FONTS['eox'] = teselles.FONTS['pnoa']
    d = teselles.Descarregador(lambda z, x, y: True, fils=2)
    clau = (19, 1, 1)     # una tesella de l'Artic que no es a la cache
    d.demanar(clau, 0.0)
    t0 = time.time()
    while d.pendents() and time.time() - t0 < 30:
        time.sleep(0.1)
    d.demanar(clau, 0.0)
    ok(d.fallades == 1 and d.pendents() == 0, 'sense xarxa: la tesella falla sense cap excepcio i no es torna a '
       f'demanar fins d\'aqui a {teselles.ESPERA_ERROR_S:.0f} s')
    d.aturar()
    teselles.FONTS.update(fonts)


def amb_finestra():
    import glfw
    from slimgui import imgui
    from PIL import Image
    from dades import geodesia

    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades.observador import UBICACIONS_PROVES
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova del mosaic', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    ce = app.camera_exploracio

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

    def imatge():
        app.ctx.finish()
        return Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    def esperar(maxim_s=120):
        """Fotogrames fins que totes les teselles que calen son a la textura. Retorna el temps."""
        t = time.time()
        while time.time() - t < maxim_s:
            fotograma(3)
            if app.mosaic.estat()[0] == 0:
                break
        fotograma(2)
        return time.time() - t

    def temps_fotograma(n=60):
        fotograma(5)
        app.ctx.finish()
        t = time.perf_counter()
        fotograma(n)
        app.ctx.finish()
        return (time.perf_counter() - t) / n * 1000

    def punt_sota_cursor(pixel=None):   # el picking llegeix el framebuffer de la prova (el programa, la pantalla)
        mx, my = io.mouse_pos
        px, py = (int(mx), H - 1 - int(my)) if pixel is None else pixel[:2]
        d = float(np.frombuffer(objectiu.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'), 'f4')[0])
        return None if d >= 1.0 else app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
    app.punt_sota_cursor = punt_sota_cursor

    def pixel_cursor():         # el framebuffer de la prova te un pixel per punt (la finestra pot ser Retina)
        mx, my = io.mouse_pos
        px, py = int(mx), H - 1 - int(my)
        return (px, py, W, H) if 0 <= px < W and 0 <= py < H else None
    app.pixel_cursor = pixel_cursor

    def pixel_de(p):
        """Pixel (x cap a la dreta, y cap avall, com el cursor) on es veu el punt p (ECEF)."""
        cam = app.camera
        q = cam.m_proj * cam.m_view * glm.vec4(*(p - cam.posicio), 1.0)
        return (q.x / q.w * 0.5 + 0.5) * W, (0.5 - q.y / q.w * 0.5) * H

    import glm
    os.makedirs(CARPETA, exist_ok=True)
    nom, lat, lon = next(u for u in UBICACIONS_PROVES if u[0].startswith('Vic'))
    app.triar_ubicacio(lat, lon, nom)
    app.hora = 14.5     # 16:30 hora local: Sol alt, abans de l'eclipsi
    app.canviar_vista(0)

    def posar(lat_c, lon_c, alt_km, rumb, incl):
        ce.caminar = False
        ce.posicio = geodesia.ecef(lat_c, lon_c, alt_km)
        ce.orientar(rumb, incl)
        ce.inercia, ce.zoom_pendent = None, 0.0

    print('\n== Carrega i temps (finestra amagada 1280 x 860)')
    vistes = {'google_earth': (41.9288 - 0.0107, 2.2553, 0.486 + 1.19, 0.0, -55.0),   # com l'enllac de l'equip
              'aire_20km': (41.6, 2.2, 25.0, 0.0, -45.0),
              'espai': (40.0, 0.0, 8000.0, 0.0, -89.0)}
    for nom_v, v in vistes.items():
        posar(*v)
        t = esperar()
        p, baixades, disc, fallades = app.mosaic.estat()
        imatge().save(os.path.join(CARPETA, f'mosaic_{nom_v}.png'))
        con = temps_fotograma()
        app.mosaic.actiu = False
        sense = temps_fotograma()
        app.mosaic.actiu = True
        print(f'   {nom_v:13s} zoom {app.mosaic.zoom_fi:2d}: completa en {t:5.1f} s (acumulat: {baixades} baixades, '
              f'{disc} del disc, {fallades} fallades); {con:5.1f} ms amb el mosaic, {sense:5.1f} ms sense')
    ok(app.mosaic.estat()[3] == 0, 'cap tesella fallada')

    print('\n== Alineacio')
    # (la comparacio amb l'ortofoto de Vic ja no es fa: des de la F38 el programa no la carrega)
    gris = lambda img: np.asarray(img.convert('L'), dtype=float)[100:740, 320:960]
    # globus contra terreny, al delta de l'Ebre (relleu ~0)
    posar(40.70, 0.80, 3.0, 0.0, -89.0)
    esperar()
    terreny = gris(imatge())
    app.peninsula.visible = False
    if app.zona is not None:
        app.zona.visible = False
    fotograma(2)
    globus = gris(imatge())
    app.peninsula.visible = True
    if app.zona is not None:
        app.zona.visible = True
    dx, dy, q = desplacament(terreny, globus)
    m_px = 3.0 * 2 * math.tan(math.radians(ce.fov / 2)) / H * 1000
    ok(math.hypot(dx, dy) * m_px < 5.0, f'delta de l\'Ebre des de 3 km: globus contra terreny {dx:+.2f}, {dy:+.2f} px '
       f'({math.hypot(dx, dy) * m_px:.1f} m; 1 px = {m_px:.1f} m), maxim {q:.2f}')
    # pegat de 5 m contra graella general, a l'Escala des de 200 m (el pegat es posa al voltant del punt d'observacio)
    _, lat_e, lon_e = next(u for u in UBICACIONS_PROVES if 'Escala' in u[0])
    app.triar_punt(lat_e, lon_e, 'Escala')
    posar(lat_e, lon_e, 0.2, 0.0, -89.9)
    esperar()
    amb = np.asarray(imatge().convert('L'), dtype=float)
    pegat = app.zona.pegat
    app.zona.pegat = None
    fotograma(2)
    sense = np.asarray(imatge().convert('L'), dtype=float)
    app.zona.pegat = pegat
    blocs = [desplacament(amb[y:y + 128, x:x + 128], sense[y:y + 128, x:x + 128])[:2]
             for y in (238, 366, 494) for x in (448, 576, 704)]
    pitjor = max(math.hypot(*b) for b in blocs)
    m_px = 0.2 * 2 * math.tan(math.radians(ce.fov / 2)) / H * 1000
    ok(pitjor < 0.5, f'l\'Escala des de 200 m: foto sobre el pegat de 5 m contra la graella general, 9 blocs del '
       f'centre: com a molt {pitjor:.2f} px ({pitjor * m_px * 100:.0f} cm; 1 px = {m_px * 100:.0f} cm)')
    app.triar_ubicacio(lat, lon, nom)

    print('\n== Controls de la vista aeria')
    posar(41.9288 - 0.0107, 2.2553, 0.486 + 1.19, 0.0, -55.0)
    esperar()

    def moure_cursor(x, y, n=1):
        io.add_mouse_pos_event(x, y)
        fotograma(n)

    def arrossegar(cami, boto=0, shift=False, deixar_anar=True):
        time.sleep(0.4)          # dos clics seguits al mateix lloc serien un doble clic (temps real d'imgui)
        moure_cursor(*cami[0], 2)
        if shift:
            io.add_key_event(imgui.Key.KEY_LEFT_SHIFT, True)
            io.add_key_event(imgui.Key.MOD_SHIFT, True)
        io.add_mouse_button_event(boto, True)
        fotograma()
        for x, y in cami[1:]:
            moure_cursor(x, y)
        if not deixar_anar:
            return
        io.add_mouse_button_event(boto, False)
        if shift:
            io.add_key_event(imgui.Key.KEY_LEFT_SHIFT, False)
            io.add_key_event(imgui.Key.MOD_SHIFT, False)
        fotograma()

    moure_cursor(700, 500, 2)
    agafat = punt_sota_cursor()
    alt0 = ce.alcada_sobre_terra()
    cami = [(700 + 10 * i, 500 - 6 * i) for i in range(16)]
    arrossegar(cami, deixar_anar=False)      # amb el boto premut (deixar-lo anar en moviment continuaria)
    fotograma()
    px, py = pixel_de(agafat)
    io.add_mouse_button_event(0, False)
    fotograma()
    ce.inercia = None
    ok(math.hypot(px - cami[-1][0], py - cami[-1][1]) < 1.5 and abs(ce.alcada_sobre_terra() - alt0) < 0.02 * alt0,
       f'arrossegar: el punt agafat acaba a ({px:.1f}, {py:.1f}), sota el cursor ({cami[-1][0]}, {cami[-1][1]}); '
       f'altura {alt0 * 1000:.0f} -> {ce.alcada_sobre_terra() * 1000:.0f} m')
    # inercia: deixar-lo anar en moviment continua i s'atura
    p0 = ce.posicio.copy()
    arrossegar([(600 + 15 * i, 450) for i in range(10)])
    continua = ce.inercia is not None
    fotograma(240)
    ok(continua and ce.inercia is None, f'inercia: en deixar anar el terra en moviment continua '
       f'{np.linalg.norm(ce.posicio - p0) * 1000:.0f} m en total i s\'atura sola')
    # roda cap al cursor
    moure_cursor(500, 400, 2)
    punt = punt_sota_cursor()
    d0 = np.linalg.norm(punt - ce.posicio)
    pix0 = pixel_de(punt)
    app.ratoli.on_scroll(app.window, 0.0, 2.0)
    fotograma(90)
    d1 = np.linalg.norm(punt - ce.posicio)
    pix1 = pixel_de(punt)
    ok(abs(d1 / d0 - 1.35 ** -2) < 0.01 and math.hypot(pix1[0] - pix0[0], pix1[1] - pix0[1]) < 0.5,
       f'roda (2 passos) cap al cursor: distancia al punt {d0 * 1000:.0f} -> {d1 * 1000:.0f} m (x{d1 / d0:.3f}; '
       f'esperat x{1.35 ** -2:.3f}), el punt es mou {math.hypot(pix1[0] - pix0[0], pix1[1] - pix0[1]):.2f} px')
    passos = []
    app.ratoli.on_scroll(app.window, 0.0, -2.0)
    for _ in range(30):
        q = ce.posicio.copy()
        fotograma()
        passos.append(np.linalg.norm(ce.posicio - q))
    ok(max(passos) < 0.2 * sum(passos), f'la roda es suau: el pas mes gran d\'un fotograma es el '
       f'{max(passos) / sum(passos) * 100:.0f} % del moviment (repartit en uns quants fotogrames)')
    fotograma(60)
    # orbitar amb Shift: al voltant del punt del centre de la pantalla
    moure_cursor(640, 430, 2)
    centre = punt_sota_cursor()
    pix0 = (W / 2, H / 2)
    arrossegar([(640 + 8 * i, 430 + 3 * i) for i in range(20)], shift=True)
    pix1 = pixel_de(centre)
    sobre = float((ce.posicio - centre) @ (centre / np.linalg.norm(centre)))
    ok(math.hypot(pix1[0] - pix0[0], pix1[1] - pix0[1]) < 2.0 and sobre > 0,
       f'Shift + arrossegar: orbita al voltant del punt del centre (es mou {math.hypot(pix1[0] - pix0[0], pix1[1] - pix0[1]):.2f} px '
       f'de la pantalla), rumb {ce.rumb:.0f}, inclinacio {ce.inclinacio:.0f}, {sobre * 1000:.0f} m per sobre del punt')
    arrossegar([(640, 430 - 20 * i) for i in range(40)], shift=True)     # inclinar molt: no passa per sota
    sobre = float((ce.posicio - centre) @ (centre / np.linalg.norm(centre)))
    ok(sobre > 0 and ce.inclinacio < 0 and ce.alcada_sobre_terra() > 0.0015,
       f'inclinar fins al limit: la camera queda {sobre * 1000:.0f} m per sobre del punt i mirant avall '
       f'({ce.inclinacio:.1f} graus)')

    print('\n== Doble clic i edificis')
    posar(41.9288 - 0.0107, 2.2553, 0.486 + 1.19, 30.0, -55.0)
    fotograma(3)
    ok(app.edificis is not None and not app.edificis.visible, 'vista aeria: els edificis no es dibuixen')
    rumb = ce.rumb
    for _ in range(2):
        moure_cursor(640, 430, 1)
        io.add_mouse_button_event(0, True)
        fotograma()
        io.add_mouse_button_event(0, False)
        fotograma()
    fotograma(3)
    co = app.camera_observador
    ok(app.vista == 1 and abs(co.rumb - rumb) < 1e-6 and abs(co.inclinacio - programa.INCLINACIO_EN_ARRIBAR) < 1e-6,
       f'doble clic: primera persona al punt ({app.observador.lat:.5f}, {app.observador.lon:.5f}), mirant cap on mirava '
       f'la camera (rumb {co.rumb:.0f}, {co.inclinacio:.0f} graus)')
    ok(app.edificis.visible, 'en primera persona, els edificis es dibuixen')
    esperar()
    imatge().save(os.path.join(CARPETA, 'mosaic_primera_persona.png'))
    print(f'   primera persona: {temps_fotograma():.1f} ms per fotograma')
    app.canviar_vista(0)
    fotograma(2)
    ok(not app.edificis.visible and np.linalg.norm(ce.posicio - geodesia.ecef(41.9288 - 0.0107, 2.2553, 0.486 + 1.19)) < 1e-6,
       'V: es torna a la vista aeria on era la camera, sense edificis')
    app.edificis_aeris = True
    fotograma(2)
    ok(app.edificis.visible, 'opcio "Edificis tambe a la vista aeria": es dibuixen')
    app.edificis_aeris = False
    app._shutdown()


def main():
    sense_finestra()
    amb_finestra()
    print('\nTOT CORRECTE' if not errors else f'\n{len(errors)} ERRORS')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
