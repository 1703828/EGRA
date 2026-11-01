"""
Comprova les ombres del relleu (shadow mapping, basecode/ombres_relleu.py) i les compara amb la capa
d'ombres del CNIG (tasca 6.1 del pla).

1. GPU contra CPU (comprova la implementacio). El programa real (finestra amagada) dibuixa la zona de 5 m
   vista des de l'aire amb el mode de depuracio, que pinta cada pixel amb el factor d'ombra del relleu
   (1 = hi arriba el Sol, 0 = una muntanya el tapa). Per a una graella de pixels de la zona, el punt del
   terreny es treu del depth buffer i la CPU hi fa un calcul independent: un raig des del punt cap al Sol
   (la mateixa direccio que la llum del mapa) que mira si algun punt de la superficie dibuixada de la zona
   queda per sobre del raig. Es compara on la GPU es clarament a l'ombra (< 0,1) o al sol (> 0,9); la vora
   suavitzada (entremig) no es compta. Els desacords en que el terreny passa per sobre del raig menys del
   biaix de la GPU son casos limit: per evitar l'acne, la GPU mira el punt 1 texel (~8 m) fora de la
   superficie i 3 m mes a prop del Sol (ombres_relleu.py), i no veu obstacles mes baixos que aixo.
2. CPU contra el CNIG (comparacio amb una altra font). La capa terrain_shadows del CNIG diu, per a cada
   cel·la de ~230 m i a l'hora del maxim en aquella cel·la, si el relleu tapa el Sol (classes 0 i 1: el
   centre del Sol tapat; 2 i 3: visible). Es el mateix que l'ombra del relleu: si el Sol arriba al terra en
   aquell punt. El CNIG fa servir el GMTED2010 (~230 m); nosaltres ho calculem amb el MDT de 200 m
   (comparable), tambe sense refraccio (per veure'n l'efecte), i amb el de 5 m (el que dibuixem), a l'hora del maxim a l'observador i amb el Sol vist des
   de cada cel·la (en 6 km el maxim canvia menys de 10 s i el Sol es mou menys de 0,03 graus).

Limitacions: nomes la zona de 5 m projecta ombres al programa; sense edificis ni arbres; Sol aparent
amb refraccio estandard (Bennett) i sense refraccio terrestre; el CNIG no documenta com tracta la vora.

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/validar_ombres_relleu.py            # Picos (zona controlada)
    python scripts/validar_ombres_relleu.py --totes    # les sis ubicacions
"""
import argparse
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402
from slimgui import imgui  # noqa: E402

SORTIDA = os.path.join(ARREL, 'captures', 'proves')
COINCIDENCIA_MINIMA = 0.98    # GPU contra CPU, fora dels casos limit
RADI_CNIG_KM = 6.0            # cel·les del CNIG comparades: dins d'aquest radi al voltant de l'observador
# distancies al llarg del raig cap al Sol (km): pas de l'1 % de la distancia, de 20 m a 60 km
DISTANCIES = 0.02 * 1.01 ** np.arange(int(np.log(3000) / np.log(1.01)) + 1)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--totes', action='store_true', help='les sis ubicacions (per defecte, nomes Picos)')
    p.add_argument('--nomes-gpu', action='store_true', help='sense la comparacio amb el CNIG (mes rapid)')
    a = p.parse_args()

    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades.observador import UBICACIONS_PROVES
    from basecode.camera_exploracio import direccio_mirada
    from basecode.terrain import mostrejar_bilineal
    from dades import geodesia, eclipse_data
    
    W, H = 800, 600
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - ombres del relleu', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    app.mostrar_edificis = False   # ombres del relleu: els edificis no es pinten amb el mode de depuracio
    ce = app.camera_exploracio
    os.makedirs(SORTIDA, exist_ok=True)
    errors = []

    def fotograma():
        app.dt = 0.0
        app.ui_renderer.new_frame()
        imgui.new_frame()
        objectiu.use()
        app.render()
        imgui.render()

    def marge(p0, cap_al_sol, alcada_km):
        """Quant (km) queda el terreny per sobre del raig des de p0 cap al Sol (> 0: tapat)."""
        s = p0 + DISTANCIES[:, None] * cap_al_sol
        lat, lon, alt = geodesia.geodesiques(s)
        h = alcada_km(lat, lon)
        return float(np.nanmax(h - alt))

    def superficie(terreny, dibuixada):
        """Funcio (lat, lon) -> altura (km) d'un terreny: la dibuixada (triangles) o la del MDT complet.
        Fora del terreny, NaN (no hi ha res que faci ombra)."""
        def alcada(lat, lon):
            us, vs = terreny.latlon_a_uv(lat, lon)
            dins = (us >= 0) & (us <= 1) & (vs >= 0) & (vs <= 1)
            h = np.full(np.shape(us), np.nan)
            if dins.any():
                hm = (terreny.alcada_dibuixada_uv(us[dins], vs[dins]) if dibuixada
                      else mostrejar_bilineal(terreny.alt, us[dins], vs[dins]))
                h[dins] = np.maximum(hm, 0.0) / 1000.0
            return h
        return alcada

    ubicacions = UBICACIONS_PROVES if a.totes else UBICACIONS_PROVES[:1]
    for k, (nom, lat, lon) in enumerate(ubicacions):
        print(f'\n== {nom}')
        app.triar_ubicacio(lat, lon, nom)
        zona = app.zona
        # Picos: 30 min abans del maxim (al maxim hi ha totalitat i la llum directa no es veu; la geometria
        # de les ombres es la mateixa). Catalunya: al maxim (el Sol a ~4 graus).
        hora = app.model.hores['maxim'] - (30 / 60 if app.model.durada else 0.0)
        app.hora = hora
        az, el = app.model.sol(hora)
        cap_al_sol = direccio_mirada(lat, lon, az, el)
        print(f'Hora {eclipse_data.hora_local(hora)} CEST, Sol a azimut {az:.2f} i elevacio aparent {el:.2f} graus')

        # --- 1. GPU contra CPU
        _, _, amunt = geodesia.base_local(lat, lon)
        ce.posicio = app.ulls() + 4.0 * direccio_mirada(lat, lon, az, 0.0) + 7.0 * amunt
        ce.rumb, ce.inclinacio = az + 180.0, -55.0
        app.canviar_vista(0)
        app.ombres.depuracio = True
        fotograma()
        factor = np.frombuffer(objectiu.read(components=3), 'u1').reshape(H, W, 3)[..., 0] / 255.0
        prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        Image.fromarray((factor[::-1] * 255).astype('u1')).save(os.path.join(SORTIDA, f'ombres_relleu_{k}_factor.png'))

        # interruptor d'Avancat, com el fa servir l'equip: en pausa (l'hora no canvia), apagar i encendre
        # diverses vegades nomes amb app.ombres.actiu. Ha d'haver-hi ombra quan es ences i cap quan no.
        def pixels_ombra():
            fotograma()
            return int((np.frombuffer(objectiu.read(components=3), 'u1').reshape(H, W, 3)[..., 0] < 26).sum())
        estats = []
        for actiu in (False, True, False, True):
            app.ombres.actiu = actiu
            estats.append(pixels_ombra())
        # apagades, alguns pixels foscos que no son terreny de la zona (cel, globus): en queden 0-3
        # encesa les dues vegades, el mateix mapa: un pixel de la vora d'una ombra pot canviar d'una execucio a
        # l'altra (passava ja abans de la F36: ~1 de cada 3 execucions, 100.496 contra 100.497); se n'admeten 5
        ok_interruptor = max(estats[0], estats[2]) <= 10 and abs(estats[1] - estats[3]) <= 5 and min(estats[1], estats[3]) > 1000
        print(f"Interruptor (apagar, encendre, apagar, encendre en pausa): pixels a l'ombra {estats}")
        if not ok_interruptor:
            errors.append(f'{nom}: interruptor de les ombres')
        app.ombres.depuracio = False
        fotograma()
        Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(SORTIDA, f'ombres_relleu_{k}.png'))

        dibuixada = superficie(zona, True)
        from basecode.ombres_relleu import BIAIX_KM
        marge_limit = app.ombres.desplacament_km() + BIAIX_KM
        n, iguals, limit, desacords = 0, 0, 0, []
        for py in np.linspace(H * 0.05, H * 0.95, 30).astype(int):
            for px in np.linspace(W * 0.05, W * 0.95, 40).astype(int):
                d, f = float(prof[py, px]), factor[py, px]
                if d >= 1.0 or 0.1 <= f <= 0.9:
                    continue
                p0 = ce.desprojectar(px + 0.5, py + 0.5, d, W, H)
                la, lo, _ = (float(c) for c in geodesia.geodesiques(p0))
                if not zona.conte(la, lo) or np.linalg.norm(p0 - app.ombres.ancora) > 15.0:
                    continue
                m = marge(p0, cap_al_sol, dibuixada)
                n += 1
                if (m > 0) == (f < 0.1):
                    iguals += 1
                elif 0 < m < marge_limit if f > 0.9 else -marge_limit < m <= 0:
                    limit += 1
                else:
                    desacords.append((round(la, 4), round(lo, 4), 'GPU ombra' if f < 0.1 else 'GPU sol', round(m * 1000, 1)))
        frac = (iguals + limit) / max(n, 1)
        print(f'GPU contra CPU: {n} punts; coincideixen {iguals}, casos limit {limit} (dins del biaix de '
              f'{marge_limit * 1000:.1f} m), '
              f'desacords {len(desacords)} -> {frac * 100:.1f} %')
        for dd in desacords[:5]:
            print('      desacord (lat, lon, GPU, terreny sobre el raig en m):', dd)
        if n == 0 or frac < COINCIDENCIA_MINIMA:
            errors.append(f'{nom}: GPU contra CPU')
        if a.nomes_gpu:
            continue

        # --- 2. CPU contra el CNIG (cel·les de ~230 m al voltant de l'observador)
        x0, y0 = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform(lon, lat)
        a_latlon = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True)
        r = RADI_CNIG_KM * 1000 / np.cos(np.radians(lat))      # metres de Mercator
        with rasterio.open(eclipse_data.OMBRES) as ds:
            fin = rasterio.windows.from_bounds(x0 - r, y0 - r, x0 + r, y0 + r, ds.transform).round_offsets().round_lengths()
            classes = ds.read(1, window=fin)
            t = ds.window_transform(fin)
        sol_maxim, _ = app.ef.posicions(app.model.hores['maxim'])
        superficies = {'200 m': superficie(app.peninsula, False), '5 m': superficie(zona, False)}
        superficies['200 m, sense refraccio'] = superficies['200 m']
        taula = {s: np.zeros((2, 2), int) for s in superficies}   # [CNIG tapat][nostre tapat]
        for f in range(classes.shape[0]):
            for c in range(classes.shape[1]):
                classe = int(classes[f, c])
                if classe not in eclipse_data.CLASSES_OMBRES:
                    continue
                lo, la = a_latlon.transform(*(t * (c + 0.5, f + 0.5)))
                if not zona.conte(la, lo, marge=0.02):
                    continue
                # el Sol a l'hora del maxim de l'observador (en 6 km el maxim canvia menys de 10 s, el Sol
                # s'hi mou < 0,03 graus), vist des de la cel·la, amb la refraccio estandard
                az_c, el_c = geodesia.azimut_elevacio(sol_maxim - geodesia.ecef(la, lo, 0.0), la, lo)
                l_c = direccio_mirada(la, lo, az_c, el_c + geodesia.refraccio_graus(el_c))
                l_geom = direccio_mirada(la, lo, az_c, el_c)
                for nom_s, alcada in superficies.items():
                    p0 = geodesia.ecef(la, lo, float(alcada(np.array([la]), np.array([lo]))[0]))
                    llum = l_geom if nom_s.endswith('sense refraccio') else l_c
                    taula[nom_s][int(classe <= 1), int(marge(p0, llum, alcada) > 0)] += 1
        for nom_s, tt in taula.items():
            total = tt.sum()
            print(f'CNIG contra el nostre calcul amb el MDT de {nom_s}: {total} cel·les; coincideixen '
                  f'{(tt[0, 0] + tt[1, 1]) / max(total, 1) * 100:.1f} %  (CNIG tapat: {tt[1].sum()}, nosaltres '
                  f'tapat: {tt[:, 1].sum()}; tapat nomes al CNIG: {tt[1, 0]}, nomes nosaltres: {tt[0, 1]})')
        app.canviar_vista(1)

    app._shutdown()
    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'FALLA: {"; ".join(errors)}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
