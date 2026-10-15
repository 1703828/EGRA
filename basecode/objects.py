"""Objecte amb normals i ombrejat de Gouraud (ambient+difusa).
Phong (component especular) es deixa fora expressament: es la tasca del repte4.
Les subclasses nomes cal que implementin get_vertex_data() -> array (color,normal,position) x N.
"""
import glm

from . import shaders


class GouraudObject:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        self.vbo = self.get_vbo()
        self.shader_program = self.get_shader_program()
        self.vao = self.get_vao()
        self.m_model = self.get_model_matrix()
        self.visible = True
        self.on_init()

    def get_model_matrix(self):
        return glm.mat4()

    def on_init(self):
        self.shader_program['light.position'].write(self.app.light.position)
        self.shader_program['light.Ia'].write(self.app.light.Ia)
        self.shader_program['light.Id'].write(self.app.light.Id)
        self.shader_program['m_proj'].write(self.app.camera.m_proj)
        self.shader_program['m_view'].write(self.app.camera.m_view)
        self.shader_program['m_model'].write(self.m_model)

    def render(self):
        if self.visible:
            self.vao.render()

    def destroy(self):
        self.vbo.release()
        self.shader_program.release()
        self.vao.release()

    def get_vao(self):
        return self.ctx.vertex_array(
            self.shader_program, [(self.vbo, '3f 3f 3f', 'in_color', 'in_normal', 'in_position')]
        )

    def get_vertex_data(self):
        raise NotImplementedError('Cada objecte ha de generar les seves dades (color, normal, posicio)')

    def get_vbo(self):
        return self.ctx.buffer(self.get_vertex_data())

    def get_shader_program(self):
        # el shader viu a basecode/shaders/gouraud.vert i .frag (editable sense tocar Python)
        return shaders.load_program(self.ctx, 'gouraud')
