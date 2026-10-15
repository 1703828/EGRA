#version 330
layout (location = 0) out vec4 fragColor;
in vec2 uv;
in vec3 pos_mon;
in float base;
uniform sampler2D tex_altitud;
uniform sampler2D tex_gradient;
uniform sampler2D tex_costa;
uniform float exaggeration;
uniform vec3 sun_dir;
uniform vec3 cam_pos;
uniform vec3 color_cel;
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

void main() {
    vec3 sol = normalize(sun_dir);
    float d = texture(tex_costa, uv).r;          // km a la costa (mar > 0, terra < 0)
    // aigua: mes clara a prop de la costa, mes fosca mar endins; menys llum amb el Sol baix
    vec3 aigua = mix(vec3(0.16, 0.42, 0.58), vec3(0.04, 0.14, 0.32), 1.0 - exp(-max(d, 0.0) / escala_mar));
    aigua *= 0.5 + 0.5 * max(sol.y, 0.0);
    vec3 color;

    if (es_faldilla) {
        // normal plana de la paret a partir de les derivades de la posicio; girada cap a la camera
        vec3 n = normalize(cross(dFdx(pos_mon), dFdy(pos_mon)));
        if (dot(n, cam_pos - pos_mon) < 0.0) n = -n;
        vec3 paret = d > 0.0 ? aigua * 0.6 : mix(vec3(0.45, 0.35, 0.25), vec3(0.22, 0.16, 0.11), base);
        color = paret * (0.35 + 0.65 * max(dot(n, sol), 0.0));
    } else {
        float height = texture(tex_altitud, uv).r;
        vec2 g = texture(tex_gradient, uv).rg;   // (dh/dx, dh/dz) a resolucio completa
        // superficie y = k*h(x,z) -> normal = (-k*dh/dx, 1, -k*dh/dz), exacta per a qualsevol k
        vec3 normal = normalize(vec3(-exaggeration * g.x, 1.0, -exaggeration * g.y));
        vec3 terra = rampa(height) * (0.25 + 0.75 * max(dot(normal, sol), 0.0));
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
