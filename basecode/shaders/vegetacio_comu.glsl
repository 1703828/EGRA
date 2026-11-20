// Sortides comunes del geometry shader (vegetacio.geom) i del vertex shader d'instancing (vegetacio_inst.vert): les
// dues maneres de fer la columna donen exactament els mateixos valors al fragment shader (vegetacio.frag). Poques
// sortides per vertex: cada component que emet el geometry shader es paga (12 vertexs per punt, milions de punts).
out vec3 pos_rel;       // relativa a la camera (km)
out float h01;          // 0 al terra, 1 a dalt de la columna
flat out vec3 normal_s; // normal de la superficie suavitzada (dades: basecode/vegetacio.normals_superficie)
flat out float to_verd; // 0..1: color de la capcada (basecode/vegetacio.punts_cel); -1: a tocar d'un edifici
// (la profunditat logaritmica es calcula al fragment shader amb gl_FragCoord.w = 1 / w: una sortida menys)
uniform mat4 m_proj;
uniform mat4 m_view;
uniform vec3 origen_rel;    // origen de la vegetacio relatiu a la camera (km)
uniform vec3 est, nord, amunt;
uniform float meitat;       // mitja cel·la (km)
uniform float dist_max;     // km

// el que es igual a tota la columna (es calcula un cop per punt)
vec3 c_ns; float c_verd;
void columna(vec2 ns, float verd, int cares) {
    c_ns = normalize(ns.x * est + ns.y * nord + sqrt(max(1.0 - dot(ns, ns), 0.0)) * amunt);
    c_verd = (cares & 16) != 0 ? -1.0 : verd;
}

// p: vertex relatiu a la camera (km); h: 0 a la base, 1 a dalt
void sortida(vec3 p, float h) {
    gl_Position = m_proj * m_view * vec4(p, 1.0);
    pos_rel = p;
    h01 = h;
    normal_s = c_ns;
    to_verd = c_verd;
}
