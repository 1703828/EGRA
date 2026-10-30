#version 330 core
// Cel (basecode/cel.py): un triangle que cobreix tota la pantalla, a la profunditat maxima (z = w -> 1). Amb el
// test de profunditat "<=" nomes es pinta on no s'ha dibuixat res (el Sol, la Lluna, la Terra, el terreny i els
// edificis queden per davant i no es toquen).
out vec2 ndc;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0;   // (-1,-1), (3,-1), (-1,3)
    ndc = p;
    gl_Position = vec4(p, 1.0, 1.0);
}
