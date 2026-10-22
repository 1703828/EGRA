#version 330 core

in vec3 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;

out vec4 frag_color;

struct Light {
    vec3 position;
    vec3 Ia;
    vec3 Id;
    vec3 Is;
};

uniform Light light;
uniform vec3 view_pos;

void main() {
    vec3 N = normalize(v_normal);
    vec3 L = normalize(light.position - v_frag_pos);
    vec3 V = normalize(view_pos - v_frag_pos);
    vec3 R = reflect(-L, N);

    // Ambient
    vec3 ambient = light.Ia;

    // Difusa (Lambert)
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * light.Id;

    // Especular (Phong)
    float brillantor = 32.0;
    float spec = pow(max(dot(R, V), 0.0), brillantor);
    if (diff == 0.0) {
        spec = 0.0;
    }
    vec3 specular = spec * light.Is;

    vec3 color = v_color * (ambient + diffuse) + specular;
    frag_color = vec4(color, 1.0);
}
