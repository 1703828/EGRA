#version 330
// Vegetacio i altres objectes mesurats (F53). Il·lustratiu: el LiDAR dona la forma, no l'especie ni el color.
//  - Normal: a la coberta, la de la superficie suavitzada (basecode/vegetacio.normals_superficie): una massa d'arbres
//    s'il·lumina com una superficie arrodonida, no com graons de 2 m; a les cares laterals, barrejada amb la de la
//    cara (que surt de les derivades de la posicio). Un relleu de fulles (soroll) que s'apaga de lluny.
//  - Color: un to de verd per capcada (basecode/vegetacio.punts_cel, soroll de ~6 m: varia a poc a poc d'una columna
//    a la del costat) i clapes de fulles (~0,5 m), en coordenades del lloc (no rellisca en moure's); mes fosc cap a
//    baix (oclusio aproximada: la llum entra poc dins la massa).
//  - Llum: Sol amb les ombres del relleu i dels edificis (ombres.glsl, una lectura), una mica de llum que travessa les
//    fulles (embolcall), i el cel per la part que veu cap amunt. Gris a tocar dels edificis (rafecs, porxos).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in float h01;
flat in vec3 normal_s;
flat in float to_verd;     // -1: a tocar d'un edifici
uniform float coef_log;
uniform float densitat_boira;   // boira com edifici.vert (aqui per fragment: menys sortides del geometry shader)
uniform vec3 boira_sol, boira_contra, sol_horitzontal, amunt_camera;
uniform vec3 sol_dir;
uniform float llum_sol;
uniform float llum_cel;
uniform vec3 color_sol;
uniform vec3 color_amb;
uniform vec3 origen_rel, est, nord, amunt;
uniform sampler2D tex_soroll;   // soroll de les fulles (basecode/vegetacio.textura_soroll), amb mipmaps
uniform float mida_soroll;      // m que cobreix la textura
#define OMBRA_RAPIDA   // ombres.glsl: una lectura per mapa (la vegetacio te molts fragments)
#include "ombres.glsl"

const vec3 VERDS[4] = vec3[](vec3(0.13, 0.22, 0.09),   // alzina, pi: fosc
                             vec3(0.19, 0.29, 0.11),   // roure, pollancre
                             vec3(0.27, 0.34, 0.14),   // oliver, matolls clars
                             vec3(0.33, 0.33, 0.17));  // sec, gespa alta

void main() {
    gl_FragDepth = log2(1.0 + 1.0 / gl_FragCoord.w) * coef_log * 0.5;   // = log2(1 + w), com la resta de l'escena
    bool prop_edifici = to_verd < 0.0;
    vec3 nf = normalize(cross(dFdx(pos_rel), dFdy(pos_rel)));
    if (dot(nf, -pos_rel) < 0.0) nf = -nf;            // la cara que es veu
    bool coberta = dot(nf, amunt) > 0.5;
    vec3 l = (pos_rel - origen_rel) * 1000.0;         // m des de l'origen de la cel·la
    vec3 q = vec3(dot(l, est), dot(l, nord), dot(l, amunt));
    vec2 s = coberta ? q.xy : vec2(abs(dot(nf, est)) > 0.5 ? q.y : q.x, q.z);
    vec3 base;
    vec4 f1 = texture(tex_soroll, s / mida_soroll), f2 = texture(tex_soroll, s / (0.36 * mida_soroll) + 0.37);
    if (prop_edifici) {
        base = vec3(0.52, 0.50, 0.47) * (0.94 + 0.12 * f1.a);
    } else {
        float k = clamp(to_verd * 3.0, 0.0, 2.999);
        base = mix(VERDS[int(k)], VERDS[int(k) + 1], fract(k));
        base *= 0.62 + 0.75 * (0.6 * f1.r + 0.4 * f2.r);             // clapes de fulles (llum i forats)
    }
    // normal per a la llum: la de la superficie, barrejada amb la de la cara als costats, i el relleu de les fulles
    // (de lluny, els mipmaps fan la mitjana de la textura: la inclinacio tendeix a 0 sola)
    vec3 n = coberta ? normal_s : normalize(0.3 * nf + normal_s);   // els costats, gairebe com la coberta: sense graons de llum
    if (!prop_edifici) {
        vec2 g = (f1.gb - 0.5) + 0.6 * (f2.gb - 0.5);
        vec3 t1 = normalize(cross(n, abs(dot(n, amunt)) < 0.9 ? amunt : est)), t2 = cross(n, t1);
        n = normalize(n + 1.2 * (g.x * t1 + g.y * t2));
    }
    // oclusio aproximada: dins la massa arriba poca llum del cel; a la base de les cares laterals, menys
    float oclusio = prop_edifici || coberta ? 1.0 : mix(0.65, 1.0, smoothstep(0.0, 0.9, h01));
    float ombra = factor_ombra(pos_rel, nf, sol_dir);
    float ns_ = dot(n, sol_dir);
    float difusa = prop_edifici ? max(ns_, 0.0) : max((ns_ + 0.35) / 1.35, 0.0);   // fulles: llum que travessa
    vec3 cel = 0.25 * llum_cel * color_amb * (0.6 + 0.4 * dot(n, amunt));
    vec3 sol = 0.75 * llum_sol * color_sol * difusa * ombra;
    vec3 color = base * (cel * oclusio + sol * mix(0.6, 1.0, oclusio));
    vec3 d = normalize(pos_rel);
    vec3 hz = d - dot(d, amunt_camera) * amunt_camera;
    float w = length(hz) > 1e-6 ? 0.5 + 0.5 * dot(normalize(hz), sol_horitzontal) : 0.5;
    float visibilitat = exp(-pow(length(pos_rel) * densitat_boira, 2.0));
    fragColor = vec4(mix(mix(boira_contra, boira_sol, w * w), color, visibilitat), 1.0);
}
