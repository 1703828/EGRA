"""
Comprova els llocs nous amb detall (dades/llocs.py) i el doble clic que els prepara (main.py).

1. Sense finestra: clau i centre arrodonits a 100 m, cobertura dels edificis (marge de 500 m), i l'esborrat dels
   llocs mes antics (amb fitxers de prova en una carpeta temporal: no toca els llocs reals).
2. Amb el programa (finestra oculta):
   - doble clic a la UAB (edificis de la zona del Valles): no es prepara cap lloc;
   - doble clic al mar: no es prepara cap lloc;
   - doble clic a Manresa: si el lloc ja hi es, es carrega al moment (zona i edificis); si no (o amb --xarxa en
     un punt nou), es prepara en segon pla: el bucle de dibuix continua (fotogrames durant la preparacio) i, en
     acabar, l'observador queda sobre el relleu de 5 m del lloc, amb els edificis.
   - en reproduccio, el lloc preparat no es carrega fins a la pausa.
Captures a captures/proves/llocs_*.png.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_llocs.py [--xarxa]
(--xarxa: prepara un lloc nou, a Igualada, encara que ja hi sigui: baixa ~6 MB i tarda ~40 s.)
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
    print('== 1. Claus, cobertura i esborrat')
    c = llocs.clau(901500.0, 4630500.0)
    ok(llocs.centre(c) == (901500.0, 4630500.0), f'clau {c} -> centre')
    ok(llocs.cobreix(c, 901500 + 499, 4630500 - 499) and not llocs.cobreix(c, 901500 + 501, 4630500),
       'els edificis cobreixen el punt fins a 500 m del centre (1 km de quadrat menys 500 m de marge)')
    dir_real = llocs.DIR_LLOCS
    with tempfile.TemporaryDirectory() as tmp:
        llocs.DIR_LLOCS = tmp
        claus = [llocs.clau(1000.0 * k, 0.0) for k in range(5)]
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

    def esperar(maxim_s=600):
        t0, n = time.time(), 0
        while app.preparacio is not None and time.time() - t0 < maxim_s:
            fotograma()
            n += 1
            time.sleep(0.05)
        return n, time.time() - t0

    doble_clic(*UAB)
    ok(app.preparacio is None and app.edificis is not None, f'UAB: sense lloc nou; zona {app.nom_zona}, '
       f'{app.edificis.n_parts if app.edificis else 0} parts')
    doble_clic(*MAR)
    ok(app.preparacio is None, 'mar: sense lloc nou')

    lat, lon = IGUALADA if XARXA else MANRESA
    if XARXA:
        x, y = llocs._a_utm.transform(lon, lat)
        ck = llocs.clau(round(x / 100) * 100, round(y / 100) * 100)
        for f in llocs.fitxers(ck):
            if os.path.exists(f):
                os.remove(f)
    t0 = time.time()
    doble_clic(lat, lon)
    if app.preparacio is not None:
        n, s = esperar()
        ok(n > 10, f'preparacio en segon pla: {n} fotogrames dibuixats en {s:.0f} s')
    else:
        print(f'   (el lloc ja hi era: carregat en {time.time() - t0:.1f} s; --xarxa per preparar-ne un de nou)')
    clau = app.clau_zona.get(app.nom_zona, '')
    o = app.observador
    alt_zona = app.zona.altitud_latlon(o.lat, o.lon) if app.zona is not None else None
    ok(clau.startswith('lloc_') and app.edificis is not None and app.edificis.n_parts > 100,
       f'lloc carregat: {app.nom_zona}, {app.edificis.n_parts if app.edificis else 0} parts d\'edifici')
    ok(alt_zona is not None and abs(o.altitud_m - alt_zona) < 0.01,
       f'observador sobre el relleu de 5 m del lloc ({o.altitud_m:.1f} m)')
    app.camera_observador.mirar(200.0, 5.0)
    for _ in range(3):
        fotograma()
    desa('llocs_ulls.png')

    # reproduccio: el lloc preparat espera la pausa
    class Fet:
        fet, error = True, None

        def segons(self):
            return 0.0
    fet = Fet()
    fet.clau = clau
    app.preparacio, app.reproduint = fet, True
    fotograma()
    ok(app.preparacio is not None and 'pausar' in app.text_lloc(), 'en reproduccio, el lloc espera la pausa')
    app.reproduint = False
    fotograma()
    ok(app.preparacio is None, 'en pausa, es carrega')

    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
