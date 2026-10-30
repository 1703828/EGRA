#version 330 core
// Color del cel per dispersio de la llum a l'atmosfera (Rayleigh, Mie i absorcio de l'ozo), amb l'ombra de la
// Lluna a cada punt del raig. El mateix calcul que dades/atmosfera.py (alla s'explica el model); qualsevol canvi
// s'ha de fer als dos llocs (scripts/prova_cel.py en compara els resultats).
layout (location = 0) out vec4 fragColor;
in vec2 ndc;
uniform mat3 vista_inv;        // de coordenades de la camera al mon (la transposada de la rotacio de m_view)
uniform vec2 escala_proj;      // 1 / m_proj[0][0] i 1 / m_proj[1][1]: de la pantalla a la direccio
// (no s'inverteix m_proj * m_view: amb near = 1e-6 km i far = 1e9 km, en float32 no te prou precisio)
uniform vec3 cam_ecef;         // posicio de la camera (ECEF, km)
uniform float alcada_km;       // altura de la camera sobre l'el·lipsoide
uniform float radi_terra;      // radi de l'esfera de la Terra per al calcul (km)
uniform vec3 sol_rel;          // Sol i Lluna relatius a la camera (km)
uniform vec3 lluna_rel;
uniform float radi_sol;
uniform float radi_lluna;
uniform float visible_camera;  // part del Sol que es veu des de la camera (adaptacio de l'ull)

const float ALCADA_ATMOSFERA = 80.0;
const vec3 BETA_R = vec3(5.802e-3, 13.558e-3, 33.1e-3);
const float ESCALA_R = 8.0;
const float BETA_M = 3.996e-3;
const float EXTINCIO_M = 4.40e-3;
const float ESCALA_M = 1.2;
const float G_MIE = 0.8;
const vec3 BETA_O = vec3(0.650e-3, 1.881e-3, 0.085e-3);
const float OZO_CENTRE = 25.0, OZO_AMPLE = 15.0;
const float SOL = 20.0;
const float EXPOSICIO = 3.0;
const float ADAPTACIO = 0.6, VISIBLE_MIN = 0.01;
const float LLUM_DIFOSA = 0.003;  // dins de l'ombra: llum dispersada des de fora (il·lustratiu)
const float SATURACIO = 0.85;
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
const int N_VISTA = 12, N_LLUM = 4;
const float PI = 3.14159265;

// (t0, t1) del raig o + t d amb l'esfera de radi r centrada a l'origen; t0 > t1 si no la toca
vec2 esfera(vec3 o, vec3 d, float r) {
    float b = dot(o, d);
    float c = dot(o, o) - r * r;
    float disc = b * b - c;
    if (disc < 0.0) return vec2(1.0, -1.0);
    float s = sqrt(disc);
    return vec2(-b - s, -b + s);
}

float ozo(float h) { return max(0.0, 1.0 - abs(h - OZO_CENTRE) / OZO_AMPLE); }

// la mateixa formula que dades/model_eclipsi.py i terrain.frag
float area_tapada(float d, float r1, float r2) {
    if (d >= r1 + r2) return 0.0;
    if (d <= abs(r2 - r1)) return min(1.0, (r2 * r2) / (r1 * r1));
    float a1 = r1 * r1 * acos(clamp((d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1), -1.0, 1.0));
    float a2 = r2 * r2 * acos(clamp((d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2), -1.0, 1.0));
    float a3 = 0.5 * sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0.0));
    return (a1 + a2 - a3) / (PI * r1 * r1);
}

float tapat_des_de(vec3 p) {
    vec3 s = sol_rel - p, l = lluna_rel - p;
    float rs = asin(min(1.0, radi_sol / length(s))), rl = asin(min(1.0, radi_lluna / length(l)));
    float d = 2.0 * asin(min(1.0, 0.5 * length(normalize(s) - normalize(l))));
    return area_tapada(d, rs, rl);
}

vec3 llum_dispersada(vec3 d) {
    float r = radi_terra;
    vec3 o = normalize(cam_ecef) * (r + alcada_km);
    vec2 tt = esfera(o, d, r + ALCADA_ATMOSFERA);
    if (tt.x > tt.y || tt.y <= 0.0) return vec3(0.0);
    float t0 = max(tt.x, 0.0), t1 = tt.y;
    vec2 terra = esfera(o, d, r);
    if (terra.x <= terra.y && terra.x > 0.0) t1 = min(t1, terra.x);
    float longitud = t1 - t0;
    vec3 s_dir = normalize(sol_rel);
    float mu = dot(d, s_dir);
    float fase_r = 3.0 / (16.0 * PI) * (1.0 + mu * mu);
    float g2 = G_MIE * G_MIE;
    float fase_m = 3.0 / (8.0 * PI) * (1.0 - g2) * (1.0 + mu * mu) / ((2.0 + g2) * pow(1.0 + g2 - 2.0 * G_MIE * mu, 1.5));
    float od_r = 0.0, od_m = 0.0, od_o = 0.0;
    vec3 suma_r = vec3(0.0), suma_m = vec3(0.0);
    for (int i = 0; i < N_VISTA; i++) {
        float fa = float(i) / float(N_VISTA), fb = float(i + 1) / float(N_VISTA);
        float ds = longitud * (fb * fb - fa * fa);
        vec3 x = o + d * (t0 + longitud * (0.5 * (fa + fb)) * (0.5 * (fa + fb)));
        float h = length(x) - r;
        float dr = exp(-h / ESCALA_R) * ds, dm = exp(-h / ESCALA_M) * ds;
        od_r += dr;
        od_m += dm;
        od_o += ozo(h) * ds;
        vec2 ts = esfera(x, s_dir, r);
        if (ts.x <= ts.y && ts.x > 0.0) continue;        // la Terra tapa el Sol en aquest punt
        float dsl = esfera(x, s_dir, r + ALCADA_ATMOSFERA).y / float(N_LLUM);
        float ol_r = 0.0, ol_m = 0.0, ol_o = 0.0;
        for (int j = 0; j < N_LLUM; j++) {
            float hl = length(x + s_dir * (float(j) + 0.5) * dsl) - r;
            ol_r += exp(-hl / ESCALA_R) * dsl;
            ol_m += exp(-hl / ESCALA_M) * dsl;
            ol_o += ozo(hl) * dsl;
        }
        vec3 transm = exp(-(BETA_R * (od_r + ol_r) + EXTINCIO_M * (od_m + ol_m) + BETA_O * (od_o + ol_o)));
        float visible = max(1.0 - tapat_des_de(x - o), LLUM_DIFOSA);
        suma_r += dr * transm * visible;
        suma_m += dm * transm * visible;
    }
    return SOL * (BETA_R * fase_r * suma_r + BETA_M * fase_m * suma_m);
}

vec3 to(vec3 llum) {
    vec3 c = llum * EXPOSICIO * pow(max(visible_camera, VISIBLE_MIN), -ADAPTACIO);
    vec3 canal = 1.0 - exp(-c);
    float y = dot(c, LUMA);
    if (y <= 1e-9) return vec3(0.0);
    float yt = 1.0 - exp(-y);
    vec3 lum = c * (yt / y);
    float m = max(lum.r, max(lum.g, lum.b));
    if (m > 1.0) lum = lum + (1.0 - lum) * min(1.0, (m - 1.0) / max(m - yt, 1e-6));
    vec3 res = 0.5 * (canal + clamp(lum, 0.0, 1.0));
    float g = dot(res, LUMA);
    return clamp(g + SATURACIO * (res - g), 0.0, 1.0);
}

void main() {
    vec3 d = normalize(vista_inv * vec3(ndc * escala_proj, -1.0));
    fragColor = vec4(to(llum_dispersada(d)), 1.0);
}
