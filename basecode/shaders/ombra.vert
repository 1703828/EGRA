#version 330
// Passada des del Sol del shadow mapping (basecode/ombres_relleu.py): el relleu de la zona de detall
// vist des del Sol. Nomes cal la profunditat: el fragment shader no escriu cap color.
// La posicio del vertex es la mateixa que a terrain.vert (mode globus), pero relativa a l'ancora (el
// punt d'observacio) en lloc de la camera.
layout (location = 0) in vec2 in_uv;
layout (location = 1) in vec3 in_offset;   // sobre l'el·lipsoide, relatiu a l'origen del terreny (km)
layout (location = 2) in vec3 in_amunt;    // vertical del lloc
layout (location = 3) in float in_h;       // altura del vertex (m), calculada a la CPU
out vec2 uv;
uniform mat4 m_llum;        // posicio relativa a l'ancora (km) -> coordenades de clip de la llum
uniform vec3 origen;        // origen del terreny relatiu a l'ancora (km)
uniform float exaggeration;
void main() {
    uv = in_uv;
    vec3 p = origen + in_offset + in_amunt * (max(in_h, 0.0) / 1000.0 * exaggeration);
    gl_Position = m_llum * vec4(p, 1.0);
}
