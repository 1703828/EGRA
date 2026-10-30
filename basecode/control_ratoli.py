"""
Control de la mirada amb el ratoli capturat (com als jocs en primera persona) i la roda.

- Cursor lliure (per defecte): el ratoli fa servir el panell; arrossegar gira la mirada i, a l'exploracio,
  el doble clic tria el punt d'observacio.
- Tab (main.py, teclat) o un clic dret a l'escena capturen el ratoli a l'instant: el cursor s'amaga i el
  moviment del ratoli gira la mirada sense premer cap boto ni topar amb la vora de la pantalla. GLFW ho fa
  amb el mode CURSOR_DISABLED: el cursor queda lligat a la finestra i get_cursor_pos dona una posicio
  "virtual" sense limits; la diferencia entre dos fotogrames es el moviment relatiu, que s'aplica un sol cop
  per fotograma i sense multiplicar per dt (el ratoli ja dona un desplacament, no una velocitat). (El
  moviment "raw", sense acceleracio, nomes existeix a Windows i Linux; si el sistema el te, s'activa.)
- El clic esquerre no captura: aixi arrossegar (girar) i el doble clic (triar el punt) funcionen igual que
  sempre i no cal esperar el temps del doble clic per saber que vol l'usuari.
- Tab, Esc (main.py, run) o perdre el focus de la finestra alliberen el ratoli. En capturar, el primer
  moviment es compta des d'on es el cursor en aquell moment: no hi ha salts.
- Mentre es capturat, imgui no rep el ratoli (ConfigFlags.NO_MOUSE): el cursor invisible no pot clicar el
  panell. El backend de slimgui (GlfwRenderer.new_frame) torna a posar CURSOR_NORMAL a cada fotograma per
  canviar la forma del cursor: mentre es capturat, aquest pas se salta (si no, la captura nomes duraria un
  fotograma i el cursor tornaria a topar amb les vores).
- La roda i el lliscament amb dos dits del trackpad arriben a GLFW com el mateix esdeveniment de
  desplacament (scroll), amb valors fraccionaris al trackpad. Es sumen fins al fotograma seguent i van o al
  panell (si el cursor hi es a sobre) o a la camera, mai a tots dos. GLFW no rep el gest de pessigar de
  macOS (veure el pla, tasca 12.4).
Els callbacks de GLFW criden tambe els que hi havia (els d'imgui), per no trencar el panell.
"""
import glfw
from slimgui import imgui

SENSIBILITAT = 0.15        # graus per punt de pantalla de moviment del ratoli (capturat o arrossegant), sense zoom


def graus_per_punt(fov, fov_base):
    """Sensibilitat amb zoom: proporcional al camp de visio, perque un mateix moviment del ratoli desplaci la
    imatge la mateixa fraccio de pantalla amb zoom i sense (com uns prismatics)."""
    return SENSIBILITAT * fov / fov_base


class ControlRatoli:
    def __init__(self, app):
        self.window = app.window
        self.capturat = False
        self.focus = True           # la finestra te el focus (sense focus, main.py no mou la camera amb el teclat)
        self.ultima = None          # posicio del cursor al fotograma anterior (capturat)
        self.roda = 0.0             # desplacament de la roda acumulat des de l'ultim fotograma
        self.capturat_des_de = -1e9 # temps (glfw) de l'ultima captura: l'avis dels controls es veu uns segons
        self.scroll_anterior = glfw.set_scroll_callback(self.window, self.on_scroll)
        self.focus_anterior = glfw.set_window_focus_callback(self.window, self.on_focus)
        renderer = getattr(app, 'ui_renderer', None)
        if renderer is not None:
            canviar_cursor = renderer._update_mouse_cursor

            def cursor_imgui():
                if not self.capturat:
                    canviar_cursor()
            renderer._update_mouse_cursor = cursor_imgui

    def on_scroll(self, window, dx, dy):
        if self.scroll_anterior:
            self.scroll_anterior(window, dx, dy)
        self.roda += dy

    def on_focus(self, window, focus):
        if self.focus_anterior:
            self.focus_anterior(window, focus)
        self.focus = bool(focus)
        if not focus:
            self.alliberar()
            self.roda = 0.0

    def capturar(self):
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
        if glfw.raw_mouse_motion_supported():
            glfw.set_input_mode(self.window, glfw.RAW_MOUSE_MOTION, glfw.TRUE)
        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags.NO_MOUSE
        self.capturat, self.ultima = True, None
        self.capturat_des_de = glfw.get_time()

    def alliberar(self):
        if not self.capturat:
            return
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_NORMAL)
        io = imgui.get_io()
        io.config_flags &= ~imgui.ConfigFlags.NO_MOUSE
        self.capturat, self.ultima = False, None

    def commutar(self):
        """Tab: captura si es lliure, allibera si es capturat."""
        if self.capturat:
            self.alliberar()
        else:
            self.capturar()

    def fotograma(self):
        """Es crida un cop per fotograma, despres de glfw.poll_events. Retorna (dx, dy, roda): el moviment
        del ratoli capturat (punts de pantalla) i els passos de roda que toquen a la camera."""
        roda, self.roda = self.roda, 0.0
        if self.capturat:
            x, y = glfw.get_cursor_pos(self.window)
            if self.ultima is None:      # primer fotograma capturat: nomes es pren la referencia
                self.ultima = (x, y)
            dx, dy = x - self.ultima[0], y - self.ultima[1]
            self.ultima = (x, y)
            return dx, dy, roda
        if imgui.get_io().want_capture_mouse:   # el cursor es sobre el panell: el panell fa servir el ratoli
            return 0.0, 0.0, 0.0
        if imgui.is_mouse_clicked(imgui.MouseButton.RIGHT):
            self.capturar()
        return 0.0, 0.0, roda
