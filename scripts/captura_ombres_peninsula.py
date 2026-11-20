"""
Ombres del relleu fora de les zones de 5 m (tasca 6.1, basecode/ombres_relleu.py): captures amb i sense ombres i amb
el mode de depuracio (el terreny pintat amb el factor d'ombra: blanc Sol, negre ombra), i el temps de dibuix (mediana
de 120 fotogrames amb ctx.finish(), GPU inclosa) i de la passada des del Sol (que nomes es refa quan canvia l'hora).
Sense preparar llocs nous (detall.preparar = False): el relleu es el de la peninsula (200 m).
Comprovacio independent (com scripts/validar_ombres_relleu.py a les zones): per a una graella de pixels de la imatge
de depuracio clarament a l'ombra (< 0,1) o al Sol (> 0,9), la CPU fa un raig des del punt (del depth buffer) cap al
Sol (la mateixa direccio que el mapa: Sol aparent des de l'ancora) i mira si la superficie dibuixada de la peninsula
hi passa per sobre. Els desacords dins del biaix contra l'acne de la GPU (1 texel + 3 m) es compten com a casos limit.

Executa:  python scripts/captura_ombres_peninsula.py
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA = os.path.join(ARREL, 'captures', 'ombres')
# (nom, lat, lon, altura sobre el terra (km), rumb, inclinacio, hora TU)
VISTES = [('montserrat', 41.560, 1.770, 6.0, 60.0, -30.0, 17.3),
          ('montserrat_40km', 41.400, 1.600, 40.0, 30.0, -45.0, 17.3),
          ('pirineu_cadi', 42.230, 1.650, 9.0, 20.0, -30.0, 17.3)]


def main():
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    import glfw
    import numpy as np
    from PIL import Image
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='ombres', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    app.detall.preparar = False
    obj = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    os.makedirs(CARPETA, exist_ok=True)

    def fotograma():
        glfw.poll_events()
        app.dt = 1 / 60
        app.ui_renderer.new_frame()
        io.display_size, io.display_framebuffer_scale = (W, H), (1.0, 1.0)
        imgui.new_frame()
        obj.use()
        app.render()
        imgui.render()

    def imatge():
        return Image.frombytes('RGB', (W, H), obj.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    def temps(n=120):
        t = []
        for _ in range(n):
            t0 = time.perf_counter()
            fotograma()
            app.ctx.finish()
            t.append((time.perf_counter() - t0) * 1000)
        return float(np.median(t))

    from basecode.camera_exploracio import direccio_mirada
    from basecode.ombres_relleu import BIAIX_KM
    distancies = np.concatenate([np.arange(0.02, 2.0, 0.02), np.arange(2.0, 80.0, 0.1)])
    pen = app.peninsula

    def alcada(lat_, lon_):
        us, vs = pen.latlon_a_uv(lat_, lon_)
        dins = (us >= 0) & (us <= 1) & (vs >= 0) & (vs <= 1)
        h = np.full(np.shape(us), np.nan)
        if dins.any():
            h[dins] = np.maximum(pen.alcada_dibuixada_uv(us[dins], vs[dins]), 0.0) / 1000.0
        return h

    errors = []
    for nom, lat, lon, alt, rumb, incl, hora in VISTES:
        app.hora = hora
        app.camera.aturar_moviment()
        app.camera.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + alt)
        app.camera.orientar(rumb, incl)
        t = time.time()
        while time.time() - t < 30 and (time.time() - t < 4 or app.mosaic.descarregador.pendents()):
            fotograma()
        resultats = {}
        for etiqueta, actiu, depuracio in (('sense', False, False), ('amb', True, False), ('factor', True, True)):
            app.ombres.actiu, app.ombres.depuracio = actiu, depuracio
            for _ in range(5):
                fotograma()
            imatge().save(os.path.join(CARPETA, f'{nom}_{etiqueta}.png'))
            resultats[etiqueta] = temps() if not depuracio else None
        # la passada des del Sol sola (es refa nomes quan canvia l'hora; aqui es forca)
        app.ombres.depuracio = False
        t_pas = []
        for k in range(20):
            app.hora = hora + (k + 1) / 3600.0
            t0 = time.perf_counter()
            app.ombres.actualitzar()
            app.ctx.finish()
            t_pas.append((time.perf_counter() - t0) * 1000)
        # GPU contra CPU (amb el mapa de l'hora de la captura)
        app.hora = hora
        app.ombres.depuracio = True
        fotograma()
        fac = np.frombuffer(obj.read(components=3), 'u1').reshape(H, W, 3)[..., 0] / 255.0
        prof = np.frombuffer(obj.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        app.ombres.depuracio = False
        la_a, lo_a, _ = (float(v) for v in geodesia.geodesiques(app.ombres.ancora))
        az, el = geodesia.azimut_elevacio(app.sol_ecef - geodesia.ecef(la_a, lo_a, 0.0), la_a, lo_a)
        cap_al_sol = direccio_mirada(la_a, lo_a, az, el + geodesia.refraccio_graus(el))
        limit_m = app.ombres.desplacament_km() + BIAIX_KM
        n = iguals = limit = 0
        for py in np.linspace(H * 0.3, H * 0.95, 30).astype(int):
            for px in np.linspace(W * 0.05, W * 0.95, 40).astype(int):
                d, fv = float(prof[py, px]), fac[py, px]
                if d >= 1.0 or 0.1 <= fv <= 0.9:
                    continue
                p0 = app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)
                if np.linalg.norm(p0 - app.ombres.ancora) > 0.9 * app.ombres.texel_km * 4096 / 2:
                    continue
                q = p0 + distancies[:, None] * cap_al_sol
                la_q, lo_q, al_q = geodesia.geodesiques(q)
                m = float(np.nanmax(alcada(la_q, lo_q) - al_q))
                n += 1
                if (m > 0) == (fv < 0.1):
                    iguals += 1
                elif (0 < m < limit_m) if fv > 0.9 else (-limit_m < m <= 0):
                    limit += 1
        frac = (iguals + limit) / max(n, 1)
        if n == 0 or frac < 0.95:
            errors.append(nom)
        f = np.asarray(Image.open(os.path.join(CARPETA, f'{nom}_factor.png')).convert('L'), float)
        terreny = f[H // 3:]
        print(f'{nom}: zona {app.zona.cami if app.zona else None}; mapa valid {app.ombres.valid}, ancora a '
              f'{np.round(geodesia.geodesiques(app.ombres.ancora)[:2], 3)}; fotograma {resultats["sense"]:.1f} ms sense '
              f'ombres, {resultats["amb"]:.1f} ms amb; passada des del Sol {np.median(t_pas):.1f} ms (1 cop per segon '
              f'de temps de l\'eclipsi); terreny a l\'ombra a la meitat de baix: {(terreny < 60).mean() * 100:.1f} %; '
              f'GPU contra CPU: {n} punts, coincideixen {iguals}, casos limit {limit} -> {frac * 100:.1f} %',
              flush=True)
    app._shutdown()
    print('\n' + ('Tot correcte' if not errors else f'GPU contra CPU per sota del 95 %: {errors}'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
