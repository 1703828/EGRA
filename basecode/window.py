"""Creacio de finestra + context OpenGL amb glfw. Comu a tots els reptes."""
import sys
import glfw


def create_window(width=900, height=900, title="EGRA", gl_major=3, gl_minor=3, core_profile=True):
    if not glfw.init():
        raise RuntimeError("No s'ha pogut inicialitzar glfw")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, gl_major)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, gl_minor)
    if core_profile:
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)

    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("No s'ha pogut crear la finestra glfw")

    glfw.make_context_current(window)
    return window


def should_close(window):
    return glfw.window_should_close(window)


def is_escape_pressed(window):
    return glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS


def swap_and_poll(window):
    glfw.swap_buffers(window)
    glfw.poll_events()


def close(window):
    glfw.destroy_window(window)
    glfw.terminate()
    sys.exit()
