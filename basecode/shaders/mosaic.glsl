// Mosaic d'imatges aeries (basecode/mosaic.py, dades/teselles.py). L'inclouen terrain.frag i terra.frag.
//
// Una textura de capes (sampler2DArray): cada capa es un nivell de zoom de Web Mercator, amb 8 x 8 teselles de
// 256 px centrades a sota de la camera. L'index 0 es el nivell mes detallat que es fa servir ara; cada index
// seguent te la meitat de resolucio i cobreix el doble. Les teselles es guarden "en anell" (toroidal): la tesella
// (x, y) va a la posicio (x mod 8, y mod 8) de la capa; quan la camera es mou, nomes cal escriure les teselles
// noves i la resta no es mou. Per aixo les coordenades de textura passen de 1 i la textura es repeteix (REPEAT).
//
// rel: coordenada Mercator del punt menys la de la camera (0..1 = tot el mon). Es petita a prop de la camera,
// i en float32 conserva tota la precisio que cal fins a z = 19.
uniform bool usar_mosaic;
uniform sampler2DArray tex_mosaic;
uniform int mosaic_n;                 // nivells actius
uniform float mosaic_escala[12];      // 2^zoom: teselles per unitat de Mercator
uniform vec2 mosaic_centre[12];       // posicio de la camera dins de la finestra del nivell (teselles, 0..8)
uniform vec2 mosaic_toro[12];         // origen de la finestra mod 8: on comenca dins de la capa
uniform float mosaic_capa[12];        // capa de la textura
uniform uvec2 mosaic_valides[12];     // un bit per posicio (y * 8 + x): ja hi ha la tesella que toca
const float TESELLES = 8.0;

// Color (rgb) del mosaic en aquest punt i quina part en cobreix (a: 0 encara no hi ha imatge, 1 si). dx, dy:
// derivades de rel en pantalla, calculades abans de cap discard.
// Nivell: el que te un texel per pixel de pantalla en la direccio mes nitida (la mes borrosa la resol el filtre
// anisotropic); entre dos nivells, es barregen (sense salts). Si un nivell encara no te la tesella (s'esta
// baixant) o el punt queda fora de la seva finestra, es completa amb el seguent, menys detallat.
vec4 color_mosaic(vec2 rel, vec2 dx, vec2 dy) {
    if (!usar_mosaic || mosaic_n == 0) return vec4(0.0);
    float px = max(min(length(dx), length(dy)), 1e-30);         // Mercator per pixel
    float k = clamp(log2(mosaic_escala[0] * 256.0 * px), 0.0, float(mosaic_n - 1));
    int i0 = int(k);
    float f = k - float(i0);
    vec3 c = vec3(0.0);
    float a = 0.0;
    for (int i = i0; i < mosaic_n && a < 0.995; i++) {
        vec2 l = rel * mosaic_escala[i] + mosaic_centre[i];         // teselles des de l'origen de la finestra
        float vora = min(min(l.x, l.y), min(TESELLES - l.x, TESELLES - l.y));
        float w = smoothstep(0.25, 1.75, vora);                     // a la vora de la finestra, cap al seguent
                                                                    // (gradual: 1,5 teselles, sense linia)
        ivec2 s = ivec2(mod(floor(l + mosaic_toro[i]), TESELLES));
        int bit = s.y * 8 + s.x;
        uint m = bit < 32 ? mosaic_valides[i].x : mosaic_valides[i].y;
        if (((m >> uint(bit & 31)) & 1u) == 0u) w = 0.0;
        if (i == i0) w *= 1.0 - f;
        if (w > 0.0) {
            float e = mosaic_escala[i] / TESELLES;
            vec3 t = textureGrad(tex_mosaic, vec3((l + mosaic_toro[i]) / TESELLES, mosaic_capa[i]), dx * e, dy * e).rgb;
            c += (1.0 - a) * w * t;
            a += (1.0 - a) * w;
        }
    }
    return vec4(a > 0.0 ? c / a : c, a);
}
