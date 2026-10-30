#version 330 core
// Cel (basecode/cel.py), segona passada: el triangle de pantalla completa a la profunditat maxima, que copia el
// cel calculat a baixa resolucio nomes on no hi ha res dibuixat.
out vec2 ndc;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0;
    ndc = p;
    gl_Position = vec4(p, 1.0, 1.0);
}
