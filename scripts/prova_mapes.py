"""
Recorregut R1 del pla (O4, F42): els mapes de visibilitat durant tota l'exploracio, amb el programa real (finestra
amagada, mateix bucle i panell).

Parades: la peninsula des de l'espai; el Valles des de 40 km; el Valles des de 10 km amb la camera inclinada; la UAB
des de ~500 m; una cel·la veina (3,5 km a l'est); tornar a 40 km i a la peninsula. A cada parada es deixa treballar
el programa (feines en segon pla) i es mesura:
  - cobertura: en una graella de pixels de la imatge, els que son terra d'Espanya (desprojectant la profunditat) i,
    d'aquests, quants canvien de color en activar el mapa. Un pixel que no canvia no te color de mapa (forat). La
    mesura no depen del codi del mapa: serveix abans i despres dels canvis.
  - el nivell de dades que es veu (si el programa el sap dir: app.mapes) i la llegenda (llindars) a cada parada.
  - temps de cada fotograma (mediana, p99, maxim) mentre es preparen les dades.
Captures a captures/proves/mapes_<etiqueta>_<parada>.png (amb el mapa) i ..._sense.png.

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/prova_mapes.py [--etiqueta abans] [--espera 60] [--mapa durada] [--parades 1,2,3]
--espera: segons maxims a cada parada esperant que el detall estigui preparat (el programa continua dibuixant).
"""
import argparse
import json
import math
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
W, H = 1100, 760
UAB = (41.5009, 2.1055)
# (nom, lat, lon, altura sobre el terra en km, rumb, inclinacio, segons d'espera maxims o None = --espera)
PARADES = [
    ('1_peninsula', 40.0, -3.7, 1300.0, 0.0, -89.0, 5),
    ('2_valles_40km', 41.30, 2.10, 40.0, 10.0, -60.0, None),
    ('3_valles_10km_inclinada', 41.43, 2.06, 10.0, 40.0, -30.0, None),
    ('4_uab_500m', UAB[0] - 0.006, UAB[1], 0.5, 0.0, -40.0, None),
    ('5_cel_la_veina', UAB[0] - 0.006, UAB[1] + 0.042, 0.5, 0.0, -40.0, None),
    ('6_tornar_40km', 41.30, 2.10, 40.0, 10.0, -60.0, 10),
    ('7_peninsula', 40.0, -3.7, 1300.0, 0.0, -89.0, 5),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--etiqueta', default='prova')
    p.add_argument('--espera', type=float, default=60.0)
    p.add_argument('--mapa', default='durada', help='mapa a mostrar (codi nou: ocultacio, durada, relleu, ombra)')
    p.add_argument('--parades', default='')
    p.add_argument('--hora', default='maxim-10', help='maxim-10: 10 min abans del maxim (del punt UAB)')
    a = p.parse_args()
    triades = {int(x) for x in a.parades.split(',') if x}
    os.makedirs(SORTIDA, exist_ok=True)
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia

    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova dels mapes', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    app.ratoli.focus = True
    errors, temps = [], []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text, flush=True)
        if not condicio:
            errors.append(text)
        return condicio

    def fotograma(n=1, dt=1 / 30, registrar=True, panell=True):
        for _ in range(n):
            t0 = time.perf_counter()
            glfw.poll_events()
            app.dt = dt
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            if panell:
                imgui.set_next_window_pos((10, 10), imgui.Cond.ALWAYS)
                imgui.begin('Opcions')
                app.build_ui()
                imgui.end()
            imgui.render()
            app.ui_renderer.render(imgui.get_draw_data())
            app.ctx.finish()
            if registrar:
                temps.append(time.perf_counter() - t0)

    def imatge():
        return np.frombuffer(objectiu.read(components=3), 'u1').reshape(H, W, 3).astype(int)

    def mostra_terra():
        """Pixels d'una graella (40 x 28) que son terra d'Espanya: (fila, columna) de la imatge (fila 0 = baix)."""
        prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        out = []
        for py in np.linspace(8, H - 8, 28).astype(int):
            for px in np.linspace(8, W - 8, 40).astype(int):
                d = float(prof[py, px])
                if not 0.0 < d < 1.0:
                    continue
                q = app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
                lat, lon, _ = geodesia.geodesiques(q)
                if app.peninsula.es_terra(float(lat), float(lon)):
                    out.append((py, px))
        return out

    nova = hasattr(app, 'mapes')
    t_parts = {'mapes': [], 'detall': []}
    if nova:
        # temps de les parts del fotograma que preparen dades (per trobar on son les aturades)
        for nom, obj, metode in (('mapes', app.mapes, 'actualitzar'), ('detall', app.detall, 'actualitzar')):
            original = getattr(obj, metode)

            def amb_temps(original=original, nom=nom):
                t0 = time.perf_counter()
                original()
                t_parts[nom].append(time.perf_counter() - t0)
            setattr(obj, metode, amb_temps)

    def posar_mapa(actiu):
        if nova:
            app.mapes.mostrar(a.mapa if actiu else None)
        else:
            app.mapa_visibilitat = 1 if actiu else 0

    def ocupat():
        """Si el programa encara prepara dades per al mapa o el detall (feines en segon pla)."""
        if nova:
            return app.mapes.ocupat() or bool(app.detall.feines)
        return bool(app.detall.feines) or any(not c.fet for c in app.calculs_mapa.values()) or \
            (app.calcul_detall is not None and not app.calcul_detall.fet)

    # hora: 10 min abans del maxim a la UAB
    app.triar_ubicacio(UAB[0], UAB[1], 'UAB, placa Civica')
    if a.hora.startswith('maxim'):
        app.hora = app.model.hores['maxim'] + float(a.hora[5:] or 0) / 60.0
    app.canviar_vista(0)
    posar_mapa(True)
    cam = app.camera_exploracio
    informe = []
    for i, (nom, lat, lon, alt_km, rumb, incl, espera) in enumerate(PARADES, 1):
        if triades and i not in triades:
            continue
        espera = a.espera if espera is None else espera
        terra_km = app.altitud_terra_km(lat, lon)
        cam.aturar_moviment()
        cam.posicio = geodesia.ecef(lat, lon, terra_km + alt_km)
        cam.orientar(rumb, incl)
        n0 = len(temps)
        t0 = time.time()
        fotograma(10)
        while time.time() - t0 < espera:
            fotograma(5)
            if time.time() - t0 > 3 and not ocupat():
                break
        fotograma(3)
        segons = time.time() - t0
        Image.fromarray(np.flipud(imatge()).astype('u1')).save(os.path.join(SORTIDA, f'mapes_{a.etiqueta}_{nom}.png'))
        # la cobertura es mesura al terreny (sense edificis: les cobertes es tracten a la tasca 43.3) i a plena llum
        # (C1 - 1 h), perque els colors foscos de l'escala (0 %) no es confonguin amb l'escena fosca de l'eclipsi
        vis_e = (app.mostrar_edificis, app.edificis_aeris)
        app.mostrar_edificis = app.edificis_aeris = False
        hora = app.hora
        app.hora = app.model.hores['c1'] - 1.0
        fotograma(3, registrar=False, panell=False)
        amb = imatge()
        punts = mostra_terra()
        posar_mapa(False)
        fotograma(2, registrar=False, panell=False)
        sense = imatge()
        Image.fromarray(np.flipud(sense).astype('u1')).save(os.path.join(SORTIDA, f'mapes_{a.etiqueta}_{nom}_sense.png'))
        posar_mapa(True)
        app.hora = hora
        app.mostrar_edificis, app.edificis_aeris = vis_e
        fotograma(2, registrar=False)
        canvia = [np.abs(amb[py, px] - sense[py, px]).sum() > 12 for py, px in punts]
        cob = float(np.mean(canvia)) if punts else float('nan')
        t = np.array(temps[n0:]) * 1000
        r = dict(parada=nom, segons=round(segons, 1), punts_terra=len(punts), cobertura=round(cob, 4),
                 ms_mediana=round(float(np.median(t)), 1) if len(t) else None,
                 ms_p99=round(float(np.percentile(t, 99)), 1) if len(t) else None,
                 ms_max=round(float(t.max()), 1) if len(t) else None, ocupat=ocupat())
        if nova:
            r.update(app.mapes.resum())
        informe.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        if punts:
            ok(cob > 0.98, f'{nom}: {cob * 100:.1f} % dels pixels de terra d\'Espanya amb color de mapa '
               f'({len(punts)} pixels de mostra)')
    for nom, v in t_parts.items():
        if v:
            v = np.array(v) * 1000
            print(f'  {nom}.actualitzar: mediana {np.median(v):.1f} ms, p99 {np.percentile(v, 99):.1f} ms, maxim '
                  f'{v.max():.0f} ms')
    t = np.array(temps) * 1000
    print(f'Fotogrames: {len(t)}; mediana {np.median(t):.1f} ms, p99 {np.percentile(t, 99):.1f} ms, '
          f'maxim {t.max():.0f} ms', flush=True)
    ok(np.median(t) <= 20 * 1.5 and t.max() < 1000, 'temps per fotograma: mediana <= 30 ms (finestra amagada, amb '
       'captures) i cap fotograma de mes d\'1 s')
    with open(os.path.join(SORTIDA, f'mapes_{a.etiqueta}.json'), 'w') as f:
        json.dump(informe, f, indent=1, ensure_ascii=False)
    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    app._shutdown() if hasattr(app, '_shutdown') else None
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
