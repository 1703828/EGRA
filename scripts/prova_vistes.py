"""
Prova del programa real (main.py) a les sis ubicacions: el que ha de funcionar quan l'equip fa servir la
finestra. Es dibuixa en un framebuffer propi, que es el que es llegeix; per defecte la finestra queda
amagada i amb --visible es mostra i hi va apareixent cada fotograma (es veu com passa la prova).

Per a cada ubicacio (Picos, Vic, l'Escala, Cerdanyola, Montmelo, la UAB):
  1. Ulls: mirant cap avall, la distancia (llegida del depth buffer) als triangles dibuixats es 1,7 m.
     Tambe s'escriu la diferencia entre la superficie dibuixada i el MDT original en aquell punt.
  2. Mirar al voltant i cap als peus: mirant avall (-30 i -60 graus), a la meitat de baix de la imatge
     tot es terreny proper (cap pixel de cel ni del globus llunya). Es el que fallava a la 10.1.
  3. Pausa i reproduccio: la mirada i els ulls no es mouen, el temps avanca i, en pausa, es congela.
  4. Allunyar-se fins a l'espai (camera d'exploracio, roda): a cada fotograma, una graella de pixels es
     desprojecta i ha de caure sobre la superficie dibuixada i de cara a la camera (sense forats entre
     nivells de detall ni l'interior del globus). A dalt, reprendre el temps no mou la camera. Tornar al
     punt d'observacio conserva els ulls i la mirada.
  5. "Anar al maxim": l'hora es la del maxim, pausat i sense moure la camera.
  6. L'ombra a hores representatives: brillantor del terra a l'inici, al maxim i al final, i
     "Veure l'ombra des de l'espai": el centre de la imatge es el punt on l'ombra es mes fosca.
Despres: canviar d'ubicacio des de l'exploracio no mou aquella camera, i la sequencia sencera de l'equip
(triar, observar, girar amb fletxes i ratoli, P, explorar fins a l'espai, P, tornar) amb el bucle real del
programa, el panell dibuixat i el teclat i el ratoli simulats. Al final, que el controlador no hagi escrit
cap avis de textures ("UNSUPPORTED ... texture unloadable").

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
    # es dibuixa en un framebuffer propi (el que es llegeix); amb --visible, cada fotograma es copia a la
    # finestra (llegir directament el framebuffer de la finestra de macOS dona imatges incorrectes)
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
                app.ctx.copy_framebuffer(app.ctx.screen, objectiu)
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

    # distancia a la costa de la peninsula (km; mar i fora d'Espanya > 0): alla la peninsula descarta el
    # fragment i es veu el globus
    pen = app.peninsula
    costa = np.frombuffer(pen.tex_costa.read(), 'f2').reshape(pen.alt.shape)

    def es_veu_el_globus(lat, lon):
        """True si en aquest punt hi pot haver el globus en lloc de relleu: fora de la zona de 5 m (que
        dibuixa el seu mar) i al mar o fora d'Espanya a la peninsula (amb 0,5 km de marge a la costa, per
        la textura filtrada)."""
        if app.zona is not None and app.zona.conte(lat, lon):
            return False
        u, v = pen.latlon_a_uv(lat, lon)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            return True
        files, cols = costa.shape
        return costa[min(int(v * files), files - 1), min(int(u * cols), cols - 1)] > -0.5

    def coherencia_superficie(n_x=16, n_y=12):
        """Desprojecta una graella de pixels de la camera d'exploracio i, per a cada un que es la Terra,
        comprova que el punt es sobre una de les dues superficies que hi poden ser:
          - el relleu: l'altitud coincideix amb la dels triangles dibuixats (calculada a la CPU), amb
            35 m de marge (les faldilles baixen 30 m) mes la precisio del depth buffer (24 bits amb
            profunditat logaritmica: ~1,3e-6 de la distancia, ln(far) x 2^-24; se'n prenen 2e-6);
          - el globus, nomes on la peninsula no dibuixa (es_veu_el_globus): entre 0 i 120 m per sota de
            l'el·lipsoide (la cara plana entre vertexs de la malla) i, a mes, terra.frag empeny la seva
            profunditat 2e-5 de la distancia perque el relleu li guanyi sempre (2,1e-5 amb la precisio).
        Un forat entre nivells de detall deixaria veure el globus on hi ha d'haver relleu; l'interior del
        globus es veu per sota (el raig arriba a la superficie pujant).
        Retorna (pitjor diferencia amb el relleu en km, pixels fora, vistos per sota, pixels de terra)."""
        prof = np.frombuffer(objectiu.read(components=1, attachment=-1, dtype='f4'), 'f4').reshape(H, W)
        pitjor, fora, esquena, n = 0.0, 0, 0, 0
        for py in np.linspace(H * 0.05, H * 0.95, n_y).astype(int):       # files del framebuffer
            for px in np.linspace(W * 0.05, W * 0.95, n_x).astype(int):
                d = float(prof[py, px])
                if d >= 1.0:   # cel
                    continue
                punt = ce.desprojectar(px + 0.5, py + 0.5, d, W, H)
                r = float(np.linalg.norm(punt - ce.posicio))
                lat_p, lon_p, alt_p = (float(c) for c in geodesia.geodesiques(punt))
                if alt_p > 100.0:   # el Sol o la Lluna
                    continue
                _, _, amunt = geodesia.base_local(lat_p, lon_p)
                esquena += np.dot(amunt, (punt - ce.posicio) / r) > 0.02
                dif = alt_p - app.altitud_terra_km(lat_p, lon_p)
                relleu = abs(dif) <= 0.035 + 2e-6 * r
                globus = -(0.12 + 2.1e-5 * r) <= alt_p <= 2e-6 * r and es_veu_el_globus(lat_p, lon_p)
                fora += not (relleu or globus)
                if not globus and abs(dif) > abs(pitjor):
                    pitjor = dif
                n += 1
        return pitjor, fora, esquena, n

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

        # 4. allunyar-se fins a l'espai (comprovant la superficie a cada fotograma), reprendre el temps
        # alla dalt i tornar
        app.posar_exploracio_sobre_el_punt()
        app.canviar_vista(0)
        ce.inclinacio = -60.0
        alcades, pitjor, fora, esquena, n_total = [], (0.0, 0.0), 0, 0, 0
        for i in range(60):
            ce.avancar(-1.0)
            fotograma()
            alcada = ce.alcada_sobre_terra()
            dif, n_fora, n_esquena, n_pixels = coherencia_superficie()
            fora, esquena, n_total = fora + n_fora, esquena + n_esquena, n_total + n_pixels
            if abs(dif) > abs(pitjor[0]):
                pitjor = (dif, alcada)
            for objectiu_km in (50, 800, 20000):
                if alcada > objectiu_km and objectiu_km not in alcades:
                    alcades.append(objectiu_km)
                    captures.append((imatge(), f'{nom}  explorant a {alcada:,.0f} km'))
            if alcada > 20000:
                break
        ok(alcades == [50, 800, 20000] and app.hora == h1,
           f'allunyar-se fins a {ce.alcada_sobre_terra():,.0f} km sense canviar l\'hora')
        ok(fora == 0 and esquena == 0, f'pujant, {n_total} pixels de terra: {fora} fora de la superficie dibuixada, '
                                       f'{esquena} vistos per sota (pitjor {pitjor[0] * 1000:+.1f} m, a {pitjor[1]:,.1f} km)')
        cam, mirada_ce, h2 = ce.posicio.copy(), (ce.rumb, ce.inclinacio), app.hora
        app.reproduir_pausar()
        fotograma(30)
        app.reproduir_pausar()
        ok(app.hora > h2 and np.array_equal(ce.posicio, cam) and (ce.rumb, ce.inclinacio) == mirada_ce,
           "a l'espai, reprendre el temps no mou la camera d'exploracio (ni la posicio ni l'orientacio)")
        app.hora = h1
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
    cam, ulls = ce.posicio.copy(), app.ulls()
    nom, lat, lon = programa.UBICACIONS[1]
    app.triar_punt(lat, lon, nom)
    fotograma()
    ok(np.array_equal(ce.posicio, cam) and np.linalg.norm(app.ulls() - ulls) > 10,
       "canviar d'ubicacio des de l'exploracio: la camera d'exploracio no es mou; els ulls van al punt nou")

    bucle_real(app, programa, ok)   # l'ultima: en acabar, run() tanca el programa
    # avisos del controlador
    os.dup2(_stderr, 2)
    _avisos.seek(0)
    text = _avisos.read().decode(errors='replace')
    sys.stderr.write(text)
    ok('UNSUPPORTED' not in text and 'unloadable' not in text,
       "el controlador no ha escrit cap avis de textures ('UNSUPPORTED', 'texture unloadable')")
    print(f'\nCaptures a {SORTIDA}')
    print('RESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


def bucle_real(app, programa, ok):
    """La sequencia que fa l'equip, amb el bucle real del programa (GraphicsEngineBase.run: el panell es
    dibuixa a cada fotograma) i el teclat i el ratoli simulats: les tecles P i V i el ratoli entren com a
    esdeveniments d'imgui (els mateixos que envia GLFW); les fletxes, que el programa llegeix amb
    glfw.get_key, es simulen substituint aquesta funcio. Triar la ubicacio crida app.triar_ubicacio, que es el
    que fa el desplegable del panell. Comprova l'estat (no les imatges: llegir el framebuffer de la finestra
    de macOS no es fiable)."""
    from basecode import window as winmod
    co, ce = app.camera_observador, app.camera_exploracio
    io = imgui.get_io()
    premudes = set()
    get_key = glfw.get_key
    glfw.get_key = lambda finestra, k: glfw.PRESS if k in premudes else get_key(finestra, k)
    estat = {}

    def tecla(k):   # premer i deixar anar en dos fotogrames: es retorna el que cal fer a cada un
        return [lambda: io.add_key_event(k, True), lambda: io.add_key_event(k, False)]

    def desa(nom):
        return lambda: estat.__setitem__(nom, dict(ulls=co.posicio.copy(), mirada=(co.rumb, co.inclinacio),
                                                   cam=ce.posicio.copy(), cam_mirada=(ce.rumb, ce.inclinacio),
                                                   hora=app.hora, reproduint=app.reproduint, vista=app.vista))

    nom, lat, lon = programa.UBICACIONS[3]
    passos = [lambda: app.triar_ubicacio(lat, lon, nom), lambda: app.canviar_vista(1),   # 1. triar la ubicacio
              lambda: co.mirar(200.0, 5.0), desa('inici'),
              lambda: premudes.add(glfw.KEY_RIGHT)] + [None] * 15 + [             # 3. girar amb les fletxes
              lambda: premudes.clear(), desa('fletxes'),
              lambda: (io.add_mouse_pos_event(700, 400), io.add_mouse_button_event(0, True))] + [
              (lambda i=i: io.add_mouse_pos_event(700 + 8 * i, 400 - 3 * i)) for i in range(1, 10)] + [
              lambda: io.add_mouse_button_event(0, False), None, desa('ratoli')] + \
             tecla(imgui.Key.KEY_P) + [None] * 20 + [desa('reproduint')] + tecla(imgui.Key.KEY_P) + [  # 4. P
              desa('pausa')] + [None] * 10 + [desa('pausa_despres')] + \
             tecla(imgui.Key.KEY_V) + [None, desa('exploracio')] + [                # 5. explorar i allunyar-se
              (lambda: io.add_mouse_wheel_event(0.0, -1.0)) for _ in range(90)] + [None, desa('espai')] + \
             tecla(imgui.Key.KEY_P) + [None] * 20 + [desa('espai_reproduint')] + tecla(imgui.Key.KEY_P) + [  # 6
              lambda: app.tornar_al_punt(), None, desa('tornada')]                  # 7. tornar al punt
    # despres, les capes i els filferros de l'apartat Avancat, i canviar de zona (per als avisos de textures)
    for capa in (1, 2, 3, 0):
        passos += [lambda c=capa: [setattr(t, 'overlay', c) for t in app.terrenys()], None]
    passos += [lambda: [setattr(t, 'wireframe', True) for t in app.terrenys()], None,
               lambda: [setattr(t, 'wireframe', False) for t in app.terrenys()],
               lambda: app.triar_punt(*programa.UBICACIONS[0][1:], programa.UBICACIONS[0][0]), None, None]
    n = [0]
    render = app.render

    def render_amb_passos():
        if n[0] < len(passos) and passos[n[0]] is not None:
            passos[n[0]]()
        render()
        n[0] += 1

    app.render = render_amb_passos
    should_close = winmod.should_close
    winmod.should_close = lambda finestra: n[0] >= len(passos) + 2
    print('\n== Sequencia amb el bucle real i el panell')
    app.run()
    winmod.should_close, glfw.get_key, app.render = should_close, get_key, render

    e = estat
    ok(e['inici']['vista'] == 1 and app.nom_zona is not None,
       f"1-2. ubicacio triada ({nom}) i vista d'observacio als ulls")
    ok(e['fletxes']['mirada'][0] != e['inici']['mirada'][0] and np.allclose(e['fletxes']['ulls'], e['inici']['ulls']),
       f"3. fletxa dreta: el rumb passa de {e['inici']['mirada'][0]:.1f} a {e['fletxes']['mirada'][0]:.1f} graus "
       f"i els ulls no es mouen")
    ok(e['ratoli']['mirada'] != e['fletxes']['mirada'] and np.allclose(e['ratoli']['ulls'], e['inici']['ulls']),
       f"3. arrossegar el ratoli: la mirada passa a ({e['ratoli']['mirada'][0]:.1f}, {e['ratoli']['mirada'][1]:.1f}) "
       f"graus i els ulls no es mouen")
    r, p, pd = e['reproduint'], e['pausa'], e['pausa_despres']
    ok(r['reproduint'] and r['hora'] > e['ratoli']['hora'] and r['mirada'] == e['ratoli']['mirada']
       and np.allclose(r['ulls'], e['inici']['ulls']),
       '4. tecla P: el temps avanca i la mirada (que no segueix el Sol) i els ulls es queden')
    ok(not p['reproduint'] and pd['hora'] == p['hora'], '4. tecla P altra vegada: el temps es congela')
    x, s, sr = e['exploracio'], e['espai'], e['espai_reproduint']
    alt = float(np.linalg.norm(s['cam'])) - 6371.0
    sobre = float(np.linalg.norm(x['cam'] - x['ulls']))
    ok(x['vista'] == 0 and sobre < 20.0, f"5. tecla V: l'exploracio comenca a {sobre:.1f} km dels ulls, "
                                          f"sobre la ubicacio triada")
    ok(x['vista'] == 0 and alt > 5000 and s['hora'] == p['hora'],
       f"5. tecla V i roda: la camera d'exploracio puja a ~{alt:,.0f} km sense canviar l'hora")
    ok(sr['reproduint'] and sr['hora'] > s['hora'] and np.array_equal(sr['cam'], s['cam'])
       and sr['cam_mirada'] == s['cam_mirada'],
       "6. tecla P a l'espai: el temps avanca i la camera no es mou ni gira")
    t = e['tornada']
    ok(t['vista'] == 1 and np.allclose(t['ulls'], e['inici']['ulls']) and t['mirada'] == e['ratoli']['mirada'],
       "7. tornar al punt d'observacio: els mateixos ulls i la mirada que s'havia deixat")


if __name__ == '__main__':
    sys.exit(main())
