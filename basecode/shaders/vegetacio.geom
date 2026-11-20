#version 330
// Geometry shader (OpenGL 3.2+): rep un punt i emet una columna de base quadrada (la cel·la del model d'alcaries) que
// arriba a l'alcaria mesurada: la coberta i les cares laterals. Es la mateixa idea que l'exemple de les cases de
// Learn OpenGL (un punt -> una figura), pero la mida no s'inventa: la columna es exactament la superficie que fa
// servir el calcul de la visibilitat (dades/visibilitat.py, nivell N3), aixi el que es veu tapa el Sol on el calcul
// diu que el tapa. L'aspecte (normal suavitzada, color) nomes canvia la llum, no la forma (F53).
// Per costar menys, no s'emet res (i el punt no surt del shader) si: es mes lluny de dist_max, es fora de la vista,
// o la cara no mira cap a la camera o te al costat una columna igual o mes alta (bits de v_cares, calculats a la CPU).
layout (points) in;
layout (triangle_strip, max_vertices = 12) out;    // coberta + com a molt dues cares visibles
in vec3 v_base[];
in float v_alt[];
in int v_cares[];
in vec2 v_normal[];
in float v_verd[];
#include "vegetacio_comu.glsl"

void main() {
    vec3 b = v_base[0] + origen_rel;          // relatiu a la camera
    if (length(b) > dist_max) return;
    float alt = v_alt[0];
    vec3 t = b + alt * amunt;
    // la columna on hi ha la camera (p. ex. els ulls sota una capcada: el model d'alcaries es 2,5D i la capcada hi
    // arriba fins a terra) no es dibuixa, perque taparia tota la vista; el calcul la continua comptant
    if (abs(dot(b, est)) < meitat && abs(dot(b, nord)) < meitat && dot(b, amunt) < 0.0 && dot(t, amunt) > 0.0) return;
    // fora de la vista (amb marge): el centre de la columna, retallat amb el seu radi
    vec4 c = m_proj * m_view * vec4(0.5 * (b + t), 1.0);
    float r = alt + 2.0 * meitat;
    if (c.w < -r || abs(c.x) > c.w + 2.0 * r || abs(c.y) > c.w + 2.0 * r) return;   // darrere o al costat
    vec3 e = meitat * est, n = meitat * nord;
    int k = v_cares[0];
    columna(v_normal[0], v_verd[0], k);
    if (dot(t, amunt) < 0.0) {                  // la coberta, si la camera es per sobre
        sortida(t - e - n, 1.0); EmitVertex();
        sortida(t + e - n, 1.0); EmitVertex();
        sortida(t - e + n, 1.0); EmitVertex();
        sortida(t + e + n, 1.0); EmitVertex();
        EndPrimitive();
    }
    vec3 cares[4] = vec3[](est, -est, nord, -nord);
    for (int i = 0; i < 4; i++) {
        vec3 a = cares[i] * meitat;
        if ((k & (1 << i)) == 0 || dot(b + a, cares[i]) > 0.0) continue;   // tapada o d'esquena
        vec3 s = (i < 2 ? nord : est) * meitat;
        sortida(b + a - s, 0.0); EmitVertex();
        sortida(t + a - s, 1.0); EmitVertex();
        sortida(b + a + s, 0.0); EmitVertex();
        sortida(t + a + s, 1.0); EmitVertex();
        EndPrimitive();
    }
}
