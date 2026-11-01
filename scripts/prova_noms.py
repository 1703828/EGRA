"""
Prova dels noms de lloc sobre el mapa (ui.noms_al_mapa, data/noms_mapa.json) amb el programa real i el panell dibuixat.

  1. El fitxer hi es i te els tres nivells (capitals de l'Estat i de comunitat, de provincia i de comarca).
  2. Amb la camera d'exploracio sobre Catalunya, mirant avall, a diferents altures: quins nivells s'escriuen a cada
     altura (ALCADES_NOMS) i que de prop no se n'escriu cap. Es compten els textos que el panell afegeix a la llista
     de dibuix de fons d'imgui (un nom = un punt).
  3. Des del terra i caminant no s'escriuen.
Captures a captures/proves/noms_<altura>km.png (carpeta ignorada pel Git).

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/prova_noms.py
"""
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
SORTIDA = os.path.join(ARREL, 'captures', 'proves')

import glfw  # noqa: E402
from OpenGL import GL  # noqa: E402
from PIL import Image  # noqa: E402
from slimgui import imgui  # noqa: E402


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    import ui
    from dades import geodesia, noms

    app = programa.GraphicsEngine(win_size=(1280, 860), title='EGRA - prova dels noms', use_ui_panel=True)
    W, H = glfw.get_framebuffer_size(app.window)
    objectiu = app.ctx.simple_framebuffer((W, H))
    os.makedirs(SORTIDA, exist_ok=True)
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    escrits = []
    original = ui.noms_al_mapa

    def comptar(a):
        """Els noms que s'escriuen aquest fotograma: es comptaran els punts (add_circle_filled) de la llista de fons."""
        dl = imgui.get_background_draw_list()
        escrits.clear()
        punts = []
        cercle = type(dl).add_circle_filled

        def registrar(self, centre, *args, **kwargs):
            punts.append(centre)
            return cercle(self, centre, *args, **kwargs)
        type(dl).add_circle_filled = registrar
        try:
            original(a)
        finally:
            type(dl).add_circle_filled = cercle
        escrits.extend(punts)
    ui.noms_al_mapa = comptar

    def fotograma(n=1):
        for _ in range(n):
            glfw.poll_events()
            app.dt = 1 / 60
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
            imgui.begin('Eclipsi')
            app.build_ui()
            imgui.end()
            imgui.render()
            GL.glUseProgram(0)
            objectiu.use()
            app.ui_renderer.render(imgui.get_draw_data())

    llista = noms.noms_mapa()
    nivells = [sum(n == k for _, n, _, _ in llista) for k in range(3)]
    ok(all(nivells), f'data/noms_mapa.json: {len(llista)} noms (nivell 0: {nivells[0]}, 1: {nivells[1]}, '
                     f'2: {nivells[2]})')

    # camera d'exploracio sobre el centre de Catalunya, mirant avall (una mica inclinada)
    lat, lon = 41.7251, 1.8266     # Manresa (capital del Bages): a 8 km ha de quedar a la imatge
    app.canviar_vista(0)
    ce = app.camera_exploracio
    ce.caminar = False
    for alcada in (1200.0, 300.0, 60.0, 8.0, 1.5):
        ce.posicio = geodesia.ecef(lat - alcada / 400.0, lon, alcada)
        ce.orientar(0.0, -70.0)
        fotograma(4)
        esperats = {k for k, (h0, h1) in ui.ALCADES_NOMS.items() if h0 < alcada < h1}
        fotograma()
        n = len(escrits)
        Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(SORTIDA, f'noms_{alcada:g}km.png'))
        if esperats:
            ok(n > 0, f'a {alcada:g} km: {n} noms escrits (nivells que toquen: {sorted(esperats)})')
        else:
            ok(n == 0, f'a {alcada:g} km: cap nom (de prop desapareixen); escrits {n}')
    # nivell 2 (comarques) nomes per sota de 200 km: a 60 km hi ha d'haver mes noms que a 300 km
    ce.posicio = geodesia.ecef(lat - 0.15, lon, 60.0)
    ce.orientar(0.0, -70.0)
    fotograma(3)
    n60 = len(escrits)
    ce.posicio = geodesia.ecef(lat - 0.75, lon, 300.0)
    fotograma(3)
    n300 = len(escrits)
    ok(n60 > 0 and n300 > 0, f'a 60 km {n60} noms (amb comarques) i a 300 km {n300} (provincies i comunitats)')
    # des del terra i caminant, cap
    app.canviar_vista(1)
    fotograma(3)
    ok(len(escrits) == 0, f'des del terra: cap nom ({len(escrits)})')
    app.mostrar_noms = False
    app.canviar_vista(0)
    ce.posicio = geodesia.ecef(lat - 0.15, lon, 60.0)
    fotograma(3)
    ok(len(escrits) == 0, f'casella "Noms de lloc" desactivada: cap nom ({len(escrits)})')
    print()
    print('Tot correcte' if not errors else f'{len(errors)} errors')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
