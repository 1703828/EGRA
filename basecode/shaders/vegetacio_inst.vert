#version 330
// Vegetacio mesurada amb instancing (basecode/vegetacio.py, mode alternatiu i didactic): un cub compartit (36 vertexs)
// i, per a cada instancia (glVertexAttribDivisor = 1), el punt de la columna (20 bytes, els mateixos que fa servir el
// geometry shader). Cada vertex es col·loca segons la seva cara; les cares que el geometry shader no emetria (tapades,
// d'esquena, lluny) es fan degenerades (tots els vertexs al mateix punt: sense area, no generen fragments). A
// diferencia del geometry shader, els 36 vertexs de cada instancia es processen sempre: per aixo costa mes
// (scripts/estudi_vegetacio_gpu.py).
layout (location = 0) in vec3 in_cub;     // -1..1 en x (est) i y (nord), 0..1 en z (amunt)
layout (location = 1) in float in_cara;   // 0 coberta, 1 est, 2 oest, 3 nord, 4 sud, 5 base
layout (location = 2) in vec3 in_base;    // per instancia
layout (location = 3) in float in_alt;
layout (location = 4) in vec4 in_dades;   // com vegetacio.vert
#include "vegetacio_comu.glsl"
void main() {
    vec3 b = in_base + origen_rel;
    int cara = int(in_cara + 0.5), mask = int(in_dades.x * 255.0 + 0.5);
    vec3 n = cara == 1 ? est : cara == 2 ? -est : cara == 3 ? nord : cara == 4 ? -nord : cara == 0 ? amunt : -amunt;
    vec3 p = b + in_cub.x * meitat * est + in_cub.y * meitat * nord + in_cub.z * in_alt * amunt;
    bool fora = length(b) > dist_max || cara == 5 ||
                (abs(dot(b, est)) < meitat && abs(dot(b, nord)) < meitat && dot(b, amunt) < 0.0 &&
                 dot(b + in_alt * amunt, amunt) > 0.0);
    if (cara >= 1 && cara <= 4) fora = fora || (mask & (1 << (cara - 1))) == 0 || dot(b + n * meitat, n) > 0.0;
    if (cara == 0) fora = fora || dot(b + in_alt * amunt, amunt) > 0.0;
    if (fora) p = vec3(0.0, 0.0, -1e6);
    columna(in_dades.yz * 2.0 - 1.0, in_dades.w, mask);
    sortida(p, in_cub.z);
}
