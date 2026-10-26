#version 330
// Passada des del Sol: nomes la profunditat (la GPU l'escriu sola). Els forats son els mateixos que a
// terrain.frag: on hi ha el pegat dens, la graella general no hi es.
in vec2 uv;
uniform vec4 forats[4];
uniform int n_forats;
void main() {
    for (int i = 0; i < n_forats; i++)
        if (uv.x > forats[i].x && uv.x < forats[i].z && uv.y > forats[i].y && uv.y < forats[i].w) discard;
}
