#version 330 core
layout (location = 0) in vec3 in_color;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec3 in_position;

out vec3 color;

struct Light {
    vec3 position;
    vec3 Ia;
    vec3 Id;
    vec3 Is;
};

uniform Light light;
uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

void main() {
    vec3 normal = mat3(transpose(inverse(m_model))) * normalize(in_normal);
    vec3 ambient = light.Ia;
    vec3 diffuse = light.Id * max(0, dot(normalize(light.position - in_position), normalize(normal)));
    color = ambient + in_color * diffuse;
    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
}
