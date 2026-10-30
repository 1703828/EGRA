#version 330 core
// Closca de l'atmosfera vista des de l'espai (basecode/terra.py): la malla de la Terra, aixecada ALCADA km sobre
// l'el·lipsoide al llarg de la vertical de cada punt.
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec3 in_normal;
out vec3 pos_rel;    // relativa a la camera (km)
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform float alcada;
void main() {
    vec4 p = m_model * vec4(in_position + normalize(in_normal) * alcada, 1.0);
    pos_rel = p.xyz;
    gl_Position = m_proj * m_view * p;
    logz = 1.0 + gl_Position.w;   // profunditat logaritmica, com terra.vert
}
