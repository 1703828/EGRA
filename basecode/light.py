"""Font de llum puntual: component ambient, difusa i especular (Ia, Id, Is)."""
import glm


class Light:
    def __init__(self, position=(5, 5, 0), color=(1, 1, 1)):
        self.position = glm.vec3(position)
        self.color = glm.vec3(color)
        self.ka = 0.1
        self.kd = 0.8
        self.ks = 1.0
        self._update_intensities()

    def _update_intensities(self):
        self.Ia = self.ka * self.color
        self.Id = self.kd * self.color
        self.Is = self.ks * self.color
