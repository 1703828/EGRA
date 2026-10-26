#version 330
// Parets del cub de navegacio (basecode/paret_cub.py). Els vertexs ja venen relatius a la camera (km).
layout (location = 0) in vec3 in_position;
layout (location = 1) in float in_cara;     // 0..5: x-, x+, y-, y+, z-, z+
out vec3 pos_rel;
flat out int cara;
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
void main() {
    pos_rel = in_position;
    cara = int(in_cara + 0.5);
    gl_Position = m_proj * m_view * vec4(in_position, 1.0);
    logz = 1.0 + gl_Position.w;   // profunditat logaritmica al fragment shader, com els altres objectes
}
