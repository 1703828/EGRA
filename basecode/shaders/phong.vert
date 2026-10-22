#version 330 core

in vec3 in_color;
in vec3 in_normal;
in vec3 in_position;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

out vec3 v_color;
out vec3 v_normal;
out vec3 v_frag_pos;

void main() {
    v_color = in_color;
    v_normal = mat3(transpose(inverse(m_model))) * in_normal;
    v_frag_pos = vec3(m_model * vec4(in_position, 1.0));
    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
}
