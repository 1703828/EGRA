#version 330
// Vegetacio i altres objectes mesurats: color de fulla segons l'alcaria (estetic; gris a tocar dels edificis) i la llum del Sol i del cel (com edifici.frag, sense ombres).
layout (location = 0) out vec4 fragColor;
in vec3 normal_g;
in float alcada_g;
flat in int prop_edifici;   // 1: objecte enganxat a un edifici (rafec, porxo...): gris, no es un arbre
in float logz;
uniform float coef_log;
uniform vec3 sol_dir;
uniform float llum_sol;
uniform float llum_cel;
uniform vec3 color_sol;
uniform vec3 color_amb;
void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 base = prop_edifici == 1 ? vec3(0.55, 0.53, 0.50)
                                  : mix(vec3(0.20, 0.32, 0.14), vec3(0.30, 0.40, 0.18), clamp(alcada_g / 20.0, 0.0, 1.0));
    vec3 llum = 0.25 * llum_cel * color_amb + 0.75 * llum_sol * max(dot(normalize(normal_g), sol_dir), 0.0) * color_sol;
    fragColor = vec4(base * llum, 1.0);
}
