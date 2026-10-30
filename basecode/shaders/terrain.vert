#version 330
layout (location = 0) in vec2 in_uv;
layout (location = 1) in float in_base;  // faldilles: 0 = a dalt, 1 = a la cota base
// mode globus: posicio de cada vertex sobre l'el·lipsoide (km, relativa a l'origen del terreny),
// la vertical del lloc i la direccio de les columnes de la textura (cap a l'est de la quadricula)
layout (location = 2) in vec3 in_offset;
layout (location = 3) in vec3 in_amunt;
layout (location = 4) in vec3 in_tx;
layout (location = 5) in float in_h;   // mode globus: altura del vertex (m), calculada a la CPU
layout (location = 6) in vec2 in_merc; // mode globus: coordenada Web Mercator menys la de l'origen del terreny
out vec2 uv;
out vec3 pos_mon;   // posicio en km (mode globus: relativa a la camera), per a la boira i la llum
out float base;
out vec3 amunt;     // mode globus: vertical del lloc
out vec3 tx;        // mode globus: direccio de les columnes
out float logz;     // per a la profunditat logaritmica
out vec3 color_sol_v;   // mode globus: color de la llum del Sol i del cel en aquest punt (blanc al mode pla)
out vec3 color_amb_v;
out vec3 boira_v;       // mode globus: color de la boira en la direccio d'aquest vertex
out vec2 merc_rel;      // mode globus: Mercator del vertex menys la de la camera (mosaic d'imatges)
out float dens_boira;   // mode globus: densitat de la boira (1/km) de la camera a aquest vertex (-1 al mode pla)
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
uniform vec3 sol_rel;        // mode globus: posicio del Sol relativa a la camera (km)
uniform vec3 boira_sol;      // mode globus: color del cel a l'horitzo cap al Sol i al contrari
uniform vec3 boira_contra;
uniform vec3 sol_horitzontal;
uniform vec3 amunt_camera;
uniform vec2 cam_merc;       // Mercator de la camera menys la de l'origen del terreny (CPU, float64)
uniform float alcada_camera; // km sobre el nivell del mar
uniform float boira_terra;   // 1/km: densitat de la boira a nivell del mar
// Color de la llum del Sol i del cel en un punt (dades/atmosfera.py: color_llum_sol i color_llum_cel). Es calcula
// per vertex (no per fragment): varia molt poc d'un vertex al seguent i, per fragment, costava ~2 ms a 2560 px.
vec3 transmissio_sol(float sin_el) {
    float el = degrees(asin(clamp(sin_el, -1.0, 1.0)));
    if (el < -1.0) return vec3(0.0);
    float massa = 1.0 / (max(sin_el, 0.0) + 0.50572 * pow(max(el, -0.9) + 6.07995, -1.6364));
    vec3 vertical = vec3(5.802e-3, 13.558e-3, 33.1e-3) * 8.0 + 4.40e-3 * 1.2;
    return exp(-vertical * massa);
}
vec3 color_llum_sol(float sin_el) {
    return sqrt(clamp(transmissio_sol(sin_el) / transmissio_sol(1.0), 0.0, 1.0));
}
vec3 color_llum_cel(float sin_el) {
    return mix(vec3(0.82, 0.70, 0.66), vec3(0.72, 0.80, 0.95), smoothstep(0.0, 0.3, sin_el));
}
// Densitat mitjana de l'aire (relativa a la del nivell del mar) en la recta de la camera (altura hc, km) a un punt
// (altura ht): l'aire decreix exponencialment amb l'altura (escala 8 km, dades/atmosfera.py) i la integral en una
// recta es exacta: 8 (e^-ht/8 - e^-hc/8) / (hc - ht). Des de dalt, mirar lluny travessa l'aire dens de prop del
// terra: la boira hi es mes espessa que la densitat a l'altura de la camera.
float densitat_cami(float hc, float ht) {
    hc = max(hc, 0.0);
    ht = max(ht, 0.0);
    float a = exp(-ht / 8.0), b = exp(-hc / 8.0);
    return abs(hc - ht) < 0.05 ? 0.5 * (a + b) : 8.0 * (a - b) / (hc - ht);
}
void main() {
    uv = in_uv;
    base = in_base;
    vec3 p;
    if (globus) {
        // el punt de l'el·lipsoide, aixecat al llarg de la vertical del lloc. L'altura ve de la CPU
        // (in_h): aixi la CPU sap on es exactament la superficie dibuixada (els ulls, a 1,7 m)
        float y = max(in_h, 0.0) / 1000.0 * exaggeration - in_base * profunditat_faldilla;
        p = in_offset + in_amunt * y;
        // dos nombres petits (relatius a l'origen del terreny): la resta conserva la precisio. Abans es passava la
        // coordenada sencera partida en alta + baixa, pero el compilador de la GPU pot reordenar les sumes i es
        // perdia ~1 m per vertex (la foto es veia esmicolada al pegat de 5 m)
        merc_rel = in_merc - cam_merc;
        dens_boira = boira_terra * densitat_cami(alcada_camera, y);
        amunt = in_amunt;
        tx = in_tx;
    } else {
        color_sol_v = color_amb_v = boira_v = vec3(1.0);
        merc_rel = vec2(0.0);
        dens_boira = -1.0;
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
    if (globus) {
        float sin_el = dot(normalize(in_amunt), normalize(sol_rel - q.xyz));
        color_sol_v = color_llum_sol(sin_el);
        color_amb_v = color_llum_cel(sin_el);
        // boira: entre el color de l'horitzo cap al Sol i el contrari, segons la direccio horitzontal
        vec3 d = normalize(q.xyz);
        vec3 hz = d - dot(d, amunt_camera) * amunt_camera;
        float w = length(hz) > 1e-6 ? 0.5 + 0.5 * dot(normalize(hz), sol_horitzontal) : 0.5;
        boira_v = mix(boira_contra, boira_sol, w * w);
    }
    gl_Position = m_proj * m_view * q;
    // profunditat logaritmica (mode globus): la calcula el fragment shader (gl_FragDepth) a partir de logz.
    // gl_Position.z es deixa com el dona la projeccio: el retall (clipping) dels triangles es fa
    // interpolant z linealment entre vertexs, i una z logaritmica per vertex retallaria triangles
    // grans que passen per darrere de la camera (el terra als peus desapareixia).
    logz = 1.0 + gl_Position.w;
}
