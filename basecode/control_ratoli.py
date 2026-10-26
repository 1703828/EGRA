"""
Control de la mirada amb el ratoli capturat (com als jocs en primera persona) i la roda.

- Cursor lliure (per defecte): el ratoli fa servir el panell; arrossegar gira la mirada i, a l'exploracio,
  el doble clic tria el punt d'observacio.
- Un clic a l'escena (fora del panell) captura el ratoli: el cursor s'amaga i el moviment del ratoli gira
  la mirada sense haver de premer cap boto ni topar amb la vora de la pantalla. GLFW ho fa amb el mode
  CURSOR_DISABLED: el cursor queda lligat a la finestra i get_cursor_pos dona una posicio "virtual" sense
  limits; la diferencia entre dos fotogrames es el moviment relatiu. (El moviment "raw", sense
  acceleracio, nomes existeix a Windows i Linux; si el sistema el te, s'activa.)
- Un clic d'un doble clic no captura: el clic espera el temps del doble clic (0,3 s) abans de capturar,
  i si arriba el segon clic es un doble clic (triar el punt).
- Esc (main.py, run) o perdre el focus de la finestra alliberen el ratoli. En capturar, el primer
  moviment es compta des d'on es el cursor en aquell moment: no hi ha salts.
- Mentre es capturat, imgui no rep el ratoli (ConfigFlags.NO_MOUSE): el cursor invisible no pot clicar el
  panell.
- La roda i el lliscament amb dos dits del trackpad arriben a GLFW com el mateix esdeveniment de
  desplacament (scroll), amb valors fraccionaris al trackpad. Es sumen fins al fotograma seguent. GLFW no
  rep el gest de pessigar de macOS (veure el pla, tasca 12.4).
Els callbacks de GLFW criden tambe els que hi havia (els d'imgui), per no trencar el panell.
"""
import glfw
from slimgui import imgui

SENSIBILITAT = 0.12        # graus per punt de pantalla de moviment del ratoli capturat (sense zoom)
MOVIMENT_CLIC = 4.0        # punts: si el ratoli es mou mes entre premer i deixar anar, es arrossegar


class ControlRatoli:
    def __init__(self, app):
        self.window = app.window
        self.capturat = False
        self.ultima = None          # posicio del cursor al fotograma anterior (capturat)
        self.roda = 0.0             # desplacament de la roda acumulat des de l'ultim fotograma
        self.premut = None          # on s'ha premut el boto (per distingir un clic d'arrossegar)
        self.clic_pendent = None    # temps d'un clic que capturara si no arriba el segon clic
        self.scroll_anterior = glfw.set_scroll_callback(self.window, self.on_scroll)
        self.focus_anterior = glfw.set_window_focus_callback(self.window, self.on_focus)

    def on_scroll(self, window, dx, dy):
        if self.scroll_anterior:
            self.scroll_anterior(window, dx, dy)
        self.roda += dy

    def on_focus(self, window, focus):
        if self.focus_anterior:
            self.focus_anterior(window, focus)
        if not focus:
            self.alliberar()

    def capturar(self):
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)
        if glfw.raw_mouse_motion_supported():
            glfw.set_input_mode(self.window, glfw.RAW_MOUSE_MOTION, glfw.TRUE)
        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags.NO_MOUSE
        self.capturat, self.ultima, self.clic_pendent = True, None, None

    def alliberar(self):
        if not self.capturat:
            return
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_NORMAL)
        io = imgui.get_io()
        io.config_flags &= ~imgui.ConfigFlags.NO_MOUSE
        self.capturat, self.ultima, self.premut = False, None, None

    def fotograma(self, ara):
        """Es crida un cop per fotograma, despres de glfw.poll_events. Retorna (dx, dy, roda): el moviment
        del ratoli capturat (punts de pantalla) i els passos de roda que toquen a la camera."""
        roda, self.roda = self.roda, 0.0
        if self.capturat:
            x, y = glfw.get_cursor_pos(self.window)
            if self.ultima is None:      # primer fotograma capturat: cap salt
                self.ultima = (x, y)
            dx, dy = x - self.ultima[0], y - self.ultima[1]
            self.ultima = (x, y)
            return dx, dy, roda
        io = imgui.get_io()
        if io.want_capture_mouse:        # el cursor es sobre el panell: el panell fa servir el ratoli
            self.premut = self.clic_pendent = None
            return 0.0, 0.0, 0.0
        boto = imgui.MouseButton.LEFT
        if imgui.is_mouse_double_clicked(boto):
            self.clic_pendent = self.premut = None   # doble clic: es per triar el punt, no captura
        elif imgui.is_mouse_clicked(boto):
            self.premut = tuple(io.mouse_pos)
        elif imgui.is_mouse_released(boto) and self.premut is not None:
            mx, my = io.mouse_pos
            if abs(mx - self.premut[0]) + abs(my - self.premut[1]) <= MOVIMENT_CLIC:
                self.clic_pendent = ara
            self.premut = None
        if self.clic_pendent is not None and ara - self.clic_pendent > io.mouse_double_click_time:
            self.capturar()
        return 0.0, 0.0, roda
