#version 330
// Edificis (basecode/edificis.py): vertexs en km relatius a l'origen dels edificis (ECEF). El que es constant per
// part (color, plantes) i el que varia poc (la boira) es calcula aqui, un cop per vertex; edifici.frag nomes fa
// la llum i les finestres.
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec4 in_atr;   // u (m al llarg del costat), v (m sobre el sol), llargada del costat
                                        // (m; -1 a les cobertes) i index de la part (dades/edificis.malla_zona)
out vec3 pos_rel;     // relativa a la camera (km)
out vec2 uv_facana;   // (u, v) en metres
out vec3 boira_v;     // color de la boira en aquesta direccio
out float visibilitat; // 1 sense boira, 0 tot boira
flat out float llargada;
flat out float plantes;
flat out float mesurada;      // 1 si l'altura ve d'un LiDAR (dades/alcaries.py), 0 si es estimada per plantes
flat out vec3 base;   // color de la coberta o de la facana d'aquesta part
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model; // trasllada l'origen dels edificis a la seva posicio relativa a la camera
out float logz;
uniform sampler2D tex_parts;   // per part: RGB color de la coberta, A plantes (0-63) + 64 si l'altura es mesurada
                               // + 128 si el color de la coberta es de l'ortofoto
uniform float densitat_boira;  // 1/km
uniform vec3 boira_sol;        // color del cel a l'horitzo cap al Sol i al contrari (com terrain.frag)
uniform vec3 boira_contra;
uniform vec3 sol_horitzontal;
uniform vec3 amunt_camera;

// colors estetics: facanes mediterranies i, sense ortofoto, teula o terrat
const vec3 FACANES[6] = vec3[](vec3(0.86, 0.80, 0.68), vec3(0.80, 0.66, 0.50), vec3(0.90, 0.86, 0.78),
                               vec3(0.74, 0.58, 0.46), vec3(0.78, 0.76, 0.72), vec3(0.84, 0.72, 0.56));
const vec3 COBERTES[3] = vec3[](vec3(0.62, 0.36, 0.26), vec3(0.55, 0.53, 0.50), vec3(0.70, 0.46, 0.34));

uint hash(uint x) {
    x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
    return x;
}

void main() {
    vec4 p = m_model * vec4(in_position, 1.0);
    pos_rel = p.xyz;
    uv_facana = in_atr.xy;
    llargada = in_atr.z;
    int part = int(in_atr.w + 0.5);
    vec4 dades = texelFetch(tex_parts, ivec2(part % 1024, part / 1024), 0);
    int a = int(dades.a * 255.0 + 0.5);
    plantes = float(a & 63);
    mesurada = float((a & 64) != 0);
    uint h = hash(uint(part) + 1u);
    float variacio = float((h >> 8) & 255u) / 255.0;
    if (llargada < 0.0)
        base = a >= 128 ? dades.rgb : COBERTES[h % 3u] * (0.9 + 0.2 * variacio);
    else
        base = FACANES[h % 6u] * (0.92 + 0.16 * variacio);
    vec3 d = normalize(p.xyz);
    vec3 hz = d - dot(d, amunt_camera) * amunt_camera;
    float w = length(hz) > 1e-6 ? 0.5 + 0.5 * dot(normalize(hz), sol_horitzontal) : 0.5;
    boira_v = mix(boira_contra, boira_sol, w * w);
    visibilitat = exp(-pow(length(p.xyz) * densitat_boira, 2.0));
    gl_Position = m_proj * m_view * p;
    logz = 1.0 + gl_Position.w;   // profunditat logaritmica al fragment shader, com la resta de l'escena
}
