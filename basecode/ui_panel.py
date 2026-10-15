"""Petites utilitats per construir el panell d'opcions amb slimgui."""
from slimgui import imgui


def radio_group(label, options, selected_index):
    """Dibuixa un grup de radio_button en linia. Retorna l'index seleccionat (nou o l'actual)."""
    imgui.text(label)
    result = selected_index
    for i, option_label in enumerate(options):
        if i > 0:
            imgui.same_line()
        if imgui.radio_button(option_label, selected_index == i):
            result = i
    return result
