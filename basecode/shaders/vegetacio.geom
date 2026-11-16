#version 330
// Geometry shader (OpenGL 3.2+): rep un punt i emet una columna de base quadrada (la cel·la del model d'alcaries) que
// arriba a l'alcaria mesurada: la coberta i les cares laterals. Es la mateixa idea que l'exemple de les cases de
// Learn OpenGL (un punt -> una figura), pero la mida no s'inventa: la columna es exactament la superficie que fa
// servir el calcul de la visibilitat (dades/visibilitat.py, nivell N3), aixi el que es veu tapa el Sol on el calcul
// diu que el tapa.
// Per costar menys, no s'emet res (i el punt no surt del shader) si: es mes lluny de dist_max, es fora de la vista,
// o la cara no mira cap a la camera o te al costat una columna igual o mes alta (bits de v_cares, calculats a la CPU).
layout (points) in;
layout (triangle_strip, max_vertices = 12) out;    // coberta + com a molt dues cares visibles
in vec3 v_base[];
in float v_alt[];
in int v_cares[];
out vec3 normal_g;
out float alcada_g;     // m
flat out int prop_edifici;
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform vec3 origen_rel;    // origen de la vegetacio relatiu a la camera (km)
uniform vec3 est, nord, amunt;
uniform float meitat;       // mitja cel·la (km)
uniform float dist_max;     // km

void vertex(vec3 p, vec3 n) {
    vec4 q = m_proj * m_view * vec4(p, 1.0);
    gl_Position = q;
    logz = 1.0 + q.w;
    normal_g = n;
    EmitVertex();
}

void main() {
    vec3 b = v_base[0] + origen_rel;          // relatiu a la camera
    if (length(b) > dist_max) return;
    vec3 t = b + v_alt[0] * amunt;
    // la columna on hi ha la camera (p. ex. els ulls sota una capcada: el model d'alcaries es 2,5D i la capcada hi
    // arriba fins a terra) no es dibuixa, perque taparia tota la vista; el calcul la continua comptant
    if (abs(dot(b, est)) < meitat && abs(dot(b, nord)) < meitat && dot(b, amunt) < 0.0 && dot(t, amunt) > 0.0) return;
    // fora de la vista (amb marge): el centre de la columna, retallat amb el seu radi
    vec4 c = m_proj * m_view * vec4(0.5 * (b + t), 1.0);
    float r = v_alt[0] + 2.0 * meitat;
    if (c.w < -r || abs(c.x) > c.w + 2.0 * r || abs(c.y) > c.w + 2.0 * r) return;   // darrere o al costat
    vec3 e = meitat * est, n = meitat * nord;
    alcada_g = v_alt[0] * 1000.0;
    prop_edifici = (v_cares[0] & 16) != 0 ? 1 : 0;
    if (dot(t, amunt) < 0.0) {                  // la coberta, si la camera es per sobre
        vertex(t - e - n, amunt); vertex(t + e - n, amunt); vertex(t - e + n, amunt); vertex(t + e + n, amunt);
        EndPrimitive();
    }
    vec3 cares[4] = vec3[](est, -est, nord, -nord);
    for (int i = 0; i < 4; i++) {
        vec3 a = cares[i] * meitat;
        if ((v_cares[0] & (1 << i)) == 0 || dot(b + a, cares[i]) > 0.0) continue;   // tapada o d'esquena
        vec3 s = (i < 2 ? nord : est) * meitat;
        vertex(b + a - s, cares[i]); vertex(t + a - s, cares[i]); vertex(b + a + s, cares[i]); vertex(t + a + s, cares[i]);
        EndPrimitive();
    }
}
