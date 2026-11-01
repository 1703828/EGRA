#version 330
// Edificis: volums opacs il·luminats pel Sol (amb la part que en tapa la Lluna i el color que li dona
// l'atmosfera) i pel cel. La normal de cada cara (coberta o facana) surt de les derivades de la posicio.
// Aspecte (el color de cada part i la boira venen d'edifici.vert):
//  - Altura estimada (sense mesura LiDAR): tot l'edifici blau (BLAU_ESTIMADA), que no es un color d'edifici.
//  - Cobertes amb altura mesurada: el color de la fotografia aeria sobre aquella coberta (dada real) o, si no n'hi
//    ha, un color de teula o de terrat triat per edifici (estetic).
//  - Facanes: un color per edifici d'una paleta de facanes mediterranies i finestres procedimentals (estetic),
//    una fila per planta real del Catastro (cada 3 m) i repartides per cada costat; a la planta baixa, mes altes.
//    De lluny (a mes de 400 m, o quan una finestra ocupa menys d'un parell de pixels) el dibuix es substitueix pel
//    seu color mitja, per evitar parpelleigs (com un mipmap) i perque costi menys.
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in vec2 uv_facana;
in vec3 boira_v;
in float visibilitat;
flat in float llargada;
flat in float plantes;
flat in float mesurada;
flat in vec3 base;
in float logz;
uniform float coef_log;
uniform vec3 sol_dir;          // cap al Sol (unitari)
uniform float llum_sol;        // llum directa del Sol al centre dels edificis (0..1), amb l'eclipsi
uniform float llum_cel;        // llum del cel (0..1)
uniform vec3 color_sol;        // color de la llum del Sol (dades/atmosfera.color_llum_sol)
uniform vec3 color_amb;        // color de la llum del cel
uniform vec3 amunt;            // vertical local al centre dels edificis (unitari)

// ombres del relleu i dels altres edificis (basecode/ombres_relleu.py): factor_ombra; nomes treu la llum directa del Sol
#include "ombres.glsl"

const float PLANTA = 3.0;      // m (com dades/edificis.ALCADA_PLANTA_M)
const float K_CEL = 0.25;      // pes de la llum del cel i del Sol (els mateixos que terrain.frag)
const float K_SOL = 0.75;
const float ALBEDO_TERRA = 0.25; // part de la llum que reflecteix el terra (asfalt, formigo i vegetacio: ~0,1-0,35)
const float PAS_FINESTRA = 3.2;
const vec3 BLAU_ESTIMADA = vec3(0.30, 0.50, 0.95);   // edificis amb l'altura estimada per plantes

// 1 dins de l'interval [a, b] de x, amb una vora d'un pixel (antialias); w = amplada d'un pixel en unitats de x
float banda(float x, float a, float b, float w) {
    return smoothstep(a - w, a + w, x) - smoothstep(b - w, b + w, x);
}

void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 n = normalize(cross(dFdx(pos_rel), dFdy(pos_rel)));
    if (dot(n, -pos_rel) < 0.0) n = -n;          // la cara que es veu mira cap a la camera
    vec2 px = max(fwidth(uv_facana), vec2(1e-4)); // metres per pixel (abans de cap branca)
    float vidre = 0.0;                            // 1 on hi ha una finestra
    if (llargada >= 0.0) {
        float u = uv_facana.x, v = uv_facana.y;
        float n_fin = floor(llargada / PAS_FINESTRA);
        if (n_fin >= 1.0 && v > 0.0 && v < plantes * PLANTA - 0.4) {
            float lluny = max(step(0.4, length(pos_rel)), smoothstep(0.25, 0.8, max(px.x, px.y)));
            if (lluny >= 1.0) {
                vidre = 0.17;                     // la mitjana: (1,2 / 3,2) x (1,4 / 3)
            } else {
                float local = u - 0.5 * (llargada - n_fin * PAS_FINESTRA);
                float x = mod(local, PAS_FINESTRA);
                float dins_x = step(0.0, local) * step(local, n_fin * PAS_FINESTRA);
                float planta = floor(v / PLANTA), y = mod(v, PLANTA);
                float fy = planta < 0.5 ? banda(y, 0.3, 2.6, px.y) : banda(y, 0.9, 2.3, px.y);
                vidre = mix(banda(x, 1.0, 2.2, px.x) * fy * dins_x, 0.17 * dins_x, lluny);
            }
        }
    }
    float lambert = max(dot(n, sol_dir), 0.0) * factor_ombra(pos_rel, n, sol_dir);
    vec3 cel = K_CEL * llum_cel * color_amb, sol = K_SOL * llum_sol * color_sol;
    vec3 llum = cel + lambert * sol;             // cobertes: com el terra (terrain.frag), que te el mateix color de foto
    if (llargada >= 0.0) {
        // Facanes. Una paret vertical nomes veu la meitat del cel, pero l'altra meitat es el terra, que reflecteix
        // la llum que rep (albedo ALBEDO_TERRA): a l'ombra, la paret no queda negra.
        float nu = dot(n, amunt);
        vec3 terra = ALBEDO_TERRA * (cel + max(dot(sol_dir, amunt), 0.0) * sol);
        llum = (0.5 + 0.5 * nu) * cel + lambert * sol + (0.5 - 0.5 * nu) * terra;
        // Contrast entre cares com el veu l'ull: la llum es lineal, pero la pantalla codifica els colors en sRGB
        // (gamma ~2,2). Es codifica la proporcio respecte d'una cara de cara al Sol; la cara mes il·luminada no
        // canvia, i les de l'ombra passen de ~1/4 a ~1/2 (aproximacio il·lustrativa, com a les fotos).
        vec3 maxim = max(cel + sol, vec3(1e-4));
        llum = maxim * pow(clamp(llum / maxim, 0.0, 1.0), vec3(1.0 / 2.2));
    }
    // el vidre: fosc, amb una mica del color del cel (la boira de l'horitzo) que s'hi reflecteix
    vec3 finestra = vec3(0.05, 0.06, 0.08) * llum + 0.08 * llum_cel * boira_v;
    vec3 b = base;
    if (mesurada < 0.5)
        b = llargada >= 0.0 ? BLAU_ESTIMADA : 0.8 * BLAU_ESTIMADA;   // la coberta, una mica mes fosca
    vec3 color = mix(b * llum, finestra, vidre);
    fragColor = vec4(mix(boira_v, color, visibilitat), 1.0);
}
