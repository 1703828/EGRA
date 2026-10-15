"""
Terreny: MDT dibuixat amb un heightmap com a textura (T2-T6).

- La geometria es una graella plana fixa (com a maxim MAX_VERTEXS x MAX_VERTEXS vertexs) amb
  nomes coordenades UV; el vertex shader hi llegeix l'altura (shaders/terrain.vert).
- Les normals es fan al fragment shader amb el pendent a la resolucio del fitxer (5 m), i alla
  tambe hi ha la rampa de colors, el mar, les faldilles, la boira, les zones de detall i els
  overlays de l'eclipsi (shaders/terrain.frag).
- Copies a la CPU de l'altitud per a la camera (enganxada al terreny) i el punt d'observacio.
"""
import math
import os

import glm
import numpy as np
import moderngl as mgl
import rasterio
from pyproj import Transformer

from basecode import shaders
import data_io
import eclipse_data

SHADERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shaders')
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
        # shaders/terrain.vert i terrain.frag (es poden editar sense tocar el codi Python)
        return shaders.load_program(self.ctx, 'terrain', SHADERS_DIR)


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
