#version 330
// Paret translucida del cub de navegacio: ratlles diagonals blaves, com el limit del mon d'un joc.
// Nomes es veu quan la camera s'hi acosta (opacitat de cada cara, calculada a la CPU).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
flat in int cara;
in float logz;
uniform float coef_log;
uniform float opacitat[6];     // de cada cara: 0 lluny, 1 a la paret
uniform float distancia[6];    // distancia (km) de la camera al pla de cada cara, calculada en doble precisio
void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    float a = opacitat[cara];
    if (a <= 0.0) discard;
    // el punt de la paret: on el raig de la camera talla el pla de la cara. Les cares fan centenars de
    // milions de km i la posicio interpolada (float32) no te prou precisio a prop de la camera; la direccio
    // si, i la distancia al pla es petita i exacta.
    int eix = cara / 2;
    vec3 dir = normalize(pos_rel);
    float d = distancia[cara] / max(abs(dir[eix]), 1e-6);
    vec3 p = dir * d;
    vec2 pla = eix == 0 ? p.yz : (eix == 1 ? p.xz : p.xy);
    // ratlles diagonals d'amplada proporcional a la distancia (~1/20): dues escales de potencia de 2
    // barrejades, perque no canviin de cop quan la camera s'acosta
    float nivell = log2(max(d, 1e-4) / 20.0);
    float n0 = floor(nivell);
    float ratlla = 0.0;
    for (int k = 0; k < 2; k++) {
        float periode = exp2(n0 + float(k));
        float t = (pla.x + pla.y) / periode;
        float w = fwidth(t);
        float r = smoothstep(0.25 - w, 0.25 + w, abs(fract(t) - 0.5));
        ratlla += r * (k == 0 ? 1.0 - fract(nivell) : fract(nivell));
    }
    fragColor = vec4(vec3(0.55, 0.78, 1.0), a * (0.10 + 0.40 * ratlla));
}
