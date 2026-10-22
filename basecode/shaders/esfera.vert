#version 330 core
layout (location = 0) in vec3 in_color;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec3 in_position;

out vec3 v_color;
out vec3 v_normal;
out vec3 v_frag_pos;
out vec3 v_obj;      // normal en coordenades de l'objecte (per a la textura de la Lluna i la superficie del Sol)
out float logz;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

void main() {
    v_color = in_color;
    v_normal = mat3(transpose(inverse(m_model))) * in_normal;
    v_obj = in_normal;
    v_frag_pos = vec3(m_model * vec4(in_position, 1.0));
    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
    // profunditat logaritmica: la calcula el fragment shader (gl_FragDepth) a partir de logz.
    // gl_Position.z es deixa com el dona la projeccio: el retall (clipping) dels triangles es fa
    // interpolant z linealment entre vertexs, i una z logaritmica per vertex retallaria triangles
    // grans que passen per darrere de la camera (el terra als peus desapareixia).
    logz = 1.0 + gl_Position.w;
}
