#version 330
// Vegetacio mesurada (basecode/vegetacio.py): un punt per cel·la de 2 m del model d'alcaries (LiDAR) amb un objecte
// que no es edifici. El vertex shader nomes passa el punt; el geometry shader (vegetacio.geom) en fa la columna.
layout (location = 0) in vec3 in_base;    // km, relatiu a l'origen de la vegetacio (ECEF): el terra de la cel·la
layout (location = 1) in float in_alt;    // km: alcaria de la vegetacio sobre el terra (superficie - terra)
layout (location = 2) in float in_cares;  // cares exposades: bits 1 est, 2 oest, 4 nord, 8 sud
out vec3 v_base;
out float v_alt;
out int v_cares;
void main() {
    v_base = in_base;
    v_alt = in_alt;
    v_cares = int(in_cares + 0.5);
}
