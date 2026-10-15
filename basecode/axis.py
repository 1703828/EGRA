"""Eixos X (vermell) Y (verd) Z (blau), com a referencia visual."""
import moderngl as mgl
import glm
import numpy as np


class Axis:
    def __init__(self, app, length=1.5):
        self.app = app
        self.ctx = app.ctx
        self.length = length
        self.vbo = self.get_vbo()
        self.shader_program = self.get_shader_program()
        self.vao = self.get_vao()
        self.m_model = glm.mat4()
        self.on_init()
        self.visible = True

    def on_init(self):
        self.shader_program['m_proj'].write(self.app.camera.m_proj)
        self.shader_program['m_view'].write(self.app.camera.m_view)
        self.shader_program['m_model'].write(self.m_model)

    def render(self):
        if self.visible:
            self.vao.render(mgl.LINES)

    def destroy(self):
        self.vbo.release()
        self.shader_program.release()
        self.vao.release()

    def get_vao(self):
        return self.ctx.vertex_array(self.shader_program, [(self.vbo, '3f 3f', 'in_color', 'in_position')])

    def get_vertex_data(self):
        l = self.length
        vertices = [(0, 0, 0), (l, 0, 0), (0, l, 0), (0, 0, l)]
        indices = [(0, 1), (0, 2), (0, 3)]
        colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        data = [(colors[i], vertices[ind]) for i, line in enumerate(indices) for ind in line]
        return np.array(data, dtype='f4')

    def get_vbo(self):
        return self.ctx.buffer(self.get_vertex_data())

    def get_shader_program(self):
        return self.ctx.program(
            vertex_shader='''
                #version 330
                layout (location = 0) in vec3 in_color;
                layout (location = 1) in vec3 in_position;
                out vec3 color;
                uniform mat4 m_proj;
                uniform mat4 m_view;
                uniform mat4 m_model;
                void main() {
                    color = in_color;
                    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330
                layout (location = 0) out vec4 fragColor;
                in vec3 color;
                void main() {
                    fragColor = vec4(color, 1.0);
                }
            ''',
        )
