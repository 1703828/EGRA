"""
Interficie del programa (slimgui): el panell principal i la barra de temps.

GraphicsEngineBase (basecode/engine.py) obre la finestra "Opcions" a cada fotograma i crida
GraphicsEngine.build_ui(), que crida build_ui(app) d'aquest fitxer. imgui es una interficie
"immediata": es torna a dibuixar sencera a cada fotograma a partir de les variables del programa.

El panell nomes te el necessari: el temps (reproduir/pausar, hora, velocitat), la vista (explorar o
observar des del terra), el punt d'observacio i una ajuda curta. Les capes tecniques i les opcions
de depuracio son a l'apartat "Avancat", tancat per defecte.
Textos sense accents: la font de slimgui no els mostra be.
"""
import glfw
import numpy as np
from slimgui import imgui

from basecode.terrain import (OVERLAYS, ENFOSQUIMENT_MIN, COLORS_ENFOSQUIMENT, COLOR_TOTALITAT,
                              COLORS_DURADA, COLORS_OMBRES)
from dades import eclipse_data
from dades.observador import UBICACIONS

VISTES = ['Explorar', 'Observar des del terra', "Allunyar-se fins a l'espai (guiat)"]
VELOCITATS = [1, 10, 60, 300, 1000]   # x temps real ('Auto' a mes: lent a la totalitat)
COLOR_FASE = {'TOTALITAT': (1.0, 0.45, 0.9, 1.0), 'Eclipsi parcial': (1.0, 0.8, 0.3, 1.0)}
COLOR_SUAU = (0.65, 0.68, 0.72, 1.0)


def build_ui(app):
    """El panell "Opcions" (el crida GraphicsEngine.build_ui) i la finestra de la barra de temps.
    Els controls no son parades de Tab (NO_TAB_STOP): imgui faria servir Tab per passar d'un control al
    seguent i es quedaria el teclat; aixi Tab queda lliure per capturar el ratoli (main.py, teclat)."""
    imgui.set_window_size((330, 0), imgui.Cond.ALWAYS)   # amplada fixa, alcada segons el contingut
    imgui.push_item_flag(imgui.ItemFlags.NO_TAB_STOP, True)
    imgui.text_colored((1.0, 0.85, 0.4, 1.0), 'ECLIPSI DEL 12 D\'AGOST DE 2026')

    panell_temps(app)
    imgui.separator_text('Vista  (tecles V i G)')
    for i, nom in enumerate(VISTES):
        if i == 1:
            imgui.same_line()
        if imgui.radio_button(nom, app.vista == i):
            app.canviar_vista(i)
    if app.vista == 0:
        panell_caminar(app)
    if imgui.button("Mirar l'eclipsi (cap al Sol)", (-1.0, 0.0)):
        app.mirar_el_sol()
    if app.vista == 2:
        panell_guiat(app)
    if imgui.button("Veure l'ombra des de l'espai", (-1.0, 0.0)):
        app.veure_ombra_des_de_lespai()
    _, app.ressaltar_ombra = imgui.checkbox("Ressaltar l'ombra amb linies (didactic)", app.ressaltar_ombra)
    if app.ressaltar_ombra:
        imgui.text_colored(COLOR_SUAU, 'Groc: 25, 50 i 75 % del Sol tapat. Lila: totalitat.')
        imgui.text_colored(COLOR_SUAU, "Nomes linies: la foscor de l'ombra no canvia.")

    panell_imatges(app)
    imgui.separator_text("Punt d'observacio")
    panell_punt(app)

    if imgui.collapsing_header('Ajuda', None, imgui.TreeNodeFlags.DEFAULT_OPEN)[0]:
        panell_ajuda(app)
    if imgui.collapsing_header('Avancat')[0]:
        panell_avancat(app)
    imgui.spacing()
    imgui.text_disabled('Relleu i eclipsi: IGN / CNIG (CC BY 4.0)')
    imgui.text_disabled('Posicions del Sol i la Lluna: NASA/JPL')
    imgui.text_disabled('Textures: NASA')
    if app.mosaic.actiu or (app.zona is not None and app.zona.orto is not None):
        imgui.text_disabled('Fotografia aeria: PNOA (c) IGN (CC BY 4.0)')
    if app.mosaic.actiu:
        imgui.text_disabled('Sentinel-2 cloudless 2020 (c) EOX,')
        imgui.text_disabled('  dades Copernicus (CC BY-NC-SA 4.0)')
    imgui.pop_item_flag()

    barra_temps(app)
    avis_ratoli(app)


def panell_imatges(app):
    """Fotografia aeria (mosaic de teselles que es baixen a mesura que calen) i el seu estat."""
    _, app.mosaic.actiu = imgui.checkbox('Fotografia aeria (es baixa en segon pla)', app.mosaic.actiu)
    pendents, baixades, _, fallades = app.mosaic.estat()
    if app.mosaic.actiu and pendents:
        imgui.same_line()
        imgui.text_colored(COLOR_SUAU, f'{pendents} pendents')
    if app.mosaic.actiu and fallades and pendents == 0 and baixades == 0:
        imgui.text_colored((1.0, 0.8, 0.4, 1.0), 'Sense connexio: colors segons l\'altitud')


def panell_caminar(app):
    """Dins d'Explorar: vol lliure o caminar sobre el relleu."""
    cam = app.camera_exploracio
    imgui.text('  ')
    imgui.same_line()
    if imgui.radio_button('Vol lliure', not cam.caminar):
        cam.caminar = False
    imgui.same_line()
    if imgui.radio_button('Caminar (ulls a 1,7 m)', cam.caminar) and not cam.caminar:
        app.passar_a_caminar()
    if glfw.get_time() < app.avis_caminar_fins:
        imgui.text_colored((0.5, 0.9, 0.6, 1.0) if cam.caminar else (1.0, 0.8, 0.4, 1.0), app.avis_caminar)
        if not cam.caminar and imgui.button("Caminar des del punt d'observacio", (-1.0, 0.0)):
            app.caminar_des_del_punt()
    if cam.caminar and cam.a_la_vora:
        imgui.text_colored(COLOR_SUAU, 'Aturat: aqui acaba el relleu (mar o sense dades)')


def panell_guiat(app):
    """Vista guiada: on es del recorregut, el progres (tambe amb la roda) i recentrar."""
    cam = app.camera_guiada
    imgui.text_colored((0.5, 0.9, 0.6, 1.0), cam.tram())
    d = float(np.linalg.norm(cam.posicio - app.ulls()))
    imgui.same_line()
    imgui.text_colored(COLOR_SUAU, f'a {d:,.1f} km del punt' if d < 1e4 else f'a {d:,.0f} km del punt')
    imgui.push_item_width(-1.0)
    canviat, progres = imgui.slider_float('##progres', cam.progres, 0.0, 1.0, 'a prop  <-  roda  ->  lluny')
    imgui.pop_item_width()
    if canviat:
        cam.progres = progres
    if imgui.button('Recentrar (mirada i hora actual)', (-1.0, 0.0)):
        cam.recentrar()
    if abs(app.hora - cam.hora_ancora) * 3600 > 60:   # el temps no mou la camera: s'avisa
        imgui.text_colored((1.0, 0.8, 0.4, 1.0),
                           f'Recorregut de les {eclipse_data.hora_local(cam.hora_ancora)[:5]} (Recentrar)')
    if cam.progres > 0.6:
        imgui.text_colored(COLOR_SUAU, 'Mides reals: lluny, els astres son petits')


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
    imgui.text('Mirada amb el ratoli.  Tab o Esc: tornar a tenir el cursor')
    imgui.end()


def panell_temps(app):
    m = app.model
    fase = m.fase(app.hora)
    if imgui.button('Pausa  (P)' if app.reproduint else 'Reproduir  (P)', (-1.0, 0.0)):
        app.reproduir_pausar()
    imgui.text(f'{eclipse_data.hora_local(app.hora)}  hora d\'estiu')
    imgui.same_line()
    imgui.text_colored(COLOR_FASE.get(fase, (0.8, 0.8, 0.8, 1.0)), fase)
    imgui.progress_bar(app.tapada, (-1.0, 0.0), f'Sol tapat al punt triat: {app.tapada * 100:.1f} %')
    imgui.text('Velocitat:')
    for v in VELOCITATS:
        imgui.same_line()
        if imgui.radio_button(f'x{v}', not app.velocitat_auto and app.velocitat == v):
            app.velocitat, app.velocitat_auto = v, False
    if imgui.radio_button('Auto (lent a la totalitat)', app.velocitat_auto):
        app.velocitat_auto = True


def panell_punt(app):
    o = app.observador
    imgui.text(o.nom if o.nom else 'Punt triat al mapa')
    imgui.text_colored(COLOR_SUAU, f'{o.lat:.4f}, {o.lon:.4f}   {o.altitud_m:.0f} m')
    if o.desplacament_m > 0:   # el lloc triat es dins d'un edifici: els ulls son al carrer o a la placa
        imgui.text_colored((1.0, 0.8, 0.4, 1.0), f'Lloc dins d\'un edifici: ulls a {o.desplacament_m:.0f} m, a fora')
    noms = [n for n, _, _ in UBICACIONS]
    actual = noms.index(o.nom) if o.nom in noms else -1
    if imgui.begin_combo('##ubicacio', o.nom if actual >= 0 else 'Escull una ubicacio...'):
        for i, (nom, lat, lon) in enumerate(UBICACIONS):
            clicat, _ = imgui.selectable(nom, i == actual)
            if clicat:
                app.triar_ubicacio(lat, lon, nom)
        imgui.end_combo()
    if app.reproduint:
        imgui.text_colored(COLOR_SUAU, 'Bloquejat mentre es reprodueix (pausa amb P)')
    elif glfw.get_time() < app.marcador_fins:
        imgui.text_colored((0.5, 0.9, 0.6, 1.0), 'Punt d\'observacio canviat')
    else:
        imgui.text_colored(COLOR_SUAU, 'O doble clic al terreny (Explorar): hi vas a peu')
    panell_edificis(app)
    if imgui.button("Anar al maxim del punt seleccionat", (-1.0, 0.0)):
        app.anar_al_maxim()
    if imgui.button("Tornar al punt d'observacio", (-1.0, 0.0)):
        app.tornar_al_punt()


def panell_edificis(app):
    """Mostrar edificis (zones amb dades del Catastro) i quina part del Sol tapen des dels ulls."""
    e = app.edificis
    if e is None:
        imgui.text_disabled('Sense edificis en aquesta zona')
        return
    _, app.mostrar_edificis = imgui.checkbox(f'Edificis des del terra ({e.n_parts} parts, Catastro)',
                                             app.mostrar_edificis)
    _, app.edificis_aeris = imgui.checkbox('Edificis tambe a la vista aeria', app.edificis_aeris)
    if app.mostrar_edificis:
        lluna, edificis, visible = e.fraccions(app.ulls())
        if edificis > 0:
            estat = 'tot el Sol' if visible == 0 and lluna < 1 else f'el {edificis * 100:.0f} % del Sol'
            imgui.text_colored((1.0, 0.7, 0.4, 1.0), f'Els edificis tapen {estat}')
        else:
            imgui.text_colored(COLOR_SUAU, 'Cap edifici tapa el Sol des dels ulls')
        imgui.text_colored(COLOR_SUAU, '(altures estimades: plantes x 3 m)')


def panell_ajuda(app):
    if app.ratoli.capturat:
        imgui.text_colored((0.5, 0.9, 0.6, 1.0), 'Ratoli capturat. Tab o Esc: alliberar-lo')
    else:
        imgui.text_colored(COLOR_SUAU, 'Tab o clic dret: mirar amb el ratoli')
    linies = ['P: reproduir o pausar el temps', 'V: explorar / observar des del terra',
              'G: allunyar-se (guiat) / tornar',
              'Ratoli capturat, arrossegar o fletxes: mirar',
              'Esc: alliberar el ratoli; lliure, tanca']
    if app.vista == 0 and app.camera_exploracio.caminar:
        linies += ['W A S D: caminar (1,5 m/s)   Shift: correr',
                   'Els edificis (si es mostren) son obstacles',
                   'Doble clic (cursor lliure): triar el punt']
    elif app.vista == 0:
        linies += ['Arrossegar: moure el terra',
                   'Shift + arrossegar (o boto del mig): girar i inclinar',
                   'Roda o dos dits: apropar-se al cursor',
                   'W A S D: moure\'s   E / Q: pujar / baixar   Ctrl: rapid',
                   'Doble clic: anar-hi i mirar des del terra']
    elif app.vista == 2:
        linies += ['Roda, dos dits o W/S: apropar/allunyar',
                   'Recentrar: tornar a enquadrar']
    else:
        linies += [f'Roda o dos dits amunt/avall: zoom (ara x{app.camera.zoom():.1f})']
    for linia in linies:
        imgui.bullet_text(linia)


def panell_avancat(app):
    imgui.text(f'FPS: {app.fps:.0f}')
    if app.vista == 0:
        lat, lon, alt = app.camera.geodesiques()
        imgui.text_colored(COLOR_SUAU, f'Camera: {lat:.3f}, {lon:.3f}, {alt:,.1f} km')
    if imgui.tree_node('Dades del CNIG en aquest punt'):
        panell_cnig(app)
        imgui.tree_pop()
    if imgui.tree_node('Capes sobre el terreny'):
        panell_capes(app)
        imgui.tree_pop()
    if app.zona is not None and app.zona.orto is not None:
        _, app.usar_ortofoto = imgui.checkbox('Ortofoto descarregada de la zona', app.usar_ortofoto)
        imgui.text_colored(COLOR_SUAU, 'Sota la fotografia aeria (sense connexio)')
    _, app.ombres.actiu = imgui.checkbox('Ombres del relleu (zona de 5 m)', app.ombres.actiu)
    imgui.text_colored(COLOR_SUAU, 'On una muntanya tapa el Sol (no es la Lluna)')
    if imgui.tree_node('Depuracio'):
        t = app.peninsula
        canviat, exag = imgui.slider_float('Exageracio', t.exaggeration, 1, 20)
        if canviat:
            for terreny in app.terrenys():
                terreny.exaggeration = exag
        imgui.text_colored(COLOR_SUAU, '(eina de visualitzacio: 1 = relleu real)')
        canviat, filferros = imgui.checkbox('Filferros', t.wireframe)
        if canviat:
            for terreny in app.terrenys():
                terreny.wireframe = filferros
        imgui.tree_pop()


def panell_cnig(app):
    m, e = app.model, app.cnig
    if e is None:
        imgui.text_disabled("Sense dades del CNIG en aquest punt")
        return
    imgui.text_colored(COLOR_SUAU, "Hores d'estiu: CNIG i el nostre model")
    if imgui.begin_table('fases', 3, imgui.TableFlags.ROW_BG | imgui.TableFlags.BORDERS_INNER_H):
        hl = eclipse_data.hora_local
        for nom, k in (('Inici', 'c1'), ('Inici totalitat', 'c2'), ('Maxim', 'maxim'),
                       ('Final totalitat', 'c3'), ('Final', 'c4'), ('Posta del Sol', 'posta')):
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
    imgui.text(f"Durada totalitat: {e['durada']:.1f} s" if e['durada'] else 'Sense totalitat')
    imgui.text(f"Enfosquiment maxim: {e['enfosquiment'] * 100:.2f} %")
    imgui.text_wrapped(f"Relleu (CNIG): {e['text_ombres']}")


def panell_capes(app):
    """Capes del CNIG sobre el terreny (una de cada vegada), opacitat i llegenda dels colors."""
    t = app.peninsula
    for i, nom in enumerate(OVERLAYS):
        if imgui.radio_button(nom, t.overlay == i):
            for terreny in app.terrenys():
                terreny.overlay = i
    if t.overlay:
        canviat, op = imgui.slider_float('Opacitat', t.opacitat, 0, 1)
        if canviat:
            for terreny in app.terrenys():
                terreny.opacitat = op
    canviat, lim = imgui.checkbox('Limits de la totalitat', t.limits_totalitat)
    if canviat:
        for terreny in app.terrenys():
            terreny.limits_totalitat = lim

    def llegenda(color, text):
        imgui.color_button(f'##{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (14, 14))
        imgui.same_line()
        imgui.text(text)

    if t.overlay == 1:
        passos = [ENFOSQUIMENT_MIN + (1 - ENFOSQUIMENT_MIN) * k / 3 for k in range(4)]
        for color, valor in zip(COLORS_ENFOSQUIMENT, passos):
            llegenda(color, f'{valor * 100:.1f} %')
        llegenda(COLOR_TOTALITAT, 'totalitat (100 %)')
    elif t.overlay == 2:
        for k, color in enumerate(COLORS_DURADA):
            llegenda(color, f'{t.durada_min + (t.durada_max - t.durada_min) * k / 4:.0f} s')
    elif t.overlay == 3:
        for classe, color in enumerate(COLORS_OMBRES):
            llegenda(color, f'{classe}: {eclipse_data.CLASSES_OMBRES[classe]}')


def barra_temps(app):
    """Finestra de la barra de temps, a baix al mig: l'hora es pot arrossegar (en pausa o no)."""
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
        hh, hl = m.hores, eclipse_data.hora_local
        text = f"Al punt triat:  inici {hl(hh['c1'])[:5]}"
        if hh['c2'] is not None:
            text += f"   |   totalitat {hl(hh['c2'])} - {hl(hh['c3'])}"
        if hh['c4'] is not None:
            text += f"   |   final {hl(hh['c4'])[:5]}"
        if hh['posta'] is not None:
            text += f"   |   posta {hl(hh['posta'])[:5]}"
        imgui.text_disabled(text)
    text_lloc = app.text_lloc()    # preparacio d'un lloc nou (doble clic), si n'hi ha
    if text_lloc:
        imgui.text_colored((1.0, 0.8, 0.4, 1.0), text_lloc)
    imgui.pop_item_flag()
    imgui.end()
