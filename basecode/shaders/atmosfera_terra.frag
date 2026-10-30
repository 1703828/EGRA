#version 330 core
// Resplendor de l'atmosfera vista des de l'espai (il·lustrativa, no es un calcul de dispersio): cada pixel suma un
// blau que creix amb la quantitat d'aire que travessa la mirada (poca mirant avall, molta a la vora del disc) i
// s'esvaeix per sobre de la vora (l'aire es menys dens amunt). Nomes al costat de dia.
// Els calculs es fan en un espai on l'el·lipsoide es una esfera (z multiplicada per a/b).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in float logz;
uniform vec3 centre_rel;   // centre de la Terra relatiu a la camera (km)
uniform vec3 sol_dir;      // direccio cap al Sol
uniform float alcada;      // gruix de la closca (km)
uniform float coef_log;
uniform float intensitat;  // 0 dins de l'atmosfera, 1 a l'espai
const float A = 6378.137, B = 6356.752;
const float CAMI = 1500.0; // km de cami efectiu per a una resplendor de 1 - 1/e
const float ESCALA = 70.0; // km: com s'esvaeix amb l'altura (visual: molt mes gruixut que l'aire real, 8 km, perque es vegi de lluny)

// distancies (en unitats de d) on la recta o + t d entra i surt de l'esfera de radi r centrada a c; (-1, -1) si no hi toca
vec2 esfera(vec3 o, vec3 d, vec3 c, float r) {
    vec3 oc = o - c;
    float a = dot(d, d), b = dot(oc, d), k = dot(oc, oc) - r * r;
    float disc = b * b - a * k;
    if (disc < 0.0) return vec2(-1.0);
    float s = sqrt(disc);
    return vec2(-b - s, -b + s) / a;
}

void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 esc = vec3(1.0, 1.0, A / B);
    vec3 d = pos_rel * esc, c = centre_rel * esc;      // la camera es l'origen: el pixel es a t = 1
    vec2 closca = esfera(vec3(0.0), d, c, A + alcada);
    // cada mirada suma un sol cop: al punt on entra a la closca (la cara del darrere es descarta). Amb la camera
    // dins de la closca no hi ha entrada: compta el punt on en surt, l'unic que es dibuixa
    if (closca.x > 0.0 && abs(closca.x - 1.0) > 1e-3) discard;
    // cami efectiu per l'aire (km d'aire com el de baix, que decreix amb l'altura amb escala ESCALA):
    // - si la mirada topa amb la Terra: ESCALA / cos(angle amb la vertical) (curt mirant avall, llarg de reull);
    // - si passa per sobre, a una altura h: el cami rasant, sqrt(2 pi R ESCALA), per e^(-h / ESCALA)
    vec2 terra = esfera(vec3(0.0), d, c, A);
    vec3 baix;
    float cami;
    if (terra.x > 0.0) {
        baix = d * terra.x - c;
        cami = ESCALA / max(dot(normalize(baix), -normalize(d)), 0.04);
    } else {
        baix = d * max(dot(c, d) / dot(d, d), 0.0) - c;      // punt mes baix de la mirada
        cami = sqrt(6.2831853 * A * ESCALA) * exp(-max(length(baix) - A, 0.0) / ESCALA);
    }
    float aire = 1.0 - exp(-cami / CAMI);
    // dia: el Sol sobre l'horitzo del punt mes baix (amb un marge per al crepuscle, que es mes vermellos)
    float cs = dot(normalize(baix), normalize(sol_dir * esc));
    float dia = smoothstep(-0.25, 0.15, cs);
    vec3 color = mix(vec3(1.0, 0.45, 0.25), vec3(0.35, 0.60, 1.0), smoothstep(-0.1, 0.3, cs));
    fragColor = vec4(color * aire * dia * intensitat, 1.0);
}
