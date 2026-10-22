#version 330 core
// La Terra: una malla de l'el·lipsoide WGS84 (posicions en km respecte del centre de la Terra).
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec3 in_normal;    // vertical del lloc
layout (location = 2) in vec2 in_uv;        // longitud i latitud -> textura equirectangular
out vec3 pos_rel;    // posicio relativa a la camera (km)
out vec3 normal;
out vec2 uv;
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;   // trasllada el centre de la Terra a la seva posicio relativa a la camera
uniform float coef_log;
void main() {
    vec4 p = m_model * vec4(in_position, 1.0);
    pos_rel = p.xyz;
    normal = in_normal;
    uv = in_uv;
    gl_Position = m_proj * m_view * p;
    logz = 1.0 + gl_Position.w;
    gl_Position.z = (log2(max(1e-6, logz)) * coef_log - 1.0) * gl_Position.w;
}
