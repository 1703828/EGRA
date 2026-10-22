"""
Prova del programa real (main.py) a les sis ubicacions: el que ha de funcionar quan l'equip fa servir la
finestra. Per defecte la finestra queda amagada i es dibuixa en un framebuffer; amb --visible es fa
servir la finestra de veritat (es veu com passa la prova).

Per a cada ubicacio (Picos, Vic, l'Escala, Cerdanyola, Montmelo, la UAB):
  1. Ulls: mirant cap avall, la distancia (llegida del depth buffer) als triangles dibuixats es 1,7 m.
     Tambe s'escriu la diferencia entre la superficie dibuixada i el MDT original en aquell punt.
  2. Mirar al voltant i cap als peus: mirant avall (-30 i -60 graus), a la meitat de baix de la imatge
     tot es terreny proper (cap pixel de cel ni del globus llunya). Es el que fallava a la 10.1.
  3. Pausa i reproduccio: la mirada i els ulls no es mouen, el temps avanca i, en pausa, es congela.
  4. Allunyar-se fins a l'espai (camera d'exploracio, roda) i tornar al punt d'observacio: la vista
     d'observacio conserva els ulls i la mirada.
  5. "Anar al maxim": l'hora es la del maxim, pausat i sense moure la camera.
  6. L'ombra a hores representatives: brillantor del terra a l'inici, al maxim i al final, i
     "Veure l'ombra des de l'espai": el centre de la imatge es el punt on l'ombra es mes fosca.
Al final, que el controlador no hagi escrit cap avis de textures ("UNSUPPORTED").

Les captures de cada ubicacio es desen a captures/proves/ (carpeta ignorada pel Git) per inspeccionar-les.

Executa (des de l'arrel del projecte, amb l'entorn egra):
    python scripts/prova_vistes.py              # finestra amagada
    python scripts/prova_vistes.py --visible    # amb la finestra visible
"""
import argparse
import math
import os
import sys
import tempfile

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
SORTIDA = os.path.join(ARREL, 'captures', 'proves')

# els avisos del controlador d'OpenGL van directament al descriptor 2 (stderr): els desviem a un fitxer
# per poder-los comprovar al final, i els tornem a escriure a la consola
_stderr = os.dup(2)
_avisos = tempfile.TemporaryFile()
os.dup2(_avisos.fileno(), 2)

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from slimgui import imgui  # noqa: E402

TOLERANCIA_ULLS_M = 0.02   # 2 cm: el depth buffer de 24 bits amb profunditat logaritmica resol ~1 mm a 2 m
DISTANCIA_PEUS_KM = 0.5    # mirant avall, tot el que hi ha a la meitat de baix de la imatge es a menys de 500 m


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--visible', action='store_true', help='fer servir la finestra visible')
    a = p.parse_args()

    glfw.init()
    if not a.visible:
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from basecode.camera_exploracio import COEF_LOG
    from dades import geodesia, eclipse_data
    from dades.model_eclipsi import punt_ombra

    W, H = 960, 640
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de les vistes', use_ui_panel=True)
    if a.visible:
        W, H = glfw.get_framebuffer_size(app.window)
        objectiu = app.ctx.screen
    else:
        objectiu = app.ctx.simple_framebuffer((W, H))
    os.makedirs(SORTIDA, exist_ok=True)
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    def fotograma(n=1):
        for _ in range(n):
            app.dt = 1 / 60
            app.ui_renderer.new_frame()
            imgui.new_frame()
            objectiu.use()
            app.render()
            imgui.render()   # el panell no es dibuixa: nomes cal tancar el fotograma d'imgui
        if a.visible:
            glfw.swap_buffers(app.window)
            glfw.poll_events()

    def llegir_distancies():
        """Distancia (km, al llarg de l'eix de la camera) de cada pixel; inf on no hi ha res (cel)."""
        d = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)[::-1]
        w = 2.0 ** (d.astype(float) * 2.0 / COEF_LOG) - 1.0
        w[d >= 1.0] = np.inf
        return w

    def imatge():
        return Image.frombytes('RGB', (W, H), objectiu.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM)

    def full(imatges, columnes=4, escala=0.5):
        w, h = int(W * escala), int(H * escala)
        files = (len(imatges) + columnes - 1) // columnes
        f = Image.new('RGB', (w * columnes, h * files))
        dib = ImageDraw.Draw(f)
        for i, (im, text) in enumerate(imatges):
            x, y = (i % columnes) * w, (i // columnes) * h
            f.paste(im.resize((w, h)), (x, y))
            dib.text((x + 6, y + 6), text, fill=(255, 255, 0))
        return f

    co, ce = app.camera_observador, app.camera_exploracio
    for k, (nom, lat, lon) in enumerate(programa.UBICACIONS):
        print(f'\n== {nom}')
        app.reproduint = False
        app.canviar_vista(1)
        ok(app.triar_punt(lat, lon, nom), 'en pausa es pot triar el punt')
        ok(app.nom_zona is not None, f'zona de detall de 5 m carregada: {app.nom_zona}')
        m = app.model
        app.hora = m.hores['maxim'] - 20 / 60
        captures = []

        # 1. ulls a 1,7 m dels triangles dibuixats
        co.mirar(0.0, -89.99)
        fotograma(2)
        dist = llegir_distancies()[H // 2, W // 2] * 1000
        ok(abs(dist - 1.7) < TOLERANCIA_ULLS_M, f'mirant avall, el terra dibuixat es a {dist:.3f} m dels ulls')
        dibuixada = app.altitud_terra_km(lat, lon) * 1000
        original = app.zona.altitud_latlon(lat, lon, dibuixada=False)
        print(f'      terra dibuixat {dibuixada:.2f} m, MDT original {original:.2f} m '
              f'(diferencia {dibuixada - original:+.2f} m)')

        # 2. mirar al voltant i als peus
        az_sol, _ = m.sol(app.hora)
        for rumb, inc in ((0, -5), (90, -5), (180, -5), (270, -5), (az_sol, -30), (az_sol + 90, -60)):
            co.mirar(rumb, inc)
            fotograma(2)
            captures.append((imatge(), f'{nom}  rumb {rumb % 360:.0f}  incl {inc}'))
            if inc <= -30:
                baix = llegir_distancies()[H // 2:]
                ok(np.isfinite(baix).all() and baix.max() < DISTANCIA_PEUS_KM,
                   f'mirant a {inc} graus, la meitat de baix es terreny a menys de {baix.max() * 1000:.0f} m')

        # 3. pausa i reproduccio sense moure la mirada
        co.mirar(az_sol, 5.0)
        fotograma()
        ulls, mirada, h0 = co.posicio.copy(), (co.rumb, co.inclinacio), app.hora
        app.reproduir_pausar()
        fotograma(30)
        ok(app.reproduint and app.hora > h0 and np.allclose(co.posicio, ulls)
           and (co.rumb, co.inclinacio) == mirada, 'reproduint: el temps avanca i els ulls i la mirada no es mouen')
        app.reproduir_pausar()
        h1 = app.hora
        fotograma(30)
        ok(app.hora == h1 and (co.rumb, co.inclinacio) == mirada, 'en pausa, el temps es congela')

        # 4. allunyar-se fins a l'espai i tornar
        app.posar_exploracio_sobre_el_punt()
        app.canviar_vista(0)
        ce.inclinacio = -60.0
        alcades = []
        for i in range(60):
            ce.avancar(-1.0)
            fotograma()
            alcada = ce.alcada_sobre_terra()
            for objectiu_km in (50, 800, 20000):
                if alcada > objectiu_km and objectiu_km not in alcades:
                    alcades.append(objectiu_km)
                    captures.append((imatge(), f'{nom}  explorant a {alcada:,.0f} km'))
            if alcada > 20000:
                break
        ok(alcades == [50, 800, 20000] and app.hora == h1,
           f'allunyar-se fins a {ce.alcada_sobre_terra():,.0f} km sense canviar l\'hora')
        app.tornar_al_punt()
        fotograma()
        ok(app.vista == 1 and np.allclose(co.posicio, ulls, atol=1e-9) and (co.rumb, co.inclinacio) == mirada,
           "tornar al punt d'observacio: els mateixos ulls i la mateixa mirada")

        # 5. anar al maxim
        pos = co.posicio.copy()
        app.anar_al_maxim()
        fotograma()
        ok(app.hora == m.hores['maxim'] and not app.reproduint and np.allclose(co.posicio, pos),
           f"anar al maxim: {eclipse_data.hora_local(app.hora)}, pausat, la camera no es mou")

        # 6. l'ombra a hores representatives: brillantor del terra mirant avall cap al Sol
        brillantors = []
        for etiqueta, hora in (('inici', m.hores['c1'] + 5 / 60), ('maxim', m.hores['maxim']),
                               ('final', min(m.hores['c4'] or app.ef.final, app.ef.final) - 5 / 60)):
            app.hora = hora
            co.mirar(az_sol, -20.0)
            fotograma(2)
            im = imatge()
            brillantors.append(np.asarray(im)[H // 2:].mean())
            captures.append((im, f'{nom}  {etiqueta} {eclipse_data.hora_local(hora)}  '
                                 f'Sol tapat {app.tapada * 100:.1f} %'))
        ok(brillantors[1] < brillantors[0],
           f"al maxim el terra es mes fosc que a l'inici (brillantor {brillantors[0]:.0f} -> {brillantors[1]:.0f})")
        app.hora = m.hores['maxim']
        app.veure_ombra_des_de_lespai()
        fotograma(2)
        dist_c = llegir_distancies()[H // 2, W // 2]
        punt = ce.posicio + ce.davant() * dist_c / np.dot(ce.davant(), ce.davant())
        lat_c, lon_c, _ = geodesia.geodesiques(punt)
        lat_o, lon_o, _ = punt_ombra(app.hora)
        sep = geodesia.ecef(float(lat_c), float(lon_c), 0.0) - geodesia.ecef(lat_o, lon_o, 0.0)
        ok(np.linalg.norm(sep) < 50, f"veure l'ombra des de l'espai: el centre de la imatge es a "
                                     f"{np.linalg.norm(sep):.1f} km del punt mes fosc de l'ombra")
        captures.append((imatge(), f"{nom}  l'ombra des de l'espai, {eclipse_data.hora_local(app.hora)}"))
        app.ressaltar_ombra = True
        fotograma(2)
        captures.append((imatge(), f"{nom}  el mateix, amb les linies (didactic)"))
        app.ressaltar_ombra = False
        full(captures).save(os.path.join(SORTIDA, f'{k}_{nom.split(",")[0].split(" (")[0].replace(" ", "_")}.png'))

    # comprovacions generals (independents de la ubicacio)
    print('\n== General')
    o = app.observador
    app.reproduir_pausar()
    ok(app.triar_punt(41.5, 2.1) is False and app.observador is o, 'durant la reproduccio no es pot canviar el punt')
    app.reproduir_pausar()
    app.posar_exploracio_sobre_el_punt()
    app.canviar_vista(0)
    ce.inclinacio = -45.0
    fotograma(2)
    d = float(np.frombuffer(objectiu.read(viewport=(W // 2, H // 2, 1, 1), components=1, attachment=-1,
                                          dtype='f4'), 'f4')[0])
    lat_p, lon_p, alt_p = geodesia.geodesiques(ce.desprojectar(W // 2 + 0.5, H // 2 + 0.5, d, W, H))
    dif = (float(alt_p) - app.altitud_terra_km(float(lat_p), float(lon_p))) * 1000
    ok(abs(dif) < 1.0, f'doble clic (picking): el punt queda a {dif:+.2f} m de la superficie dibuixada')
    p0, v0 = ce.posicio.copy(), ce.velocitat()
    ce.moure(1, 0, 0, 0.5)
    ok(v0 < 10 and np.linalg.norm(ce.posicio - p0) > 0, f'a {ce.alcada_sobre_terra():.1f} km del terra, W va a {v0:.2f} km/s')
    ce.posicio = ce.posicio + 20000 * ce.posicio / np.linalg.norm(ce.posicio)
    ok(ce.velocitat() > 1000, f'a {ce.alcada_sobre_terra():,.0f} km, W va a {ce.velocitat():,.0f} km/s')

    app._shutdown()
    # avisos del controlador
    os.dup2(_stderr, 2)
    _avisos.seek(0)
    text = _avisos.read().decode(errors='replace')
    sys.stderr.write(text)
    ok('UNSUPPORTED' not in text, "el controlador no ha escrit cap avis de textures ('UNSUPPORTED')")
    print(f'\nCaptures a {SORTIDA}')
    print('RESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
