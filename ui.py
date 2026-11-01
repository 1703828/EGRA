"""
Interficie del programa (slimgui): dos panells ("Eclipsi" a l'esquerra i "Camera" a la dreta) i la barra de temps.

GraphicsEngineBase (basecode/engine.py) obre la finestra "Opcions" a cada fotograma i crida
GraphicsEngine.build_ui(), que crida build_ui(app) d'aquest fitxer. imgui es una interficie
"immediata": es torna a dibuixar sencera a cada fotograma a partir de les variables del programa.

Els panells nomes tenen controls (sense textos d'explicacio, peticio de l'equip del 30/10), separats en dos (peticio
de l'equip de l'1/11):
  - "Eclipsi": quin eclipsi, fase i velocitat, punt d'observacio (amb el nom del lloc), mapa de visibilitat, linies
    de l'ombra de la Lluna i capes del CNIG.
  - "Camera": vista, on es la camera (alcada sobre el terra i altitud), que es dibuixa (foto, edificis, ombres del
    relleu) i l'estat del detall del lloc; les tecles i les opcions de depuracio en desplegables tancats.
Reproduir i pausar es a la barra de temps (a baix).
Textos sense accents: la font de slimgui no els mostra be (els noms dels serveis, p. ex. Valencia, es mostren sense).
"""
import unicodedata

import glfw
import glm
import numpy as np
from slimgui import imgui

from basecode.terrain import (OVERLAYS, MAPES, ENFOSQUIMENT_MIN, COLORS_ENFOSQUIMENT, COLOR_TOTALITAT,
                              COLORS_DURADA, COLORS_OMBRES, COLORS_CENTRAL, COLOR_TAPAT_RELLEU)
from dades import eclipse_data, eclipsis, geodesia, noms
from dades.observador import UBICACIONS

VISTES = ['Explorar', 'Des del terra', 'Espai (guiat)']
AMPLADA_PANELL = 300
# Noms de lloc sobre el mapa (noms_al_mapa): cada nivell es veu amb la camera entre aquestes altures sobre el terra
# (km): de lluny, nomes els mes importants; de prop, desapareixen (el terreny ja es reconeix i taparien la vista)
ALCADES_NOMS = {0: (25.0, 4000.0),    # capital de l'Estat i capitals de comunitat autonoma
                1: (12.0, 1500.0),    # capitals de provincia
                2: (3.0, 200.0)}      # capitals de comarca de Catalunya
MIDA_NOMS = {0: 19.0, 1: 16.0, 2: 14.0}          # mida de la lletra (punts)
VELOCITATS = [1, 10, 60, 300, 1000]   # x temps real ('Auto' a mes: lent a la totalitat)
COLOR_FASE = {'TOTALITAT': (1.0, 0.45, 0.9, 1.0), 'ANULARITAT': (1.0, 0.6, 0.2, 1.0),
              'Eclipsi parcial': (1.0, 0.8, 0.3, 1.0)}
COLOR_SUAU = (0.65, 0.68, 0.72, 1.0)
COLOR_AVIS = (1.0, 0.8, 0.4, 1.0)
COLOR_ALCADA_ESTIMADA = (0.30, 0.50, 0.95)   # el mateix que BLAU_ESTIMADA (shaders/edifici.frag)
# marques de la barra de temps: contacte, color
MARQUES = [('c1', (1.0, 0.85, 0.3)), ('c2', COLOR_TOTALITAT), ('maxim', (1.0, 1.0, 1.0)), ('c3', COLOR_TOTALITAT),
           ('c4', (1.0, 0.85, 0.3)), ('posta', (1.0, 0.45, 0.2))]


def build_ui(app):
    """Els dos panells i la finestra de la barra de temps. El panell "Eclipsi" es la finestra que obre el bucle de
    main.py (a l'esquerra); el panell "Camera" n'obre una altra a la dreta.
    Els controls no son parades de Tab (NO_TAB_STOP): imgui faria servir Tab per passar d'un control al
    seguent i es quedaria el teclat; aixi Tab queda lliure per capturar el ratoli (main.py, teclat)."""
    imgui.set_window_size((AMPLADA_PANELL, 0), imgui.Cond.ALWAYS)   # amplada fixa, alcada segons el contingut
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    panell_eclipsi(app)
    panell_temps(app)
    imgui.separator_text("Punt d'observacio")
    panell_punt(app)
    imgui.separator_text('Mapa de visibilitat')
    panell_mapa(app)
    panell_capes_eclipsi(app)
    imgui.text_disabled('IGN/CNIG, Catastro, NASA/JPL, PNOA, EOX')
    imgui.pop_item_flag()

    noms_al_mapa(app)
    panell_camera(app)
    barra_temps(app)
    avis_ratoli(app)


def panell_camera(app):
    """Finestra "Camera", a dalt a la dreta: com es mira, on es la camera, que es dibuixa i el detall del lloc."""
    w, _ = imgui.get_io().display_size
    imgui.set_next_window_pos((w - 10, 10), imgui.Cond.FIRST_USE_EVER, (1.0, 0.0))
    imgui.set_next_window_size((AMPLADA_PANELL, 0), imgui.Cond.ALWAYS)
    imgui.begin('Camera')
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    panell_vista(app)
    imgui.separator_text('On es la camera')
    panell_posicio(app)
    imgui.separator_text('Que es dibuixa')
    panell_capes(app)
    imgui.separator_text('Detall del lloc')
    panell_detall(app)
    if imgui.collapsing_header('Tecles')[0]:
        panell_tecles(app)
    if imgui.collapsing_header('Avancat')[0]:
        panell_avancat(app)
    imgui.pop_item_flag()
    imgui.end()


def preparar_noms(app):
    """Els noms del mapa (dades/noms.noms_mapa) amb la seva posicio ECEF (km) sobre el relleu de la peninsula: es
    calcula un cop."""
    llista = []
    for nom, nivell, lat, lon in noms.noms_mapa():
        alt = app.peninsula.altitud_latlon(lat, lon)
        p = geodesia.ecef(lat, lon, (alt or 0.0) / 1000.0)
        llista.append((sense_accents(nom), nivell, np.asarray(p, dtype=float)))
    return llista


def noms_al_mapa(app):
    """Escriu els noms de lloc importants sobre l'escena (fons d'imgui, sota els panells), segons l'altura de la
    camera sobre el terra (ALCADES_NOMS), com a Google Maps. Nomes a les vistes aeries (explorar en vol lliure i
    espai). No s'escriuen els que queden darrere de l'horitzo de la Terra ni els que en taparien un de mes
    important (o, a igual nivell, un de mes proper)."""
    if not app.mostrar_noms or app.vista == 1 or (app.vista == 0 and app.camera_exploracio.caminar):
        return
    if app.noms_mapa is None:
        app.noms_mapa = preparar_noms(app)
    cam = app.camera
    lat, lon, alt = (float(v) for v in geodesia.geodesiques(cam.posicio))
    h = alt - app.altitud_terra_km(lat, lon)
    w, hp = imgui.get_io().display_size
    vp = cam.m_proj * cam.m_view
    candidats = []
    for nom, nivell, p in app.noms_mapa:
        h0, h1 = ALCADES_NOMS[nivell]
        if not h0 < h < h1:
            continue
        rel = p - cam.posicio
        n = p / np.linalg.norm(p)
        if np.dot(-rel, n) <= 0:                    # darrere de l'horitzo (el pla tangent al punt)
            continue
        c = vp * glm.vec4(*(float(v) for v in rel), 1.0)
        if c.w <= 0:
            continue
        x, y = (c.x / c.w + 1) * 0.5 * w, (1 - c.y / c.w) * 0.5 * hp
        if -50 < x < w + 50 and -20 < y < hp + 20:
            candidats.append((nivell, float(np.linalg.norm(rel)), nom, x, y))
    dl = imgui.get_background_draw_list()
    font = imgui.get_font()
    ocupat = []
    for nivell, _, nom, x, y in sorted(candidats):
        mida = MIDA_NOMS[nivell]
        tw, th = imgui.calc_text_size(nom)
        tw, th = tw * mida / imgui.get_font_size(), th * mida / imgui.get_font_size()
        r = (x + 6, y - th / 2, x + 6 + tw, y + th / 2)
        if any(r[0] < o[2] + 4 and o[0] < r[2] + 4 and r[1] < o[3] + 2 and o[1] < r[3] + 2 for o in ocupat):
            continue
        ocupat.append(r)
        dl.add_circle_filled((x, y), 3.0, imgui.get_color_u32((1.0, 1.0, 1.0, 0.9)))
        dl.add_circle((x, y), 3.5, imgui.get_color_u32((0.0, 0.0, 0.0, 0.7)))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):         # vora fosca: es llegeix sobre qualsevol fons
            dl.add_text(font, mida, (r[0] + dx, r[1] + dy), imgui.get_color_u32((0.0, 0.0, 0.0, 0.75)), nom)
        dl.add_text(font, mida, (r[0], r[1]), imgui.get_color_u32((1.0, 1.0, 1.0, 1.0)), nom)


def distancia(km):
    """Text d'una distancia: en metres per sota d'1 km, en km per sobre (amb separador de milers)."""
    if abs(km) < 0.01:
        return f'{km * 1000:.1f} m'
    if abs(km) < 1:
        return f'{km * 1000:.0f} m'
    if abs(km) < 100:
        return f'{km:.1f} km'
    return f'{km:,.0f} km'.replace(',', '.')


def panell_posicio(app):
    """Alcada de la camera sobre la superficie dibuixada (el relleu que hi ha a sota), altitud sobre l'el·lipsoide
    (aproximadament, sobre el nivell del mar) i coordenades."""
    lat, lon, alt = (float(v) for v in geodesia.geodesiques(app.camera.posicio))
    terra = app.altitud_terra_km(lat, lon)
    linia('Sobre el terra', distancia(alt - terra))
    linia('Altitud', distancia(alt) + ' (sobre el mar)')
    linia('Posicio', f"{abs(lat):.4f} {'N' if lat >= 0 else 'S'}, {abs(lon):.4f} {'E' if lon >= 0 else 'O'}")


def amplada_completa():
    return (-1.0, 0.0)


def sense_accents(text):
    """La font del panell no te accents: 'Valencia' en lloc de 'València'."""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


def linia(etiqueta, text, color=None):
    """Una etiqueta curta i un text que fa salts de linia dins del panell."""
    imgui.text_disabled(etiqueta)
    imgui.same_line()
    if color:
        imgui.push_style_color(imgui.Col.TEXT, color)
    imgui.text_wrapped(sense_accents(text))
    if color:
        imgui.pop_style_color()


def panell_eclipsi(app):
    actiu = eclipsis.actiu()
    imgui.push_item_width(-1.0)
    if imgui.begin_combo('##eclipsi', titol_eclipsi(actiu)):
        for clau in eclipsis.disponibles():
            if imgui.selectable(titol_eclipsi(clau), clau == actiu)[0]:
                app.canviar_eclipsi(clau)
        imgui.end_combo()
    imgui.pop_item_width()


def titol_eclipsi(clau):
    e = eclipsis.dades(clau)
    return f"{e['titol']}  ({e['tipus']})"


def panell_temps(app):
    fase = app.model.fase(app.hora)
    imgui.text(eclipse_data.hora_local(app.hora))
    imgui.same_line()
    imgui.text_colored(COLOR_FASE.get(fase, (0.8, 0.8, 0.8, 1.0)), fase)
    imgui.progress_bar(app.tapada, amplada_completa(), f'Sol tapat {app.tapada * 100:.1f} %')
    if imgui.radio_button('Auto', app.velocitat_auto):
        app.velocitat_auto = True
    for k, v in enumerate(VELOCITATS):
        if k != 3:      # dues files: Auto x1 x10 / x60 x300 x1000
            imgui.same_line()
        if imgui.radio_button(f'x{v}', not app.velocitat_auto and app.velocitat == v):
            app.velocitat, app.velocitat_auto = v, False


def panell_vista(app):
    for i, nom in enumerate(VISTES):
        if i == 1:
            imgui.same_line()
        if imgui.radio_button(nom, app.vista == i):
            app.canviar_vista(i)
    if app.vista == 0:
        cam = app.camera_exploracio
        if imgui.radio_button('Vol lliure', not cam.caminar):
            cam.caminar = False
        imgui.same_line()
        if imgui.radio_button('Caminar', cam.caminar) and not cam.caminar:
            app.passar_a_caminar()
        if glfw.get_time() < app.avis_caminar_fins:
            imgui.text_colored(COLOR_AVIS, app.avis_caminar)
            if not cam.caminar and imgui.button("Caminar des del punt", amplada_completa()):
                app.caminar_des_del_punt()
    if app.vista == 2:
        cam = app.camera_guiada
        imgui.push_item_width(-1.0)
        canviat, progres = imgui.slider_float('##progres', cam.progres, 0.0, 1.0, cam.tram())
        imgui.pop_item_width()
        if canviat:
            cam.progres = progres
        if imgui.button('Recentrar', amplada_completa()):
            cam.recentrar()
    if imgui.button('Mirar el Sol', amplada_completa()):
        app.mirar_el_sol()
    if imgui.button("Ombra de la Lluna des de l'espai", amplada_completa()):
        app.veure_ombra_des_de_lespai()


def panell_punt(app):
    o = app.observador
    noms = [n for n, _, _ in UBICACIONS]
    actual = noms.index(o.nom) if o.nom in noms else -1
    imgui.push_item_width(-1.0)
    if imgui.begin_combo('##ubicacio', o.nom if actual >= 0 else f'{o.lat:.4f}, {o.lon:.4f}'):
        for i, (nom, lat, lon) in enumerate(UBICACIONS):
            if imgui.selectable(nom, i == actual)[0]:
                app.triar_ubicacio(lat, lon, nom)
        imgui.end_combo()
    imgui.pop_item_width()
    lat_ref = o.lat_ref if o.lat_ref is not None else o.lat
    lon_ref = o.lon_ref if o.lon_ref is not None else o.lon
    linia('Coordenades', f"{lat_ref:.5f} N, {abs(lon_ref):.5f} {'E' if lon_ref >= 0 else 'O'}")
    if app.consulta_nom is not None:
        linia('Nom', app.consulta_nom.estat, COLOR_SUAU)
    elif app.nom_punt is not None:
        r = app.nom_punt[1]
        n, m = r.get('nucli'), r.get('municipi')
        if n is None:
            linia('Nucli', 'cap a prop' if not r.get('errors') else 'no disponible (servei)')
        elif n[1] == 'dins del nucli':
            linia('Nucli', f'dins de {n[0]}')
        else:
            linia('Nucli', f'{n[0]} (el mes proper, a {n[2]:.1f} km)')
        if m is not None:
            linia('Municipi', f'{m[0]} ({m[1]})')
        else:
            linia('Municipi', 'no disponible' + (' (servei)' if any('municipi' in e for e in r.get('errors', [])) else ''))
    if imgui.button('Tornar al punt', (140, 0)):
        app.tornar_al_punt()
    imgui.same_line()
    if imgui.button('Anar al maxim', amplada_completa()):
        app.anar_al_maxim()


def llegenda(color, text):
    imgui.color_button(f'##{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (12, 12))
    imgui.same_line()
    imgui.text(text)


def panell_mapa(app):
    for i, nom in enumerate(MAPES):
        if i % 2:       # dues per fila
            imgui.same_line()
        if imgui.radio_button(nom, app.mapa_visibilitat == i):
            app.mapa_visibilitat = i
    if app.mapa_visibilitat == 1:
        for classe, text in enumerate(['Tapat', 'Menys de mig Sol', 'Mes de mig Sol', 'Sencer']):
            llegenda(COLORS_OMBRES[classe], text)
    elif app.mapa_visibilitat == 2:
        maxim = max((t.visibilitat['durada_max'] for t in app.terrenys() if t.visibilitat), default=0.0)
        for k, color in enumerate(COLORS_CENTRAL):
            llegenda(color, f'{maxim * k / 4:.0f} s')
    elif app.mapa_visibilitat == 3:
        llegenda(COLOR_TAPAT_RELLEU, 'El relleu tapa el Sol')
        for k, color in enumerate(COLORS_ENFOSQUIMENT):    # rampa de la part tapada per la Lluna, de 0 a 100 %
            imgui.color_button(f'##rampa{k}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (12, 12))
            imgui.same_line()
        imgui.text('Sol tapat 0 - 100 %')
        llegenda(COLOR_TOTALITAT, 'Fase central')


def panell_capes(app):
    _, app.mosaic.actiu = imgui.checkbox('Fotografia aeria', app.mosaic.actiu)
    _, app.mostrar_edificis = imgui.checkbox('Edificis', app.mostrar_edificis)
    imgui.same_line()
    _, app.edificis_aeris = imgui.checkbox('A la vista aeria', app.edificis_aeris)
    if app.mostrar_edificis or app.edificis_aeris:
        llegenda(COLOR_ALCADA_ESTIMADA, 'Blau: altura estimada (sense LiDAR)')
    _, app.ombres.actiu = imgui.checkbox('Ombres (relleu i edificis)', app.ombres.actiu)
    _, app.mostrar_noms = imgui.checkbox('Noms de lloc (vista aeria)', app.mostrar_noms)


def panell_capes_eclipsi(app):
    _, app.ressaltar_ombra = imgui.checkbox("Linies de l'ombra de la Lluna", app.ressaltar_ombra)
    if eclipsis.actiu() == '2026':      # les capes del CNIG nomes son del 2026
        t = app.peninsula
        imgui.push_item_width(-1.0)
        if imgui.begin_combo('##cnig', f'CNIG: {OVERLAYS[t.overlay]}'):
            for i, nom in enumerate(OVERLAYS):
                if imgui.selectable(nom, t.overlay == i)[0]:
                    for terreny in app.terrenys():
                        terreny.overlay = i
            imgui.end_combo()
        imgui.pop_item_width()
        llegenda_cnig(app)


def panell_detall(app):
    """Quin detall hi ha al punt de detall (el que es mira explorant, o el punt d'observacio), per separat."""
    e = app.detall.estat
    for etiqueta, clau in (('Terreny', 'terreny'), ('Foto', 'foto'), ('Edificis', 'edificis'), ('Mapa', 'mapa')):
        text = e.get(clau, '')
        actiu = any(p in text for p in ('preparant', 'Baixant', 'Llegint', 'calculant', 'mesurant', 'Horitzo',
                                        'Circumst', 'baixant'))
        linia(etiqueta, text or '-', COLOR_AVIS if actiu else None)


def llegenda_cnig(app):
    t = app.peninsula
    if t.overlay == 1:
        passos = [ENFOSQUIMENT_MIN + (1 - ENFOSQUIMENT_MIN) * k / 3 for k in range(4)]
        for color, valor in zip(COLORS_ENFOSQUIMENT, passos):
            llegenda(color, f'{valor * 100:.1f} %')
        llegenda(COLOR_TOTALITAT, '100 %')
    elif t.overlay == 2:
        for k, color in enumerate(COLORS_DURADA):
            llegenda(color, f'{t.durada_min + (t.durada_max - t.durada_min) * k / 4:.0f} s')
    elif t.overlay == 3:
        for classe, color in enumerate(COLORS_OMBRES):
            llegenda(color, eclipse_data.CLASSES_OMBRES[classe])


def panell_tecles(app):
    linies = ['P: reproduir / pausar', 'V: explorar / des del terra', 'G: espai / tornar',
              'Tab o clic dret: mirar amb el ratoli', 'Fletxes: mirar', 'Esc: alliberar el ratoli; tancar']
    if app.vista == 0:
        linies += ['W A S D: moure\'s   E / Q: pujar / baixar', 'Ctrl: rapid   Shift: correr (caminant)',
                   'Arrossegar: moure el terra', 'Shift + arrossegar: girar', 'Roda: apropar-se',
                   'Doble clic: anar-hi']
    elif app.vista == 2:
        linies += ['Roda o W / S: apropar / allunyar']
    else:
        linies += ['Roda: zoom']
    for linia in linies:
        imgui.bullet_text(linia)


def panell_avancat(app):
    imgui.text(f'FPS: {app.fps:.0f}' + ('  (en repos: no canvia res)' if app.en_repos else ''))
    if app.zona is not None and app.zona.orto is not None:
        _, app.usar_ortofoto = imgui.checkbox('Ortofoto de la zona', app.usar_ortofoto)
    t = app.peninsula
    if eclipsis.actiu() == '2026':      # les capes del CNIG nomes son del 2026: en un altre eclipsi enganyarien
        canviat, lim = imgui.checkbox('Limits de la totalitat (CNIG)', t.limits_totalitat)
        if canviat:
            for terreny in app.terrenys():
                terreny.limits_totalitat = lim
        canviat, op = imgui.slider_float('Opacitat CNIG', t.opacitat, 0, 1)
        if canviat:
            for terreny in app.terrenys():
                terreny.opacitat = op
    canviat, exag = imgui.slider_float('Exageracio', t.exaggeration, 1, 20)
    if canviat:
        for terreny in app.terrenys():
            terreny.exaggeration = exag
    canviat, filferros = imgui.checkbox('Filferros', t.wireframe)
    if canviat:
        for terreny in app.terrenys():
            terreny.wireframe = filferros
    if app.cnig is not None and imgui.tree_node('CNIG i model'):
        panell_cnig(app)
        imgui.tree_pop()


def panell_cnig(app):
    m, e = app.model, app.cnig
    if imgui.begin_table('fases', 3, imgui.TableFlags.ROW_BG | imgui.TableFlags.BORDERS_INNER_H):
        hl = eclipse_data.hora_local
        for nom, k in (('C1', 'c1'), ('C2', 'c2'), ('Maxim', 'maxim'), ('C3', 'c3'), ('C4', 'c4'), ('Posta', 'posta')):
            hc, hm = e['hores_tu'].get(k), m.hores.get(k)
            if hc is None and hm is None:
                continue
            imgui.table_next_row()
            imgui.table_next_column()
            imgui.text(nom)
            imgui.table_next_column()
            imgui.text(hl(hc) if hc is not None else '-')
            imgui.table_next_column()
            imgui.text(hl(hm) if hm is not None else '-')
        imgui.end_table()


def avis_ratoli(app):
    """Avis discret i temporal (uns segons despres de capturar el ratoli), a dalt al mig."""
    if not app.ratoli.capturat or glfw.get_time() - app.ratoli.capturat_des_de > 4.0:
        return
    w, _ = imgui.get_io().display_size
    imgui.set_next_window_pos((w / 2, 12), imgui.Cond.ALWAYS, (0.5, 0.0))
    imgui.set_next_window_bg_alpha(0.6)
    flags = (imgui.WindowFlags.NO_DECORATION | imgui.WindowFlags.NO_INPUTS | imgui.WindowFlags.ALWAYS_AUTO_RESIZE
             | imgui.WindowFlags.NO_SAVED_SETTINGS | imgui.WindowFlags.NO_FOCUS_ON_APPEARING
             | imgui.WindowFlags.NO_NAV)
    imgui.begin('##avis_ratoli', False, flags)
    imgui.text('Tab o Esc: tornar a tenir el cursor')
    imgui.end()


def barra_temps(app):
    """Finestra de la barra de temps, a baix al mig: l'hora es pot arrossegar (en pausa o no). Marques al punt
    triat: inici i final (groc), fase central (lila), maxim (blanc) i posta (taronja)."""
    m = app.model
    io = imgui.get_io()
    w, h = io.display_size
    imgui.set_next_window_pos((w / 2, h - 12), imgui.Cond.ALWAYS, (0.5, 1.0))
    imgui.set_next_window_size((min(w - 40, 760), 0), imgui.Cond.ALWAYS)
    imgui.set_next_window_bg_alpha(0.85)
    flags = (imgui.WindowFlags.NO_TITLE_BAR | imgui.WindowFlags.NO_RESIZE | imgui.WindowFlags.NO_MOVE
             | imgui.WindowFlags.NO_COLLAPSE | imgui.WindowFlags.NO_SAVED_SETTINGS)
    imgui.begin('Temps', False, flags)
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    inici, final = app.ef.inici, app.ef.final
    if imgui.button('Pausa (P)' if app.reproduint else 'Reproduir (P)', (110, 0)):
        app.reproduir_pausar()
    imgui.same_line()
    if imgui.button('-5 min'):
        app.hora -= 5 / 60
    imgui.same_line()
    if imgui.button('+5 min'):
        app.hora += 5 / 60
    app.hora = min(max(app.hora, inici), final)
    imgui.same_line()
    imgui.push_item_width(-1.0)
    text = f"{eclipse_data.hora_local(app.hora)}  -  {m.fase(app.hora)}"
    canviat, minuts = imgui.slider_float('##hora', (app.hora - inici) * 60, 0, (final - inici) * 60,
                                         text.replace('%', '%%'))
    imgui.pop_item_width()
    if canviat:
        app.hora = inici + minuts / 60
    if m.valid:
        marques_barra(m.hores, inici, final)
        hh, hl = m.hores, eclipse_data.hora_local
        parts = [f"inici {hl(hh['c1'])[:5]}"]
        if hh['c2'] is not None:
            parts.append(f"{'anularitat' if m.anular else 'totalitat'} {hl(hh['c2'])} - {hl(hh['c3'])}")
        parts.append(f"maxim {hl(hh['maxim'])[:5]}")
        if hh['c4'] is not None:
            parts.append(f"final {hl(hh['c4'])[:5]}")
        if hh['posta'] is not None:
            parts.append(f"posta {hl(hh['posta'])[:5]}")
        imgui.text_disabled('   |   '.join(parts))
    imgui.pop_item_flag()
    imgui.end()


def marques_barra(hores, inici, final):
    """Marques verticals sobre el control lliscant de l'hora (el darrer element dibuixat)."""
    x0, y0 = imgui.get_item_rect_min()
    x1, y1 = imgui.get_item_rect_max()
    dl = imgui.get_window_draw_list()
    for clau, color in MARQUES:
        t = hores.get(clau)
        if t is None or not inici <= t <= final:
            continue
        x = x0 + (x1 - x0) * (t - inici) / (final - inici)
        gruix = 3.0 if clau == 'maxim' else 2.0
        dl.add_line((x, y0), (x, y0 + 5), imgui.get_color_u32((*color, 1.0)), gruix)
        dl.add_line((x, y1 - 5), (x, y1), imgui.get_color_u32((*color, 1.0)), gruix)
