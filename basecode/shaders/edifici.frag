#version 330
// Edificis: volums opacs il·luminats pel Sol (amb la part que en tapa la Lluna i el color que li dona
// l'atmosfera) i pel cel. La normal de cada cara (coberta o facana) surt de les derivades de la posicio.
// Aspecte (el material, els colors i les finestres de cada part venen d'edifici.vert; F52 i F53):
//  - Altura estimada (sense mesura LiDAR): tot l'edifici blau (BLAU_ESTIMADA), que no es un color d'edifici.
//  - Cobertes amb altura mesurada: la fotografia aeria del seu propi lloc (mosaic.glsl, les mateixes teselles que
//    el terreny; dada real). On la tesella encara no ha arribat, el material provisional d'edifici.vert, i la foto
//    el substitueix a mesura que arriba (sense salts: color_mosaic diu quina part ja cobreix).
//  - Facanes (F53): una fotografia de material real (arrebossat, mao, pedra, formigo, xapa; texture array de
//    basecode/textures_facanes.py) a la seva mida real, en metres de la facana (uv_facana): no s'estira mai. Mapa de
//    normals (relleu de les juntes i del gra) i de rugositat (brillantor: el formigo i la xapa, una mica; l'arrebossat,
//    gens). Per trencar la repeticio, la mateixa imatge molt ampliada modula el to (taques grans). Amb mipmaps: de
//    lluny no parpelleja i el detall no s'apaga a ma. Il·lustratiu: el Catastro no diu el material.
//  - Finestres, una fila per planta real del Catastro (cada 3 m), amb la mida del tipus d'edifici: marc, persiana
//    (mes o menys baixada a cada finestra) i vidre que reflecteix el cel segons l'angle (Fresnel) i el Sol.
//    Quan una finestra fa menys d'un parell de pixels, el seu color mitja (sense parpelleig).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in vec2 uv_facana;
in vec2 merc_rel;
in vec3 boira_v;
in float visibilitat;
flat in float llargada;
flat in int part;
uniform sampler2D tex_parts;    // per part: RGB color mitja de la foto a la coberta, A plantes (0-63) + 64 si l'altura
                                // es mesurada + 128 si el color de la coberta es de la foto
uniform sampler2D tex_aspecte;  // per part, TEXELS texels RGBA32F seguits: dades/edificis.aspecte_parts
const int TEXELS = 6;           // (dades/edificis.TEXELS_ASPECTE)
// l'aspecte de la part d'aquest fragment (llegir_part): material, colors, finestres i textura de la facana
float plantes, mesurada, llavor;
vec3 base, base2, tint, coberta_provisional;
int material, capa, tipus_part;
vec4 finestres;
vec3 finestres_pb;
vec2 desplacament;
bool coberta_de_foto;

vec4 aspecte(int k) {
    int i = part * TEXELS + k;
    return texelFetch(tex_aspecte, ivec2(i % 1024, i / 1024), 0);
}

void llegir_part() {
    int a = int(texelFetch(tex_parts, ivec2(part % 1024, part / 1024), 0).a * 255.0 + 0.5);
    plantes = float(a & 63);
    mesurada = float((a & 64) != 0);
    coberta_de_foto = a >= 128;
    vec4 t0 = aspecte(0), t1 = aspecte(1), t2 = aspecte(2), t4 = aspecte(4), t5 = aspecte(5);
    base = t0.rgb; material = int(t0.a + 0.5);
    base2 = t1.rgb; llavor = t1.a;
    tint = t2.rgb; capa = int(floor(t2.a + 0.5));
    finestres = aspecte(3);
    finestres_pb = t4.rgb; tipus_part = int(t4.a + 0.5);
    coberta_provisional = t5.rgb;
    desplacament = vec2(floor(t5.a / 2048.0), mod(t5.a, 2048.0)) * 0.01;
    if (coberta_de_foto) coberta_provisional = texelFetch(tex_parts, ivec2(part % 1024, part / 1024), 0).rgb;
}
uniform sampler2DArray tex_facana;      // color (basecode/textures_facanes.py)
uniform sampler2DArray tex_facana_nr;   // RG normal (OpenGL), B rugositat
uniform vec2 mida_capa[16];             // m de cada capa
uniform vec3 mitjana_capa[16];
in float logz;
uniform float coef_log;
uniform vec3 sol_dir;          // cap al Sol (unitari)
uniform float llum_sol;        // llum directa del Sol al centre dels edificis (0..1), amb l'eclipsi
uniform float llum_cel;        // llum del cel (0..1)
uniform vec3 color_sol;        // color de la llum del Sol (dades/atmosfera.color_llum_sol)
uniform vec3 color_amb;        // color de la llum del cel
uniform vec3 amunt;            // vertical local al centre dels edificis (unitari)

// ombres del relleu i dels altres edificis (basecode/ombres_relleu.py): factor_ombra; nomes treu la llum directa del Sol
#include "ombres.glsl"

// fotografia aeria de les cobertes (basecode/mosaic.py): color_mosaic(merc_rel, ...)
#include "mosaic.glsl"

// mapa de l'eclipsi a les cobertes (terrats, basecode/mapes.py): el mateix codi que el terreny (mapes.glsl), amb les
// coordenades del mapa (m, UTM relatiu a l'origen dels edificis) i la Lluna al centre dels edificis (canvia menys
// d'un 0,1 % en 3 km)
uniform vec3 cam_menys_origen;   // camera - origen dels edificis (km)
uniform mat3 a_utm;              // de posicio relativa a l'origen (km) a UTM relatiu a l'origen (m): files x, y
uniform vec3 sol_rel;            // el Sol relatiu a la camera (km)
uniform float tapat_aqui;
uniform bool central_aqui;
vec2 uv;                         // coordenades del mapa d'aquest fragment (les fa servir mapes.glsl)
vec3 pos_mon;
float tapat_des_de(vec3 p) { return tapat_aqui; }
bool central_des_de(vec3 p) { return central_aqui; }
#include "mapes.glsl"

const float PLANTA = 3.0;      // m (com dades/edificis.ALCADA_PLANTA_M)
const float K_CEL = 0.25;      // pes de la llum del cel i del Sol (els mateixos que terrain.frag)
const float K_SOL = 0.75;
const float ALBEDO_TERRA = 0.25; // part de la llum que reflecteix el terra (asfalt, formigo i vegetacio: ~0,1-0,35)
const vec3 BLAU_ESTIMADA = vec3(0.30, 0.50, 0.95);   // edificis amb l'altura estimada per plantes
const int ARREBOSSAT = 0, MAO = 1, PEDRA = 2, FORMIGO = 3, XAPA = 4, CORTINA = 5;
bool tipus_habitatge() { return tipus_part <= 1; }   // casa o bloc (dades/edificis.CASA, BLOC)

// 1 dins de l'interval [a, b] de x, amb una vora d'un pixel (antialias); w = amplada d'un pixel en unitats de x
float banda(float x, float a, float b, float w) {
    return smoothstep(a - w, a + w, x) - smoothstep(b - w, b + w, x);
}

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

// Facana amb textura: color (RGB) i normal en l'espai de la facana (x al llarg, y amunt, z cap a fora) i rugositat
struct Mostra { vec3 color; vec3 normal; float rugositat; };

Mostra mostra_facana(vec2 q) {
    Mostra m;
    if (capa < 0) {                                    // mur cortina (o sense textures): el color base, llis
        m.color = base; m.normal = vec3(0.0, 0.0, 1.0); m.rugositat = material == CORTINA ? 0.3 : 0.8;
        return m;
    }
    vec2 st = (q + desplacament) / mida_capa[capa];
    // de lluny (un pixel cobreix mes de 20 cm de facana) la textura ja es gairebe la seva mitjana (mipmaps): es fa servir el
    // color mitja, sense mapa de normals ni brillantor (molt mes barat; la majoria de pixels de facana des de l'aire)
    float m_px = max(fwidth(q.x), fwidth(q.y));
    float lluny = smoothstep(0.1, 0.2, m_px);
    if (lluny >= 1.0) {
        m.color = mitjana_capa[capa] * tint;
        if (material == ARREBOSSAT) m.color = mix(m.color, base2, banda(q.y, -10.0, 0.7, m_px));
        m.normal = vec3(0.0, 0.0, 1.0); m.rugositat = 1.0;
        return m;
    }
    vec3 c = mix(texture(tex_facana, vec3(st, float(capa))).rgb, mitjana_capa[capa], lluny);
    // taques grans: la mateixa imatge, 7 vegades mes gran i girada, llegida d'un mipmap de 32 x 32 (ja no s'hi
    // veuen les peces, nomes les variacions de to): modula el color i dissimula que la textura es repeteix
    vec2 st2 = mat2(0.6, -0.8, 0.8, 0.6) * st * 0.14 + 0.31;
    float macro = dot(textureLod(tex_facana, vec3(st2, float(capa)), 5.0).rgb, vec3(1.0)) /
                  max(dot(mitjana_capa[capa], vec3(1.0)), 0.05);
    m.color = c * tint * mix(1.0, macro, 0.35);
    if (material == ARREBOSSAT) m.color = mix(m.color, base2, banda(q.y, -10.0, 0.7, 0.02));  // socol de 70 cm
    if (material == XAPA) {
        // xapa: la foto te taques d'oxid massa marcades per a una nau; menys contrast i el nervi de 20 cm (el to
        // canvia amb l'angle de cada cara del grecat), que s'apaga quan fa menys d'un pixel
        float px_x = fwidth(q.x);
        float costella = 0.5 + 0.5 * sin(6.2831853 * q.x / 0.2);
        m.color = mix(base, m.color, 0.35) * mix(1.0, 0.86 + 0.18 * costella, 1.0 - smoothstep(0.04, 0.1, px_x));
    }
    vec3 nr = texture(tex_facana_nr, vec3(st, float(capa))).rgb;
    vec2 xy = (nr.rg * 2.0 - 1.0) * (1.0 - lluny);
    m.normal = vec3(xy, sqrt(max(1.0 - dot(xy, xy), 0.0)));
    m.rugositat = nr.b;
    return m;
}

// el vidre: el que hi ha dins (fosc) i el reflex de l'entorn segons l'angle (Fresnel de Schlick, n = 1,5)
vec3 color_vidre(vec3 n, vec3 v, vec3 llum, float fosc, float ombra) {
    vec3 r = reflect(-v, n);
    float amunt_r = dot(r, amunt);
    vec3 cel = mix(boira_v, boira_v * vec3(0.55, 0.70, 1.0), clamp(amunt_r, 0.0, 1.0));   // horitzo -> zenit
    vec3 terra = ALBEDO_TERRA * llum;
    vec3 entorn = amunt_r > 0.0 ? cel * max(llum_cel, 0.05) * 1.1 : terra;
    float f = 0.04 + 0.96 * pow(1.0 - max(dot(n, v), 0.0), 5.0);
    vec3 dins = vec3(0.03, 0.035, 0.04) * fosc * llum;
    float brill = pow(max(dot(r, sol_dir), 0.0), 600.0) * llum_sol * ombra * 6.0;           // el Sol reflectit
    return mix(dins, entorn, max(f, 0.2)) + brill * color_sol;
}

void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    llegir_part();
    vec3 n = normalize(cross(dFdx(pos_rel), dFdy(pos_rel)));
    if (dot(n, -pos_rel) < 0.0) n = -n;          // la cara que es veu mira cap a la camera
    vec2 px = max(fwidth(uv_facana), vec2(1e-4)); // metres per pixel (abans de cap branca)
    vec2 merc_dx = dFdx(merc_rel), merc_dy = dFdy(merc_rel);
    vec3 v_cam = normalize(-pos_rel);
    // direccio en que creix u a la facana (per al mapa de normals); les derivades, fora de cap branca
    vec3 t_fac = normalize(cross(amunt, n) + vec3(1e-6));
    if (dot(dFdx(pos_rel), t_fac) * dFdx(uv_facana.x) + dot(dFdy(pos_rel), t_fac) * dFdy(uv_facana.x) < 0.0)
        t_fac = -t_fac;
    float vidre = 0.0, marc = 0.0, persiana = 0.0, fosc = 1.0;   // finestra: vidre, marc i persiana (0..1)
    if (llargada >= 0.0) {
        float u = uv_facana.x, v = uv_facana.y;
        float pas = finestres.x;
        float n_fin = floor(llargada / pas);
        if (n_fin >= 1.0 && v > 0.0 && v < plantes * PLANTA - 0.4) {
            float planta = floor(v / PLANTA), y = mod(v, PLANTA);
            bool pb = planta < 0.5;
            float amp = pb ? finestres_pb.x : finestres.y;
            vec2 fy = pb ? finestres_pb.yz : finestres.zw;
            float mitjana = (amp / pas) * (fy.y - fy.x) / PLANTA;
            float lluny = smoothstep(0.12, 0.35, max(px.x, px.y));      // finestra de menys de ~2 pixels: la mitjana
            float local = u - 0.5 * (llargada - n_fin * pas);
            float dins_x = step(0.0, local) * step(local, n_fin * pas);
            float x = mod(local, pas);
            float a0 = 0.5 * (pas - amp);
            float forat = banda(x, a0, a0 + amp, px.x) * banda(y, fy.x, fy.y, px.y) * dins_x;
            float k = hash21(vec2(floor(local / pas), planta) + 17.0 * llavor);    // cada finestra, diferent
            float m_marc = material == CORTINA ? 0.05 : 0.07;
            float vid = banda(x, a0 + m_marc, a0 + amp - m_marc, px.x) * banda(y, fy.x + m_marc, fy.y - m_marc, px.y);
            // persiana enrotllable (habitatges): baixada una part de l'alcada, diferent a cada finestra
            float baixada = (tipus_habitatge() && !pb) ? max(0.0, k * 1.3 - 0.35) : 0.0;
            float pers = step(fy.y - m_marc - baixada * (fy.y - fy.x - 2.0 * m_marc), y);
            vidre = mix(forat * vid * (1.0 - pers), mitjana * dins_x * 0.8, lluny);
            persiana = mix(forat * vid * pers, mitjana * dins_x * 0.15, lluny);
            marc = mix(forat * (1.0 - vid), mitjana * dins_x * 0.05, lluny);
            fosc = 0.6 + 0.8 * hash21(vec2(k, 3.0));
        }
    }
    float ombra = factor_ombra(pos_rel, n, sol_dir);
    float lambert = max(dot(n, sol_dir), 0.0) * ombra;
    vec3 cel = K_CEL * llum_cel * color_amb, sol = K_SOL * llum_sol * color_sol;
    vec3 llum = cel + lambert * sol;             // cobertes: com el terra (terrain.frag), que te el mateix color de foto
    if (llargada >= 0.0) {
        // Facanes. Una paret vertical nomes veu la meitat del cel, pero l'altra meitat es el terra, que reflecteix
        // la llum que rep (albedo ALBEDO_TERRA): a l'ombra, la paret no queda negra.
        float nu = dot(n, amunt);
        vec3 terra = ALBEDO_TERRA * (cel + max(dot(sol_dir, amunt), 0.0) * sol);
        llum = (0.5 + 0.5 * nu) * cel + lambert * sol + (0.5 - 0.5 * nu) * terra;
        // Contrast entre cares com el veu l'ull: la llum es lineal, pero la pantalla codifica els colors en sRGB
        // (gamma ~2,2). Es codifica la proporcio respecte d'una cara de cara al Sol; la cara mes il·luminada no
        // canvia, i les de l'ombra passen de ~1/4 a ~1/2 (aproximacio il·lustrativa, com a les fotos).
        vec3 maxim = max(cel + sol, vec3(1e-4));
        llum = maxim * pow(clamp(llum / maxim, 0.0, 1.0), vec3(1.0 / 2.2));
    }
    vec3 color;
    if (mesurada < 0.5) {
        color = (llargada >= 0.0 ? BLAU_ESTIMADA : 0.8 * BLAU_ESTIMADA) * llum;   // la coberta, una mica mes fosca
    } else if (llargada >= 0.0) {
        // facana: la normal del mapa, de l'espai de la facana (t al llarg, amunt, n cap a fora) a l'escena
        Mostra m = mostra_facana(uv_facana);
        vec3 nm = normalize(m.normal.x * t_fac + m.normal.y * amunt + m.normal.z * n);
        float lamb_m = max(dot(nm, sol_dir), 0.0) * step(0.0, dot(n, sol_dir)) * ombra;
        float nu = dot(nm, amunt);
        vec3 terra = ALBEDO_TERRA * (cel + max(dot(sol_dir, amunt), 0.0) * sol);
        vec3 l2 = (0.5 + 0.5 * nu) * cel + lamb_m * sol + (0.5 - 0.5 * nu) * terra;
        vec3 maxim = max(cel + sol, vec3(1e-4));
        l2 = maxim * pow(clamp(l2 / maxim, 0.0, 1.0), vec3(1.0 / 2.2));
        // brillantor segons la rugositat (Blinn-Phong): el formigo i la xapa en tenen una mica, l'arrebossat gens
        float llis = (1.0 - m.rugositat) * (1.0 - m.rugositat);
        float spec = pow(max(dot(nm, normalize(sol_dir + v_cam)), 0.0), mix(8.0, 90.0, llis)) * llis * 0.35 * lamb_m;
        color = m.color * l2 + spec * sol;
        if (material == CORTINA) {
            // mur cortina: tot vidre, amb els muntants (base2) cada pas de finestra
            float muntant = 1.0 - banda(mod(uv_facana.x, finestres.x), 0.06, finestres.x - 0.06, px.x) *
                                  banda(mod(uv_facana.y, PLANTA), 0.1, PLANTA - 0.1, px.y);
            color = mix(color_vidre(n, v_cam, cel + sol, 0.8, ombra), base2 * llum, muntant);
        }
    } else {
        vec4 foto = color_mosaic(merc_rel, merc_dx, merc_dy);
        color = mix(coberta_provisional, foto.rgb, foto.a) * llum;
    }
    if (llargada >= 0.0) {             // finestres (tambe a les facanes blaves: les plantes son del Catastro)
        vec3 c_marc = (material == CORTINA ? base2 : vec3(0.82, 0.80, 0.76)) * llum;
        vec3 c_pers = mix(vec3(0.78, 0.74, 0.66), vec3(0.62, 0.60, 0.57), fract(llavor * 7.0)) * llum;
        color = mix(color, c_marc, marc);
        color = mix(color, c_pers, persiana);
        // vidre: de prop, el reflex segons l'angle; de lluny (finestres de menys d'un parell de pixels), un color mitja
        vec3 c_vidre = max(px.x, px.y) > 0.35 ? mix(vec3(0.035) * llum, boira_v * max(llum_cel, 0.05), 0.3)
                                              : color_vidre(n, v_cam, cel + sol, fosc, ombra);
        color = mix(color, c_vidre, vidre);
    }
    color = mix(boira_v, color, visibilitat);
    // mapa als terrats: nomes a les cobertes (cares horitzontals), despres de la llum i de la boira com al terreny
    if ((mapa == 2 || mapa == 3) && llargada < 0.0) {
        pos_mon = pos_rel;
        uv = (a_utm * (pos_rel + cam_menys_origen)).xy;
        vec4 mv = color_mapa(tapat_aqui, 0.0, amunt);
        color = mix(color, mv.rgb * (0.85 + 0.15 * max(dot(n, amunt), 0.0)), mv.a);
    }
    fragColor = vec4(color, 1.0);
}
