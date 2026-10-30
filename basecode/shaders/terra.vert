#version 330 core
// La Terra: una malla de l'el·lipsoide WGS84 (posicions en km respecte del centre de la Terra).
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec3 in_normal;    // vertical del lloc
layout (location = 2) in vec2 in_uv;        // longitud i latitud -> textura equirectangular
out vec3 pos_rel;    // posicio relativa a la camera (km)
out vec3 normal;
out vec2 uv;
out float logz;
out vec3 color_sol_v;   // color de la llum del Sol i del cel en aquest punt
out vec3 color_amb_v;
out vec3 boira_v;       // color de la boira en la direccio d'aquest vertex (com terrain.vert)
out float dens_boira;   // densitat de la boira de la camera a aquest vertex (com terrain.vert)
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;   // trasllada el centre de la Terra a la seva posicio relativa a la camera
uniform vec3 sol_rel;   // Sol relatiu a la camera (km)
uniform vec3 boira_sol;      // color del cel a l'horitzo cap al Sol i al contrari (main.py, actualitzar_cel)
uniform vec3 boira_contra;
uniform vec3 sol_horitzontal;
uniform vec3 amunt_camera;
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
    vec4 p = m_model * vec4(in_position, 1.0);
    pos_rel = p.xyz;
    normal = in_normal;
    float sin_el = dot(normalize(in_normal), normalize(sol_rel - p.xyz));
    color_sol_v = color_llum_sol(sin_el);
    color_amb_v = color_llum_cel(sin_el);
    vec3 d = normalize(p.xyz);
    vec3 hz = d - dot(d, amunt_camera) * amunt_camera;
    float w = length(hz) > 1e-6 ? 0.5 + 0.5 * dot(normalize(hz), sol_horitzontal) : 0.5;
    boira_v = mix(boira_contra, boira_sol, w * w);
    dens_boira = boira_terra * densitat_cami(alcada_camera, 0.0);
    uv = in_uv;
    gl_Position = m_proj * m_view * p;
    // profunditat logaritmica: la calcula el fragment shader (gl_FragDepth) a partir de logz.
    // gl_Position.z es deixa com el dona la projeccio: el retall (clipping) dels triangles es fa
    // interpolant z linealment entre vertexs, i una z logaritmica per vertex retallaria triangles
    // grans que passen per darrere de la camera (el terra als peus desapareixia).
    logz = 1.0 + gl_Position.w;
}
