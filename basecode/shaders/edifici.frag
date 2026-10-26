#version 330
// Edificis: volums opacs d'un sol color, il·luminats pel Sol (amb la part que en tapa la Lluna) i pel cel.
// La normal de cada cara (coberta o facana) surt de les derivades de la posicio: cada triangle es pla.
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in float logz;
uniform float coef_log;
uniform vec3 sol_dir;          // cap al Sol (unitari)
uniform float llum_sol;        // llum directa del Sol al punt d'observacio (0..1)
uniform float llum_cel;        // llum del cel (0..1)
uniform vec3 color_cel;
uniform float densitat_boira;  // 1/km
void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 n = normalize(cross(dFdx(pos_rel), dFdy(pos_rel)));
    if (dot(n, -pos_rel) < 0.0) n = -n;          // la cara que es veu mira cap a la camera
    vec3 color = vec3(0.80, 0.76, 0.70) * (0.30 * llum_cel + 0.70 * llum_sol * max(dot(n, sol_dir), 0.0));
    float f = exp(-pow(length(pos_rel) * densitat_boira, 2.0));
    fragColor = vec4(mix(color_cel, color, f), 1.0);
}
