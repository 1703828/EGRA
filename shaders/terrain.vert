#version 330
layout (location = 0) in vec2 in_uv;
layout (location = 1) in float in_base;  // faldilles: 0 = a dalt, 1 = a la cota base
out vec2 uv;
out vec3 pos_mon;   // posicio en km (per a la boira i les normals de les faldilles)
out float base;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform sampler2D tex_altitud;
uniform vec2 mida_km;        // mida del terreny (est, sud) en km
uniform float lod_vertexs;   // nivell de mipmap: mitjana de l'area de cada vertex
uniform float exaggeration;
uniform float cota_base;     // altura (km) del fons de les faldilles
uniform bool curvatura;
uniform vec2 centre_curvatura;  // (x, z) de l'objectiu de la camera: alli no hi ha caiguda
const float RADI_TERRA = 6371.0;
void main() {
    uv = in_uv;
    base = in_base;
    float h = textureLod(tex_altitud, in_uv, lod_vertexs).r;  // metres
    vec2 xz = (in_uv - 0.5) * mida_km;
    float y = mix(max(h, 0.0) / 1000.0 * exaggeration, cota_base, in_base);
    if (curvatura) {
        // la Terra es corba: a distancia d el terra baixa d^2/(2R) (sense exageracio)
        vec2 d = xz - centre_curvatura;
        y -= dot(d, d) / (2.0 * RADI_TERRA);
    }
    vec4 p = m_model * vec4(xz.x, y, xz.y, 1.0);
    pos_mon = p.xyz;
    gl_Position = m_proj * m_view * p;
}
