#version 330 core
layout (location = 0) out vec4 fragColor;

in vec3 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;
in vec3 v_obj;
in float logz;

struct Light {
    vec3 Ia;
    vec3 Id;
};

uniform Light light;
uniform vec3 sun_dir;      // direccio cap al Sol (llum direccional: el Sol es molt lluny)
uniform vec3 cam_pos;
uniform int mode;          // 0 il·luminada, 1 el Sol, 2 halo (resplendor i corona), 3 la Lluna
uniform float intensitat;  // opacitat del halo
uniform float ambient;     // llum ambient (multiplica light.Ia)
uniform float coef_log;
uniform float temps;       // segons de rellotge (no de simulacio): anima la superficie del Sol
uniform sampler2D textura; // la Lluna: color (LRO)
uniform sampler2D altitud; // la Lluna: altitud en km (LOLA), si amb_relleu
uniform bool amb_relleu;
uniform float radi_lluna;  // km (esfera de referencia de les altituds)
uniform mat4 m_model;
// Lluna vista des de dins de l'atmosfera
uniform bool atmosfera;
uniform float radi_sol;    // radi angular del Sol vist des de la camera (rad)
uniform vec3 tint;         // color de la llum del Sol que arriba a la camera (posta: daurat, vermellos)
uniform float dins_atmosfera;  // 1 des del terra, 0 a l'espai (main.py: app.atmosfera; transicio fins a 60 km)

// soroll de valor 3D (per a la granulacio del Sol, il·lustrativa)
float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float soroll(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
               mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
// soroll fractal: 5 octaves, cada una el doble de fina i la meitat de forta
float fbm(vec3 p) {
    float s = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++) {
        s += a * soroll(p);
        p = p * 2.03 + vec3(1.7, 9.2, 3.1);
        a *= 0.5;
    }
    return s;
}

// Crateres petits de la Lluna (il·lustratius: no son dades), per quan la camera es tan a prop que un pixel de la
// textura (1,3 km) ocupa molts pixels de pantalla. p: punt de la superficie en unitats de la mida de la cel·la; a 4 de
// cada 10 cel·les hi ha un crater, de posicio a l'atzar i radi sovint petit (com a la Lluna: molts mes crateres petits
// que grans), amb forma de bol (h = prof (d^2 - 1)) i una vora aixecada.
// Retorna el pendent (gradient de l'altura, en 3D: despres se'n treu la part vertical).
vec3 crateres(vec3 p) {
    vec3 i = floor(p), f = fract(p), g = vec3(0.0);
    vec3 o = step(0.5, f) - 1.0;                  // les 2 x 2 x 2 cel·les mes properes
    for (int k = 0; k < 8; k++) {
        vec3 c = o + vec3(k & 1, (k >> 1) & 1, (k >> 2) & 1);
        if (hash(i + c + 5.3) > 0.4) continue;
        vec3 centre = c + vec3(hash(i + c), hash(i + c + 3.1), hash(i + c + 7.7));
        float r = 0.08 + 0.42 * pow(hash(i + c + 11.3), 3.0);
        vec3 dp = f - centre;
        float d = length(dp) / r;
        if (d > 1.6 || d < 1e-4) continue;
        // dh/dd: bol (prof 0,35 r) i vora (gaussiana a d = 1)
        float dh = (d < 1.0 ? 2.0 * 0.35 * d : 0.0) - 0.12 * 2.0 * (d - 1.0) / 0.09 * exp(-(d - 1.0) * (d - 1.0) / 0.09);
        g += dh * dp / (length(dp) * r);       // dh/dd * dd/dp
    }
    return g;
}

void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 n = normalize(v_normal);
    vec3 v = normalize(cam_pos - v_frag_pos);   // del fragment cap a la camera
    if (mode == 1) {
        // El Sol. Des del terra, com el veiem: un disc blanc que enlluerna (amb el color que li dona l'atmosfera,
        // tint). Des de l'espai, amb aspecte de foc (il·lustratiu: s'assembla a les fotos fetes amb filtre, que el
        // mostren taronja; a ull nu, sense atmosfera, es blanc). Entre els dos, en pujar, es barregen. Flames: soroll fractal deformat per un altre soroll
        // (domain warping) que es mou a poc a poc; granulacio fina; la vora mes fosca i vermella (enfosquiment
        // del limbe, fisic: I = 1 - 0,6 (1 - mu)).
        float mu = max(dot(n, v), 0.0);
        vec3 q = normalize(v_obj);
        float t = temps;
        vec3 w = vec3(fbm(q * 3.0 + vec3(0.0, 0.0, t * 0.02)), fbm(q * 3.0 + vec3(5.2, 1.3, 2.8) - t * 0.015),
                      fbm(q * 3.0 + vec3(2.1, 7.4, 4.6) + t * 0.01));
        float foc = fbm(q * 7.0 + 3.0 * w + vec3(0.0, t * 0.04, 0.0));
        float gra = soroll(q * 90.0 + vec3(t * 0.15));
        float limbe = 1.0 - 0.6 * (1.0 - mu);
        float calor = clamp((1.5 * foc - 0.2 + 0.3 * gra) * (0.3 + 0.7 * limbe), 0.0, 1.0);
        vec3 color = mix(vec3(0.45, 0.04, 0.00), vec3(0.95, 0.22, 0.02), smoothstep(0.0, 0.35, calor));
        color = mix(color, vec3(1.00, 0.55, 0.08), smoothstep(0.30, 0.65, calor));
        color = mix(color, vec3(1.00, 0.90, 0.55), smoothstep(0.65, 1.00, calor));
        vec3 blanc = vec3(1.0, 0.98, 0.94) * (0.93 + 0.07 * limbe);   // enlluerna: la vora gairebe no es nota
        fragColor = vec4(mix(color, blanc, dins_atmosfera) * tint, 1.0);
        return;
    }
    if (mode == 2) {
        // mes intens al centre (on la normal mira la camera) i s'esvaeix cap a la vora
        float a = pow(max(dot(n, v), 0.0), 6.0);
        fragColor = vec4(v_color * tint, intensitat * a);
        return;
    }
    vec3 base = v_color;
    float diff = max(dot(n, normalize(sun_dir)), 0.0);
    if (mode == 3) {
        // la Lluna: textura equirectangular (longitud 0 al centre, la cara que mira la Terra)
        vec3 o = normalize(v_obj);
        vec2 uv = vec2(0.5 + atan(-o.z, o.x) / 6.2831853, 0.5 - asin(clamp(o.y, -1.0, 1.0)) / 3.14159265);
        // derivades sense el salt de la costura (u passa de 1 a 0): sense aixo, el nivell de mipmap s'hi dispara
        // i es veia una linia fosca de pol a pol
        vec2 dx = dFdx(uv), dy = dFdy(uv);
        dx.x -= floor(dx.x + 0.5);
        dy.x -= floor(dy.x + 0.5);
        base = textureGrad(textura, uv, dx, dy).rgb;
        // relleu: el pendent (est, nord) surt de l'altitud dels veins; la normal s'inclina segons el pendent
        vec3 nord = normalize(vec3(0.0, 1.0, 0.0) - o * o.y + vec3(1e-5, 0.0, 0.0));
        vec3 est = cross(nord, o);
        float cos_lat = max(sqrt(1.0 - o.y * o.y), 0.02);
        vec2 km_uv = vec2(6.2831853 * radi_lluna * cos_lat, 3.14159265 * radi_lluna);   // km per unitat d'uv
        vec3 pendent = vec3(0.0);
        if (amb_relleu) {
            // pas: un texel, o el que ocupa un pixel de pantalla si es mes gran (de lluny, sense soroll)
            vec2 pas = max(1.0 / vec2(textureSize(altitud, 0)), max(abs(dx), abs(dy)));
            float he = textureGrad(altitud, uv + vec2(pas.x, 0.0), dx, dy).r;
            float hw = textureGrad(altitud, uv - vec2(pas.x, 0.0), dx, dy).r;
            float hn = textureGrad(altitud, uv - vec2(0.0, pas.y), dx, dy).r;
            float hs = textureGrad(altitud, uv + vec2(0.0, pas.y), dx, dy).r;
            pendent = est * (he - hw) / (2.0 * pas.x * km_uv.x) + nord * (hn - hs) / (2.0 * pas.y * km_uv.y);
        }
        // de molt a prop (un pixel de pantalla < ~0,5 km), crateres petits il·lustratius: on la textura ja no te detall
        float px_km = max(length(dx * km_uv), length(dy * km_uv));
        vec3 p_km = o * radi_lluna;
        for (int k = 0; k < 3; k++) {
            float mida = 4.0 / pow(3.5, float(k));               // cel·les de 4, 1,1 i 0,33 km
            float w = smoothstep(0.5 * mida, 0.1 * mida, px_km);
            if (w > 0.0) {
                vec3 g = crateres(p_km / mida + float(k) * 17.0);
                pendent += w * 0.45 * (g - o * dot(g, o));
            }
        }
        // i una mica de variacio de color (pols i roques), tambe il·lustrativa
        base *= mix(1.0, 0.85 + 0.3 * fbm(p_km * 1.5), smoothstep(1.0, 0.2, px_km));
        vec3 n_obj = normalize(o - pendent);
        vec3 nl = normalize(mat3(m_model) * n_obj);
        // llum: Lambert lunar (McEwen): barreja de Lambert i de Lommel-Seeliger, 2 mu0 / (mu0 + mu), que fa que
        // la Lluna plena es vegi gairebe igual de clara al centre que a la vora, com la de veritat
        float mu0 = max(dot(nl, normalize(sun_dir)), 0.0), mu = max(dot(nl, v), 0.0);
        diff = mix(mu0, 2.0 * mu0 / (mu0 + mu + 1e-4), 0.7);
        diff *= smoothstep(-0.02, 0.02, dot(n, normalize(sun_dir)));  // el terminador de l'esfera
    }
    vec3 color = base * (ambient * light.Ia + light.Id * diff);
    if (atmosfera) {
        // des de terra, la Lluna nova no es veu (el cel que hi ha davant es tan brillant com la
        // resta): nomes es veu, fosca, on tapa el disc del Sol
        if (dot(-v, normalize(sun_dir)) < cos(radi_sol))
            discard;
        color *= 0.15;
    }
    fragColor = vec4(color, 1.0);
}
