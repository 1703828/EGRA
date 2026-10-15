"""GraphicsEngine comu: finestra glfw + context moderngl + rellotge + (opcional) panell slimgui.

Cada repte crea una subclasse i sobreescriu on_init() / drawables() / render() / build_ui().
"""
import glfw
import moderngl as mgl

from . import window as winmod

try:
    from slimgui import imgui
    from slimgui.integrations.glfw import GlfwRenderer
except ImportError:  # nomes cal per als reptes que usen panell d'opcions
    imgui = None
    GlfwRenderer = None


class GraphicsEngineBase:
    def __init__(self, win_size=(900, 900), title="EGRA", core_profile=True, use_ui_panel=False):
        self.WIN_SIZE = win_size
        self.window = winmod.create_window(win_size[0], win_size[1], title, core_profile=core_profile)
        self.ctx = mgl.create_context()
        self.ctx.enable_only(mgl.DEPTH_TEST | mgl.CULL_FACE)

        # rellotge
        self.time = 0.0
        self.dt = 0.0
        self._last_time = glfw.get_time()

        # panell d'opcions (slimgui), opcional
        self.use_ui_panel = use_ui_panel and imgui is not None
        self.ui_renderer = None
        if self.use_ui_panel:
            imgui.create_context()
            self.ui_renderer = GlfwRenderer(self.window)

        self.on_init()

    # --- per sobreescriure a cada repte ---
    def on_init(self):
        """Crear camera / axis / scene / light aqui."""
        pass

    def drawables(self):
        """Objectes amb .shader_program que s'han d'actualitzar quan canvia la camera."""
        return []

    def render(self):
        """Netejar framebuffer i dibuixar l'escena. Obligatori."""
        raise NotImplementedError

    def build_ui(self):
        """Afegir checkbox/radio_button/slider_* dins la finestra 'Opcions'."""
        pass

    def on_destroy(self):
        """Alliberar recursos propis abans de tancar."""
        pass

    # --- rellotge ---
    def get_time(self):
        now = glfw.get_time()
        self.dt = now - self._last_time
        self._last_time = now
        self.time = now

    # --- bucle principal ---
    def run(self):
        while not winmod.should_close(self.window):
            glfw.poll_events()
            if winmod.is_escape_pressed(self.window):
                break

            self.get_time()

            if self.use_ui_panel:
                self.ui_renderer.new_frame()
                imgui.new_frame()

            self.render()

            if self.use_ui_panel:
                imgui.set_next_window_pos((10, 10), imgui.Cond.FIRST_USE_EVER)
                imgui.begin('Opcions')
                self.build_ui()
                imgui.end()
                imgui.render()
                self.ui_renderer.render(imgui.get_draw_data())

            glfw.swap_buffers(self.window)

        self._shutdown()

    def _shutdown(self):
        if self.use_ui_panel:
            self.ui_renderer.shutdown()
            imgui.destroy_context(None)
        self.on_destroy()
        for obj in self.drawables():
            if hasattr(obj, 'destroy'):
                obj.destroy()
        glfw.destroy_window(self.window)
        glfw.terminate()
