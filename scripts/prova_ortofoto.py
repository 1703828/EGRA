"""
Prova de l'ortofoto del PNOA a una zona de detall (per defecte Vic): mesures i captures per valorar-la.

1. Alineacio (sense finestra): les vores dels contorns del Catastro contra les vores de la foto (gradient), en
   1,5 x 1,5 km al voltant del punt, desplacant els contorns fins a +-3 m. Si la foto i els contorns estan ben
   alineats, la coincidencia maxima es a prop de (0, 0). Els edificis alts hi surten inclinats (la foto no es
   ortofoto vertadera): aixo eixampla el maxim, pero no el desplaca gaire.
2. Programa real (finestra amagada, 1280 x 860): mida dels fitxers, temps de carrega, memoria de les textures
   (calculada: amplada x alcada x 4 bytes x 4/3 dels mipmaps; el controlador no la informa), i temps per fotograma
   (mitjana de 120 fotogrames, amb ctx.finish) a les vistes de la captura, amb fotografia i sense.
3. Captures (captures/proves/ortofoto_<zona>_*.png i una lamina): caminant a la placa (quatre direccions), a 60 m,
   400 m, 3 km i 20 km, amb fotografia i sense; a les 16:30 (Sol alt) i al maxim de l'eclipsi.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_ortofoto.py [vic]
"""
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

ZONA = sys.argv[1] if len(sys.argv) > 1 else 'vic'
CARPETA = os.path.join(ARREL, 'captures', 'proves')


def alineacio(detall, zona, centre_xy):
    from rasterio import features
    from scipy import ndimage
    from dades.edificis import llegir_zona
    parts = llegir_zona(zona)
    with rasterio.open(detall) as f:
        res = f.transform.a
        col, fil = ~f.transform * centre_xy
        mig = int(750 / res)
        fin = rasterio.windows.Window(int(col) - mig, int(fil) - mig, 2 * mig, 2 * mig)
        img = f.read(window=fin).astype('f4').mean(axis=0)
        t = f.window_transform(fin)
    b = rasterio.transform.array_bounds(img.shape[0], img.shape[1], t)
    sel = parts.cx[b[0]:b[2], b[1]:b[3]]
    mascara = features.rasterize(((g, 1) for g in sel.geometry), out_shape=img.shape, transform=t, dtype='u1')
    vora = (ndimage.binary_dilation(mascara) ^ ndimage.binary_erosion(mascara)).astype('f4')
    gx, gy = ndimage.sobel(ndimage.gaussian_filter(img, 1.0), 1), ndimage.sobel(ndimage.gaussian_filter(img, 1.0), 0)
    grad = np.hypot(gx, gy)
    grad = (grad - grad.mean()) / grad.std()
    m = int(3 / res)
    puntuacio = np.zeros((2 * m + 1, 2 * m + 1))
    for i, dy in enumerate(range(-m, m + 1)):
        for j, dx in enumerate(range(-m, m + 1)):
            puntuacio[i, j] = (np.roll(np.roll(vora, dy, 0), dx, 1)[m:-m, m:-m] * grad[m:-m, m:-m]).sum() / vora.sum()
    i, j = np.unravel_index(np.argmax(puntuacio), puntuacio.shape)
    dx, dy = (j - m) * res, -(i - m) * res      # files cap avall = sud
    return dx, dy, puntuacio[m, m], puntuacio.max(), len(sel)


def main():
    import glfw
    from slimgui import imgui
    from PIL import Image, ImageDraw
    from dades.data_io import ortofotos
    from dades.edificis import ZONA_DE_LA_UBICACIO
    from dades import geodesia

    general, detalls = ortofotos(ZONA)
    if general is None:
        print(f'Sense ortofoto de {ZONA}: python scripts/descarregar_ortofoto.py {ZONA}')
        return 1
    print(f'== Fitxers ({ZONA})')
    for cami in [general] + [c for c, _ in detalls]:
        with rasterio.open(cami) as f:
            print(f'   {os.path.relpath(cami, ARREL)}: {f.width} x {f.height} px a {f.transform.a:g} m, '
                  f'{os.path.getsize(cami) / 1e6:.1f} MB al disc; a la GPU ~{f.width * f.height * 4 * 4 / 3 / 1e6:.0f} MB '
                  f'(RGBA8 amb mipmaps)')

    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades.observador import UBICACIONS_PROVES
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de l\'ortofoto', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    ce, co = app.camera_exploracio, app.camera_observador

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

    def temps_fotograma(n=120):
        fotograma(5)
        app.ctx.finish()
        t = time.perf_counter()
        fotograma(n)
        app.ctx.finish()
        return (time.perf_counter() - t) / n * 1000

    def imatge():
        app.ctx.finish()
        return Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    nom, lat, lon = next(u for u in UBICACIONS_PROVES if ZONA_DE_LA_UBICACIO[u[0]] == ZONA)
    t0 = time.time()
    app.triar_ubicacio(lat, lon, nom)
    print(f'   carregar la zona amb l\'ortofoto: {time.time() - t0:.1f} s (inclou el relleu i els edificis)')
    if app.zona.orto is None:
        print('El programa no ha carregat l\'ortofoto')
        return 1
    o = app.observador
    x, y = app.edificis.obstacles.utm(o.lat, o.lon) if app.edificis else app.peninsula.de_latlon.transform(o.lon, o.lat)
    if app.zona.orto_detall is not None:
        dx, dy, p0, pmax, n = alineacio(app.zona.camins_orto[1], ZONA, (x, y))
        print(f'\n== Alineacio foto - Catastro ({n} parts en 1,5 x 1,5 km): maxim a ({dx:+.1f} m est, {dy:+.1f} m nord); '
              f'coincidencia {pmax:.2f} (a 0,0: {p0:.2f})')

    os.makedirs(CARPETA, exist_ok=True)
    m = app.model
    hores = [('16h30', 14.5), ('maxim', m.hores['maxim'])]
    _, _, amunt = geodesia.base_local(o.lat, o.lon)
    # vistes: (nom, funcio que posa la camera)
    def caminant(rumb):
        def f():
            app.caminar_des_del_punt()
            ce.orientar(rumb, 2.0)
        return f

    def aire(dist_km, inclinacio):
        def f():
            ce.caminar = False
            app.canviar_vista(0)
            az = 200.0
            ce.posicio = app.ulls() + dist_km * (math.cos(math.radians(inclinacio)) * -geodesia.base_local(o.lat, o.lon)[1]
                                                 + math.sin(math.radians(inclinacio)) * amunt)
            lat_c, lon_c, _ = ce.geodesiques()
            az, el = geodesia.azimut_elevacio(app.ulls() - ce.posicio, lat_c, lon_c)
            ce.orientar(az, el)
        return f
    vistes = [('carrer_N', caminant(0.0)), ('carrer_E', caminant(90.0)), ('carrer_S', caminant(180.0)),
              ('carrer_O', caminant(270.0)), ('aire_60m', aire(0.12, 30.0)), ('aire_400m', aire(0.6, 40.0)),
              ('aire_3km', aire(4.0, 45.0)), ('aire_20km', aire(25.0, 50.0))]
    print('\n== Temps per fotograma (ms, finestra amagada 1280 x 860) i captures')
    files = []
    for nom_h, h in hores:
        app.hora, app.reproduint = h, False
        for nom_v, posar in vistes:
            fila = []
            for amb in (True, False):
                app.usar_ortofoto = amb
                posar()
                fotograma(3)
                img = imatge()
                img.save(os.path.join(CARPETA, f'ortofoto_{ZONA}_{nom_h}_{nom_v}_{"foto" if amb else "rampa"}.png'))
                ms = temps_fotograma(60) if nom_h == '16h30' else None
                fila.append((img, ms))
            if fila[0][1] is not None:
                print(f'   {nom_v:10s} amb foto {fila[0][1]:5.1f} ms   sense {fila[1][1]:5.1f} ms')
            files.append((f'{nom_h} {nom_v}', fila))
    # lamina: a l'esquerra amb foto, a la dreta sense
    mw, mh = 480, 322
    lam = Image.new('RGB', (2 * mw, len(files) * (mh + 18)), (30, 30, 30))
    d = ImageDraw.Draw(lam)
    for k, (titol, fila) in enumerate(files):
        for c, (img, _) in enumerate(fila):
            lam.paste(img.resize((mw, mh)), (c * mw, k * (mh + 18) + 18))
        d.text((6, k * (mh + 18) + 3), f'{titol}   (esquerra: fotografia aeria; dreta: color per altitud)', fill=(230, 230, 230))
    cami = os.path.join(CARPETA, f'ortofoto_{ZONA}_lamina.jpg')
    lam.save(cami, quality=85)
    print(f'   captures a {os.path.relpath(CARPETA, ARREL)}/ortofoto_{ZONA}_*.png; lamina: {os.path.relpath(cami, ARREL)}')
    app._shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
