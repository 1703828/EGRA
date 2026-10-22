"""
Terreny: MDT dibuixat amb un heightmap com a textura (T2-T6).

- La geometria es una graella plana fixa (com a maxim MAX_VERTEXS x MAX_VERTEXS vertexs) amb
  nomes coordenades UV; el vertex shader hi llegeix l'altura (basecode/shaders/terrain.vert).
- Les normals es fan al fragment shader amb el pendent a la resolucio del fitxer (5 m), i alla
  tambe hi ha la rampa de colors, el mar, les faldilles, la boira, les zones de detall i els
  overlays de l'eclipsi (basecode/shaders/terrain.frag).
- Segueix l'estructura dels objectes del repte 4 (get_vbo, get_vao, get_shader_program, on_init,
  render, destroy); el Sol es app.light (sol.py) i la camera escriu m_proj i m_view.
- Copies a la CPU de l'altitud per a la camera (enganxada al terreny) i el punt d'observacio.
- Dos modes. Pla (globus=False): el terreny es un rectangle en km amb l'origen al centre (el fan
  servir scripts/captura.py i l'exercici 1.0). Globus (globus=True, main.py): cada vertex es posa a
  la seva latitud i longitud reals sobre l'el·lipsoide WGS84, en coordenades terrestres (ECEF), i
  la llum i l'ombra de la Lluna es calculen per a cada punt. Les posicions es guarden relatives a
  l'origen del terreny (float32 n'hi ha prou) i es dibuixen relatives a la camera.
- Al mode globus, l'altura de cada vertex la calcula la CPU (atribut in_h) en lloc de llegir-la el
  vertex shader de la textura: aixi la CPU sap exactament quins triangles es dibuixen, i els ulls de
  l'observador es poden posar a 1,7 m de la superficie dibuixada (alcada_dibuixada).
- Nivells de detall (mode globus): la graella general del fitxer (com a maxim MAX_VERTEXS per costat)
  i un pegat dens al voltant de l'observador, amb un vertex per pixel del fitxer (MIDA_PEGAT pixels
  per costat). La graella general no es dibuixa dins del pegat ni dins dels terrenys mes detallats
  que hi ha a sobre (forats). A la vora de cada nivell, l'altura passa suaument a la del nivell de
  sota (transicio), perque no hi hagi esglaons ni escletxes.
"""
import os
import math

import glm
import numpy as np
import moderngl as mgl
import rasterio
from pyproj import Transformer

from . import shaders
from .programes import carregar_programa
from dades import data_io, eclipse_data, geodesia

MAX_VERTEXS = 1024              # vertexs maxims per costat de la graella
MAX_ZONES = 4                   # rectangles de zones de detall que pot dibuixar el shader
MAX_FORATS = 4                  # rectangles on el terreny no es dibuixa (mode globus)
MIDA_PEGAT = 512                # pixels del fitxer per costat del pegat dens al voltant de l'observador
TRANSICIO = 0.12                # fraccio de cada nivell (des de la vora) on l'altura passa a la del de sota
FALDILLA_GLOBUS_KM = 0.03       # al mode globus, les faldilles baixen 30 m per sota de la vora
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


def mostrejar_bilineal(alt, us, vs):
    """Altitud (m) a les UV (arrays) amb interpolacio bilineal, amb el conveni de texture(): el pixel
    k te el centre a u = (k + 0.5) / pixels."""
    files, cols = alt.shape
    c = np.clip(us * cols - 0.5, 0.0, cols - 1.0)
    f = np.clip(vs * files - 0.5, 0.0, files - 1.0)
    c0, f0 = np.minimum(c.astype(int), cols - 2), np.minimum(f.astype(int), files - 2)
    tc, tf = c - c0, f - f0
    return ((alt[f0, c0] * (1 - tc) + alt[f0, c0 + 1] * tc) * (1 - tf)
            + (alt[f0 + 1, c0] * (1 - tc) + alt[f0 + 1, c0 + 1] * tc) * tf)


def interpolar_triangles(h, finestra, us, vs):
    """Altura sobre els triangles d'una graella (la que es dibuixa): h[fila, columna] son les altures
    dels vertexs, repartits uniformement dins de finestra = (u0, v0, u1, v1). Cada cel·la a, b (a dalt)
    i c, d (a baix) es parteix pel diagonal b-c en els triangles (a, c, b) i (b, c, d), com build_grid."""
    files, cols = h.shape
    u0, v0, u1, v1 = finestra
    s = np.clip((us - u0) / (u1 - u0) * (cols - 1), 0.0, cols - 1.0)
    t = np.clip((vs - v0) / (v1 - v0) * (files - 1), 0.0, files - 1.0)
    i, j = np.minimum(s.astype(int), cols - 2), np.minimum(t.astype(int), files - 2)
    fs, ft = s - i, t - j
    ha, hb, hc, hd = h[j, i], h[j, i + 1], h[j + 1, i], h[j + 1, i + 1]
    return np.where(fs + ft <= 1.0, ha + fs * (hb - ha) + ft * (hc - ha),
                    hd + (1 - fs) * (hc - hd) + (1 - ft) * (hb - hd))


def pes_transicio(us, vs, finestra, amplada):
    """0 a la vora de la finestra i 1 a partir d'amplada (fraccio de la finestra) cap a dins."""
    u0, v0, u1, v1 = finestra
    d = np.minimum.reduce([(us - u0) / (u1 - u0), (u1 - us) / (u1 - u0), (vs - v0) / (v1 - v0), (v1 - vs) / (v1 - v0)])
    x = np.clip(d / amplada, 0.0, 1.0)
    return x * x * (3 - 2 * x)


class Terrain:
    def __init__(self, app, path, globus=False):
        self.app = app
        self.ctx = app.ctx
        self.globus = globus
        self.cami = path
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
        self.de_latlon = Transformer.from_crs('EPSG:4326', self.crs, always_xy=True)

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

        # rang de la rampa de durada: el de la franja dins d'aquest terreny, arrodonit a 10 s
        dur = d['ecl_efem'][..., 1][d['ecl_efem'][..., 2] > 0.5].astype('f4') if d['ecl_ombres'].size else []
        self.durada_min = 10 * math.floor(dur.min() / 10) if len(dur) else 0.0
        self.durada_max = max(10 * math.ceil(dur.max() / 10), self.durada_min + 10) if len(dur) else 120.0

        # --- objecte OpenGL, com els del repte 4: VBO/IBO + shader program + VAO + m_model
        self.n_cols, self.n_files = d['n_cols'], d['n_files']  # graella fixa, independent de la mida del fitxer
        self.lod_vertexs = d['lod_vertexs']
        if globus:
            # origen del terreny: el seu centre sobre l'el·lipsoide (km, ECEF, float64)
            lon_c, lat_c = self.a_latlon.transform(*self.utm_de_uv(0.5, 0.5))
            self.origen_ecef = geodesia.ecef(lat_c, lon_c, 0.0)
        self.vbo, self.ibo, self.vbo_faldilla, self.ibo_faldilla = self.get_vbo()
        self.shader_program = self.get_shader_program()
        self.vao, self.vao_faldilla = self.get_vao()
        self.m_model = self.get_model_matrix()
        print(f"Textures {cols}x{files} px, graella {self.n_cols}x{self.n_files} vertexs, "
              f"{self.n_triangles} triangles (amb faldilles), altitud max {self.max_height:.0f} m")

        self.visible = True
        self.wireframe = False
        # exageracio inicial segons l'escala: ~1.4 a 20 km, ~5 a 220 km, 10 a la peninsula
        self.exaggeration = min(10.0, max(1.0, (mida_km / 10) ** 0.5))
        self.boira = 0.35            # densitat relativa: la distancia es mesura en "mides de terreny"
        self.curvatura = False       # curvatura de la Terra (la posa el GraphicsEngine)
        self.centre_curvatura = glm.vec2(0.0)  # punt (x, z) sense caiguda: l'objectiu de la camera
        self.zones = []              # rectangles (u0, v0, u1, v1) de les zones de detall
        self.mostrar_zones = True
        self.overlay = 0             # index a OVERLAYS (0 = cap)
        self.opacitat = 0.6
        self.limits_totalitat = True
        # mode globus: nivells de detall (els posa el GraphicsEngine)
        self.pare = None             # terreny menys detallat que hi ha a sota (la peninsula), o None
        self.fills = []              # terrenys mes detallats a sobre: aqui no es dibuixa (forats)
        self.pegat = None            # pegat dens al voltant de l'observador (posar_pegat)
        self.dibuixar_mar = False    # True: el mar del fitxer es dibuixa a 0 m (si no, es veu el globus)
        # llum de l'eclipsi (la posa el GraphicsEngine): 1, 1 i COLOR_CEL = dia normal
        self.llum_sol = 1.0
        self.llum_cel = 1.0
        self.color_cel = COLOR_CEL
        self.on_init()

    # ------------------------------------------------------------ objecte OpenGL

    def get_vertex_data(self):
        """Graella i faldilles: (vertexs, indexs) de cadascuna."""
        return build_grid(self.n_cols, self.n_files), build_skirt(self.n_cols, self.n_files)

    def get_vbo(self):
        (vertices, indices), (vertices_f, indices_f) = self.get_vertex_data()
        self.n_triangles = (len(indices) + len(indices_f)) // 3
        if self.globus:
            # cada vertex porta, a mes de la UV, la seva posicio sobre l'el·lipsoide, la vertical i la
            # direccio de les columnes (9 floats mes)
            g, g_f = self.atributs_globus(vertices[:, 0], vertices[:, 1]), self.atributs_globus(vertices_f[:, 0], vertices_f[:, 1])
            vertices = np.hstack([vertices, g]).astype('f4')
            vertices_f = np.hstack([vertices_f, g_f]).astype('f4')
            # altura de cada vertex (m), calculada a la CPU: la mitjana per blocs del fitxer (com el nivell
            # de mipmap que llegeix el mode pla) als vertexs. Va en un buffer a part perque la transicio
            # amb el pare pot canviar quan canvia el pegat del pare.
            self.finestra = (0.0, 0.0, 1.0, 1.0)
            self.h_graella_original = np.maximum(mostrejar_bilineal(
                self.alt_vertexs, vertices[:, 0], vertices[:, 1]), 0.0).reshape(self.n_files, self.n_cols)
            self.h_graella = self.h_graella_original.copy()
            self.vbo_h = self.ctx.buffer(self.h_graella.astype('f4'))
            self.vbo_h_faldilla = self.ctx.buffer(reserve=len(vertices_f) * 4)
            self.uv_faldilla = vertices_f[:, :2]
            self.vbo_h_faldilla.write(self.alcades_faldilla(self.h_graella, self.finestra, self.uv_faldilla))
        return (self.ctx.buffer(vertices), self.ctx.buffer(indices),
                self.ctx.buffer(vertices_f), self.ctx.buffer(indices_f))

    @staticmethod
    def alcades_faldilla(h, finestra, uv):
        """Altura (m) dels vertexs de les faldilles: la de la vora de la graella al mateix punt."""
        return np.maximum(interpolar_triangles(h, finestra, uv[:, 0], uv[:, 1]), 0.0).astype('f4').tobytes()

    def get_vao(self):
        # la graella porta in_uv (+ els atributs del globus): in_base hi val 0 (valor per defecte d'un
        # atribut sense buffer)
        g = ' 3f 3f 3f' if self.globus else ''
        noms_g = ('in_offset', 'in_amunt', 'in_tx') if self.globus else ()
        h, h_f = ([(self.vbo_h, '1f', 'in_h')], [(self.vbo_h_faldilla, '1f', 'in_h')]) if self.globus else ([], [])
        vao = self.ctx.vertex_array(self.shader_program, [(self.vbo, '2f' + g, 'in_uv', *noms_g)] + h,
                                    index_buffer=self.ibo)
        vao_faldilla = self.ctx.vertex_array(
            self.shader_program, [(self.vbo_faldilla, '2f 1f' + g, 'in_uv', 'in_base', *noms_g)] + h_f,
            index_buffer=self.ibo_faldilla)
        return vao, vao_faldilla

    def utm_de_uv(self, u, v):
        """UV del terreny (0..1) -> coordenades UTM (m), amb el mateix conveni que info_punt."""
        return (self.origen_utm[0] + u * self.mida.x * 1000, self.origen_utm[1] - v * self.mida.y * 1000)

    def atributs_globus(self, us, vs, desar=True):
        """Per a cada UV: posicio sobre l'el·lipsoide relativa a l'origen (km), vertical del lloc i
        direccio de les columnes (cap on creix u), en ECEF. Es desa a data/cache/<nom>.globus_<n>.npz
        (el pegat, que canvia amb l'observador, no: desar=False)."""
        nom = os.path.splitext(os.path.basename(self.cami))[0]
        cache = os.path.join(data_io.DIR_CACHE, f'{nom}.globus_{len(us)}_{self.n_cols}x{self.n_files}.npz')
        if desar and os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(self.cami):
            with np.load(cache) as z:
                return z['g']
        def ecef_de_uv(u, v):
            lon, lat = self.a_latlon.transform(*self.utm_de_uv(u, v))
            return geodesia.ecef(lat, lon, 0.0), lat, lon
        p, lat, lon = ecef_de_uv(us, vs)
        du = 0.5 / self.n_cols
        tx = ecef_de_uv(us + du, vs)[0] - ecef_de_uv(us - du, vs)[0]
        tx /= np.linalg.norm(tx, axis=1, keepdims=True)
        fi, la = np.radians(lat), np.radians(lon)
        amunt = np.stack([np.cos(fi) * np.cos(la), np.cos(fi) * np.sin(la), np.sin(fi)], axis=1)
        g = np.hstack([p - self.origen_ecef, amunt, tx]).astype('f4')
        if desar:
            os.makedirs(data_io.DIR_CACHE, exist_ok=True)
            np.savez(cache, g=g)
        return g

    def get_shader_program(self):
        # el shader viu a basecode/shaders/terrain.vert i .frag (editable sense tocar Python);
        # al mode globus es compila amb la profunditat logaritmica
        if self.globus:
            return carregar_programa(self.ctx, 'terrain', ['PROFUNDITAT_LOG'])
        return shaders.load_program(self.ctx, 'terrain')

    def get_model_matrix(self):
        return glm.mat4()

    def on_init(self):
        """Uniforms que no canvien. m_proj i m_view les escriu la camera (com set_camera al repte 4)."""
        sp = self.shader_program
        sp['tex_altitud'].value, sp['tex_gradient'].value, sp['tex_costa'].value = 0, 1, 2
        sp['tex_eclipsi'].value, sp['tex_ombres'].value = 3, 4
        sp['enfosquiment_min'].value = ENFOSQUIMENT_MIN
        sp['colors_enfosquiment'].write(np.array(COLORS_ENFOSQUIMENT, 'f4').tobytes())
        sp['color_totalitat'].value = COLOR_TOTALITAT
        sp['durada_min'].value, sp['durada_max'].value = self.durada_min, self.durada_max
        sp['colors_durada'].write(np.array(COLORS_DURADA, 'f4').tobytes())
        sp['colors_ombres'].write(np.array(COLORS_OMBRES, 'f4').tobytes())
        sp['m_model'].write(self.m_model)
        sp['mida_km'].write(self.mida)
        sp['lod_vertexs'].value = self.lod_vertexs
        sp['cota_base'].value = self.cota_base
        sp['escala_mar'].value = 0.03 * max(self.mida)  # a aquesta distancia de la costa el mar ja es fosc
        sp['globus'].value = self.globus
        if 'coef_log' in sp:   # nomes el fa servir el mode globus
            sp['coef_log'].value = 0.0
        sp['n_forats'].value = 0

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

    def latlon_a_uv(self, lat, lon):
        """(u, v) d'un punt geografic dins d'aquest terreny (pot quedar fora de 0..1)."""
        return self.uv_de_utm(*self.de_latlon.transform(lon, lat))

    def conte(self, lat, lon, marge=0.0):
        u, v = self.latlon_a_uv(lat, lon)
        return marge <= u <= 1 - marge and marge <= v <= 1 - marge

    def altitud_latlon(self, lat, lon, dibuixada=True):
        """Altitud (m, el mar a 0) en un punt geografic: de la superficie dibuixada o del MDT a
        resolucio completa. None si el punt es fora del terreny.
        Superficie dibuixada: al mode globus, la dels triangles (graella o pegat, amb les transicions),
        sense l'exageracio; al mode pla, la mitjana de la graella amb interpolacio bilineal."""
        u, v = self.latlon_a_uv(lat, lon)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            return None
        if dibuixada and self.globus:
            return float(self.alcada_dibuixada_uv(np.array([u]), np.array([v]))[0])
        x, z = (u - 0.5) * self.mida.x, (v - 0.5) * self.mida.y
        return max(self.altitud_m(x, z, self.alt_vertexs if dibuixada else None), 0.0)

    # ------------------------------------------------------------ nivells de detall (mode globus)

    def uv_a(self, altre, us, vs):
        """UV d'aquest terreny -> UV d'un altre terreny del mateix CRS (passant per UTM)."""
        assert self.crs == altre.crs, 'els nivells de detall han de tenir el mateix CRS'
        return altre.uv_de_utm(*self.utm_de_uv(us, vs))

    def rectangle_a(self, altre):
        """Rectangle (u0, v0, u1, v1) que ocupa aquest terreny sencer en UV d'un altre terreny."""
        u0, v0 = self.uv_a(altre, 0.0, 0.0)
        u1, v1 = self.uv_a(altre, 1.0, 1.0)
        return (u0, v0, u1, v1)

    def alcada_dibuixada_uv(self, us, vs):
        """Altura (m, sense exageracio) dels triangles que es dibuixen a les UV donades (arrays):
        el pegat si el punt hi es, si no la graella general (amb la transicio cap al pare)."""
        h = interpolar_triangles(self.h_graella, self.finestra, us, vs)
        if self.pegat is not None:
            u0, v0, u1, v1 = self.pegat['finestra']
            dins = (us >= u0) & (us <= u1) & (vs >= v0) & (vs <= v1)
            if dins.any():
                h[dins] = interpolar_triangles(self.pegat['h'], self.pegat['finestra'], us[dins], vs[dins])
        return h

    def actualitzar_transicio(self):
        """Altures de la graella general: a la franja de la vora passen suaument a les de la
        superficie dibuixada del pare (no hi ha esglao entre nivells). Cal tornar-ho a fer quan el pare
        canvia el seu pegat."""
        h = self.h_graella_original
        if self.pare is not None:
            us, vs = np.meshgrid(np.linspace(0, 1, self.n_cols), np.linspace(0, 1, self.n_files))
            w = pes_transicio(us, vs, (0.0, 0.0, 1.0, 1.0), TRANSICIO)
            franja = w < 1.0
            hp = self.pare.alcada_dibuixada_uv(*self.uv_a(self.pare, us[franja], vs[franja]))
            h = h.copy()
            h[franja] = hp + w[franja] * (h[franja] - hp)
        self.h_graella = h
        self.vbo_h.write(h.astype('f4').tobytes())
        self.vbo_h_faldilla.write(self.alcades_faldilla(h, self.finestra, self.uv_faldilla))

    def posar_pegat(self, lat, lon):
        """Pegat dens al voltant del punt (lat, lon): MIDA_PEGAT x MIDA_PEGAT vertexs, un al centre de
        cada pixel del fitxer (el detall complet del MDT). A la vora, l'altura passa a la de la graella
        general. Si el punt es fora del terreny, el treu."""
        self.treure_pegat()
        u, v = self.latlon_a_uv(lat, lon)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            return
        files, cols = self.alt.shape
        n_c, n_f = min(MIDA_PEGAT, cols), min(MIDA_PEGAT, files)
        c0 = int(min(max(round(u * cols - n_c / 2), 0), cols - n_c))
        f0 = int(min(max(round(v * files - n_f / 2), 0), files - n_f))
        finestra = ((c0 + 0.5) / cols, (f0 + 0.5) / files, (c0 + n_c - 0.5) / cols, (f0 + n_f - 0.5) / files)
        u0, v0, u1, v1 = finestra
        (vertexs, index), (vertexs_f, index_f) = build_grid(n_c, n_f), build_skirt(n_c, n_f)
        for vv in (vertexs, vertexs_f):   # UV de 0..1 a la finestra
            vv[:, 0] = u0 + vv[:, 0] * (u1 - u0)
            vv[:, 1] = v0 + vv[:, 1] * (v1 - v0)
        us, vs = vertexs[:, 0].astype(float), vertexs[:, 1].astype(float)
        fi = np.maximum(self.alt[f0:f0 + n_f, c0:c0 + n_c], 0.0).reshape(-1)
        base = interpolar_triangles(self.h_graella, self.finestra, us, vs)
        w = pes_transicio(us, vs, finestra, TRANSICIO)
        h = (base + w * (fi - base)).reshape(n_f, n_c)
        g, g_f = self.atributs_globus(us, vs, desar=False), self.atributs_globus(vertexs_f[:, 0], vertexs_f[:, 1], desar=False)
        vbo = self.ctx.buffer(np.hstack([vertexs, g]).astype('f4'))
        vbo_f = self.ctx.buffer(np.hstack([vertexs_f, g_f]).astype('f4'))
        vbo_h = self.ctx.buffer(h.astype('f4'))
        vbo_h_f = self.ctx.buffer(self.alcades_faldilla(h, finestra, vertexs_f[:, :2]))
        ibo, ibo_f = self.ctx.buffer(index), self.ctx.buffer(index_f)
        sp, g3 = self.shader_program, '2f 3f 3f 3f'
        vao = self.ctx.vertex_array(sp, [(vbo, g3, 'in_uv', 'in_offset', 'in_amunt', 'in_tx'), (vbo_h, '1f', 'in_h')],
                                    index_buffer=ibo)
        vao_f = self.ctx.vertex_array(sp, [(vbo_f, '2f 1f 3f 3f 3f', 'in_uv', 'in_base', 'in_offset', 'in_amunt', 'in_tx'),
                                           (vbo_h_f, '1f', 'in_h')], index_buffer=ibo_f)
        self.pegat = dict(finestra=finestra, h=h, vao=vao, vao_faldilla=vao_f,
                          recursos=(vao, vao_f, vbo, vbo_f, vbo_h, vbo_h_f, ibo, ibo_f))

    def treure_pegat(self):
        if self.pegat is not None:
            for obj in self.pegat['recursos']:
                obj.release()
            self.pegat = None

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

    def render(self):
        if not self.visible:
            return
        cam = self.app.camera
        sp = self.shader_program
        if self.globus:
            self.render_globus()
            return
        sp['cam_pos'].write(cam.position)
        sp['exaggeration'].value = self.exaggeration
        sp['sun_dir'].write(self.app.light.direccio())
        sp['llum_sol'].value = self.llum_sol
        sp['llum_cel'].value = self.llum_cel
        sp['color_cel'].value = tuple(self.color_cel)
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

    def render_globus(self):
        """Dibuix sobre la Terra: tot relatiu a la camera (app.camera.posicio, ECEF en float64)."""
        app, sp = self.app, self.shader_program
        rel = app.camera.posicio
        sp['m_model'].write(glm.translate(glm.vec3(*(self.origen_ecef - rel))))
        sp['cam_pos'].write(glm.vec3(0.0))
        sp['coef_log'].value = app.coef_log
        sp['sol_rel'].write(glm.vec3(*(app.sol_ecef - rel)))
        sp['lluna_rel'].write(glm.vec3(*(app.lluna_ecef - rel)))
        sp['radi_sol'].value, sp['radi_lluna'].value = app.radi_sol_km, app.radi_lluna_km
        sp['exaggeration'].value = self.exaggeration
        sp['color_cel'].value = tuple(app.color_cel)
        sp['densitat_boira'].value = app.densitat_boira
        sp['inici_boira'].value = 0.0
        sp['curvatura'].value = False
        sp['n_zones'].value = 0
        sp['dibuixar_mar'].value = self.dibuixar_mar
        sp['cam_ecef'].write(glm.vec3(*rel))
        sp['atmosfera'].value = app.atmosfera
        app.terra.textura.use(5)
        sp['tex_terra'].value = 5
        sp['profunditat_faldilla'].value = FALDILLA_GLOBUS_KM
        for i, tex in enumerate((self.tex_altitud, self.tex_gradient, self.tex_costa, self.tex_eclipsi, self.tex_ombres)):
            tex.use(i)
        sp['overlay'].value = self.overlay
        sp['opacitat'].value = self.opacitat
        sp['limits_totalitat'].value = self.limits_totalitat
        self.ctx.wireframe = self.wireframe
        # forats: on hi ha un terreny mes detallat (fills) no es dibuixa; la graella general tampoc
        # dins del pegat, que es dibuixa a continuacio
        forats = [f.rectangle_a(self) for f in self.fills if f.visible]
        nivells = [(self.vao, self.vao_faldilla, forats + ([self.pegat['finestra']] if self.pegat else []))]
        if self.pegat is not None:
            nivells.append((self.pegat['vao'], self.pegat['vao_faldilla'], forats))
        for vao, vao_faldilla, rects in nivells:
            rects = rects[:MAX_FORATS]
            sp['n_forats'].value = len(rects)
            sp['forats'].write(np.array(rects + [(0, 0, 0, 0)] * (MAX_FORATS - len(rects)), dtype='f4').tobytes())
            sp['es_faldilla'].value = False
            vao.render()
            sp['es_faldilla'].value = True
            vao_faldilla.render()
        self.ctx.wireframe = False

    def destroy(self):
        self.treure_pegat()
        objectes = [self.vbo, self.ibo, self.vao, self.vbo_faldilla, self.ibo_faldilla, self.vao_faldilla,
                    self.shader_program, self.tex_altitud, self.tex_gradient, self.tex_costa, self.tex_eclipsi,
                    self.tex_ombres]
        if self.globus:
            objectes += [self.vbo_h, self.vbo_h_faldilla]
        for obj in objectes:
            obj.release()


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
