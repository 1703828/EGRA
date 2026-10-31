#version 330
layout (location = 0) out vec4 fragColor;
in vec2 uv;
in vec3 pos_mon;
in float base;
in vec3 amunt;
in vec3 tx;
in float logz;
in vec3 color_sol_v;    // color de la llum del Sol i del cel (terrain.vert)
in vec3 color_amb_v;
in vec3 boira_v;        // color de la boira (terrain.vert)
in vec2 merc_rel;       // Mercator relativa a la camera (mosaic d'imatges)
in float dens_boira;    // mode globus: densitat de la boira en el cami fins aqui (terrain.vert)
uniform sampler2D tex_altitud;
uniform sampler2D tex_gradient;
uniform sampler2D tex_costa;
uniform float exaggeration;
uniform vec3 sun_dir;
uniform vec3 cam_pos;
uniform vec3 color_cel;
uniform float llum_sol;         // fraccio del Sol que no tapa la Lluna (1 = sense eclipsi)
uniform float llum_cel;         // brillantor del cel (llum ambient): baixa a la totalitat i de nit
uniform float densitat_boira;   // 1/km
uniform float inici_boira;      // km: fins a aquesta distancia no hi ha boira
uniform float escala_mar;       // km
uniform bool es_faldilla;
uniform vec4 zones[4];          // rectangles de les zones de detall en UV (u0, v0, u1, v1)
uniform int n_zones;
// eclipsi
uniform sampler2D tex_eclipsi;  // RGBA: enfosquiment, durada (s), franja (0/1), valid (0/1)
uniform sampler2D tex_ombres;   // classe d'ombres del CNIG / 255 (NEAREST); 255 = sense dades
uniform int overlay;            // 0 cap, 1 enfosquiment, 2 durada, 3 ombres
uniform float opacitat;
uniform bool limits_totalitat;
uniform float enfosquiment_min;
uniform vec3 colors_enfosquiment[4];
uniform vec3 color_totalitat;
uniform float durada_min;
uniform float durada_max;
uniform vec3 colors_durada[5];
uniform vec3 colors_ombres[4];
// mode globus (main.py): llum i ombra de la Lluna calculades per a cada punt de la superficie
uniform bool globus;
uniform float coef_log;         // profunditat logaritmica (0 = normal)
uniform vec3 sol_rel;           // posicio del Sol relativa a la camera (km)
uniform vec3 lluna_rel;         // posicio de la Lluna relativa a la camera (km)
uniform float radi_sol;         // km
uniform float radi_lluna;       // km
uniform vec4 forats[4];         // rectangles (u0, v0, u1, v1) en UV on no es dibuixa: hi ha un
uniform int n_forats;           //   nivell mes detallat (una zona de 5 m o el pegat de l'observador)
uniform bool dibuixar_mar;      // el mar del fitxer es dibuixa a 0 m (zones de 5 m de la costa)
#ifdef PROFUNDITAT_LOG
// el mar de les zones de detall es pinta com el globus (mateixa textura i mateixa llum que terra.frag),
// perque a la vora de la zona no es noti on acaba
uniform sampler2D tex_terra;    // textura de la Terra (NASA Blue Marble)
uniform vec3 cam_ecef;          // posicio de la camera (ECEF, km; float32 n'hi ha prou per a la textura)
uniform float atmosfera;        // 1 dins de l'atmosfera, 0 a l'espai (el contorn blau, nomes des de fora)
uniform bool ressaltar_ombra;
// ombres del relleu (shadow mapping, basecode/ombres_relleu.py)
uniform sampler2DShadow tex_ombra;  // profunditat vista des del Sol; compara per maquinari
uniform bool ombres_relleu;         // aquest terreny rep ombres (la zona de 5 m)
uniform mat4 m_llum;                // posicio relativa a l'ancora -> coordenades de clip de la llum
uniform vec3 cam_menys_ancora;      // camera - ancora (km)
uniform float desplacament_normal;  // km: el punt es mira una mica fora de la superficie (acne)
uniform float biaix_profunditat;    // i una mica mes a prop del Sol (unitats de profunditat)
uniform bool depuracio_ombra;       // depuracio (scripts): el color es el factor d'ombra del relleu
// ortofoto del PNOA (basecode/terrain.py, posar_ortofoto): color base del terra en lloc de la rampa
uniform bool usar_orto;
uniform sampler2D tex_orto;          // tota la zona, mateixes UV que el terreny (graella del MDT)
uniform sampler2D tex_orto_detall;   // detall (0,5 m) al voltant del punt d'observacio
// mapa de visibilitat de l'eclipsi (dades/visibilitat.py, objectiu O3); mateixes UV que el relleu, NEAREST.
// R, G: primer i darrer moment amb el centre del Sol per sobre de l'horitzo (s des de l'inici de les efemerides);
// B: marge al maxim (centesimes de grau + 32768); A: segons de fase central visibles x 10. 65535: sense valor.
uniform sampler2D tex_visibilitat;
uniform bool hi_ha_mapa;             // el del terreny (n'hi pot haver nomes el de detall)
uniform sampler2D tex_vis_detall;    // el mateix a 1 m amb el LiDAR, dins de rect_vis_detall (UV del terreny)
uniform bool hi_ha_vis_detall;
uniform vec4 rect_vis_detall;
uniform int mapa;                    // 0 cap, 1 al maxim, 2 totalitat visible, 3 instant actual
uniform float hora_s;                // l'hora de la barra, en s des de l'inici de les efemerides
uniform float radi_sol_graus;
uniform float durada_central_max;    // s
uniform vec3 colors_central[5];
uniform vec3 color_tapat_relleu;
uniform bool hi_ha_detall;
uniform vec4 rect_detall;            // rectangle del detall en UV del terreny (u0, v0, u1, v1)
// atmosfera (dades/atmosfera.py): la boira es del color del cel a l'horitzo segons la direccio (terrain.vert)
#include "mosaic.glsl"
#endif

// rampa hipsometrica absoluta: la mateixa altitud te el mateix color a tots els fitxers
const float COTES[6] = float[](0.0, 200.0, 600.0, 1200.0, 2000.0, 3000.0);
const vec3 COLORS[6] = vec3[](
    vec3(0.17, 0.40, 0.20),   //    0 m: verd fosc de costa
    vec3(0.33, 0.54, 0.25),   //  200 m: verd
    vec3(0.62, 0.66, 0.38),   //  600 m: verd groguenc (meseta)
    vec3(0.62, 0.50, 0.33),   // 1200 m: marro
    vec3(0.56, 0.52, 0.49),   // 2000 m: roca grisa
    vec3(0.96, 0.96, 0.97));  // 3000 m: neu
vec3 rampa(float h) {
    for (int i = 1; i < 6; i++)
        if (h < COTES[i])
            return mix(COLORS[i - 1], COLORS[i], clamp((h - COTES[i - 1]) / (COTES[i] - COTES[i - 1]), 0.0, 1.0));
    return COLORS[5];
}

// distancia en pixels de pantalla a la vora del rectangle r (molt gran si es lluny)
float pixels_a_vora(vec4 r) {
    vec2 px = max(fwidth(uv), vec2(1e-7));   // quant UV hi ha en un pixel
    float dx = min(abs(uv.x - r.x), abs(uv.x - r.z)) / px.x;
    float dy = min(abs(uv.y - r.y), abs(uv.y - r.w)) / px.y;
    bool dins_x = uv.x >= r.x && uv.x <= r.z;
    bool dins_y = uv.y >= r.y && uv.y <= r.w;
    return min(dins_y ? dx : 1e9, dins_x ? dy : 1e9);
}

// color (rgb) i opacitat propia (a) de l'overlay actiu en aquest punt
vec4 color_overlay() {
    vec4 e = texture(tex_eclipsi, uv);
    float franja = smoothstep(0.4, 0.6, e.b);
    if (overlay == 1) {
        // rampa continua de enfosquiment_min a 1 en 3 trams; la totalitat, d'un color a part
        float t = clamp((e.r - enfosquiment_min) / (1.0 - enfosquiment_min), 0.0, 1.0) * 3.0;
        int i = min(int(t), 2);
        vec3 c = mix(colors_enfosquiment[i], colors_enfosquiment[i + 1], t - float(i));
        return vec4(mix(c, color_totalitat, franja), e.a);
    }
    if (overlay == 2) {
        float t = clamp((e.g - durada_min) / (durada_max - durada_min), 0.0, 1.0) * 4.0;  // 5 colors, 4 trams
        int i = min(int(t), 3);
        vec3 c = mix(colors_durada[i], colors_durada[i + 1], t - float(i));
        // corbes de durada cada 10 s (com les de la capa durtot del GeoPackage)
        float l = e.g / 10.0;
        float px = abs(fract(l - 0.5) - 0.5) / max(fwidth(l), 1e-6);
        c *= mix(0.45, 1.0, smoothstep(0.5, 1.5, px));
        return vec4(c, franja * e.a);
    }
    if (overlay == 3) {
        int classe = int(texture(tex_ombres, uv).r * 255.0 + 0.5);
        if (classe > 3) return vec4(0.0);  // sense dades: transparent
        return vec4(colors_ombres[classe], 1.0);
    }
    return vec4(0.0);
}

// Part del disc del Sol (radi r1) tapada per la Lluna (radi r2) amb els centres a d (radians).
// La mateixa formula que dades/model_eclipsi.py (area_tapada).
float area_tapada(float d, float r1, float r2) {
    if (d >= r1 + r2) return 0.0;
    if (d <= abs(r2 - r1)) return min(1.0, (r2 * r2) / (r1 * r1));
    float a1 = r1 * r1 * acos(clamp((d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1), -1.0, 1.0));
    float a2 = r2 * r2 * acos(clamp((d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2), -1.0, 1.0));
    float a3 = 0.5 * sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0));
    return (a1 + a2 - a3) / (3.14159265 * r1 * r1);
}

// Quina part del Sol tapa la Lluna vista des del punt p: 1 a l'ombra (umbra), entre 0 i 1 a la
// penombra i 0 fora. Es aixo el que dibuixa l'ombra de la Lluna sobre la Terra.
float tapat_des_de(vec3 p) {
    vec3 s = sol_rel - p, l = lluna_rel - p;
    float rs = asin(radi_sol / length(s)), rl = asin(radi_lluna / length(l));
    float d = 2.0 * asin(min(1.0, 0.5 * length(normalize(s) - normalize(l))));
    return area_tapada(d, rs, rl);
}

#ifdef PROFUNDITAT_LOG
// Color del globus en aquest punt de la superficie (el mateix calcul que terra.frag)
vec3 color_globus(vec3 up, vec3 sol, float visible) {
    vec3 e = cam_ecef + pos_mon;
    float lon = atan(e.y, e.x);
    float lat = atan(e.z, length(e.xy) * (1.0 - 0.00669438));   // latitud geodesica a l'altura 0
    vec3 c = texture(tex_terra, vec2(lon / 6.2831853 + 0.5, 0.5 - lat / 3.14159265)).rgb;
    float cos_sol = dot(up, sol);
    float dia = smoothstep(-0.10, 0.10, cos_sol);
    c *= 0.03 + dia * visible * (0.25 * color_amb_v + 0.95 * max(cos_sol, 0.0) * color_sol_v);
    float vora = pow(1.0 - max(dot(up, normalize(-pos_mon)), 0.0), 3.0);
    return c + vec3(0.30, 0.50, 1.00) * vora * 0.6 * dia * (1.0 - atmosfera);
}
#endif

#ifdef PROFUNDITAT_LOG
// Ombra del relleu: 1 si el Sol arriba a aquest punt, 0 si una muntanya el tapa (entremig a la vora).
// El punt es passa a l'espai de la llum i la seva distancia al Sol es compara amb la del mapa. Per evitar
// que la superficie s'ombregi a si mateixa ("acne": el mapa te texels de ~10 m i amb el Sol baix cada un
// cobreix un tros inclinat de terreny), el punt es desplaca una mica en la direccio de la normal i se li
// resta un marge petit. 3 x 3 lectures (cada una ja barreja 2 x 2 texels) suavitzen la vora.
float llum_relleu(vec3 normal) {
    if (!ombres_relleu) return 1.0;
    vec4 q = m_llum * vec4(pos_mon + cam_menys_ancora + normal * desplacament_normal, 1.0);
    vec3 s = q.xyz / q.w * 0.5 + 0.5;
    if (any(lessThan(s, vec3(0.0))) || any(greaterThan(s, vec3(1.0)))) return 1.0;   // fora del mapa
    vec2 texel = 1.0 / vec2(textureSize(tex_ombra, 0));
    float llum = 0.0;
    for (int i = -1; i <= 1; i++)
        for (int j = -1; j <= 1; j++)
            llum += texture(tex_ombra, vec3(s.xy + vec2(i, j) * texel, s.z - biaix_profunditat));
    return llum / 9.0;
}

// Ressaltat didactic de l'ombra (opcional, desactivat per defecte): linies on la Lluna tapa el 25, el 50
// i el 75 % del Sol (groc) i el limit de la totalitat (lila), nomes on el Sol es sobre l'horitzo (pes).
// Nomes dibuixa linies: no canvia ni la mida ni la foscor de l'ombra. df = fwidth(f), calculat abans de
// qualsevol discard (despres, les derivades no estan definides als pixels veins descartats).
vec3 ressaltar(vec3 c, float f, float df, float pes) {
    float g = f * 4.0;
    float px = abs(fract(g - 0.5) - 0.5) / max(4.0 * df, 1e-6);
    vec3 r = c;
    if (g > 0.5 && g < 3.5)
        r = mix(vec3(1.0, 0.8, 0.2), r, smoothstep(0.5, 1.5, px));
    float pt = abs(f - 0.999) / max(df, 1e-6);
    r = mix(vec3(1.0, 0.3, 1.0), r, smoothstep(1.0, 2.5, pt));
    return mix(c, r, pes);
}
#endif

#ifdef PROFUNDITAT_LOG
// fase central (totalitat o anularitat) vista des del punt p: un disc sencer dins de l'altre
bool central_des_de(vec3 p) {
    vec3 s = sol_rel - p, l = lluna_rel - p;
    float rs = asin(radi_sol / length(s)), rl = asin(radi_lluna / length(l));
    float d = 2.0 * asin(min(1.0, 0.5 * length(normalize(s) - normalize(l))));
    return d < abs(rl - rs);
}

// color (rgb) i opacitat (a) del mapa de visibilitat en aquest punt; tapat = part del Sol que tapa la Lluna aqui
vec4 color_mapa(float tapat) {
    vec2 td = (uv - rect_vis_detall.xy) / (rect_vis_detall.zw - rect_vis_detall.xy);
    bool detall = hi_ha_vis_detall && all(greaterThanEqual(td, vec2(0.0))) && all(lessThanEqual(td, vec2(1.0)));
    if (!detall && !hi_ha_mapa) return vec4(0.0);
    vec4 v = (detall ? texture(tex_vis_detall, td) : texture(tex_visibilitat, uv)) * 65535.0;
    if (mapa == 1) {
        if (v.b < 0.5) return vec4(0.0);                // sense eclipsi
        float m = (v.b - 32768.0) / 100.0;              // marge (graus)
        int classe = m > radi_sol_graus ? 3 : (m > 0.0 ? 2 : (m > -radi_sol_graus ? 1 : 0));
        return vec4(colors_ombres[classe], 0.8);
    }
    if (mapa == 2) {
        if (v.a > 65534.5) return vec4(0.0);            // fora de la franja central
        float t = clamp(v.a / 10.0 / durada_central_max, 0.0, 1.0) * 4.0;
        int i = min(int(t), 3);
        return vec4(mix(colors_central[i], colors_central[i + 1], t - float(i)), 0.85);
    }
    if (mapa == 3) {
        if (tapat <= 0.0) return vec4(0.0);             // aqui no hi ha eclipsi en aquest instant
        if (v.r > 65534.5 || hora_s < v.r || hora_s > v.g) return vec4(color_tapat_relleu, 0.85);   // el relleu el tapa
        if (central_des_de(pos_mon)) return vec4(color_totalitat, 0.85);
        float t = clamp(tapat, 0.0, 1.0) * 3.0;
        int i = min(int(t), 2);
        return vec4(mix(colors_enfosquiment[i], colors_enfosquiment[i + 1], t - float(i)), 0.75);
    }
    return vec4(0.0);
}
#endif

void main() {
#ifdef PROFUNDITAT_LOG
    gl_FragDepth = log2(logz) * coef_log * 0.5;   // nomes al mode globus (main.py)
    float tapat = tapat_des_de(pos_mon), d_tapat = fwidth(tapat);   // abans de cap discard
    vec2 merc_dx = dFdx(merc_rel), merc_dy = dFdy(merc_rel);
#endif
    float d = texture(tex_costa, uv).r;          // km a la costa (mar > 0, terra < 0)
    vec3 sol = normalize(sun_dir);
    float llum_sol_aqui = llum_sol, llum_cel_aqui = llum_cel;
    vec3 color_sol = vec3(1.0), color_amb = vec3(1.0), boira = color_cel;   // mode pla: llum blanca
    if (globus) {
        // el mar i les zones sense dades (Portugal, Franca) no es dibuixen: es veu el globus
        // (excepte a les zones de detall de la costa, que dibuixen el mar a 0 m)
        if (d > 0.0 && !dibuixar_mar) discard;
        for (int i = 0; i < n_forats; i++)
            if (uv.x > forats[i].x && uv.x < forats[i].z && uv.y > forats[i].y && uv.y < forats[i].w) discard;
        // llum del Sol i del cel en aquest punt: segons l'altura del Sol aqui i la part que en tapa la Lluna
        sol = normalize(sol_rel - pos_mon);
        float elev = dot(normalize(amunt), sol);                       // sinus de l'elevacio del Sol
        float visible = 1.0 - tapat_des_de(pos_mon);
        llum_sol_aqui = visible * smoothstep(-0.0175, 0.0175, elev);   // entre -1 i +1 graus
        float dia = smoothstep(-0.105, 0.07, elev);                    // crepuscle: de -6 a +4 graus
        llum_cel_aqui = max(0.03, dia * (0.04 + 0.96 * pow(visible, 0.4)));
#ifdef PROFUNDITAT_LOG
        color_sol = color_sol_v;
        color_amb = color_amb_v;
        boira = boira_v;
#endif
    }
    // aigua: mes clara a prop de la costa, mes fosca mar endins; menys llum amb el Sol baix
    vec3 aigua = mix(vec3(0.16, 0.42, 0.58), vec3(0.04, 0.14, 0.32), 1.0 - exp(-max(d, 0.0) / escala_mar));
    aigua *= (0.5 + 0.5 * max(globus ? dot(sol, normalize(amunt)) : sol.y, 0.0)) * llum_cel_aqui * color_amb;
#ifdef PROFUNDITAT_LOG
    if (dibuixar_mar) {
        // les parets (faldilles) sobre el mar no es dibuixen: a la vora de la zona hi ha el mar del globus
        if (es_faldilla && d > 0.0) discard;
        // a prop de la vora de la zona, el color del globus; cap a dins, el de l'aigua (la textura del
        // globus te pixels de 20 km i a la costa barreja terra i mar)
        float a_vora = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
        aigua = mix(color_globus(normalize(amunt), sol, 1.0 - tapat_des_de(pos_mon)), aigua,
                    smoothstep(0.02, 0.25, a_vora));
    }
#endif
    vec3 color;

    if (es_faldilla) {
        // normal plana de la paret a partir de les derivades de la posicio; girada cap a la camera
        vec3 n = normalize(cross(dFdx(pos_mon), dFdy(pos_mon)));
        if (dot(n, cam_pos - pos_mon) < 0.0) n = -n;
        vec3 paret = d > 0.0 ? aigua * 0.6 : mix(vec3(0.45, 0.35, 0.25), vec3(0.22, 0.16, 0.11), base);
        color = paret * (0.35 * llum_cel_aqui * color_amb + 0.65 * llum_sol_aqui * max(dot(n, sol), 0.0) * color_sol);
    } else {
        float height = texture(tex_altitud, uv).r;
        vec2 g = texture(tex_gradient, uv).rg;   // (dh/dx, dh/dz) a resolucio completa
        // superficie y = k*h(x,z) -> normal = (-k*dh/dx, 1, -k*dh/dz), exacta per a qualsevol k.
        // Al globus, els eixos x (columnes), y (amunt) i z (files, cap al sud) son els del lloc.
        vec3 normal;
        if (globus) {
            vec3 up = normalize(amunt), ex = normalize(tx), ez = normalize(cross(ex, up));
            normal = normalize(-exaggeration * g.x * ex + up - exaggeration * g.y * ez);
        } else {
            normal = normalize(vec3(-exaggeration * g.x, 1.0, -exaggeration * g.y));
        }
        float relleu = 1.0;     // ombra del relleu: nomes la llum directa del Sol, no la del cel
#ifdef PROFUNDITAT_LOG
        relleu = llum_relleu(normal);
#endif
        vec3 base = rampa(height);
#ifdef PROFUNDITAT_LOG
        if (usar_orto) {
            // fotografia aeria (dada real); a la vora del detall (3 % del costat) es passa suaument a la de la
            // zona: es la mateixa foto, nomes canvia la resolucio
            // (les dues textures es llegeixen sempre: dins d'un if que depen del pixel, el nivell de mipmap
            // no estaria ben definit a la vora)
            vec2 t = (uv - rect_detall.xy) / (rect_detall.zw - rect_detall.xy);
            vec3 detall = texture(tex_orto_detall, clamp(t, 0.0, 1.0)).rgb;
            float w = hi_ha_detall ? smoothstep(0.0, 0.03, min(min(t.x, 1.0 - t.x), min(t.y, 1.0 - t.y))) : 0.0;
            base = mix(texture(tex_orto, uv).rgb, detall, w);
        }
#endif
        vec3 llum = 0.25 * llum_cel_aqui * color_amb + 0.75 * llum_sol_aqui * relleu * max(dot(normal, sol), 0.0) * color_sol;
        vec3 terra = base * llum;
#ifdef PROFUNDITAT_LOG
        if (depuracio_ombra) { fragColor = vec4(vec3(relleu), 1.0); return; }
#endif
        // costa: la distancia filtrada es suau, aixi el pas terra -> mar no fa escales.
        // fwidth = quant canvia d en un pixel de pantalla -> transicio d'1 pixel (antialias)
        float w = max(fwidth(d), 1e-6);
        color = mix(terra, aigua, smoothstep(-w, w, d));
#ifdef PROFUNDITAT_LOG
        // fotografia aeria (mosaic): a terra i al mar de la costa, en lloc de la rampa i de l'aigua dibuixada; on
        // encara no hi es (s'esta baixant), el que hi havia
        vec4 foto = color_mosaic(merc_rel, merc_dx, merc_dy);
        color = mix(color, foto.rgb * llum, foto.a);
#endif

        // vores de les zones de detall: linies de ~2 pixels dibuixades sobre el relleu
        for (int i = 0; i < n_zones; i++)
            color = mix(vec3(1.0, 0.25, 0.10), color, smoothstep(1.0, 2.0, pixels_a_vora(zones[i])));

        // overlay de l'eclipsi
        vec4 o = color_overlay();
        color = mix(color, o.rgb, opacitat * o.a);
#ifdef PROFUNDITAT_LOG
        // mapa de visibilitat (nomes a terra)
        if (mapa != 0) {
            vec4 mv = color_mapa(tapat);
            color = mix(color, mv.rgb, mv.a * (1.0 - smoothstep(-w, w, d)));
        }
#endif
        // limits de la franja de totalitat: on la mascara (filtrada, suau) passa per 0.5
        if (limits_totalitat) {
            float b = texture(tex_eclipsi, uv).b;
            float px = abs(b - 0.5) / max(fwidth(b), 1e-6);
            color = mix(vec3(1.0), color, smoothstep(1.0, 2.0, px));
        }
    }

    // boira exponencial quadratica segons la distancia a la camera (a partir d'inici_boira)
    float dist_boira = max(length(pos_mon - cam_pos) - inici_boira, 0.0);
    float f = globus ? exp(-dist_boira * dens_boira)                     // extincio (Beer-Lambert)
                     : exp(-pow(dist_boira * densitat_boira, 2.0));      // mode pla: com sempre
    color = mix(boira, color, f);
#ifdef PROFUNDITAT_LOG
    if (ressaltar_ombra)
        color = ressaltar(color, tapat, d_tapat, smoothstep(-0.03, 0.0, dot(normalize(amunt), normalize(sol_rel - pos_mon))));
#endif
    fragColor = vec4(color, 1.0);
}
