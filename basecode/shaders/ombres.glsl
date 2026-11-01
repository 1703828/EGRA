// Ombres del relleu i dels edificis (shadow mapping, basecode/ombres_relleu.py), compartit per terrain.frag i
// edifici.frag (#include). Dos mapes de profunditat vistos des del Sol, ancorats al punt de detall:
//  - el gran (tex_ombra): 32 x 32 km, texels de ~8 m: les muntanyes;
//  - el fi (tex_ombra_fi): 3 x 3 km, texels de menys d'1 m: els edificis (fer ombra i rebre'n).
// Dins del fi es fa servir el fi (amb una transicio suau a la vora) i fora, el gran.
uniform sampler2DShadow tex_ombra;     // compara per maquinari: 1 si el punt es mes a prop del Sol que el mapa
uniform sampler2DShadow tex_ombra_fi;
uniform bool ombres_relleu;            // aquest objecte rep ombres (la zona de 5 m i els seus edificis)
uniform bool ombres_fi;                // hi ha mapa fi
uniform mat4 m_llum;                   // posicio relativa a l'ancora (km) -> clip de la llum (mapa gran)
uniform mat4 m_llum_fi;                // el mateix per al mapa fi
uniform vec3 cam_menys_ancora;         // camera - ancora (km)
uniform float desplacament_normal;     // mapa gran: el punt es mira 1 texel fora de la superficie (acne)
uniform float biaix_profunditat;       // mapa gran: i 3 m mes a prop del Sol (unitats de profunditat)
uniform float texel_fi;                // mapa fi: mida d'un texel (km)
uniform float biaix_fi;                // mapa fi: marge fix (km)
uniform float km_a_profunditat;        // de km a unitats de profunditat de la llum (ortografica)

const float PENDENT_MAX = 20.0;        // el marge creix amb la inclinacio de la llum fins a 20 texels

// 3 x 3 lectures (cada una ja barreja 2 x 2 texels): suavitzen la vora de l'ombra
float mostrar_ombra(sampler2DShadow t, vec3 s, float biaix) {
    vec2 texel = 1.0 / vec2(textureSize(t, 0));
    float llum = 0.0;
    for (int i = -1; i <= 1; i++)
        for (int j = -1; j <= 1; j++)
            llum += texture(t, vec3(s.xy + vec2(i, j) * texel, s.z - biaix));
    return llum / 9.0;
}

// p: posicio relativa a la camera (km); normal i sol, unitaris. 1 si el Sol hi arriba, 0 si un obstacle el tapa.
// Mapa gran: el punt es desplaca una mica en la direccio de la normal i se li resta un marge fix (el mapa te
// texels de ~8 m i amb el Sol baix cada un cobreix un tros inclinat de terreny). Mapa fi: el marge creix amb la
// inclinacio de la llum sobre la superficie (texel x tangent de l'angle): una facana de cara al Sol te un marge
// petit i el terra amb el Sol rasant, gran (s'hi perden els primers metres de l'ombra arran de l'obstacle).
float factor_ombra(vec3 p, vec3 normal, vec3 sol) {
    if (!ombres_relleu) return 1.0;
    vec3 pa = p + cam_menys_ancora;
    float gran = 1.0;
    vec4 q = m_llum * vec4(pa + normal * desplacament_normal, 1.0);
    vec3 s = q.xyz / q.w * 0.5 + 0.5;
    if (all(greaterThanEqual(s, vec3(0.0))) && all(lessThanEqual(s, vec3(1.0))))
        gran = mostrar_ombra(tex_ombra, s, biaix_profunditat);
    if (!ombres_fi) return gran;
    float c = clamp(dot(normal, sol), 0.02, 1.0);
    float tangent = min(sqrt(1.0 - c * c) / c, PENDENT_MAX);
    q = m_llum_fi * vec4(pa + normal * texel_fi, 1.0);
    s = q.xyz / q.w * 0.5 + 0.5;
    if (any(lessThan(s, vec3(0.0))) || any(greaterThan(s, vec3(1.0)))) return gran;
    float fi = mostrar_ombra(tex_ombra_fi, s, (biaix_fi + texel_fi * tangent) * km_a_profunditat);
    float vora = min(min(s.x, 1.0 - s.x), min(s.y, 1.0 - s.y));
    return mix(gran, fi, smoothstep(0.0, 0.05, vora));
}
