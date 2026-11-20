"""
Captures i temps de GPU dels edificis en vistes fixes (programa real, finestra amagada): des del carrer i des de l'aire
a Mataro (33.009 parts) i a Moia (5.609). Serveix per comparar l'aspecte i el cost abans i despres d'un canvi als shaders.

Cada vista: la camera hi va (des del carrer, amb anar_al_punt: els ulls a l'exterior dels edificis, i el rumb que veu
edificis entre 30 i 200 m, d'entre 12 provats), s'espera que arribin les teselles de la foto (com a molt 60 s), es desa la captura a
captures/edificis/<etiqueta>_<vista>.png i es mesura el temps de dibuix (mediana de 120 fotogrames, amb
ctx.finish() perque la mesura inclogui la GPU; aqui volem precisament aquest temps).
Les dades dels llocs han de ser al disc (no se'n preparen de noves: detall.preparar = False).

Executa:  python scripts/captura_edificis.py <etiqueta> [--sense-foto] [--vegetacio] [--vistes a,b,...]
  --sense-foto: sense la fotografia aeria (com abans que arribin les teselles): les cobertes amb el material
                provisional; nomes les vistes aeries
  --vegetacio:  amb la vegetacio (basecode/vegetacio.py) i nomes les vistes VISTES_VEGETACIO; s'espera que estigui
                carregada i es diu quant ha tardat (carrega de dades, a part del temps de dibuix)
  --vistes:     nomes aquestes vistes (noms de VISTES o VISTES_VEGETACIO)
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA = os.path.join(ARREL, 'captures', 'edificis')
# (nom, lat, lon, altura sobre el terra en km, rumb, inclinacio)
VISTES = [('mataro_carrer', 41.5390, 2.4440, 0.0017, 160.0, 8.0),
          ('mataro_carrer2', 41.5410, 2.4410, 0.0017, 60.0, 12.0),
          ('mataro_200m', 41.5370, 2.4420, 0.20, 40.0, -30.0),
          ('mataro_1km', 41.5300, 2.4350, 1.0, 40.0, -35.0),
          ('mataro_industrial', None, 3, 0.0017, 0.0, 6.0),     # (None, tipus): davant de l'edifici mes gran d'aquell tipus
          ('mataro_comercial', None, 2, 0.0017, 0.0, 6.0),
          ('moia_carrer', 41.8110, 2.0970, 0.0017, 250.0, 10.0),
          ('moia_300m', 41.8070, 2.0930, 0.30, 30.0, -35.0),
          ('uab_carrer', 41.5018, 2.1041, 0.0017, 100.0, 8.0),       # zones fetes a ma (data_io.ZONES_DETALL)
          ('uab_300m', 41.4990, 2.1000, 0.30, 40.0, -35.0),
          ('vic_carrer', 41.9301, 2.2545, 0.0017, 0.0, 8.0),
          ('vic_300m', 41.9270, 2.2510, 0.30, 30.0, -35.0),
          ('escala_carrer', 42.1226, 3.1336, 0.0017, 0.0, 8.0),
          ('escala_300m', 42.1190, 3.1300, 0.30, 30.0, -35.0)]
# vegetacio: llocs amb arbres mesurats (UAB, Cerdanyola, Vic); rumb fix perque la comparacio sigui la mateixa camera
VISTES_VEGETACIO = [('veg_uab_12m', 41.5018, 2.1041, 0.012, 100.0, -4.0),
                    ('veg_uab_40m', 41.5000, 2.1000, 0.04, 30.0, -12.0),
                    ('veg_uab_200m', 41.4980, 2.0990, 0.20, 30.0, -30.0),
                    ('veg_cerdanyola_100m', 41.4900, 2.1400, 0.10, 0.0, -20.0),
                    ('veg_vic_150m', 41.9300, 2.2500, 0.15, 60.0, -25.0)]


def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else 'prova'
    sense_foto = '--sense-foto' in sys.argv
    vegetacio = '--vegetacio' in sys.argv
    filtre = sys.argv[sys.argv.index('--vistes') + 1].split(',') if '--vistes' in sys.argv else None
    os.chdir(ARREL)
    sys.path.insert(0, ARREL)
    import glfw
    import numpy as np
    from OpenGL import GL
    from PIL import Image
    from slimgui import imgui
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    W, H = 1280, 860
    app = programa.GraphicsEngine(win_size=(W, H), title='captura', use_ui_panel=True)
    app.on_resize(app.window, W, H)
    app.detall.preparar = False
    if sense_foto:
        app.mosaic.actiu = False
    if vegetacio:
        app.vegetacio.actiu = True
        # temps de GPU de la passada de la vegetacio sola (consulta GL_TIME_ELAPSED al voltant de Vegetacio.render)
        temps_veg = []
        dibuixar_veg = app.vegetacio.render
        consulta = app.ctx.query(time=True)

        def render_mesurat():
            with consulta:
                dibuixar_veg()
            temps_veg.append(consulta.elapsed / 1e6)
        app.vegetacio.render = render_mesurat
    app.hora = 15.0                      # 17:00 local: Sol alt, abans de l'eclipsi
    obj = app.ctx.simple_framebuffer((W, H))
    io = imgui.get_io()
    os.makedirs(CARPETA, exist_ok=True)

    def punt(px, py):         # el picking del programa llegeix la pantalla; aqui, el framebuffer de la prova
        d = float(np.frombuffer(obj.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4'), 'f4')[0])
        return None if not 0.0 < d < 1.0 else app.camera.desprojectar(px + 0.5, py + 0.5, d, W, H)

    def millor_rumb(incl):
        millor = (-1, 0.0)
        for rumb in range(0, 360, 30):
            app.camera.orientar(float(rumb), incl)
            for _ in range(2):
                fotograma()
            d = [punt(x, y) for x in range(100, W, 120) for y in (H // 2, H // 3)]
            n = sum(1 for q in d if q is not None and 0.03 < np.linalg.norm(q - app.camera.posicio) < 0.2)
            millor = max(millor, (n, float(rumb)))
        return millor[1]

    def fotograma(ui=False):
        glfw.poll_events()
        app.dt = 1 / 60
        app.ui_renderer.new_frame()
        io.display_size, io.display_framebuffer_scale = (W, H), (1.0, 1.0)
        imgui.new_frame()
        obj.use()
        app.render()
        imgui.render()

    def davant_de_tipus(tipus):
        """(lat, lon) de l'edifici carregat mes gran d'aquell tipus (dades/edificis.tipus_parts), un punt a 45 m al sud
        del seu contorn, i el rumb cap a ell."""
        import shapely
        from pyproj import Transformer
        e = app.edificis
        i = max(np.flatnonzero(e.tipus == tipus), key=lambda k: shapely.area(e.contorns[k]))
        c = e.contorns[i]
        x, y = c.centroid.x, c.bounds[1] - 45.0
        lon, lat = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True).transform(x, y)
        return lat, lon

    for nom, lat, lon, alt, rumb, incl in (VISTES_VEGETACIO if vegetacio else VISTES):
        if sense_foto and alt < 0.01 or filtre and nom not in filtre:
            continue
        app.camera.aturar_moviment()
        if lat is None:
            lat, lon = davant_de_tipus(lon)
        t = time.time()
        if alt < 0.01:
            app.anar_al_punt(lat, lon)
        else:
            app.camera.posicio = geodesia.ecef(lat, lon, app.altitud_terra_km(lat, lon) + alt)
        app.camera.orientar(rumb, incl)
        while time.time() - t < 60:
            fotograma()
            # (lloc de la quadricula o zona feta a ma que conte el punt)
            if time.time() - t > 4 and not app.detall.feines and app.mosaic.descarregador.pendents() == 0 and \
                    app.edificis is not None and app.zona is not None and app.zona.conte(lat, lon) and \
                    not (vegetacio and (app.vegetacio.feines or not app.vegetacio.cel_les)):
                break
        carrega = time.time() - t
        if alt < 0.01:
            app.anar_al_punt(lat, lon)      # amb els edificis de la zona carregats, els ulls a l'exterior
            fix = 'industrial' in nom or 'comercial' in nom or vegetacio
            app.camera.orientar(rumb if fix else millor_rumb(incl), incl)
            t = time.time()
            while time.time() - t < 30 and (app.mosaic.descarregador.pendents() or time.time() - t < 2):
                fotograma()
        for _ in range(5):
            fotograma()
        Image.frombytes('RGB', (W, H), obj.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(CARPETA, f'{etiqueta}_{nom}.png'))
        temps = []
        if vegetacio:
            temps_veg.clear()
        for _ in range(120):
            t0 = time.perf_counter()
            fotograma()
            app.ctx.finish()
            temps.append((time.perf_counter() - t0) * 1000)
        e = app.edificis
        v = app.vegetacio
        print(f'{nom}: {np.median(temps):.1f} ms (p90 {np.percentile(temps, 90):.1f}); dades a punt en {carrega:.1f} s; '
              f'edificis {e.zona if e else None} {e.n_parts if e else 0} parts, {e.n_triangles if e else 0} triangles'
              + (f'; vegetacio {v.n_punts} punts a {len(v.cel_les)} cel·les, passada {np.median(temps_veg):.1f} ms de GPU'
                 if vegetacio else ''), flush=True)
    app._shutdown()


if __name__ == '__main__':
    main()
