#version 330 core
layout (location = 0) out vec4 fragColor;
in vec2 ndc;
uniform sampler2D tex_cel;     // el cel a 1/4 de resolucio (interpolacio lineal: el cel es suau)
void main() {
    fragColor = vec4(texture(tex_cel, ndc * 0.5 + 0.5).rgb, 1.0);
}
