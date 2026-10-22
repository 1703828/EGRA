#version 330
layout (location = 0) out vec4 fragColor;
in vec2 uv;
in vec3 pos_mon;
in float base;
in vec3 amunt;
in vec3 tx;
in float logz;
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
uniform bool hi_ha_forat;       // la zona de detall (Picos) es dibuixa a part: aqui no
uniform vec4 forat;             // rectangle (u0, v0, u1, v1) en UV d'aquest terreny

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

void main() {
#ifdef PROFUNDITAT_LOG
    gl_FragDepth = log2(logz) * coef_log * 0.5;   // nomes al mode globus (main.py)
#endif
    float d = texture(tex_costa, uv).r;          // km a la costa (mar > 0, terra < 0)
    vec3 sol = normalize(sun_dir);
    float llum_sol_aqui = llum_sol, llum_cel_aqui = llum_cel;
    if (globus) {
        // el mar i les zones sense dades (Portugal, Franca) no es dibuixen: es veu el globus
        if (d > 0.0) discard;
        if (hi_ha_forat && uv.x > forat.x && uv.x < forat.z && uv.y > forat.y && uv.y < forat.w) discard;
        // llum del Sol i del cel en aquest punt: segons l'altura del Sol aqui i la part que en tapa la Lluna
        sol = normalize(sol_rel - pos_mon);
        float elev = dot(normalize(amunt), sol);                       // sinus de l'elevacio del Sol
        float visible = 1.0 - tapat_des_de(pos_mon);
        llum_sol_aqui = visible * smoothstep(-0.0175, 0.0175, elev);   // entre -1 i +1 graus
        float dia = smoothstep(-0.105, 0.07, elev);                    // crepuscle: de -6 a +4 graus
        llum_cel_aqui = max(0.03, dia * (0.04 + 0.96 * pow(visible, 0.4)));
    }
    // aigua: mes clara a prop de la costa, mes fosca mar endins; menys llum amb el Sol baix
    vec3 aigua = mix(vec3(0.16, 0.42, 0.58), vec3(0.04, 0.14, 0.32), 1.0 - exp(-max(d, 0.0) / escala_mar));
    aigua *= (0.5 + 0.5 * max(globus ? dot(sol, normalize(amunt)) : sol.y, 0.0)) * llum_cel_aqui;
    vec3 color;

    if (es_faldilla) {
        // normal plana de la paret a partir de les derivades de la posicio; girada cap a la camera
        vec3 n = normalize(cross(dFdx(pos_mon), dFdy(pos_mon)));
        if (dot(n, cam_pos - pos_mon) < 0.0) n = -n;
        vec3 paret = d > 0.0 ? aigua * 0.6 : mix(vec3(0.45, 0.35, 0.25), vec3(0.22, 0.16, 0.11), base);
        color = paret * (0.35 * llum_cel_aqui + 0.65 * llum_sol_aqui * max(dot(n, sol), 0.0));
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
        vec3 terra = rampa(height) * (0.25 * llum_cel_aqui + 0.75 * llum_sol_aqui * max(dot(normal, sol), 0.0));
        // costa: la distancia filtrada es suau, aixi el pas terra -> mar no fa escales.
        // fwidth = quant canvia d en un pixel de pantalla -> transicio d'1 pixel (antialias)
        float w = max(fwidth(d), 1e-6);
        color = mix(terra, aigua, smoothstep(-w, w, d));

        // vores de les zones de detall: linies de ~2 pixels dibuixades sobre el relleu
        for (int i = 0; i < n_zones; i++)
            color = mix(vec3(1.0, 0.25, 0.10), color, smoothstep(1.0, 2.0, pixels_a_vora(zones[i])));

        // overlay de l'eclipsi
        vec4 o = color_overlay();
        color = mix(color, o.rgb, opacitat * o.a);
        // limits de la franja de totalitat: on la mascara (filtrada, suau) passa per 0.5
        if (limits_totalitat) {
            float b = texture(tex_eclipsi, uv).b;
            float px = abs(b - 0.5) / max(fwidth(b), 1e-6);
            color = mix(vec3(1.0), color, smoothstep(1.0, 2.0, px));
        }
    }

    // boira exponencial quadratica segons la distancia a la camera (a partir d'inici_boira)
    float f = exp(-pow(max(length(pos_mon - cam_pos) - inici_boira, 0.0) * densitat_boira, 2.0));
    fragColor = vec4(mix(color_cel, color, f), 1.0);
}
