#version 330 core
// La Terra vista de lluny: textura de color, llum del Sol (dia i nit) i ombra de la Lluna. La resplendor de
// l'atmosfera vista des de l'espai es una closca a part (atmosfera_terra.frag).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in vec3 normal;
in vec2 uv;
in float logz;
in vec3 color_sol_v;   // color de la llum del Sol i del cel (terra.vert)
in vec3 color_amb_v;
in vec3 boira_v;       // color de la boira (terra.vert)
in float dens_boira;
uniform sampler2D textura;
uniform vec3 sol_rel;      // Sol relatiu a la camera (km)
uniform vec3 lluna_rel;    // Lluna relativa a la camera (km)
uniform float radi_sol;    // km
uniform float radi_lluna;  // km
uniform float coef_log;
uniform bool ressaltar_ombra;
uniform vec3 cam_ecef;     // posicio de la camera (ECEF, km)
uniform float cam_asinh;   // asinh(tan(latitud de la camera)): la Y de Mercator de la camera, sense escalar
#include "mosaic.glsl"

// Mercator del punt (pos_rel, relatiu a la camera) menys la de la camera. La diferencia de longitud surt
// d'un sol atan amb el producte vectorial i escalar de les dues direccions horitzontals: c x (c + r) = c x r,
// sense restar dos nombres grans. La latitud (geodesica, punt sobre l'el·lipsoide) es fa amb float32: error
// d'~1 m, prou per a les imatges del globus (mar, Portugal, Franca; Sentinel-2 te pixels de 10 m).
vec2 mercator_relatiu(vec3 r) {
    vec3 c = cam_ecef;
    float dlon = atan(c.x * r.y - c.y * r.x, dot(c.xy, c.xy) + dot(c.xy, r.xy));
    vec3 p = c + r;
    float lat = atan(p.z, length(p.xy) * (1.0 - 0.00669438));
    if (abs(lat) > 1.4844) return vec2(10.0);   // mes enlla de 85 graus no hi ha teselles: fora de les finestres
                                                // (main: la foto s'esvaeix abans, sense cercle al pol)
    float t = tan(lat);
    return vec2(dlon, -(log(t + sqrt(t * t + 1.0)) - cam_asinh)) / 6.2831853;
}

// La mateixa formula que dades/model_eclipsi.py i terrain.frag
float area_tapada(float d, float r1, float r2) {
    if (d >= r1 + r2) return 0.0;
    if (d <= abs(r2 - r1)) return min(1.0, (r2 * r2) / (r1 * r1));
    float a1 = r1 * r1 * acos(clamp((d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1), -1.0, 1.0));
    float a2 = r2 * r2 * acos(clamp((d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2), -1.0, 1.0));
    float a3 = 0.5 * sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0));
    return (a1 + a2 - a3) / (3.14159265 * r1 * r1);
}

float tapat_des_de(vec3 p) {
    vec3 s = sol_rel - p, l = lluna_rel - p;
    float rs = asin(radi_sol / length(s)), rl = asin(radi_lluna / length(l));
    float d = 2.0 * asin(min(1.0, 0.5 * length(normalize(s) - normalize(l))));
    return area_tapada(d, rs, rl);
}

// Ressaltat didactic de l'ombra (opcional, desactivat per defecte): linies on la Lluna tapa el 25, el 50
// i el 75 % del Sol (groc) i el limit de la totalitat (lila), nomes on el Sol es sobre l'horitzo (pes).
// Nomes dibuixa linies: no canvia ni la mida ni la foscor de l'ombra. df = fwidth(f), calculat abans de
// qualsevol discard (despres, les derivades no estan definides als pixels veins descartats).
vec3 ressaltar(vec3 c, float f, float df, float pes) {
    float g = f * 4.0;
    float px = abs(fract(g - 0.5) - 0.5) / max(4.0 * df, 1e-6);
    vec3 r = c;
    if (g > 0.5 && g < 3.5)
        r = mix(vec3(1.0, 0.8, 0.2), r, smoothstep(0.5, 1.5, px));
    float pt = abs(f - 0.999) / max(df, 1e-6);
    r = mix(vec3(1.0, 0.3, 1.0), r, smoothstep(1.0, 2.5, pt));
    return mix(c, r, pes);
}

void main() {
    // profunditat logaritmica, una mica mes lluny (2 cm per km) perque el terreny detallat,
    // que es al mateix lloc, sempre quedi per sobre del globus
    gl_FragDepth = log2(1.0 + (logz - 1.0) * 1.00002) * coef_log * 0.5;
    vec2 merc = mercator_relatiu(pos_rel);
    vec2 merc_dx = dFdx(merc), merc_dy = dFdy(merc);
    vec3 n = normalize(normal);
    vec3 sol = normalize(sol_rel - pos_rel);
    float cos_sol = dot(n, sol);
    // dia i nit: el terminador es suau (el crepuscle dura uns quants graus)
    float dia = smoothstep(-0.10, 0.10, cos_sol);
    float tapat = tapat_des_de(pos_rel);
    float d_tapat = fwidth(tapat);
    float visible = 1.0 - tapat;                   // 1 al Sol, 0 a l'ombra de la Lluna
    vec3 color = texture(textura, uv).rgb;
    // fotografia aeria (mosaic d'imatges) on ja s'ha baixat; si no, la textura de tota la Terra
    vec4 foto = color_mosaic(merc, merc_dx, merc_dy);
    // de 80 a 84 graus de latitud, la foto deixa pas a la textura de tota la Terra: sense un cercle al pol
    vec3 p = cam_ecef + pos_rel;
    float lat = atan(p.z, length(p.xy) * (1.0 - 0.00669438));
    color = mix(color, foto.rgb, foto.a * smoothstep(1.466, 1.396, abs(lat)));
    // llum directa (Lambert) + una part difusa del cel que manté clar el costat de dia prop del
    // terminador (aproximacio visual de l'atmosfera)
    vec3 c = color * (0.03 + dia * visible * (0.25 * color_amb_v + 0.95 * max(cos_sol, 0.0) * color_sol_v));
    // boira, com la del terreny: el mar i els paisos veins lluny es veuen igual de velats que la terra
    c = mix(boira_v, c, exp(-length(pos_rel) * dens_boira));
    if (ressaltar_ombra)
        c = ressaltar(c, tapat, d_tapat, smoothstep(-0.03, 0.0, cos_sol));
    fragColor = vec4(c, 1.0);
}
