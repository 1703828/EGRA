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
uniform sampler2D textura; // la Lluna
// Lluna vista des de dins de l'atmosfera
uniform bool atmosfera;
uniform float radi_sol;    // radi angular del Sol vist des de la camera (rad)

// soroll de valor 3D (per a la granulacio del Sol, il·lustrativa)
float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float soroll(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
               mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

void main() {
    gl_FragDepth = log2(logz) * coef_log * 0.5;
    vec3 n = normalize(v_normal);
    vec3 v = normalize(cam_pos - v_frag_pos);   // del fragment cap a la camera
    if (mode == 1) {
        // El Sol: la vora es mes fosca i vermellosa (enfosquiment del limbe, fisic: I = 1 - 0,6 (1 - mu))
        // i la superficie te una granulacio animada (il·lustrativa: no es el Sol real d'aquell dia).
        float mu = max(dot(n, v), 0.0);
        vec3 q = normalize(v_obj) * 28.0;
        float g = 0.55 * soroll(q + vec3(0.0, temps * 0.05, 0.0)) + 0.30 * soroll(q * 2.3 - temps * 0.08)
                + 0.15 * soroll(q * 5.1 + temps * 0.12);
        float limbe = 1.0 - 0.6 * (1.0 - mu);
        vec3 color = mix(vec3(1.00, 0.45, 0.10), vec3(1.00, 0.93, 0.70), pow(mu, 0.5));
        fragColor = vec4(color * limbe * (0.82 + 0.30 * g), 1.0);
        return;
    }
    if (mode == 2) {
        // mes intens al centre (on la normal mira la camera) i s'esvaeix cap a la vora
        float a = pow(max(dot(n, v), 0.0), 6.0);
        fragColor = vec4(v_color, intensitat * a);
        return;
    }
    vec3 base = v_color;
    if (mode == 3) {
        // la Lluna: textura equirectangular (longitud 0 al centre, la cara que mira la Terra)
        vec3 o = normalize(v_obj);
        vec2 uv = vec2(0.5 + atan(-o.z, o.x) / 6.2831853, 0.5 - asin(clamp(o.y, -1.0, 1.0)) / 3.14159265);
        base = texture(textura, uv).rgb;
    }
    float diff = max(dot(n, normalize(sun_dir)), 0.0);
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
