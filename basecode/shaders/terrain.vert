#version 330
layout (location = 0) in vec2 in_uv;
layout (location = 1) in float in_base;  // faldilles: 0 = a dalt, 1 = a la cota base
// mode globus: posicio de cada vertex sobre l'el·lipsoide (km, relativa a l'origen del terreny),
// la vertical del lloc i la direccio de les columnes de la textura (cap a l'est de la quadricula)
layout (location = 2) in vec3 in_offset;
layout (location = 3) in vec3 in_amunt;
layout (location = 4) in vec3 in_tx;
layout (location = 5) in float in_h;   // mode globus: altura del vertex (m), calculada a la CPU
out vec2 uv;
out vec3 pos_mon;   // posicio en km (mode globus: relativa a la camera), per a la boira i la llum
out float base;
out vec3 amunt;     // mode globus: vertical del lloc
out vec3 tx;        // mode globus: direccio de les columnes
out float logz;     // per a la profunditat logaritmica
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
uniform bool globus;         // true: terreny posat sobre la Terra (main.py); false: pla (scripts)
uniform float profunditat_faldilla;  // mode globus: km que baixen les faldilles per sota de la vora
const float RADI_TERRA = 6371.0;
void main() {
    uv = in_uv;
    base = in_base;
    vec3 p;
    if (globus) {
        // el punt de l'el·lipsoide, aixecat al llarg de la vertical del lloc. L'altura ve de la CPU
        // (in_h): aixi la CPU sap on es exactament la superficie dibuixada (els ulls, a 1,7 m)
        float y = max(in_h, 0.0) / 1000.0 * exaggeration - in_base * profunditat_faldilla;
        p = in_offset + in_amunt * y;
        amunt = in_amunt;
        tx = in_tx;
    } else {
        float h = textureLod(tex_altitud, in_uv, lod_vertexs).r;  // metres
        float y = mix(max(h, 0.0) / 1000.0 * exaggeration, cota_base, in_base);
        vec2 xz = (in_uv - 0.5) * mida_km;
        if (curvatura) {
            // la Terra es corba: a distancia d el terra baixa d^2/(2R) (sense exageracio)
            vec2 d = xz - centre_curvatura;
            y -= dot(d, d) / (2.0 * RADI_TERRA);
        }
        p = vec3(xz.x, y, xz.y);
        amunt = vec3(0.0, 1.0, 0.0);
        tx = vec3(1.0, 0.0, 0.0);
    }
    vec4 q = m_model * vec4(p, 1.0);
    pos_mon = q.xyz;
    gl_Position = m_proj * m_view * q;
    // profunditat logaritmica (mode globus): la calcula el fragment shader (gl_FragDepth) a partir de logz.
    // gl_Position.z es deixa com el dona la projeccio: el retall (clipping) dels triangles es fa
    // interpolant z linealment entre vertexs, i una z logaritmica per vertex retallaria triangles
    // grans que passen per darrere de la camera (el terra als peus desapareixia).
    logz = 1.0 + gl_Position.w;
}
