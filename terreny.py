"""
Projecte EGRA -- Simulacio d'un eclipsi sobre terreny real
Visualitza en 3D els MDT de data/cache/ (peninsula, Asturies, zones de detall).

T2: l'altitud, el pendent i la distancia a la costa son textures. La geometria es una graella
plana fixa (com a maxim 1024 x 1024 vertexs) i el vertex shader hi llegeix l'altura. Les normals
es fan al fragment shader amb el pendent a la resolucio del fitxer (5 m).
T3: rampa de colors absoluta, mar amb profunditat i costa suau, faldilles a les vores, boira,
resize de la finestra, FPS al panell i boto per reiniciar la camera.
T4: camera amb ratoli (camera.py) enganxada al terreny, picking amb el depth buffer.
T5: selector de terrenys (es carreguen un cop i queden en memoria; derivats en cache .npz),
rectangles de les zones de detall i curvatura de la Terra.
T6: dades de l'eclipsi (eclipse_data.py): overlays d'enfosquiment, durada i ombres del CNIG,
limits de la totalitat i valors de l'eclipsi al punt d'observacio.

Reutilitza el basecode dels reptes (glfw + moderngl + slimgui).
Executa:  python terreny.py                              (selector amb els terrenys de data/cache/)
          python terreny.py data/mdt05/PNOA_...tif       (afegeix un altre MDT en EPSG:25830)
"""
import math
import os
import sys
import time

import glfw
import glm
import numpy as np
import moderngl as mgl
import rasterio
from pyproj import Transformer
from slimgui import imgui

from basecode.engine import GraphicsEngineBase
from camera import Camera
import data_io
import eclipse_data

ARREL = os.path.dirname(os.path.abspath(__file__))
# (nom al panell, fitxer, es zona de detall)
TERRENYS = [
    ('Peninsula', os.path.join(ARREL, 'data', 'cache', 'peninsula_200m.tif'), False),
    ('Asturies', os.path.join(ARREL, 'data', 'cache', 'asturias_25m.tif'), False),
    ('Picos', os.path.join(ARREL, 'data', 'cache', 'detall_5m.tif'), True),
    ('Luarca', os.path.join(ARREL, 'data', 'cache', 'detall_5m_luarca.tif'), True),
]
MAX_VERTEXS = 1024              # vertexs maxims per costat de la graella
MAX_ZONES = 4                   # rectangles de zones de detall que pot dibuixar el shader
COLOR_CEL = (0.62, 0.76, 0.90)  # color del fons i de la boira
RADI_TERRA = 6371.0             # km

# overlays de l'eclipsi: nom al panell i colors (els fan servir el shader i la llegenda del panell)
OVERLAYS = ['Cap', 'Enfosquiment maxim', 'Durada de la totalitat', 'Ombres del relleu (CNIG)']
ENFOSQUIMENT_MIN = 0.90         # la rampa va de 0.90 a 1.00 (a la peninsula no baixa de 0.90)
COLORS_ENFOSQUIMENT = [(1.00, 0.95, 0.60), (1.00, 0.62, 0.20), (0.85, 0.20, 0.20), (0.35, 0.05, 0.40)]
COLOR_TOTALITAT = (0.85, 0.00, 0.85)
# durada: 5 colors repartits entre la durada minima i maxima de la franja dins de cada terreny
COLORS_DURADA = [(1.00, 0.95, 0.50), (0.50, 0.85, 0.40), (0.20, 0.70, 0.85),
                 (0.15, 0.30, 0.80), (0.35, 0.05, 0.50)]
COLORS_OMBRES = [(0.20, 0.05, 0.40), (0.90, 0.20, 0.15), (1.00, 0.75, 0.20), (0.30, 0.80, 0.40)]


def build_grid(n_cols, n_files):
    """Graella plana de n_cols x n_files vertexs amb nomes coordenades UV (0..1).
    u = est (columnes), v = sud (files; v = 0 es la vora nord, com la fila 0 de la textura)."""
    u, v = np.meshgrid(np.linspace(0, 1, n_cols), np.linspace(0, 1, n_files))
    vertices = np.dstack([u, v]).reshape(-1, 2).astype('f4')

    i = np.arange(n_files * n_cols).reshape(n_files, n_cols)
    a, b = i[:-1, :-1], i[:-1, 1:]
    c, d = i[1:, :-1], i[1:, 1:]
    indices = np.stack([a, c, b, b, c, d], axis=-1).reshape(-1).astype('i4')
    return vertices, indices


def build_skirt(n_cols, n_files):
    """Faldilles: una paret vertical a cada vora del terreny.
    Fa servir els mateixos UV que els vertexs de la vora de la graella (aixi la part de dalt
    coincideix exactament amb el terreny) i cada punt surt dues vegades:
    base = 0 (a dalt, a l'altura del terreny) i base = 1 (a baix, a la cota base)."""
    us, vs = np.linspace(0, 1, n_cols), np.linspace(0, 1, n_files)
    vores = [(us, np.zeros(n_cols)),                # nord
             (np.ones(n_files), vs),                # est
             (us[::-1], np.ones(n_cols)),           # sud
             (np.zeros(n_files), vs[::-1])]         # oest
    vertices, indices, n = [], [], 0
    for u, v in vores:
        m = len(u)
        dalt = np.column_stack([u, v, np.zeros(m)])
        baix = np.column_stack([u, v, np.ones(m)])
        vertices.append(np.stack([dalt, baix], axis=1).reshape(-1, 3))  # dalt0, baix0, dalt1, baix1...
        k = n + 2 * np.arange(m - 1)
        indices.append(np.stack([k, k + 1, k + 2, k + 2, k + 1, k + 3], axis=-1).reshape(-1))
        n += 2 * m
    return np.concatenate(vertices).astype('f4'), np.concatenate(indices).astype('i4')


class Terrain:
    def __init__(self, app, path):
        self.app = app
        self.ctx = app.ctx
        d = data_io.carregar_terreny(path, self.ctx.info['GL_MAX_TEXTURE_SIZE'], MAX_VERTEXS)
        h, res_m, transform = d['alt'], d['res_m'], d['transform']
        files, cols = h.shape
        self.mida = glm.vec2(cols * res_m / 1000, files * res_m / 1000)  # (est, sud) en km
        mida_km = max(self.mida)
        self.cota_base = -0.015 * mida_km  # fons de les faldilles (km)

        # copies a la CPU per consultar altituds (camera enganxada al terreny, punt d'observacio)
        self.alt = h                        # resolucio completa
        self.alt_vertexs = d['alt_vertexs']  # la que fa servir la geometria (mitjana de blocs)
        self.max_height = float(h.max())
        self.origen_utm = (transform.c, transform.f)  # cantonada nord-oest, en metres
        self.crs = d['crs']
        self.a_latlon = Transformer.from_crs(self.crs, 'EPSG:4326', always_xy=True)

        # --- textures (fila 0 = nord = v 0). Totes amb mipmaps: de lluny es fa servir la mitjana.
        self.tex_altitud = self.make_texture(h, 1, 'f4')             # R32F, metres
        self.tex_gradient = self.make_texture(d['grad'], 2, 'f2')    # RG16F, dh/dx dh/dz
        self.tex_costa = self.make_texture(d['costa'], 1, 'f2')      # R16F, km (mar > 0)
        # overlays de l'eclipsi (mateixa extensio que el terreny, menys resolucio): si no hi ha
        # dades, textures d'1 pixel buides (el shader no hi dibuixa res)
        efem, ombres = d['ecl_efem'], d['ecl_ombres']
        if ombres.size == 0:
            efem, ombres = np.zeros((1, 1, 4), 'f2'), np.full((1, 1), eclipse_data.SENSE_DADES, 'u1')
        self.tex_eclipsi = self.make_texture(efem, 4, 'f2')          # RGBA16F: enfosq, durada, franja, valid
        # classes d'ombres: NEAREST i sense mipmaps (barrejar classes no te sentit)
        self.tex_ombres = self.ctx.texture((ombres.shape[1], ombres.shape[0]), 1, ombres.tobytes(),
                                           dtype='f1', alignment=1)
        self.tex_ombres.repeat_x = self.tex_ombres.repeat_y = False
        self.tex_ombres.filter = (mgl.NEAREST, mgl.NEAREST)

        # --- graella fixa, independent de la mida del fitxer (mante la proporcio del terreny)
        n_cols, n_files = d['n_cols'], d['n_files']
        vertices, indices = build_grid(n_cols, n_files)
        vertices_f, indices_f = build_skirt(n_cols, n_files)
        self.n_triangles = (len(indices) + len(indices_f)) // 3
        print(f"Textures {cols}x{files} px, graella {n_cols}x{n_files} vertexs, "
              f"{self.n_triangles} triangles (amb faldilles), altitud max {self.max_height:.0f} m")

        self.shader_program = self.get_shader_program()
        self.vbo = self.ctx.buffer(vertices)
        self.ibo = self.ctx.buffer(indices)
        # la graella nomes porta in_uv: in_base hi val 0 (valor per defecte d'un atribut sense buffer)
        self.vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '2f', 'in_uv')],
                                         index_buffer=self.ibo)
        self.vbo_faldilla = self.ctx.buffer(vertices_f)
        self.ibo_faldilla = self.ctx.buffer(indices_f)
        self.vao_faldilla = self.ctx.vertex_array(
            self.shader_program, [(self.vbo_faldilla, '2f 1f', 'in_uv', 'in_base')],
            index_buffer=self.ibo_faldilla)

        sp = self.shader_program
        sp['tex_altitud'].value, sp['tex_gradient'].value, sp['tex_costa'].value = 0, 1, 2
        sp['tex_eclipsi'].value, sp['tex_ombres'].value = 3, 4
        sp['enfosquiment_min'].value = ENFOSQUIMENT_MIN
        sp['colors_enfosquiment'].write(np.array(COLORS_ENFOSQUIMENT, 'f4').tobytes())
        sp['color_totalitat'].value = COLOR_TOTALITAT
        # rang de la rampa de durada: el de la franja dins d'aquest terreny, arrodonit a 10 s
        dur = d['ecl_efem'][..., 1][d['ecl_efem'][..., 2] > 0.5].astype('f4') if d['ecl_ombres'].size else []
        self.durada_min = 10 * math.floor(dur.min() / 10) if len(dur) else 0.0
        self.durada_max = max(10 * math.ceil(dur.max() / 10), self.durada_min + 10) if len(dur) else 120.0
        sp['durada_min'].value, sp['durada_max'].value = self.durada_min, self.durada_max
        sp['colors_durada'].write(np.array(COLORS_DURADA, 'f4').tobytes())
        sp['colors_ombres'].write(np.array(COLORS_OMBRES, 'f4').tobytes())
        sp['m_model'].write(glm.mat4())
        sp['mida_km'].write(self.mida)
        sp['lod_vertexs'].value = d['lod_vertexs']
        sp['cota_base'].value = self.cota_base
        sp['escala_mar'].value = 0.03 * mida_km    # a aquesta distancia de la costa el mar ja es fosc
        sp['color_cel'].value = COLOR_CEL

        self.visible = True
        self.wireframe = False
        # exageracio inicial segons l'escala: ~1.4 a 20 km, ~5 a 220 km, 10 a la peninsula
        self.exaggeration = min(10.0, max(1.0, (mida_km / 10) ** 0.5))
        self.sun_azimuth = 135.0     # graus des del nord, sentit horari
        self.sun_elevation = 35.0    # graus sobre l'horitzo
        self.boira = 0.35            # densitat relativa: la distancia es mesura en "mides de terreny"
        self.curvatura = False       # curvatura de la Terra (la posa el GraphicsEngine)
        self.centre_curvatura = glm.vec2(0.0)  # punt (x, z) sense caiguda: l'objectiu de la camera
        self.zones = []              # rectangles (u0, v0, u1, v1) de les zones de detall
        self.mostrar_zones = True
        self.overlay = 0             # index a OVERLAYS (0 = cap)
        self.opacitat = 0.6
        self.limits_totalitat = True

    # ------------------------------------------------------------ consultes a la CPU

    def altitud_m(self, x, z, alt=None):
        """Altitud (m) al punt (x, z) del mon (km), amb interpolacio bilineal com la de la GPU.
        Per defecte, del heightmap a resolucio completa; alt=self.alt_vertexs, la de la geometria."""
        alt = self.alt if alt is None else alt
        files, cols = alt.shape
        # mateix conveni que texture(): u = 0..1 sobre l'amplada i els texels tenen el centre a +0.5
        c = min(max((x / self.mida.x + 0.5) * cols - 0.5, 0.0), cols - 1.0)
        f = min(max((z / self.mida.y + 0.5) * files - 0.5, 0.0), files - 1.0)
        c0, f0 = min(int(c), cols - 2), min(int(f), files - 2)
        tc, tf = c - c0, f - f0
        a = alt[f0:f0 + 2, c0:c0 + 2]
        return float((a[0, 0] * (1 - tc) + a[0, 1] * tc) * (1 - tf) + (a[1, 0] * (1 - tc) + a[1, 1] * tc) * tf)

    def caiguda(self, x, z):
        """Quant baixa el punt (x, z) per la curvatura de la Terra: d^2 / (2R), en km.
        No es multiplica per l'exageracio (la Terra no es mes corbada perque exagerem el relleu)."""
        if not self.curvatura:
            return 0.0
        dx, dz = x - self.centre_curvatura.x, z - self.centre_curvatura.y
        return (dx * dx + dz * dz) / (2 * RADI_TERRA)

    def altitud_mon(self, x, z):
        """Y de la superficie dibuixada al punt (x, z), en km del mon: amb l'exageracio actual,
        el mar a 0 i, si esta activada, la caiguda per la curvatura (igual que el vertex shader)."""
        return max(self.altitud_m(x, z, self.alt_vertexs), 0.0) / 1000.0 * self.exaggeration - self.caiguda(x, z)

    def altitud_max_mon(self):
        return self.max_height / 1000.0 * self.exaggeration

    def info_punt(self, x, z):
        """Coordenades d'un punt del mon: UTM (CRS del fitxer), lat/lon (graus) i altitud (m)."""
        u, v = x / self.mida.x + 0.5, z / self.mida.y + 0.5
        x_utm = self.origen_utm[0] + u * self.mida.x * 1000
        y_utm = self.origen_utm[1] - v * self.mida.y * 1000
        lon, lat = self.a_latlon.transform(x_utm, y_utm)
        return dict(x=x, z=z, x_utm=x_utm, y_utm=y_utm, lat=lat, lon=lon, altitud=self.altitud_m(x, z))

    def uv_de_utm(self, x_utm, y_utm):
        """Coordenades UTM (m) -> (u, v) del terreny (0..1 dins del terreny)."""
        return ((x_utm - self.origen_utm[0]) / (self.mida.x * 1000),
                (self.origen_utm[1] - y_utm) / (self.mida.y * 1000))

    def mon_de_utm(self, x_utm, y_utm):
        """Coordenades UTM (m) -> (x, z) del mon (km), o None si el punt queda fora del terreny."""
        u, v = self.uv_de_utm(x_utm, y_utm)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            return None
        return (u - 0.5) * self.mida.x, (v - 0.5) * self.mida.y

    def make_texture(self, dades, components, dtype):
        files, cols = dades.shape[:2]
        tex = self.ctx.texture((cols, files), components, dades.tobytes(), dtype=dtype, alignment=1)
        tex.repeat_x = tex.repeat_y = False  # clamp to edge
        tex.build_mipmaps()
        tex.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        return tex

    def sun_direction(self):
        az, el = glm.radians(self.sun_azimuth), glm.radians(self.sun_elevation)
        # nord = -Z, est = +X
        return glm.vec3(glm.cos(el) * glm.sin(az), glm.sin(el), -glm.cos(el) * glm.cos(az))

    def render(self):
        if not self.visible:
            return
        cam = self.app.camera
        sp = self.shader_program
        sp['m_proj'].write(cam.m_proj)
        sp['m_view'].write(cam.m_view)
        sp['cam_pos'].write(cam.position)
        sp['exaggeration'].value = self.exaggeration
        sp['sun_dir'].write(self.sun_direction())
        # la boira comenca a la vora del terreny mes propera a la camera (aprox. distancia - mida/2):
        # aixi, allunyar-se no afegeix boira i el terreny sencer sempre es veu
        sp['densitat_boira'].value = self.boira / max(self.mida)
        sp['inici_boira'].value = max(0.0, cam.distance - 0.5 * max(self.mida))
        sp['curvatura'].value = self.curvatura
        sp['centre_curvatura'].write(self.centre_curvatura)
        zones = self.zones if self.mostrar_zones else []
        sp['n_zones'].value = len(zones)
        sp['zones'].write(np.array(zones + [(0, 0, 0, 0)] * (MAX_ZONES - len(zones)), dtype='f4').tobytes())
        self.tex_altitud.use(0)
        self.tex_gradient.use(1)
        self.tex_costa.use(2)
        self.tex_eclipsi.use(3)
        self.tex_ombres.use(4)
        sp['overlay'].value = self.overlay
        sp['opacitat'].value = self.opacitat
        sp['limits_totalitat'].value = self.limits_totalitat
        self.ctx.wireframe = self.wireframe
        sp['es_faldilla'].value = False
        self.vao.render()
        sp['es_faldilla'].value = True
        self.vao_faldilla.render()
        self.ctx.wireframe = False

    def destroy(self):
        for obj in (self.vbo, self.ibo, self.vao, self.vbo_faldilla, self.ibo_faldilla,
                    self.vao_faldilla, self.shader_program,
                    self.tex_altitud, self.tex_gradient, self.tex_costa, self.tex_eclipsi, self.tex_ombres):
            obj.release()

    def get_shader_program(self):
        return self.ctx.program(
            vertex_shader='''
                #version 330
                layout (location = 0) in vec2 in_uv;
                layout (location = 1) in float in_base;  // faldilles: 0 = a dalt, 1 = a la cota base
                out vec2 uv;
                out vec3 pos_mon;   // posicio en km (per a la boira i les normals de les faldilles)
                out float base;
                uniform mat4 m_proj;
                uniform mat4 m_view;
                uniform mat4 m_model;
                uniform sampler2D tex_altitud;
                uniform vec2 mida_km;        // mida del terreny (est, sud) en km
                uniform float lod_vertexs;   // nivell de mipmap: mitjana de l'area de cada vertex
                uniform float exaggeration;
                uniform float cota_base;     // altura (km) del fons de les faldilles
                uniform bool curvatura;
                uniform vec2 centre_curvatura;  // (x, z) de l'objectiu de la camera: alli no hi ha caiguda
                const float RADI_TERRA = 6371.0;
                void main() {
                    uv = in_uv;
                    base = in_base;
                    float h = textureLod(tex_altitud, in_uv, lod_vertexs).r;  // metres
                    vec2 xz = (in_uv - 0.5) * mida_km;
                    float y = mix(max(h, 0.0) / 1000.0 * exaggeration, cota_base, in_base);
                    if (curvatura) {
                        // la Terra es corba: a distancia d el terra baixa d^2/(2R) (sense exageracio)
                        vec2 d = xz - centre_curvatura;
                        y -= dot(d, d) / (2.0 * RADI_TERRA);
                    }
                    vec4 p = m_model * vec4(xz.x, y, xz.y, 1.0);
                    pos_mon = p.xyz;
                    gl_Position = m_proj * m_view * p;
                }
            ''',
            fragment_shader='''
                #version 330
                layout (location = 0) out vec4 fragColor;
                in vec2 uv;
                in vec3 pos_mon;
                in float base;
                uniform sampler2D tex_altitud;
                uniform sampler2D tex_gradient;
                uniform sampler2D tex_costa;
                uniform float exaggeration;
                uniform vec3 sun_dir;
                uniform vec3 cam_pos;
                uniform vec3 color_cel;
                uniform float densitat_boira;   // 1/km
                uniform float inici_boira;      // km: fins a aquesta distancia no hi ha boira
                uniform float escala_mar;       // km
                uniform bool es_faldilla;
                uniform vec4 zones[4];          // rectangles de les zones de detall en UV (u0, v0, u1, v1)
                uniform int n_zones;
                // eclipsi
                uniform sampler2D tex_eclipsi;  // RGBA: enfosquiment, durada (s), franja (0/1), valid (0/1)
                uniform sampler2D tex_ombres;   // classe d'ombres del CNIG / 255 (NEAREST); 255 = sense dades
                uniform int overlay;            // 0 cap, 1 enfosquiment, 2 durada, 3 ombres
                uniform float opacitat;
                uniform bool limits_totalitat;
                uniform float enfosquiment_min;
                uniform vec3 colors_enfosquiment[4];
                uniform vec3 color_totalitat;
                uniform float durada_min;
                uniform float durada_max;
                uniform vec3 colors_durada[5];
                uniform vec3 colors_ombres[4];

                // rampa hipsometrica absoluta: la mateixa altitud te el mateix color a tots els fitxers
                const float COTES[6] = float[](0.0, 200.0, 600.0, 1200.0, 2000.0, 3000.0);
                const vec3 COLORS[6] = vec3[](
                    vec3(0.17, 0.40, 0.20),   //    0 m: verd fosc de costa
                    vec3(0.33, 0.54, 0.25),   //  200 m: verd
                    vec3(0.62, 0.66, 0.38),   //  600 m: verd groguenc (meseta)
                    vec3(0.62, 0.50, 0.33),   // 1200 m: marro
                    vec3(0.56, 0.52, 0.49),   // 2000 m: roca grisa
                    vec3(0.96, 0.96, 0.97));  // 3000 m: neu
                vec3 rampa(float h) {
                    for (int i = 1; i < 6; i++)
                        if (h < COTES[i])
                            return mix(COLORS[i - 1], COLORS[i], clamp((h - COTES[i - 1]) / (COTES[i] - COTES[i - 1]), 0.0, 1.0));
                    return COLORS[5];
                }

                // distancia en pixels de pantalla a la vora del rectangle r (molt gran si es lluny)
                float pixels_a_vora(vec4 r) {
                    vec2 px = max(fwidth(uv), vec2(1e-7));   // quant UV hi ha en un pixel
                    float dx = min(abs(uv.x - r.x), abs(uv.x - r.z)) / px.x;
                    float dy = min(abs(uv.y - r.y), abs(uv.y - r.w)) / px.y;
                    bool dins_x = uv.x >= r.x && uv.x <= r.z;
                    bool dins_y = uv.y >= r.y && uv.y <= r.w;
                    return min(dins_y ? dx : 1e9, dins_x ? dy : 1e9);
                }

                // color (rgb) i opacitat propia (a) de l'overlay actiu en aquest punt
                vec4 color_overlay() {
                    vec4 e = texture(tex_eclipsi, uv);
                    float franja = smoothstep(0.4, 0.6, e.b);
                    if (overlay == 1) {
                        // rampa continua de enfosquiment_min a 1 en 3 trams; la totalitat, d'un color a part
                        float t = clamp((e.r - enfosquiment_min) / (1.0 - enfosquiment_min), 0.0, 1.0) * 3.0;
                        int i = min(int(t), 2);
                        vec3 c = mix(colors_enfosquiment[i], colors_enfosquiment[i + 1], t - float(i));
                        return vec4(mix(c, color_totalitat, franja), e.a);
                    }
                    if (overlay == 2) {
                        float t = clamp((e.g - durada_min) / (durada_max - durada_min), 0.0, 1.0) * 4.0;  // 5 colors, 4 trams
                        int i = min(int(t), 3);
                        vec3 c = mix(colors_durada[i], colors_durada[i + 1], t - float(i));
                        // corbes de durada cada 10 s (com les de la capa durtot del GeoPackage)
                        float l = e.g / 10.0;
                        float px = abs(fract(l - 0.5) - 0.5) / max(fwidth(l), 1e-6);
                        c *= mix(0.45, 1.0, smoothstep(0.5, 1.5, px));
                        return vec4(c, franja * e.a);
                    }
                    if (overlay == 3) {
                        int classe = int(texture(tex_ombres, uv).r * 255.0 + 0.5);
                        if (classe > 3) return vec4(0.0);  // sense dades: transparent
                        return vec4(colors_ombres[classe], 1.0);
                    }
                    return vec4(0.0);
                }

                void main() {
                    vec3 sol = normalize(sun_dir);
                    float d = texture(tex_costa, uv).r;          // km a la costa (mar > 0, terra < 0)
                    // aigua: mes clara a prop de la costa, mes fosca mar endins; menys llum amb el Sol baix
                    vec3 aigua = mix(vec3(0.16, 0.42, 0.58), vec3(0.04, 0.14, 0.32), 1.0 - exp(-max(d, 0.0) / escala_mar));
                    aigua *= 0.5 + 0.5 * max(sol.y, 0.0);
                    vec3 color;

                    if (es_faldilla) {
                        // normal plana de la paret a partir de les derivades de la posicio; girada cap a la camera
                        vec3 n = normalize(cross(dFdx(pos_mon), dFdy(pos_mon)));
                        if (dot(n, cam_pos - pos_mon) < 0.0) n = -n;
                        vec3 paret = d > 0.0 ? aigua * 0.6 : mix(vec3(0.45, 0.35, 0.25), vec3(0.22, 0.16, 0.11), base);
                        color = paret * (0.35 + 0.65 * max(dot(n, sol), 0.0));
                    } else {
                        float height = texture(tex_altitud, uv).r;
                        vec2 g = texture(tex_gradient, uv).rg;   // (dh/dx, dh/dz) a resolucio completa
                        // superficie y = k*h(x,z) -> normal = (-k*dh/dx, 1, -k*dh/dz), exacta per a qualsevol k
                        vec3 normal = normalize(vec3(-exaggeration * g.x, 1.0, -exaggeration * g.y));
                        vec3 terra = rampa(height) * (0.25 + 0.75 * max(dot(normal, sol), 0.0));
                        // costa: la distancia filtrada es suau, aixi el pas terra -> mar no fa escales.
                        // fwidth = quant canvia d en un pixel de pantalla -> transicio d'1 pixel (antialias)
                        float w = max(fwidth(d), 1e-6);
                        color = mix(terra, aigua, smoothstep(-w, w, d));

                        // vores de les zones de detall: linies de ~2 pixels dibuixades sobre el relleu
                        for (int i = 0; i < n_zones; i++)
                            color = mix(vec3(1.0, 0.25, 0.10), color, smoothstep(1.0, 2.0, pixels_a_vora(zones[i])));

                        // overlay de l'eclipsi
                        vec4 o = color_overlay();
                        color = mix(color, o.rgb, opacitat * o.a);
                        // limits de la franja de totalitat: on la mascara (filtrada, suau) passa per 0.5
                        if (limits_totalitat) {
                            float b = texture(tex_eclipsi, uv).b;
                            float px = abs(b - 0.5) / max(fwidth(b), 1e-6);
                            color = mix(vec3(1.0), color, smoothstep(1.0, 2.0, px));
                        }
                    }

                    // boira exponencial quadratica segons la distancia a la camera (a partir d'inici_boira)
                    float f = exp(-pow(max(length(pos_mon - cam_pos) - inici_boira, 0.0) * densitat_boira, 2.0));
                    fragColor = vec4(mix(color_cel, color, f), 1.0);
                }
            ''',
        )


def limits_utm(llista):
    """Limits UTM (rasterio BoundingBox) de cada fitxer de la llista, sense carregar-ne les dades."""
    limits = {}
    for nom, cami, _ in llista:
        with rasterio.open(cami) as f:
            limits[nom] = f.bounds
    return limits


def zones_de_detall(terrain, llista, limits):
    """Rectangles (u0, v0, u1, v1) de les zones de detall de la llista que caben dins del terreny."""
    zones = []
    for nom, _, detall in llista:
        b = limits[nom]
        u0, v0 = terrain.uv_de_utm(b.left, b.top)
        u1, v1 = terrain.uv_de_utm(b.right, b.bottom)
        if detall and 0 <= u0 and u1 <= 1 and 0 <= v0 and v1 <= 1 and len(zones) < MAX_ZONES:
            zones.append((u0, v0, u1, v1))
    return zones


class GraphicsEngine(GraphicsEngineBase):
    def on_init(self):
        self.ctx.enable_only(mgl.DEPTH_TEST)  # sense CULL_FACE: el terreny es veu per sota tambe
        self.llista = [t for t in TERRENYS if os.path.exists(t[1])]
        for nom, cami, _ in TERRENYS:
            if not os.path.exists(cami):
                print(f"AVIS: no hi ha {cami}; el terreny '{nom}' no surt al selector")
        if len(sys.argv) > 1:  # un MDT passat per la linia de comandes
            self.llista.append(('Fitxer', os.path.abspath(sys.argv[1]), False))
        self.limits = limits_utm(self.llista)  # per als rectangles de les zones de detall

        self.terrenys = {}           # nom -> Terrain, es carreguen la primera vegada que es trien
        self.terrain = None
        self.camera = None
        self.curvatura = False
        self.punt_observacio = None  # ultim punt triat amb doble clic (es fara servir a la T6)
        self.seleccionar(self.llista[-1][0] if len(sys.argv) > 1 else self.llista[0][0])

        # resize: el nostre callback crida tambe l'anterior (si n'hi ha) per no trencar res
        self.resize_anterior = glfw.set_framebuffer_size_callback(self.window, self.on_resize)
        self.fps, self.frames, self.temps_fps = 0.0, 0, 0.0

    def seleccionar(self, nom):
        """Canvia al terreny 'nom' (el carrega si es la primera vegada). Si l'objectiu de la camera
        tambe cau dins del terreny nou, es mante el mateix punt geografic (via coordenades UTM)."""
        anterior = self.terrain
        info = anterior.info_punt(self.camera.target.x, self.camera.target.z) if anterior else None

        if nom not in self.terrenys:
            t0 = time.time()
            cami = next(c for n, c, _ in self.llista if n == nom)
            self.terrenys[nom] = Terrain(self, cami)
            print(f"Terreny '{nom}' carregat en {time.time() - t0:.1f} s")
        t = self.terrain = self.terrenys[nom]
        self.nom_terreny = nom

        es_detall = any(n == nom and detall for n, _, detall in self.llista)
        t.zones = [] if es_detall else zones_de_detall(t, self.llista, self.limits)

        punt = None
        if info is not None and anterior.crs == t.crs:
            punt = t.mon_de_utm(info['x_utm'], info['y_utm'])
        if self.camera is None:
            self.camera = Camera(self, t)
        else:
            self.camera.canviar_terreny(t, punt)

    def on_resize(self, window, amplada, alcada):
        if self.resize_anterior:
            self.resize_anterior(window, amplada, alcada)
        if amplada == 0 or alcada == 0:  # finestra minimitzada
            return
        self.ctx.viewport = (0, 0, amplada, alcada)
        self.camera.aspect_ratio = amplada / alcada
        self.camera.update()

    def drawables(self):
        return [self.terrain]

    def on_destroy(self):
        # el terreny actual l'allibera GraphicsEngineBase (es a drawables); aqui, la resta
        for t in self.terrenys.values():
            if t is not self.terrain:
                t.destroy()

    def punt_sota_cursor(self):
        """Picking: llegeix la profunditat del pixel sota el cursor i la desprojecta.
        Retorna el punt del mon (glm.vec3, km) o None si el cursor apunta al cel."""
        io = imgui.get_io()
        escala_x, escala_y = io.display_framebuffer_scale       # retina: 2 pixels per punt
        _, _, amplada, alcada = self.ctx.viewport
        px = int(io.mouse_pos[0] * escala_x)
        py = alcada - 1 - int(io.mouse_pos[1] * escala_y)       # glfw: y cap avall; GL: y cap amunt
        if not (0 <= px < amplada and 0 <= py < alcada):
            return None
        dades = self.ctx.screen.read(viewport=(px, py, 1, 1), components=1, attachment=-1, dtype='f4')
        profunditat = float(np.frombuffer(dades, dtype='f4')[0])
        if profunditat >= 1.0:  # no hi ha res dibuixat (cel)
            return None
        return self.camera.desprojectar(px + 0.5, py + 0.5, profunditat, amplada, alcada)

    def triar_punt(self, x, z):
        """Punt d'observacio: coordenades del punt (x, z) del terreny actual i, si hi ha el dataset,
        els valors de l'eclipsi llegits dels GeoTIFF originals en aquell punt."""
        p = self.terrain.info_punt(x, z)
        p['eclipsi'] = eclipse_data.punt(p['lat'], p['lon']) if eclipse_data.disponible() else None
        self.punt_observacio = p

    def render(self):
        self.terrain.curvatura = self.curvatura
        self.camera.update()  # l'objectiu segueix el terreny si canvia l'exageracio o la curvatura
        self.ctx.clear(color=COLOR_CEL)
        self.terrain.render()
        # el ratoli es processa just despres de dibuixar el terreny: el depth buffer ja es ple
        punt = self.camera.processar_ratoli(self.punt_sota_cursor)
        if punt is not None:
            self.triar_punt(punt.x, punt.z)
        # FPS: mitjana de cada mig segon (self.dt el calcula GraphicsEngineBase)
        self.frames += 1
        self.temps_fps += self.dt
        if self.temps_fps >= 0.5:
            self.fps = self.frames / self.temps_fps
            self.frames, self.temps_fps = 0, 0.0

    def build_ui(self):
        imgui.text(f'FPS: {self.fps:.0f} ({1000 / max(self.fps, 1e-6):.1f} ms)')
        imgui.text(f'Triangles: {self.terrain.n_triangles / 1e6:.2f} M')
        imgui.separator()
        imgui.text('Terreny (la primera vegada es carrega)')
        for i, (nom, _, _) in enumerate(self.llista):
            if i > 0:
                imgui.same_line()
            if imgui.radio_button(nom, nom == self.nom_terreny) and nom != self.nom_terreny:
                self.seleccionar(nom)
        t, cam = self.terrain, self.camera
        if t.zones:
            _, t.mostrar_zones = imgui.checkbox('Zones de detall', t.mostrar_zones)
        _, self.curvatura = imgui.checkbox('Curvatura de la Terra', self.curvatura)
        imgui.separator()
        imgui.text('Camera')
        _, cam.yaw = imgui.slider_float('Gir', cam.yaw, -180, 180)
        _, cam.pitch = imgui.slider_float('Inclinacio', cam.pitch, 1, 89)
        _, cam.distance = imgui.slider_float('Distancia (km)', cam.distance, cam.dist_min, cam.dist_max,
                                             '%.2f', imgui.SliderFlags.LOGARITHMIC)
        if imgui.button('Reiniciar camera'):
            cam.reset()
        cam.update()
        objectiu = t.info_punt(cam.target.x, cam.target.z)
        imgui.text(f"Objectiu: {objectiu['lat']:.4f}, {objectiu['lon']:.4f}  {objectiu['altitud']:.0f} m")
        imgui.text(f'near {cam.near * 1000:.1f} m  far {cam.far:.0f} km')
        imgui.separator()
        imgui.text('Punt d\'observacio (doble clic)')
        p = self.punt_observacio
        if p is None:
            imgui.text('  cap punt seleccionat')
        else:
            imgui.text(f"  UTM {p['x_utm']:.0f} E  {p['y_utm']:.0f} N ({t.crs})")
            imgui.text(f"  lat {p['lat']:.5f}  lon {p['lon']:.5f}")
            imgui.text(f"  altitud {p['altitud']:.0f} m")
            self.panell_eclipsi_punt(p.get('eclipsi'))
        imgui.separator()
        self.panell_overlays()
        imgui.separator()
        imgui.text('Terreny')
        _, t.exaggeration = imgui.slider_float('Exageracio Y', t.exaggeration, 1, 20)
        _, t.boira = imgui.slider_float('Boira', t.boira, 0, 1)
        _, t.wireframe = imgui.checkbox('Filferros', t.wireframe)
        imgui.separator()
        imgui.text('Sol')
        _, t.sun_azimuth = imgui.slider_float('Azimut', t.sun_azimuth, 0, 360)
        _, t.sun_elevation = imgui.slider_float('Elevacio', t.sun_elevation, -5, 90)
        imgui.separator()
        imgui.text_disabled('Eclipsi: informacio astronomica oficial')
        imgui.text_disabled('IGN / Observatori Astronomic Nacional (CC BY 4.0)')
        imgui.text_disabled('MDT (c) IGN / CNIG')

    def panell_eclipsi_punt(self, e):
        """Valors de l'eclipsi al punt d'observacio (hores en CEST = TU + 2)."""
        if e is None:
            imgui.text('  (sense dades de l\'eclipsi en aquest punt)')
            return
        imgui.text(f"  Sol al maxim: azimut {e['azimut']:.1f}  elevacio {e['elevacio']:.1f} graus")
        imgui.text(f"  Enfosquiment maxim: {e['enfosquiment'] * 100:.2f} %")
        for nom, hora, visible in e['fases']:
            if visible:
                imgui.text(f"  {nom}: {hora}")
            else:
                imgui.text_colored((1.0, 0.6, 0.3, 1.0), f"  {nom}: {hora} (no visible: el Sol ja s'ha post)")
        if e['durada'] is not None:
            imgui.text(f"  Durada de la totalitat: {e['durada']:.1f} s")
        else:
            imgui.text('  Fora de la franja de totalitat')
        imgui.text(f"  Posta del Sol: {e['posta']}   (hores CEST = TU+2)")
        imgui.text(f"  Ombres CNIG: {e['text_ombres']}")
        if imgui.button("Sol al maxim de l'eclipsi"):
            self.terrain.sun_azimuth, self.terrain.sun_elevation = e['azimut'], e['elevacio']

    def panell_overlays(self):
        """Overlays de l'eclipsi (un de cada vegada), opacitat i llegenda dels colors."""
        t = self.terrain
        imgui.text("Eclipsi sobre el terreny")
        for i, nom in enumerate(OVERLAYS):
            if i % 2 == 1:
                imgui.same_line()
            if imgui.radio_button(nom, t.overlay == i):
                t.overlay = i
        if t.overlay:
            _, t.opacitat = imgui.slider_float('Opacitat', t.opacitat, 0, 1)
        _, t.limits_totalitat = imgui.checkbox('Limits de la totalitat', t.limits_totalitat)

        def llegenda(color, text):
            imgui.color_button(f'##{text}', (*color, 1.0), imgui.ColorEditFlags.NO_TOOLTIP, (14, 14))
            imgui.same_line()
            imgui.text(text)

        if t.overlay == 1:
            passos = [ENFOSQUIMENT_MIN + (1 - ENFOSQUIMENT_MIN) * k / 3 for k in range(4)]
            for color, valor in zip(COLORS_ENFOSQUIMENT, passos):
                llegenda(color, f'{valor * 100:.1f} %')
            llegenda(COLOR_TOTALITAT, 'totalitat (100 %)')
        elif t.overlay == 2:
            for k, color in enumerate(COLORS_DURADA):
                llegenda(color, f'{t.durada_min + (t.durada_max - t.durada_min) * k / 4:.0f} s')
            imgui.text_disabled('  linies cada 10 s; nomes dins la franja')
        elif t.overlay == 3:
            for classe, color in enumerate(COLORS_OMBRES):
                llegenda(color, f'{classe}: {eclipse_data.CLASSES_OMBRES[classe]}')
            imgui.text_disabled('  sense color: sense dades')


if __name__ == '__main__':
    app = GraphicsEngine(win_size=(1200, 900), title="EGRA - Terreny MDT", use_ui_panel=True)
    app.run()
