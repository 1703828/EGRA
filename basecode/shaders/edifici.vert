#version 330
// Edificis (basecode/edificis.py): vertexs en km relatius a l'origen dels edificis (ECEF).
layout (location = 0) in vec3 in_position;
out vec3 pos_rel;     // relativa a la camera (km)
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model; // trasllada l'origen dels edificis a la seva posicio relativa a la camera
void main() {
    vec4 p = m_model * vec4(in_position, 1.0);
    pos_rel = p.xyz;
    gl_Position = m_proj * m_view * p;
    logz = 1.0 + gl_Position.w;   // profunditat logaritmica al fragment shader, com la resta de l'escena
}
