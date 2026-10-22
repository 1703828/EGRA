#version 330 core
layout (location = 0) out vec4 fragColor;

in vec3 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;

struct Light {
    vec3 Ia;
    vec3 Id;
};

uniform Light light;
uniform vec3 sun_dir;      // direccio cap al Sol (llum direccional: el Sol es molt lluny)
uniform vec3 cam_pos;
uniform int mode;          // 0 il.luminada, 1 emissiva (el Sol), 2 halo (resplendor i corona)
uniform float intensitat;  // opacitat del halo
uniform float ambient;     // llum ambient (multiplica light.Ia)
// Lluna vista des de dins de l'atmosfera
uniform bool atmosfera;
uniform float radi_sol;    // radi angular del Sol (rad)

void main() {
    vec3 n = normalize(v_normal);
    vec3 v = normalize(cam_pos - v_frag_pos);   // del fragment cap a la camera
    if (mode == 1) {
        fragColor = vec4(v_color, 1.0);
        return;
    }
    if (mode == 2) {
        // mes intens al centre (on la normal mira la camera) i s'esvaeix cap a la vora
        float a = pow(max(dot(n, v), 0.0), 6.0);
        fragColor = vec4(v_color, intensitat * a);
        return;
    }
    float diff = max(dot(n, normalize(sun_dir)), 0.0);
    vec3 color = v_color * (ambient * light.Ia + light.Id * diff);
    if (atmosfera) {
        // des de terra, la Lluna nova no es veu (el cel que hi ha davant es tan brillant com la
        // resta): nomes es veu, fosca, on tapa el disc del Sol. Fora del disc no es dibuixa, i aixi
        // tampoc tapa la resplendor del Sol (la vora de la Lluna, un 4 % mes gran, no es nota)
        if (dot(-v, normalize(sun_dir)) < cos(radi_sol))
            discard;
        color *= 0.15;
    }
    fragColor = vec4(color, 1.0);
}
