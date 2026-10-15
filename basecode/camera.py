"""Camera amb projeccio perspectiva o ortografica (4 viewports), com repte2a/repte3."""
import glm


class Camera:
    def __init__(self, app, position=(4, 3, 2), at=(0, 0, 0), up=(0, 1, 0), angle=45):
        self.app = app
        self.aspect_ratio = app.WIN_SIZE[0] / app.WIN_SIZE[1]
        self.position = position
        self.at = at
        self.up = up
        self.angle = angle
        self.perspective = True
        self.pinfc = 'Camera: Perspective '
        self.m_view = self.get_view_matrix()
        self.m_proj = self.get_projection_matrix()

    def set_camera(self, position, at, up, angle):
        self.position = position
        self.at = at
        self.up = up
        self.angle = angle
        self.perspective = angle != 0
        self.pinfc = 'Camera: Perspective ' if self.perspective else 'Camera: Ortho '
        self.m_view = self.get_view_matrix()
        self.m_proj = self.get_projection_matrix()
        for obj in self.app.drawables():
            obj.shader_program['m_proj'].write(self.m_proj)
            obj.shader_program['m_view'].write(self.m_view)

    def position_vec3(self):
        """Posicio actual de la camera com a glm.vec3 (util per calcular la direccio de vista al shader)."""
        return glm.vec3(self.position)

    def get_view_matrix(self):
        return glm.lookAt(glm.vec3(*self.position), glm.vec3(*self.at), glm.vec3(*self.up))

    def get_projection_matrix(self):
        if self.angle == 0:
            return glm.ortho(-2, 2, -2, 2, 0.1, 100)
        return glm.perspective(glm.radians(self.angle), self.aspect_ratio, 0.1, 100)
