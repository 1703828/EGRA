"""
Comprova els llocs amb detall (dades/llocs.py) i el doble clic (main.py, basecode/detall.py).

1. Sense finestra: quadricula de 3 km (clau del centre mes proper), cobertura dels edificis (la cel·la, 3 x 3 km),
   els llocs antics (centre arrodonit a 100 m, 2 x 2 km amb 500 m de marge) i l'esborrat dels mes antics (amb
   fitxers de prova en una carpeta temporal: no toca els llocs reals).
2. Amb el programa (finestra amagada):
   - doble clic a la UAB (edificis de la zona del Valles): no es prepara cap lloc;
   - doble clic al mar: no es prepara cap lloc;
   - doble clic a Manresa: el lloc antic del disc es carrega al moment (zona i edificis) i l'observador queda
     sobre el seu relleu de 5 m;
   - en reproduccio, a la vista des del terra, una zona que s'acaba de carregar no canvia el relleu de sota
     l'observador fins a la pausa.
El detall que es prepara en navegar (relleu, edificis i mapa nous) el prova scripts/prova_detall.py.
Captures a captures/proves/llocs_*.png.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_llocs.py
"""
import os
import sys
import tempfile
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
from PIL import Image  # noqa: E402
from slimgui import imgui  # noqa: E402

from dades import llocs  # noqa: E402

SORTIDA = os.path.join(ARREL, 'captures', 'proves')
MANRESA = (41.72495, 1.8266)
IGUALADA = (41.5791, 1.6172)
UAB = (41.50220, 2.10416)
XARXA = '--xarxa' in sys.argv
MAR = (41.30, 2.60)


def main():
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    # ------------------------------------------------------------ 1. sense finestra
    print('== 1. Quadricula, cobertura i esborrat')
    c = llocs.clau_per_punt(901400.0, 4629600.0)
    ok(c == 'lloc_900000_4629000' and llocs.de_quadricula(c), f'el punt (901400, 4629600) es del lloc {c}')
    ok(llocs.cobreix(c, 900000 + 1499, 4629000 - 1499) and not llocs.cobreix(c, 900000 + 1501, 4629000),
       'els edificis del lloc cobreixen la seva cel·la (1,5 km al voltant del centre)')
    antic = llocs.clau(901500.0, 4630500.0)
    ok(not llocs.de_quadricula(antic) and llocs.cobreix(antic, 901500 + 499, 4630500 - 499)
       and not llocs.cobreix(antic, 901500 + 501, 4630500),
       'un lloc antic (doble clic) cobreix fins a 500 m del centre (1 km de quadrat menys 500 m de marge)')
    dir_real = llocs.DIR_LLOCS
    with tempfile.TemporaryDirectory() as tmp:
        llocs.DIR_LLOCS = tmp
        claus = [llocs.clau(3000.0 * k, 0.0) for k in range(llocs.MAX_LLOCS + 2)]
        for k, ck in enumerate(claus):
            open(llocs.cami_mdt(ck), 'w').close()
            os.utime(llocs.cami_mdt(ck), (1e9 + k, 1e9 + k))      # del mes antic al mes recent
        esborrats = llocs.esborrar_antics(protegits={claus[0]})
        queden = llocs.existents()
        ok(len(queden) == llocs.MAX_LLOCS - 1 and claus[0] in queden and claus[-1] in queden,
           f'esborrar_antics: en queden {len(queden)} (MAX_LLOCS - 1), el protegit i el mes recent; esborrats {len(esborrats)}')
    llocs.DIR_LLOCS = dir_real

    # ------------------------------------------------------------ 2. el programa
    print('\n== 2. Doble clic al programa')
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    W, H = 800, 520
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - llocs', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    os.makedirs(SORTIDA, exist_ok=True)

    def fotograma():
        app.dt = 1 / 30
        app.ui_renderer.new_frame()
        imgui.new_frame()
        objectiu.use()
        app.render()
        imgui.render()

    def desa(nom):
        Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(SORTIDA, nom))

    def doble_clic(lat, lon):
        app.canviar_vista(0)
        return app.anar_al_punt(lat, lon)

    def preparacions():
        return {t for t in app.detall.feines if t in ('relleu', 'edificis')}

    doble_clic(*UAB)
    for _ in range(10):
        fotograma()
    ok(not preparacions() and app.edificis is not None, f'UAB: sense lloc nou; zona {app.nom_zona}, '
       f'{app.edificis.n_parts if app.edificis else 0} parts')
    doble_clic(*MAR)
    for _ in range(10):
        fotograma()
    ok(not preparacions(), 'mar: sense lloc nou')

    t0 = time.time()
    doble_clic(*MANRESA)
    nou = bool(preparacions()) or app.zona is None or not app.zona.conte(*MANRESA)
    # si el lloc no era al disc, es prepara en segon pla (xarxa, ~1 min): s'espera, dibuixant
    n = 0
    while time.time() - t0 < 600 and (app.zona is None or not app.zona.conte(*MANRESA) or app.edificis is None
                                      or preparacions()):
        fotograma()
        n += 1
        time.sleep(0.05)
    for _ in range(5):
        fotograma()
    s_carrega = time.time() - t0
    o = app.observador
    clau = app.detall.carregades[app.zona.cami]['clau'] if app.zona is not None else ''
    alt_zona = app.zona.altitud_latlon(o.lat, o.lon) if app.zona is not None else None
    ok(clau.startswith('lloc_') and app.edificis is not None and app.edificis.n_parts > 100,
       f'Manresa: {"preparat en segon pla" if nou else "el lloc del disc es carrega al moment"} '
       f'({s_carrega:.1f} s, {n} fotogrames dibuixats mentrestant): {app.nom_zona}, '
       f'{app.edificis.n_parts if app.edificis else 0} parts d\'edifici')
    ok(alt_zona is not None and abs(o.altitud_m - alt_zona) < 0.01,
       f'observador sobre el relleu de 5 m del lloc ({o.altitud_m:.1f} m)')
    app.camera_observador.mirar(200.0, 5.0)
    for _ in range(3):
        fotograma()
    desa('llocs_ulls.png')

    # reproduccio des del terra: una zona carregada en segon pla no s'activa fins a la pausa
    zona_obs = app.zona
    app.reproduint = True
    cami_uab = next(c for c, z in app.detall.carregades.items() if z['nom'].startswith('Valles'))
    app.detall.recollir = lambda: None          # sense feines reals: es prova la condicio directament
    o_lat, o_lon = o.lat, o.lon
    app.observador = type(o)(UAB[0], UAB[1], o.altitud_m, o.nom)   # (no es fa servir triar_punt, que es bloqueja)
    app.detall.ultima = -1e9
    fotograma()
    ok(app.zona is zona_obs, 'en reproduccio, la vista des del terra no canvia la zona de sota l\'observador')
    app.reproduint = False
    app.detall.ultima = -1e9
    fotograma()
    ok(app.zona is not None and app.zona.cami == cami_uab, 'en pausa, la zona del punt es la que es dibuixa')
    app.observador = type(o)(o_lat, o_lon, o.altitud_m, o.nom)

    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
