"""
Horitzo cap al Sol a cada ubicacio: calculat sobre el terreny i llegit de la imatge del programa
(tasca 3.4 del pla), i si el relleu tapa el Sol al maxim (comparat amb la capa d'ombres del CNIG).

Per a cada ubicacio i en l'azimut del Sol al maxim de l'eclipsi:
  1. Horitzo del MDT complet: un raig horitzontal des dels ulls (1,7 m sobre la superficie dibuixada),
     amb punts cada 0,3 % de la distancia, de 5 m a 200 km; a cada punt, l'altitud del MDT a resolucio
     completa (la zona de 5 m si hi es; si no, la peninsula de 200 m). Angle de cada punt vist des dels
     ulls, en coordenades terrestres (ECEF): la curvatura de la Terra hi es (geometrica, sense refraccio
     terrestre, D18). L'horitzo es l'angle mes alt.
  2. Horitzo de la superficie dibuixada: el mateix raig sobre els triangles que dibuixa el programa
     (altures calculades a la CPU, app.altitud_terra_km).
  3. Horitzo renderitzat: el programa real (finestra amagada) mira en aquell azimut amb un camp de visio
     de 2 graus; es llegeix el depth buffer de la columna central i la vora superior del terreny dona
     l'angle (un pixel = 2/640 = 0,003 graus). El Sol, el halo i la Lluna s'amaguen per no confondre'ls.
  2 i 3 han de coincidir (<= 0,05 graus, objectiu de §6.4): es la comprovacio que el dibuix i el calcul
  fan servir la mateixa geometria. 1 - 2 es l'efecte de la resolucio de la malla.
  4. Ocultacio del Sol pel relleu al maxim: l'elevacio aparent del Sol (amb refraccio) respecte de
     l'horitzo 1, amb el radi aparent del Sol, classificada com la capa terrain_shadows del CNIG
     (0 tot tapat, 1 nomes part de la meitat de dalt, 2 la meitat de dalt i part de la de baix,
     3 cap). El CNIG la calcula amb el GMTED2010 (~230 m) i en una cel·la de ~230 m: es comparable la
     classe, no l'angle exacte.

Limitacions: fora d'Espanya el MDT val 0 (Portugal, Franca, mar); sense edificis ni arbres (MDT);
sense refraccio terrestre (amb k = 0,13 el relleu a 50 km es veuria ~0,03 graus mes alt, §7.2).

Executa (des de l'arrel, amb l'entorn egra):  python scripts/validar_horitzo.py
"""
import math
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from slimgui import imgui  # noqa: E402

TOLERANCIA_GRAUS = 0.05   # objectiu de §6.4 per a l'angle de l'horitzo
FOV_GRAUS = 2.0


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia, eclipse_data
    from basecode.camera_exploracio import direccio_mirada

    W, H = 640, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - horitzo', use_ui_panel=True)
    objectiu = app.ctx.simple_framebuffer((W, H))
    app.mostrar_edificis = False   # horitzo del relleu: els edificis es comproven a validar_edificis.py
    co = app.camera_observador
    errors = []

    def fotograma():
        app.dt = 0.0
        app.ui_renderer.new_frame()
        imgui.new_frame()
        objectiu.use()
        app.render()
        imgui.render()

    def altitud_mdt_km(lat, lon):
        """MDT a resolucio completa: la zona de 5 m si conte el punt, si no la peninsula (0 fora)."""
        for t in reversed(app.terrenys()):
            h = t.altitud_latlon(lat, lon, dibuixada=False)
            if h is not None:
                return h / 1000.0
        return 0.0

    def horitzo(ulls, lat, lon, azimut, altitud_km):
        """Angle (graus) mes alt del terreny vist des dels ulls en aquest azimut, i a quina distancia."""
        _, _, amunt = geodesia.base_local(lat, lon)
        horitz = direccio_mirada(lat, lon, azimut, 0.0)
        millor, dist_millor = -90.0, 0.0
        d = 0.005
        while d < 200.0:
            la, lo, _ = geodesia.geodesiques(ulls + d * horitz)   # la vertical d'aquest punt del raig
            la, lo = float(la), float(lo)
            p = geodesia.ecef(la, lo, altitud_km(la, lo))
            v = p - ulls
            angle = math.degrees(math.asin(float(np.dot(amunt, v)) / float(np.linalg.norm(v))))
            if angle > millor:
                millor, dist_millor = angle, d
            d *= 1.003
        return millor, dist_millor

    def horitzo_renderitzat(azimut, inclinacio):
        co.mirar(azimut, inclinacio)
        co.fov = FOV_GRAUS
        fotograma()
        prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        columna = prof[:, W // 2]                      # fila 0 = a baix
        terra = np.nonzero(columna < 1.0)[0]
        if len(terra) == 0 or terra.max() == H - 1:
            return None                                # tot cel o tot terra: fora del camp de visio
        fila = terra.max() + 1.0                       # la vora: entre el pixel de terra i el de cel
        y_ndc = 2.0 * fila / H - 1.0
        return inclinacio + math.degrees(math.atan(y_ndc * math.tan(math.radians(FOV_GRAUS / 2))))

    def classe(elev_sol, horitzo_graus, radi):
        if horitzo_graus >= elev_sol + radi:
            return 0
        if horitzo_graus >= elev_sol:
            return 1
        if horitzo_graus >= elev_sol - radi:
            return 2
        return 3

    # el Sol, el halo i la Lluna, amagats: render() torna a decidir si es veuen a actualitzar_cel()
    actualitzar_cel = app.actualitzar_cel

    def cel_sense_astres():
        actualitzar_cel()
        app.sol_visible.visible = app.halo.visible = app.lluna.visible = False

    app.actualitzar_cel = cel_sense_astres

    print(f"{'Ubicacio':24s} {'azimut':>7s} {'MDT':>7s} {'dist.':>8s} {'dibuix.':>8s} {'imatge':>8s} "
          f"{'img-dib':>8s} {'Sol':>6s} {'classe':>6s} {'CNIG':>5s}")
    for nom, lat, lon in programa.UBICACIONS:
        app.triar_punt(lat, lon, nom)
        m = app.model
        app.hora = m.hores['maxim']
        az, el_sol = m.sol(app.hora)            # elevacio aparent (refraccio de Bennett)
        ulls = app.ulls()
        h_mdt, d_mdt = horitzo(ulls, lat, lon, az, altitud_mdt_km)
        h_dib, _ = horitzo(ulls, lat, lon, az, app.altitud_terra_km)
        h_img = horitzo_renderitzat(az, h_dib)
        # radi aparent del Sol (graus) des de l'observador
        s = app.sol_ecef - ulls
        radi = math.degrees(math.asin(programa.RADI_SOL_KM / float(np.linalg.norm(s))))
        cl = classe(el_sol, h_mdt, radi)
        cnig = app.cnig['classe_ombres'] if app.cnig else None
        dif = None if h_img is None else h_img - h_dib
        if dif is None or abs(dif) > TOLERANCIA_GRAUS:
            errors.append(nom)
        print(f"{nom[:24]:24s} {az:7.2f} {h_mdt:7.3f} {d_mdt:7.1f}k {h_dib:8.3f} "
              f"{'-' if h_img is None else f'{h_img:8.3f}':>8s} {'-' if dif is None else f'{dif:+8.3f}':>8s} "
              f"{el_sol:6.2f} {cl:6d} {'-' if cnig is None else cnig:>5}   "
              f"({eclipse_data.hora_local(app.hora)})")
    print('Angles en graus. MDT: horitzo del MDT complet (i a quina distancia); dibuix.: de la superficie '
          'dibuixada; imatge: llegit del depth buffer; Sol: elevacio aparent al maxim; classe: ocultacio '
          'pel relleu amb l\'horitzo del MDT (com el CNIG: 3 = el relleu no tapa el Sol).')
    app._shutdown()
    print('RESULTAT:', 'TOT CORRECTE' if not errors else f'FALLA a {", ".join(errors)}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
