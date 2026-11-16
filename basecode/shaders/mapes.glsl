// Mapes de l'eclipsi sobre el terreny (basecode/mapes.py; definicions al pla, O4.1). S'inclou a terrain.frag.
//
// Les dades dels mapes del temps observable i del relleu son peces per nivells (N0 peninsula 200 m, N1 25 m, N2 5 m,
// N3 obstacles mesurats), cadascuna una capa d'una textura array del seu nivell. Per a cada punt es fa servir la
// peca mes detallada que el conte i hi te dades: on encara no n'hi ha de detall, la de sota (no queda cap forat).
// Els rectangles de les peces arriben en les UV del terreny que es dibuixa (la CPU els calcula en doble precisio).
// Les dades son classes i temps: es llegeixen sense filtre (NEAREST) i no s'interpolen entre pixels.
//
// Els colors son els de les llegendes (llindars fixos, D96): el mapa es pinta despres de la llum i de la boira, amb
// nomes un ombrejat fix del relleu (llum del nord-oest) perque es vegi la forma del terreny; la llum de l'eclipsi no
// canvia el color que es llegeix.

uniform bool mapa_cobertes;           // false: el terreny (carrer); true: les cobertes dels edificis (terrats)
uniform int mapa;                     // 0 cap, 1 ocultacio, 2 temps observable, 3 relleu, 4 ombra de la Lluna
uniform int mapa_mode;                // ocultacio: 0 al maxim, 1 ara; durada: 0 tot, 1 fase central; relleu: 0 al maxim, 1 ara
uniform bool mapa_anular;             // l'eclipsi es anular (fase central = anularitat)
uniform float hora_s;                 // l'hora de la barra, en s des de l'inici de les efemerides
uniform float radi_sol_graus;
uniform float frac_escala;            // obs i obs_central: fraccio x frac_escala
uniform sampler2DArray mapa_n0;
uniform sampler2DArray mapa_n1;
uniform sampler2DArray mapa_n2;
uniform sampler2DArray mapa_n3;
uniform vec4 mapa_rect[30];           // peces de tots els nivells, en ordre (N0, N1, N2, N3), UV del terreny
uniform vec2 mapa_escala[30];         // part de la capa que ocupa la peca
uniform int mapa_capa[30];            // primera capa de la peca a la textura del seu nivell
uniform int mapa_n[4];                // peces de cada nivell
uniform int mapa_k[4];                // intervals a la GPU per nivell (0: nomes la capa resum)
uniform sampler2D tex_graella;        // circumstancies: tapat al maxim (0-1), durada de la fase central (s); -1 sense
uniform bool hi_ha_graella;
uniform vec4 rect_graella;
uniform float ocult_llindars[11];
uniform vec3 ocult_colors[12];
uniform vec3 mapa_color_total;
uniform vec3 mapa_color_anular;
uniform float durada_llindars[7];
uniform vec3 durada_colors[9];
uniform float central_llindars[3];
uniform vec3 central_colors[6];
uniform vec3 color_fora_central;
uniform vec3 relleu_colors[4];
uniform vec3 color_posta;
uniform vec3 color_limits_central;
uniform vec3 color_sense_eclipsi;

vec4 mostra_nivell(int nivell, vec3 c) {
    if (nivell == 3) return texture(mapa_n3, c);
    if (nivell == 2) return texture(mapa_n2, c);
    if (nivell == 1) return texture(mapa_n1, c);
    return texture(mapa_n0, c);
}

// La peca mes detallada que conte el punt i hi te dades: el resum (obs, obs_central, marge + 32768, n intervals; en
// unitats de 16 bits), el nivell i on es (coordenades de la capa resum). False si cap.
bool dades_mapa(out vec4 resum, out int nivell, out vec3 coord) {
    int inici[4] = int[](0, mapa_n[0], mapa_n[0] + mapa_n[1], mapa_n[0] + mapa_n[1] + mapa_n[2]);
    for (int nv = 3; nv >= 0; nv--) {
        for (int j = 0; j < 16; j++) {
            if (j >= mapa_n[nv]) break;
            int i = inici[nv] + j;
            vec4 r = mapa_rect[i];
            vec2 t = (uv - r.xy) / (r.zw - r.xy);
            if (any(lessThan(t, vec2(0.0))) || any(greaterThanEqual(t, vec2(1.0)))) continue;
            vec3 c = vec3(t * mapa_escala[i], float(mapa_capa[i]));
            vec4 v = mostra_nivell(nv, c) * 65535.0;
            // pixel dins d'un edifici del Catastro (nomes al nivell dels obstacles): el valor es el del terrat (ulls
            // sobre la coberta). Al terreny (carrer) no es mostra (ni el nivell de sota, que no ho sap); a les
            // cobertes, nomes aquests
            bool edifici = nv == 3 && mod(floor(v.a / 256.0 + 0.001), 2.0) > 0.5;
            if (mapa_cobertes != edifici) {
                if (edifici) return false;
                continue;
            }
            if (v.r > 65534.5) continue;          // sense dades en aquesta peca: el nivell de sota
            resum = v; nivell = nv; coord = c;
            return true;
        }
    }
    return false;
}

// classe d'un valor amb llindars (el primer llindar que supera)
int banda_ocult(float f) {
    int b = 0;
    for (int i = 0; i < 11; i++) if (f >= ocult_llindars[i]) b = i + 1;
    return b;
}

// gruix de linia (0 lluny, 1 a sobre) d'una isolinia de f cada pas, d'1 pixel d'amplada a qualsevol zoom
float isolinia(float f, float pas, float df) {
    float l = f / pas;
    float px = abs(fract(l - 0.5) - 0.5) / max(df / pas, 1e-7);
    return 1.0 - smoothstep(0.5, 1.5, px);
}

// el Sol, des d'aqui, es sota l'horitzo astronomic (amb la refraccio de Bennett): la posta
bool sota_horitzo(vec3 p, vec3 up) {
    float el = degrees(asin(clamp(dot(normalize(sol_rel - p), normalize(up)), -1.0, 1.0)));
    float r = 1.0 / tan(radians(el + 7.31 / (el + 4.4))) / 60.0;
    return el + (el < -1.0 ? 0.0 : r) < -radi_sol_graus;
}

// dins d'algun interval [inici, final] del llindar (0: alguna part, 1: sencer) a l'hora de la barra
bool dins_intervals(int nivell, vec3 c, int llindar) {
    for (int i = 0; i < 2; i++) {
        if (i >= mapa_k[nivell]) break;
        vec4 v = mostra_nivell(nivell, vec3(c.xy, c.z + 1.0 + float(i))) * 65535.0;
        vec2 iv = llindar == 0 ? v.xy : v.zw;
        if (iv.x < 65534.5 && hora_s >= iv.x && hora_s <= iv.y) return true;
    }
    return false;
}

// color (rgb) i opacitat (a) del mapa en aquest punt. tapat = part del Sol que tapa la Lluna ara aqui.
vec4 color_mapa(float tapat, float d_tapat, vec3 up) {
    if (mapa == 1) {
        // ocultacio per la Lluna: al maxim (graella) o ara (calculada aqui)
        float f; bool central;
        if (mapa_mode == 1) {
            f = tapat; central = central_des_de(pos_mon);
            if (f <= 0.0) return vec4(color_sense_eclipsi, 0.35);
        } else {
            if (!hi_ha_graella) return vec4(0.0);
            vec2 g = texture(tex_graella, (uv - rect_graella.xy) / (rect_graella.zw - rect_graella.xy)).rg;
            if (g.r < 0.0) return vec4(color_sense_eclipsi, 0.35);
            f = g.r; central = g.g > 0.0;
        }
        vec3 c = central ? (mapa_anular ? mapa_color_anular : mapa_color_total) : ocult_colors[banda_ocult(f)];
        // isolinies cada 1 % per sobre del 90 % (com el mapa del CNIG), suaus
        float df = max(fwidth(f), 1e-6);
        if (f > 0.9 && !central) c = mix(c, vec3(1.0), 0.35 * isolinia(f, 0.01, df));
        return vec4(c, 0.82);
    }
    if (mapa == 4) {
        // ombra de la Lluna: la fase central ara (farcit), corbes de la penombra ara (cada 20 %) i el recorregut de
        // la fase central de tot l'eclipsi (limits i corbes de durada cada 30 s)
        vec3 c = vec3(0.0); float a = 0.0;
        if (central_des_de(pos_mon)) { c = mapa_anular ? mapa_color_anular : mapa_color_total; a = 0.8; }
        float l = isolinia(tapat, 0.2, max(d_tapat, 1e-6)) * step(0.01, tapat) * step(tapat, 0.99);
        c = mix(c, vec3(1.0, 0.92, 0.70), l); a = max(a, 0.7 * l);
        if (hi_ha_graella) {
            vec2 g = texture(tex_graella, (uv - rect_graella.xy) / (rect_graella.zw - rect_graella.xy)).rg;
            float dg = max(fwidth(g.g), 1e-6);
            float lim = 1.0 - smoothstep(0.5, 1.8, abs(g.g - 0.5) / dg);       // on la durada passa per 0
            float iso = g.g > 1.0 ? 0.5 * isolinia(g.g, 30.0, dg) : 0.0;
            c = mix(c, color_limits_central, max(lim, iso)); a = max(a, max(lim, iso));
        }
        return vec4(c, a);
    }
    // temps observable i relleu: les dades per nivells
    vec4 v; int nivell; vec3 coord;
    if (!dades_mapa(v, nivell, coord)) return vec4(0.0);          // sense dades: sense color
    if (mapa == 2) {
        float fr = (mapa_mode == 1 ? v.g : v.r);
        if (fr > 65534.5) return mapa_mode == 1 ? vec4(color_fora_central, 0.30) : vec4(color_sense_eclipsi, 0.35);
        fr /= frac_escala;
        if (mapa_mode == 1) {
            int b = fr <= 0.0 ? 0 : (fr >= 0.9995 ? 5 : 1);
            if (b == 1) for (int i = 0; i < 3; i++) if (fr >= central_llindars[i]) b = i + 2;
            return vec4(central_colors[b], 0.85);
        }
        int b = fr <= 0.0 ? 0 : 1;
        if (b == 1) for (int i = 0; i < 7; i++) if (fr >= durada_llindars[i]) b = i + 2;
        return vec4(durada_colors[b], 0.85);
    }
    if (mapa == 3) {
        if (v.b < 0.5) return vec4(color_sense_eclipsi, 0.35);
        if (mapa_mode == 0) {
            float m = (v.b - 32768.0) / 100.0;                       // marge al maxim (graus)
            int classe = m > radi_sol_graus ? 3 : (m > 0.0 ? 2 : (m > -radi_sol_graus ? 1 : 0));
            return vec4(relleu_colors[classe], 0.85);
        }
        if (tapat <= 0.0) return vec4(color_sense_eclipsi, 0.35);   // ara no hi ha eclipsi aqui
        if (dins_intervals(nivell, coord, 1)) return vec4(relleu_colors[3], 0.85);
        if (dins_intervals(nivell, coord, 0)) return vec4(relleu_colors[1], 0.85);
        if (sota_horitzo(pos_mon, up)) return vec4(color_posta, 0.85);
        return vec4(relleu_colors[0], 0.85);
    }
    return vec4(0.0);
}
