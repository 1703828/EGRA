"""
Interficie del programa (slimgui): dos panells ("Eclipsi" a l'esquerra i "Camera" a la dreta) i la barra de temps.

GraphicsEngineBase (basecode/engine.py) obre la finestra "Opcions" a cada fotograma i crida
GraphicsEngine.build_ui(), que crida build_ui(app) d'aquest fitxer. imgui es una interficie
"immediata": es torna a dibuixar sencera a cada fotograma a partir de les variables del programa.

Els panells nomes tenen controls (sense textos d'explicacio, peticio de l'equip del 30/10), separats en dos (peticio
de l'equip de l'1/11):
  - "Eclipsi" (simplificat el 18/11/2026): quin eclipsi, el punt d'observacio (lloc, coordenades, nucli i municipi)
    i el selector de Mapes. L'hora i reproduir son a la barra de temps.
  - "Camera" (simplificat el 17/11/2026, una sola vista): el boto "Mirar el Sol", les descarregues en segon pla (que
    es baixa i de quin lloc) amb els FPS, i dos desplegables tancats: que es dibuixa i les tecles.
Reproduir i pausar es a la barra de temps (a baix).
Textos sense accents: la font de slimgui no els mostra be (els noms dels serveis, p. ex. Valencia, es mostren sense).
"""
import re
import unicodedata

import glfw
import glm
import numpy as np
from slimgui import imgui

from basecode import mapes as M
from basecode.detall import ALCADA_DETALL_KM
from dades import eclipse_data, eclipsis, geodesia, noms
from dades.observador import UBICACIONS

AMPLADA_PANELL = 300
LLOC_A_PROP_KM = 15.0     # descarregues: "de Cadis" fins a aquesta distancia del nom mes proper; mes enlla, "prop de"
LLOC_MAX_KM = 150.0       # mes enlla, sense nom (mar, fora d'Espanya)
# Noms de lloc sobre el mapa (noms_al_mapa): cada nivell es veu amb la camera entre aquestes altures sobre el terra
# (km): de lluny, nomes els mes importants; de prop, desapareixen (el terreny ja es reconeix i taparien la vista)
ALCADES_NOMS = {0: (25.0, 4000.0),    # capital de l'Estat i capitals de comunitat autonoma
                1: (12.0, 1500.0),    # capitals de provincia
                2: (3.0, 200.0)}      # capitals de comarca de Catalunya
MIDA_NOMS = {0: 19.0, 1: 16.0, 2: 14.0}          # mida de la lletra (punts)
SENSE_DADA = '-'          # dada no disponible (el guio llarg, la font del panell el dibuixa '?': comprovat 18/11)
COLOR_SUAU = (0.65, 0.68, 0.72, 1.0)
COLOR_AVIS = (1.0, 0.8, 0.4, 1.0)
COLOR_ALCADA_ESTIMADA = (0.30, 0.50, 0.95)   # el mateix que BLAU_ESTIMADA (shaders/edifici.frag)
# marques de la barra de temps: contacte, color
# barra de temps: colors de les marques (la fase central en vermell, com a l'esquema de l'equip) i alcada de la barra
COLOR_CENTRAL = (0.95, 0.30, 0.30)
COLOR_ECLIPSI_BARRA = (0.92, 0.92, 0.95)


def build_ui(app):
    """Els dos panells i la finestra de la barra de temps. El panell "Eclipsi" es la finestra que obre el bucle de
    main.py (a l'esquerra); el panell "Camera" n'obre una altra a la dreta.
    Els controls no son parades de Tab (NO_TAB_STOP): imgui faria servir Tab per passar d'un control al
    seguent i es quedaria el teclat; aixi Tab queda lliure per capturar el ratoli (main.py, teclat)."""
    imgui.set_window_size((AMPLADA_PANELL, 0), imgui.Cond.ALWAYS)   # amplada fixa, alcada segons el contingut
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    panell_eclipsi(app)
    imgui.separator_text("Punt d'observacio")
    panell_punt(app)
    imgui.separator_text('Mapes')
    panell_mapa(app)
    imgui.pop_item_flag()

    noms_al_mapa(app)
    panell_camera(app)
    barra_temps(app)
    avis_ratoli(app)


def panell_camera(app):
    """Finestra "Camera", a dalt a la dreta: Mirar el Sol, descarregues en segon pla i FPS, que es dibuixa i les
    tecles (desplegables tancats en arrencar)."""
    w, _ = imgui.get_io().display_size
    imgui.set_next_window_pos((w - 10, 10), imgui.Cond.FIRST_USE_EVER, (1.0, 0.0))
    imgui.set_next_window_size((AMPLADA_PANELL, 0), imgui.Cond.ALWAYS)
    imgui.begin('Camera', False, imgui.WindowFlags.NO_SAVED_SETTINGS)   # sempre a la dreta i desplegat en arrencar
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    imgui.separator_text('Descarregues en segon pla')
    panell_descarregues(app)
    if imgui.button('Mirar el Sol', amplada_completa()):
        app.mirar_el_sol()
    if glfw.get_time() < app.avis_fins:
        imgui.text_colored(COLOR_AVIS, sense_accents(app.avis))
    if imgui.collapsing_header('Que es dibuixa')[0]:
        panell_capes(app)
    if imgui.collapsing_header('Tecles')[0]:
        panell_tecles(app)
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
    camera sobre el terra (ALCADES_NOMS), com a Google Maps: a prop del terra (per sota de 3 km) no se n'escriu cap.
    No s'escriuen els que queden darrere de l'horitzo de la Terra ni els que en taparien un de mes
    important (o, a igual nivell, un de mes proper)."""
    if not app.mostrar_noms:
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
    return f"{e['titol']} ({e['tipus']})"


def panell_punt(app):
    """El punt d'observacio actual (tambe si s'ha triat amb doble clic): el lloc de la llista i, a sota, coordenades,
    nucli i municipi (dades/noms.py, consultats en un fil quan el punt canvia). El que no se sap, SENSE_DADA."""
    o = app.observador
    noms = [n for n, _, _ in UBICACIONS]
    actual = noms.index(o.nom) if o.nom in noms else -1
    imgui.push_item_width(-1.0)
    if imgui.begin_combo('##ubicacio', o.nom if actual >= 0 else 'Punt triat al terreny'):
        for i, (nom, lat, lon) in enumerate(UBICACIONS):
            if imgui.selectable(nom, i == actual)[0]:
                app.triar_ubicacio(lat, lon, nom)
        imgui.end_combo()
    imgui.pop_item_width()
    columna = imgui.calc_text_size('Coordenades: ')[0]
    for etiqueta, valor in zip(('Coordenades:', 'Nucli:', 'Municipi:'), dades_punt(app)):
        x0 = imgui.get_cursor_pos_x()
        imgui.text_disabled(etiqueta)
        imgui.same_line(x0 + columna)
        imgui.text_wrapped(sense_accents(valor))


def dades_punt(app):
    """(coordenades, nucli, municipi) del punt d'observacio actual; SENSE_DADA el que no se sap (o es consulta)."""
    o = app.observador
    lat_ref = o.lat_ref if o.lat_ref is not None else o.lat
    lon_ref = o.lon_ref if o.lon_ref is not None else o.lon
    coordenades = SENSE_DADA if lat_ref is None or lon_ref is None else \
        f"{abs(lat_ref):.5f} {'N' if lat_ref >= 0 else 'S'}, {abs(lon_ref):.5f} {'E' if lon_ref >= 0 else 'O'}"
    nucli = municipi = SENSE_DADA
    if app.consulta_nom is None and app.nom_punt is not None:     # mentre es consulta, encara no se sap
        r = app.nom_punt[1]
        n, m = r.get('nucli'), r.get('municipi')
        if n is not None:
            nucli = n[0] if n[1] == 'dins del nucli' else f'{n[0]} (a {n[2]:.1f} km)'
        if m is not None:
            municipi = f'{m[0]} ({m[1]})'
    return coordenades, nucli, municipi


def llegenda(color, text):
    imgui.color_button(f'##{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (12, 12))
    imgui.same_line()
    imgui.text(text)


def llegenda_columnes(entrades, columnes=2):
    """Llegenda compacta: (color, text) en columnes; un color None deixa el lloc buit."""
    x0 = imgui.get_cursor_pos_x()
    amplada = (imgui.get_content_region_avail()[0]) / columnes
    for k, (color, text) in enumerate(entrades):
        if k % columnes:
            imgui.same_line(x0 + amplada * (k % columnes))
        if color is None:
            imgui.text('')
            continue
        imgui.color_button(f'##ll{k}{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (11, 11))
        imgui.same_line()
        imgui.text(text)


def panell_mapa(app):
    """Quin mapa (basecode/mapes.py), el seu mode, la llegenda (llindars fixos: no canvien amb el zoom) i d'on surten
    les dades que es veuen. (Els limits de la totalitat del CNIG ja no hi son, 19/11/2026: el mapa "Ombra de la
    Lluna" ja mostra la franja de la fase central.)"""
    m = app.mapes
    noms = [n for _, n in M.MAPES]
    claus = [c for c, _ in M.MAPES]
    actual = claus.index(m.quin) if m.quin else 0
    imgui.push_item_width(-1.0)
    canviat, nou = imgui.combo('##mapa', actual, noms)
    imgui.pop_item_width()
    if canviat:
        m.mostrar(claus[nou])
    if not m.quin:
        return
    modes = M.MODES[m.quin]
    if len(modes) > 1:
        for k, (codi, nom) in enumerate(modes):
            if k:
                imgui.same_line()
            if imgui.radio_button(nom, m.mode[m.quin] == codi):
                m.posar_mode(codi)
    mode = m.mode[m.quin]
    if m.quin == 'ocultacio':
        imgui.text_disabled('Part del Sol tapada per la Lluna' + (' ara' if mode == 'ara' else ' al maxim'))
        anular = eclipsis.ECLIPSIS[eclipsis.actiu()]['tipus'] == 'anular'
        llegenda_columnes([(c, t) for c, t in zip(M.OCULT_COLORS, M.OCULT_TEXTOS)] +
                          [(M.COLOR_ANULARITAT if anular else M.COLOR_TOTALITAT, 'Anularitat' if anular else 'Totalitat')])
    elif m.quin == 'durada':
        if mode == 'tot':
            imgui.text_disabled('Temps amb el Sol visible, sobre C1-C4')
            llegenda_columnes(list(zip(M.DURADA_COLORS, M.DURADA_TEXTOS)))
        else:
            imgui.text_disabled('Fase central amb el Sol visible')
            llegenda_columnes(list(zip(M.CENTRAL_COLORS, M.CENTRAL_TEXTOS)) +
                              [(M.COLOR_FORA_CENTRAL, 'Fora de la franja')])
        imgui.text_disabled('Durant tot l\'eclipsi (no canvia amb l\'hora)')
    elif m.quin == 'relleu':
        if mode == 'ara':
            imgui.text_disabled('El Sol ara, vist des de cada punt')
            llegenda_columnes([(M.RELLEU_COLORS[3], 'Sencer'), (M.RELLEU_COLORS[1], 'En part'),
                               (M.RELLEU_COLORS[0], 'Tapat (relleu o obst.)'), (M.COLOR_POSTA, 'Sota l\'horitzo')])
        else:
            imgui.text_disabled('El Sol al maxim (classes del CNIG)')
            llegenda_columnes(list(zip(M.RELLEU_COLORS[::-1], M.RELLEU_TEXTOS_MAXIM[::-1])))
    elif m.quin == 'ombra':
        imgui.text_disabled('Fase central ara i el seu recorregut')
        anular = eclipsis.ECLIPSIS[eclipsis.actiu()]['tipus'] == 'anular'
        llegenda_columnes([(M.COLOR_ANULARITAT if anular else M.COLOR_TOTALITAT,
                            'Anularitat ara' if anular else 'Totalitat ara'),
                           ((1.0, 0.92, 0.70), 'Penombra (20 %)'), (M.COLOR_LIMITS_CENTRAL, 'Franja (30 s)')])
    if m.amb_nivells():
        linia('Dades aqui', m.text_nivell_centre(), COLOR_SUAU)
        _, m.terrats = imgui.checkbox('Terrats (si son accessibles)', m.terrats)
        consulta_mapa(app)
    estat = m.text_estat()
    if estat:
        imgui.text_wrapped(estat)
    if m.amb_nivells() or m.quin == 'ocultacio':
        imgui.text_disabled('Sense color: sense dades. Sense meteorologia.')


def consulta_mapa(app):
    """El mapa al punt d'observacio (tasca 43.5): que s'hi veu, d'on surt i amb quins obstacles; es pot desar."""
    o = app.observador
    r = app.mapes.consulta(o.lat, o.lon, app.model)
    if not imgui.tree_node('Mapa al punt d\'observacio'):
        return
    if r is None:
        imgui.text_disabled('Encara no hi ha dades en aquest punt')
        imgui.tree_pop()
        return
    hl = eclipsis.hora_local
    linia('Temps visible', f"{r['minuts']:.0f} de {r['durada_min']:.0f} min ({100 * r['frac']:.0f} %)")
    if r['segons_central'] is not None:
        linia('Fase central', f"{r['segons_central']:.0f} de {r['durada_central_s']:.0f} s")
    if r['intervals']:
        t = ', '.join(f'{hl(a)[:5]}-{hl(b)[:5]}' for a, b in r['intervals'])
        mes = r['n_intervals'] - len(r['intervals'])
        linia('Intervals', t + (f' (+{mes})' if mes > 0 else ''))
    linia('Ulls', r['tipus'].split(' (')[0])
    imgui.text_wrapped(f"Dades: {r['dades']}. Obstacles: {r['obstacles']}.")
    if r['posta'] is not None:
        imgui.text_disabled(f"Posta {hl(r['posta'])[:5]}: despres no compta.")
    if imgui.button('Desar la consulta (CSV)', amplada_completa()):
        app.avis, app.avis_fins = f'Desada a {app.mapes.exportar(r)}', glfw.get_time() + 4.0
    imgui.tree_pop()


def panell_capes(app):
    _, app.mosaic.actiu = imgui.checkbox('Fotografia aeria', app.mosaic.actiu)
    _, app.mostrar_edificis = imgui.checkbox('Edificis', app.mostrar_edificis)
    imgui.same_line()
    _, app.edificis_aeris = imgui.checkbox('A la vista aeria', app.edificis_aeris)
    if app.mostrar_edificis or app.edificis_aeris:
        llegenda(COLOR_ALCADA_ESTIMADA, 'Blau: altura estimada (sense LiDAR)')
    _, app.vegetacio.actiu = imgui.checkbox('Vegetacio i objectes (LiDAR)', app.vegetacio.actiu)
    _, app.ombres.actiu = imgui.checkbox('Ombres (relleu i edificis)', app.ombres.actiu)
    _, app.mostrar_noms = imgui.checkbox('Noms de lloc (des de l\'aire)', app.mostrar_noms)
    imgui.text_disabled('Dades: IGN/CNIG, Catastro, NASA/JPL, PNOA, EOX')   # atribucio de les fonts (CLAUDE.md)


def nom_proper(lat, lon):
    """"de Cadis" / "prop de Cadis": el nom de lloc del mapa (dades/noms.noms_mapa: capitals de comunitat, de provincia
    i de comarca de Catalunya) mes proper al punt. Es una aproximacio sense xarxa: el lloc on es treballa es dins de la
    cel·la de 3 x 3 km del punt, no necessariament dins d'aquell municipi."""
    if not hasattr(nom_proper, 'llista'):
        nom_proper.llista = [(sense_accents(n), la, lo) for n, _, la, lo in noms.noms_mapa()]
    if not nom_proper.llista:
        return f'{lat:.2f}, {lon:.2f}'
    d, nom = min((noms.distancia_km(lat, lon, la, lo), n) for n, la, lo in nom_proper.llista)
    if d > LLOC_MAX_KM:
        return f'{lat:.2f}, {lon:.2f}'
    de = f"d'{nom}" if nom[0].upper() in 'AEIOU' else f'de {nom}'
    return de if d < LLOC_A_PROP_KM else f'prop {de}'


def descarregues(app):
    """Que es fa en segon pla ara mateix: [(text, fraccio)], una entrada per feina, a partir de les feines reals:
    basecode/detall.py (relleu de 5 m, edificis, altures LiDAR), basecode/mosaic.py (teselles de foto que s'estan
    baixant de la xarxa), basecode/mapes.py, basecode/vegetacio.py i la consulta del nom del lloc. "Descarregant" vol
    dir que la feina baixa dades d'un servei (IGN, Catastro, PNOA...); "Preparant" o "Calculant", que treballa amb
    dades del disc. fraccio (0..1) es el progres real quan se sap: teselles del lot de fotografies, o el "2/5" o
    "3 de 8" que la feina escriu al seu estat (fraccio_feina); si la feina no en dona, None (barra indeterminada)."""
    punt = app.detall.punt
    on = lambda f: nom_proper(*(getattr(f, 'lloc', None) or punt)) if (getattr(f, 'lloc', None) or punt) else ''
    linies = []
    d = app.detall.feines
    textos = {'relleu': 'Descarregant el relleu (5 m) {}', 'cadastre': 'Descarregant edificis {}',
              'lidar': 'Descarregant les altures (LiDAR) {}', 'edificis': 'Preparant edificis {}',
              'alcades': 'Descarregant les altures dels edificis (LiDAR) {}', 'zona': 'Carregant el relleu {}',
              'malla': 'Preparant edificis {}', 'carregar_edificis': 'Carregant edificis {}',
              'cobertes': 'Preparant les cobertes dels edificis {}'}
    for tipus, text in textos.items():
        if tipus in d:
            linies.append((text.format(on(d[tipus])) + '...', fraccio_feina(d[tipus])))
    mosaic = app.mosaic
    if mosaic.actiu and mosaic.descarregador.baixant:
        lloc = punt or app.camera.geodesiques()[:2]
        linies.append((f'Descarregant fotografies {nom_proper(*lloc)}...', mosaic.descarregador.progres()))
    m = app.mapes
    textos = {'relleu': 'Descarregant el relleu del mapa {}', 'bloc': 'Descarregant el relleu (25 m) del mapa {}',
              'superficie': 'Preparant els obstacles del mapa {}', 'calcular': 'Calculant el mapa de visibilitat {}',
              'llegir': 'Llegint el mapa de visibilitat'}
    vistos = set()
    for (tipus, _), f in m.feines.items():
        if tipus in textos and tipus not in vistos:
            vistos.add(tipus)
            linies.append((textos[tipus].format(on(f)).strip() + '...', fraccio_feina(f)))
    if m.feina_graella is not None:
        linies.append(("Calculant les circumstancies de l'eclipsi...", fraccio_feina(m.feina_graella)))
    if app.vegetacio.feines:
        linies.append((f'Preparant la vegetacio {on(next(iter(app.vegetacio.feines.values())))}...', None))
    if app.consulta_nom is not None:
        linies.append(('Consultant el nom del punt d\'observacio (IGN)...', None))
    return linies


def fraccio_feina(f):
    """Progres d'una feina a partir del seu estat: "(2/5, Catastro)" o "tros 3 de 8" -> la part ja acabada (1/5,
    2/8: la que s'esta fent encara no compta). None si l'estat no porta cap comptador."""
    r = re.search(r'(\d+)\s*(?:/|de)\s*(\d+)', getattr(f, 'estat', '') or '')
    if r is None or int(r.group(2)) == 0:
        return None
    return min(max((int(r.group(1)) - 1) / int(r.group(2)), 0.0), 1.0)


def motiu_sense_edificis(app):
    """Per que no es veuen edificis al punt de detall (el que mira la camera), o '' si n'hi ha o s'estan preparant.
    Surt de l'estat de basecode/detall.py: descarrega fallada (no es torna a provar sola en aquesta sessio), zona sense
    Catastro estatal, camera massa amunt (el detall es prepara a menys de 15 km), mar, o l'opcio desactivada."""
    e = app.detall.estat
    text = e.get('edificis', '')
    terreny = e.get('terreny', '')
    if app.camera.alcada_sobre_terra() > ALCADA_DETALL_KM:     # basecode/detall.py: per sobre no es prepara res
        return f'la camera es massa amunt (es carreguen a menys de {ALCADA_DETALL_KM:.0f} km del terra)'
    if any(text.startswith(p) for p in ('estimades', 'mesurades', 'preparant', 'llegint')) and \
            app.edificis is not None and app.edificis.visible:
        return ''
    if any(t in app.detall.feines for t in ('relleu', 'cadastre', 'edificis', 'zona', 'malla', 'carregar_edificis')):
        return ''
    if terreny.startswith('200 m'):    # sense relleu de 5 m: mar, fora d'Espanya o error del relleu
        return terreny
    return text


def panell_descarregues(app):
    """Les feines en segon pla (descarregues()), cadascuna amb la seva barra de progres, i els FPS. Sense progres
    conegut, la barra es indeterminada (fraccio negativa: imgui la mou d'un costat a l'altre, sense percentatge).
    Una feina fallada no es torna a provar en aquesta sessio."""
    linies = descarregues(app)
    for text, fraccio in linies:
        imgui.text_wrapped(sense_accents(text))
        imgui.progress_bar(-glfw.get_time() if fraccio is None else fraccio, (-1.0, 6.0), '')
    if not linies:
        imgui.text_disabled('Cap descarrega en curs')
    motiu = motiu_sense_edificis(app)
    if motiu:
        imgui.text_colored(COLOR_AVIS, sense_accents(f'Sense edificis aqui: {motiu}'))
        if app.detall.fallades and imgui.button('Tornar a provar', amplada_completa()):
            app.detall.fallades.clear()
    imgui.text(f'FPS: {app.fps:.0f}' + ('  (en repos: no canvia res)' if app.en_repos else ''))


def panell_tecles(app):
    """Els controls de la camera (una sola vista: main.py, teclat i render; basecode/camera_exploracio.py)."""
    linies = ['W A S D: moure la camera', 'E / Q: pujar / baixar', 'Ctrl + W A S D E Q: mes rapid',
              'Fletxes: girar la mirada', 'Arrossegar: moure el terra',
              'Majuscules + arrossegar: girar al voltant del centre de la pantalla',
              'Roda: apropar-se o allunyar-se del punt del cursor',
              'Doble clic al terreny: anar-hi, als ulls i mirant el Sol',
              'P: reproduir / pausar', 'G: ombra de la Lluna des de l\'espai / tornar',
              'Tab o clic dret: mirar amb el ratoli', 'Esc: alliberar el ratoli; tancar']
    for text in linies:
        imgui.bullet()
        imgui.text_wrapped(text)


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
    """Finestra de la barra de temps, a baix al mig, amb les mides i l'estil d'abans (format de l'equip, 19/11/2026):
    el boto de reproduir / pausar (icona dibuixada: la font del panell no te els simbols), la barra de l'hora (es pot
    arrossegar, en pausa o no; la part ja passada, omplerta), l'hora local en una caixa a la dreta i, a sota de la
    barra, les marques de l'eclipsi al punt d'observacio amb el seu nom. A sota de tot, la llegenda dels colors."""
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
    alt = imgui.get_frame_height()
    if imgui.button('##play', (alt * 1.8, 0)):
        app.reproduir_pausar()
    icona_play(imgui.get_item_rect_min(), imgui.get_item_rect_max(), app.reproduint)
    imgui.same_line()
    hora = eclipse_data.hora_local(app.hora)
    amplada_hora = imgui.calc_text_size('00:00:00')[0] + 2 * imgui.get_style().frame_padding[0]
    imgui.push_item_width(imgui.get_content_region_avail()[0] - amplada_hora - imgui.get_style().item_spacing[0])
    canviat, minuts = imgui.slider_float('##hora', (app.hora - inici) * 60, 0, (final - inici) * 60, '')
    imgui.pop_item_width()
    if canviat:
        app.hora = min(max(inici + minuts / 60, inici), final)
    barra = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    omplir_barra(barra, (app.hora - inici) / (final - inici))
    imgui.same_line()
    caixa_hora(hora, amplada_hora)
    marques = marques_eclipsi(m) if m.valid else []
    noms_marques(barra, marques, inici, final)
    if marques:
        llegenda_barra(COLOR_ECLIPSI_BARRA, 'Eclipsi')
        if any(t == 'central' for _, t, _ in marques):
            imgui.same_line(0, 24)
            llegenda_barra(COLOR_CENTRAL, 'Anularitat' if m.anular else 'Totalitat')
    imgui.pop_item_flag()
    imgui.end()


def icona_play(p0, p1, reproduint):
    """Triangle (reproduir) o dues barres (pausa) al centre del boto."""
    dl = imgui.get_window_draw_list()
    color = imgui.get_color_u32(imgui.Col.TEXT)
    cx, cy = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    r = (p1[1] - p0[1]) * 0.27
    if reproduint:
        for dx in (-r * 0.75, r * 0.25):
            dl.add_rect_filled((cx + dx, cy - r), (cx + dx + r * 0.5, cy + r), color)
    else:
        dl.add_triangle_filled((cx - r * 0.7, cy - r), (cx - r * 0.7, cy + r), (cx + r, cy), color)


def caixa_hora(text, amplada):
    """L'hora en una caixa amb el color dels botons (no fa res si es clica)."""
    color = imgui.get_style_color_vec4(imgui.Col.BUTTON)
    for c in (imgui.Col.BUTTON_HOVERED, imgui.Col.BUTTON_ACTIVE):
        imgui.push_style_color(c, color)
    imgui.button(f'{text}##hora_caixa', (amplada, 0))
    imgui.pop_style_color(2)


def omplir_barra(barra, fraccio):
    """La part de la barra ja passada, amb el color del cursor de la barra (mes suau)."""
    (x0, y0), (x1, y1) = barra
    color = imgui.get_style_color_vec4(imgui.Col.SLIDER_GRAB)
    imgui.get_window_draw_list().add_rect_filled(
        (x0, y0), (x0 + (x1 - x0) * min(max(fraccio, 0.0), 1.0), y1), imgui.get_color_u32((*color[:3], 0.35)),
        imgui.get_style().frame_rounding)


def marques_eclipsi(m):
    """[(hora TU, tipus, nom en dues linies)] al punt d'observacio: inici i fi de l'eclipsi (si el Sol es pon abans de
    C4, la fi es la posta: despres no es veu) i, si n'hi ha, inici i fi de la fase central."""
    h = m.hores
    central = 'anularitat' if m.anular else 'totalitat'
    marques = []
    if h.get('c1') is not None:
        marques.append((h['c1'], 'eclipsi', ('Inici', 'eclipsi')))
    if h.get('c2') is not None and h.get('c3') is not None:
        marques += [(h['c2'], 'central', ('Inici', central)), (h['c3'], 'central', ('Fi', central))]
    posta, c4 = h.get('posta'), h.get('c4')
    if posta is not None and (c4 is None or posta < c4):
        marques.append((posta, 'eclipsi', ('Fi', '(posta)')))
    elif c4 is not None:
        marques.append((c4, 'eclipsi', ('Fi', 'eclipsi')))
    return marques


def noms_marques(barra, marques, inici, final):
    """Les marques com a linies verticals sobre la barra i el seu nom a sota, centrat. Si dos noms es trepitjarien
    (la totalitat dura un o dos minuts: a l'escala de la barra, l'inici i la fi gairebe es toquen), l'inici i la fi
    de la fase central es fusionen en un sol nom; els altres es desplacen el just per no tocar-se."""
    (x0, y0), (x1, y1) = barra
    dl = imgui.get_window_draw_list()
    linia_h = imgui.get_text_line_height()
    etiquetes = []
    for t, tipus, nom in marques:
        if not inici <= t <= final:
            continue
        x = x0 + (x1 - x0) * (t - inici) / (final - inici)
        color = COLOR_CENTRAL if tipus == 'central' else COLOR_ECLIPSI_BARRA
        dl.add_line((x, y0 + 1), (x, y1 - 1), imgui.get_color_u32((*color, 1.0)), 2.0)
        etiquetes.append([x, tipus, nom, color])
    amplada = lambda nom: max(imgui.calc_text_size(n)[0] for n in nom)
    k = 0
    while k + 1 < len(etiquetes):      # inici i fi de la fase central massa a prop: un sol nom
        a, b = etiquetes[k], etiquetes[k + 1]
        if a[1] == b[1] == 'central' and b[0] - a[0] < (amplada(a[2]) + amplada(b[2])) / 2 + 6:
            etiquetes[k:k + 2] = [[(a[0] + b[0]) / 2, 'central', (a[2][1].capitalize(), ''), a[3]]]
        k += 1
    dreta = x0 - 1e9
    for x, _, nom, color in etiquetes:
        mig = max(x, dreta + amplada(nom) / 2 + 6)
        mig = min(mig, x1 - amplada(nom) / 2)
        for i, n in enumerate(nom):
            tw = imgui.calc_text_size(n)[0]
            dl.add_text((mig - tw / 2, y1 + 3 + i * linia_h), imgui.get_color_u32((*color, 0.9)), n)
        dreta = mig + amplada(nom) / 2
    imgui.dummy((0, 2 * linia_h + 4 if etiquetes else 0))


def llegenda_barra(color, text):
    """Un quadradet del color de la marca i el text."""
    x, y = imgui.get_cursor_screen_pos()
    mida = imgui.get_font_size() * 0.75
    y0 = y + (imgui.get_text_line_height() - mida) / 2
    imgui.get_window_draw_list().add_rect_filled((x, y0), (x + mida, y0 + mida), imgui.get_color_u32((*color, 1.0)), 2.0)
    imgui.dummy((mida + 6, imgui.get_text_line_height()))
    imgui.same_line(0, 0)
    imgui.text(text)
