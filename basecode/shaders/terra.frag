#version 330 core
// La Terra vista de lluny: textura de color, llum del Sol (dia i nit), ombra de la Lluna i un
// contorn blau d'atmosfera (aquest ultim, il·lustratiu).
layout (location = 0) out vec4 fragColor;
in vec3 pos_rel;
in vec3 normal;
in vec2 uv;
in float logz;
uniform sampler2D textura;
uniform vec3 sol_rel;      // Sol relatiu a la camera (km)
uniform vec3 lluna_rel;    // Lluna relativa a la camera (km)
uniform float radi_sol;    // km
uniform float radi_lluna;  // km
uniform float coef_log;
uniform float atmosfera;   // 1 dins de l'atmosfera, 0 a l'espai
uniform bool ressaltar_ombra;

// La mateixa formula que dades/model_eclipsi.py i terrain.frag
float area_tapada(float d, float r1, float r2) {
    if (d >= r1 + r2) return 0.0;
    if (d <= abs(r2 - r1)) return min(1.0, (r2 * r2) / (r1 * r1));
    float a1 = r1 * r1 * acos(clamp((d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1), -1.0, 1.0));
    float a2 = r2 * r2 * acos(clamp((d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2), -1.0, 1.0));
    float a3 = 0.5 * sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0));
    return (a1 + a2 - a3) / (3.14159265 * r1 * r1);
}

float tapat_des_de(vec3 p) {
    vec3 s = sol_rel - p, l = lluna_rel - p;
    float rs = asin(radi_sol / length(s)), rl = asin(radi_lluna / length(l));
    float d = 2.0 * asin(min(1.0, 0.5 * length(normalize(s) - normalize(l))));
    return area_tapada(d, rs, rl);
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

void main() {
    // profunditat logaritmica, una mica mes lluny (2 cm per km) perque el terreny detallat,
    // que es al mateix lloc, sempre quedi per sobre del globus
    gl_FragDepth = log2(1.0 + (logz - 1.0) * 1.00002) * coef_log * 0.5;
    vec3 n = normalize(normal);
    vec3 sol = normalize(sol_rel - pos_rel);
    float cos_sol = dot(n, sol);
    // dia i nit: el terminador es suau (el crepuscle dura uns quants graus)
    float dia = smoothstep(-0.10, 0.10, cos_sol);
    float tapat = tapat_des_de(pos_rel);
    float d_tapat = fwidth(tapat);
    float visible = 1.0 - tapat;                   // 1 al Sol, 0 a l'ombra de la Lluna
    vec3 color = texture(textura, uv).rgb;
    // llum directa (Lambert) + una part difusa del cel que manté clar el costat de dia prop del
    // terminador (aproximacio visual de l'atmosfera)
    vec3 c = color * (0.03 + dia * visible * (0.25 + 0.95 * max(cos_sol, 0.0)));
    // atmosfera (il·lustratiu): un contorn blau a la vora del disc, nomes al costat de dia i vist des
    // de fora de l'atmosfera (des del terra, el mar llunya es veuria d'un blau brillant)
    vec3 v = normalize(-pos_rel);
    float vora = pow(1.0 - max(dot(n, v), 0.0), 3.0);
    c += vec3(0.30, 0.50, 1.00) * vora * 0.6 * dia * (1.0 - atmosfera);
    if (ressaltar_ombra)
        c = ressaltar(c, tapat, d_tapat, smoothstep(-0.03, 0.0, cos_sol));
    fragColor = vec4(c, 1.0);
}
