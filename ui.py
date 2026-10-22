"""
Interficie del programa (slimgui): el panell "Opcions" i la barra de temps.

GraphicsEngineBase (basecode/engine.py) obre la finestra "Opcions" a cada fotograma i crida
GraphicsEngine.build_ui(), que crida build_ui(app) d'aquest fitxer. Cada funcio rep l'app (el
GraphicsEngine de main.py) i en llegeix o en canvia l'estat: imgui es una interficie "immediata",
que es torna a dibuixar sencera a cada fotograma a partir de les variables del programa.
Textos sense accents: la font de slimgui no els mostra be.
"""
from slimgui import imgui

from basecode.terrain import (OVERLAYS, ENFOSQUIMENT_MIN, COLORS_ENFOSQUIMENT, COLOR_TOTALITAT,
                              COLORS_DURADA, COLORS_OMBRES)
from dades import eclipse_data

VISTES = ['Tercera persona', 'Primera persona']
VELOCITATS = [1, 10, 60, 300]      # x temps real ('Auto' a mes: lent a la totalitat)
COLOR_FASE = {'TOTALITAT': (1.0, 0.45, 0.9, 1.0), 'Eclipsi parcial': (1.0, 0.8, 0.3, 1.0)}


def build_ui(app):
    """El panell "Opcions" (el crida GraphicsEngine.build_ui) i la finestra de la barra de temps."""
    imgui.set_window_size((340, 0), imgui.Cond.ALWAYS)   # amplada fixa, alcada segons el contingut
    imgui.text_colored((1.0, 0.85, 0.4, 1.0), 'ECLIPSI TOTAL - 12/08/2026')
    imgui.text_disabled(app.nom_regio)

    imgui.separator_text('Vista  (tecla V)')
    for i, nom in enumerate(VISTES):
        if i > 0:
            imgui.same_line()
        if imgui.radio_button(nom, app.vista == i):
            app.canviar_vista(i)
    if imgui.collapsing_header('Controls', None, imgui.TreeNodeFlags.DEFAULT_OPEN)[0]:
        panell_controls(app)

    imgui.separator_text('Ara mateix')
    panell_ara(app)

    if imgui.collapsing_header('Aquest punt (dades del CNIG)')[0]:
        panell_punt(app)
    if imgui.collapsing_header('Capes sobre el terreny')[0]:
        panell_overlays(app)
    if imgui.collapsing_header('Avancat')[0]:
        panell_avancat(app)
    imgui.spacing()
    imgui.text_disabled('MDT i eclipsi (c) IGN / CNIG (CC BY 4.0)')

    barra_temps(app)


def panell_controls(app):
    linies = ['W A S D: caminar', 'Espai: saltar   Ctrl: correr']
    if app.vista == 0:
        linies += ['Arrossegar o fletxes: girar', 'Roda: zoom   Doble clic: anar-hi']
    else:
        linies += ['Arrossegar o fletxes: mirar', f'Roda: zoom (ara x{app.camera.zoom():.1f})']
    linies += ["P: l'eclipsi des d'aqui"]
    for linia in linies:
        imgui.bullet_text(linia)


def panell_ara(app):
    m = app.model
    fase = m.fase(app.hora)
    imgui.text(f'{eclipse_data.hora_local(app.hora)} CEST')
    imgui.same_line()
    imgui.text_colored(COLOR_FASE.get(fase, (0.8, 0.8, 0.8, 1.0)), fase)
    imgui.progress_bar(app.tapada, (-1.0, 0.0), f'Sol tapat: {app.tapada * 100:.1f} %')
    el = app.light.elevacio
    estat = "sota l'horitzo" if el < 0 else f'a {el:.1f} graus'
    imgui.text(f'Sol: azimut {app.light.azimut:.0f}, {estat}')
    if app.vista == 1 and app.camera.seguir_sol:
        imgui.text_disabled('Seguint el Sol (gira per deixar-ho)')
    if imgui.button("Veure l'eclipsi des d'aqui (P)", (-1.0, 0.0)):
        app.eclipsi_des_d_aqui()


def panell_punt(app):
    i = app.info_aqui()
    imgui.text(f"{i['lat']:.4f}, {i['lon']:.4f}   {i['altitud']:.0f} m")
    e = app.cnig
    if e is None:
        imgui.text_disabled("Sense dades de l'eclipsi en aquest punt")
        return
    if imgui.begin_table('fases', 2, imgui.TableFlags.ROW_BG | imgui.TableFlags.BORDERS_INNER_H):
        files = [(nom, hora if visible else f'{hora} (Sol post)') for nom, hora, visible in e['fases']]
        files += [('Posta del Sol', e['posta']),
                  ('Durada totalitat', f"{e['durada']:.1f} s" if e['durada'] else 'no n\'hi ha'),
                  ('Enfosquiment max.', f"{e['enfosquiment'] * 100:.2f} %")]
        for nom, valor in files:
            imgui.table_next_row()
            imgui.table_next_column()
            imgui.text(nom)
            imgui.table_next_column()
            imgui.text(valor)
        imgui.end_table()
    imgui.text_wrapped(f"Relleu (CNIG): {e['text_ombres']}")
    imgui.text_disabled('Hores en CEST (TU + 2)')


def panell_overlays(app):
    """Overlays de l'eclipsi (un de cada vegada), opacitat i llegenda dels colors."""
    t = app.terrain
    for i, nom in enumerate(OVERLAYS):
        if imgui.radio_button(nom, t.overlay == i):
            t.overlay = i
    if t.overlay:
        _, t.opacitat = imgui.slider_float('Opacitat', t.opacitat, 0, 1)
    _, t.limits_totalitat = imgui.checkbox('Limits de la totalitat', t.limits_totalitat)

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
        imgui.text_disabled('  linies cada 10 s; nomes dins la franja')
    elif t.overlay == 3:
        for classe, color in enumerate(COLORS_OMBRES):
            llegenda(color, f'{classe}: {eclipse_data.CLASSES_OMBRES[classe]}')
        imgui.text_disabled('  sense color: sense dades')


def panell_avancat(app):
    t, cam = app.terrain, app.camera
    imgui.text(f'FPS: {app.fps:.0f} ({1000 / max(app.fps, 1e-6):.1f} ms)   '
               f'triangles: {t.n_triangles / 1e6:.2f} M')
    _, t.exaggeration = imgui.slider_float('Exageracio Y', t.exaggeration, 1, 20)
    _, t.boira = imgui.slider_float('Boira', t.boira, 0, 1)
    mida = max(t.mida)
    _, app.distancia_lluna = imgui.slider_float('Distancia Lluna (km)', app.distancia_lluna,
                                                 0.5 * mida, 364200, '%.0f', imgui.SliderFlags.LOGARITHMIC)
    imgui.text_disabled('  real ~364200 km (la mida aparent\n  sempre es la real)')
    _, t.wireframe = imgui.checkbox('Filferros', t.wireframe)
    imgui.same_line()
    _, t.curvatura = imgui.checkbox('Curvatura', t.curvatura)
    imgui.same_line()
    _, app.axis.visible = imgui.checkbox('Eixos', app.axis.visible)
    if app.vista == 0:
        _, cam.distance = imgui.slider_float('Zoom (km)', cam.distance, cam.dist_min, cam.dist_max,
                                             '%.2f', imgui.SliderFlags.LOGARITHMIC)
        if imgui.button('Mirar des de darrere la Lluna', (-1.0, 0.0)):
            # la camera a la banda del Sol, mes lluny que la Lluna i una mica mes amunt
            cam.yaw = (180.0 - app.light.azimut + 180.0) % 360.0 - 180.0
            cam.pitch = app.light.elevacio + 3.0
            cam.distance = min(1.3 * app.distancia_lluna, cam.dist_max)
    imgui.text(f'near {cam.near * 1000:.1f} m  far {cam.far:.0f} km')


def barra_temps(app):
    """Finestra de la barra de temps, a baix al mig (com un reproductor de video)."""
    m = app.model
    io = imgui.get_io()
    w, h = io.display_size
    imgui.set_next_window_pos((w / 2, h - 12), imgui.Cond.ALWAYS, (0.5, 1.0))
    imgui.set_next_window_size((min(w - 40, 760), 0), imgui.Cond.ALWAYS)
    imgui.set_next_window_bg_alpha(0.85)
    flags = (imgui.WindowFlags.NO_TITLE_BAR | imgui.WindowFlags.NO_RESIZE | imgui.WindowFlags.NO_MOVE
             | imgui.WindowFlags.NO_COLLAPSE | imgui.WindowFlags.NO_SAVED_SETTINGS)
    imgui.begin('Temps', False, flags)
    inici, final = m.interval()
    if imgui.button('Pausa' if app.reproduint else 'Play', (70, 0)):
        app.reproduint = not app.reproduint
        if app.reproduint and app.hora >= final:
            app.hora = inici
    imgui.same_line()
    if imgui.button('-5 min'):
        app.hora -= 5 / 60
    imgui.same_line()
    if imgui.button('+5 min'):
        app.hora += 5 / 60
    imgui.same_line()
    imgui.text('   Velocitat:')
    for v in VELOCITATS:
        imgui.same_line()
        if imgui.radio_button(f'x{v}', not app.velocitat_auto and app.velocitat == v):
            app.velocitat, app.velocitat_auto = v, False
    imgui.same_line()
    if imgui.radio_button('Auto', app.velocitat_auto):
        app.velocitat_auto = True

    app.hora = min(max(app.hora, inici), final)
    imgui.push_item_width(-1.0)
    text = f'{eclipse_data.hora_local(app.hora)} CEST  -  {m.fase(app.hora)}'
    canviat, minuts = imgui.slider_float('##hora', (app.hora - inici) * 60, 0, (final - inici) * 60,
                                         text.replace('%', '%%'))
    imgui.pop_item_width()
    if canviat:
        app.hora = inici + minuts / 60
    if m.valid:
        hh, hl = m.hores, eclipse_data.hora_local
        text = f"Inici {hl(hh['c1'])[:5]}"
        if hh['c2'] is not None:
            text += f"   |   Totalitat {hl(hh['c2'])} - {hl(hh['c3'])}"
        text += f"   |   Final {hl(hh['c4'])[:5]}"
        if hh['posta'] is not None:
            text += f"   |   Posta {hl(hh['posta'])[:5]}"
        imgui.text_disabled(text)
    imgui.end()
