"""
Captures reproduibles dels quatre mapes (tasques 44 i 47.6 del pla) amb el programa real (finestra amagada): cada mapa
i mode a tres escales (la peninsula, el Valles des de 40 km, la UAB des de 500 m, amb la camera inclinada), a l'hora
indicada (per defecte, el maxim a la UAB). Les peces de dades es deixen preparar (com a molt --espera segons per
escala). Es desen a captures/mapes/<eclipsi>_<mapa>_<mode>_<escala>.png i un full resum
captures/mapes/<eclipsi>_resum.png (files: mapes; columnes: escales).

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/captura_mapes.py [--eclipsi 2026] [--minuts 0] [--espera 120]
--minuts: minuts respecte del maxim a la UAB (p. ex. -20).
"""
import argparse
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from slimgui import imgui  # noqa: E402

W, H = 900, 640
SORTIDA = os.path.join(ARREL, 'captures', 'mapes')
UAB = (41.5009, 2.1055)
ESCALES = [('peninsula', 40.0, -3.7, 1300.0, 0.0, -89.0), ('valles_40km', 41.30, 2.10, 40.0, 10.0, -60.0),
           ('uab_500m', UAB[0] - 0.006, UAB[1], 0.5, 0.0, -40.0)]
MAPES = [('ocultacio', 'maxim'), ('ocultacio', 'ara'), ('durada', 'tot'), ('durada', 'central'), ('relleu', 'ara'),
         ('relleu', 'maxim'), ('ombra', 'ara')]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--eclipsi', default='2026')
    p.add_argument('--minuts', type=float, default=0.0)
    p.add_argument('--espera', type=float, default=120.0)
    p.add_argument('--mapes', default='', help='p. ex. ombra,ocultacio (per defecte, tots)')
    a = p.parse_args()
    mapes = [m for m in MAPES if not a.mapes or m[0] in a.mapes.split(',')]
    os.makedirs(SORTIDA, exist_ok=True)
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - captures dels mapes', use_ui_panel=True)
    fb = app.ctx.simple_framebuffer((W, H))

    def fotograma(n=1, panell=True):
        for _ in range(n):
            glfw.poll_events()
            app.dt = 1 / 30
            app.ui_renderer.new_frame()
            imgui.new_frame()
            fb.use()
            app.render()
            if panell:
                imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
                imgui.begin('Opcions')
                app.build_ui()
                imgui.end()
            imgui.render()
            app.ui_renderer.render(imgui.get_draw_data())
            app.ctx.finish()

    app.canviar_eclipsi(a.eclipsi)
    app.triar_ubicacio(UAB[0], UAB[1], 'UAB, placa Civica')
    app.hora = app.model.hores['maxim'] + a.minuts / 60.0
    app.canviar_vista(0)
    cam = app.camera_exploracio
    imatges = {}
    for escala, lat, lon, alt, rumb, incl in ESCALES:
        cam.aturar_moviment()
        cam.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + alt)
        cam.orientar(rumb, incl)
        # les dades de nivells (temps observable) es deixen preparar una vegada per escala
        app.mapes.mostrar('durada', 'tot')
        t0 = time.time()
        fotograma(10)
        while time.time() - t0 < a.espera and (app.mapes.ocupat() or app.detall.feines or time.time() - t0 < 3
                                               or not any(k[0] == 0 for k in app.mapes.peces)):
            fotograma(5)
        for quin, mode in mapes:
            app.mapes.mostrar(quin, mode)
            t1 = time.time()
            fotograma(5, panell=False)
            while time.time() - t1 < 60 and (app.mapes.ocupat() or time.time() - t1 < 1):
                fotograma(3, panell=False)
            fotograma(3, panell=False)
            im = Image.frombytes('RGB', (W, H), fb.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)
            nom = f'{a.eclipsi}_{quin}_{mode}_{escala}'
            im.save(os.path.join(SORTIDA, nom + '.png'))
            imatges[(quin, mode, escala)] = im
            if escala == 'uab_500m':        # amb el panell: la llegenda i d'on surten les dades
                fotograma(3)
                Image.frombytes('RGB', (W, H), fb.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
                    os.path.join(SORTIDA, nom + '_panell.png'))
            print(f'{nom}: {app.mapes.text_nivell_centre()}', flush=True)
    # full resum
    w, h = W // 3, H // 3
    full = Image.new('RGB', (w * len(ESCALES) + 160, h * len(mapes)), (20, 20, 20))
    d = ImageDraw.Draw(full)
    for i, (quin, mode) in enumerate(mapes):
        d.text((6, i * h + h // 2), f'{quin}\n{mode}', fill=(230, 230, 230))
        for j, (escala, *_) in enumerate(ESCALES):
            full.paste(imatges[(quin, mode, escala)].resize((w, h)), (160 + j * w, i * h))
    full.save(os.path.join(SORTIDA, f'{a.eclipsi}_resum{"_" + a.mapes.replace(",", "_") if a.mapes else ""}.png'))
    print(f'Captures a {SORTIDA}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
