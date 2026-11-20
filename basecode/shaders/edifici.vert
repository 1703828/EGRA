#version 330
// Edificis (basecode/edificis.py): vertexs en km relatius a l'origen dels edificis (ECEF). Aqui nomes el que depen
// del vertex (posicio, coordenades de la facana i de la foto, boira); l'aspecte de cada part (material, colors,
// finestres, textura) el calcula la CPU un sol cop (dades/edificis.aspecte_parts) i edifici.frag el llegeix de la
// textura tex_aspecte amb l'index de la part.
//
// Per que (F53, 20/11/2026): a la F52 l'aspecte es calculava aqui, a cada vertex, i passava al fragment shader com
// unes 25 sortides per vertex. Amb el milio de triangles del Valles vistos des de lluny, aixo pujava la mediana del
// recorregut dels mapes (scripts/prova_mapes.py) de 22 a 33 ms per fotograma.
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec4 in_atr;   // u (m al llarg del costat), v (m sobre el sol), llargada del costat
                                        // (m; -1 a les cobertes) i index de la part (dades/edificis.malla_zona)
out vec3 pos_rel;     // relativa a la camera (km)
out vec2 uv_facana;   // (u, v) en metres
out vec2 merc_rel;    // Web Mercator del punt menys la de la camera (foto de les cobertes: mosaic.glsl)
out vec3 boira_v;     // color de la boira en aquesta direccio
out float visibilitat; // 1 sense boira, 0 tot boira
flat out float llargada;
flat out int part;    // index de la part (tex_parts, tex_aspecte)
out float logz;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model; // trasllada l'origen dels edificis a la seva posicio relativa a la camera
uniform vec3 merc_jx;          // Mercator relativa = (merc_jx . p, merc_jy . p), p relativa a la camera (km):
uniform vec3 merc_jy;          // basecode/edificis.jacobia_mercator
uniform float densitat_boira;  // 1/km
uniform vec3 boira_sol;        // color del cel a l'horitzo cap al Sol i al contrari (com terrain.frag)
uniform vec3 boira_contra;
uniform vec3 sol_horitzontal;
uniform vec3 amunt_camera;

void main() {
    vec4 p = m_model * vec4(in_position, 1.0);
    pos_rel = p.xyz;
    uv_facana = in_atr.xy;
    merc_rel = vec2(dot(merc_jx, p.xyz), dot(merc_jy, p.xyz));
    llargada = in_atr.z;
    part = int(in_atr.w + 0.5);
    vec3 d = normalize(p.xyz);
    vec3 hz = d - dot(d, amunt_camera) * amunt_camera;
    float w = length(hz) > 1e-6 ? 0.5 + 0.5 * dot(normalize(hz), sol_horitzontal) : 0.5;
    boira_v = mix(boira_contra, boira_sol, w * w);
    visibilitat = exp(-pow(length(p.xyz) * densitat_boira, 2.0));
    gl_Position = m_proj * m_view * p;
    logz = 1.0 + gl_Position.w;   // profunditat logaritmica al fragment shader, com la resta de l'escena
}
