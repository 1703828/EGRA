"""
Estudi d'instancing per als edificis (tasques 40.3 i 46.1 del pla), amb el programa real (finestra amagada).

A. On es el cost del dibuix: temps de GPU de cada passada (consultes de temps d'OpenGL, GL_TIME_ELAPSED) a la UAB i a
   Vic, des de l'aire (400 m) i des del carrer: el cel, la Terra, el terreny, els edificis i la passada des del Sol
   (mapes d'ombres, forcada a cada fotograma per mesurar-la). Tambe el nombre de crides, triangles i memoria dels
   edificis.
B. Instancing: la malla actual del Catastro (una sola crida per a tota la zona) contra caixes (el rectangle minim
   orientat de cada part, de la cota del terra a la de la coberta), dibuixades sense instancing (triangles copiats)
   i amb instancing (un cub compartit i 48 bytes per caixa: un vertex i tres vectors, glVertexAttribDivisor). Totes
   tres amb el mateix shader minim i la mateixa camera: nomes canvia la geometria. Temps de GPU (mediana de 30
   repeticions) i memoria.
C. Fidelitat de les caixes: area de la caixa / area del contorn i diferencia de l'horitzo dels edificis
   (dades/edificis.perfil_edificis) des de 10 punts del carrer, a tots els azimuts amb edificis i als de la posta del
   2026 (260-300 graus).
Criteri (pla, 46.1): les caixes nomes poden substituir la malla per calcular o per veure de prop si la diferencia
d'horitzo es < 0,05 graus i hi ha un guany mesurat.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/estudi_instancing.py [UAB] [Vic]
"""
import math
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, 'scripts'))
from vista_unica import als_ulls, lliure  # noqa: E402  (F48: una sola vista)

import glfw  # noqa: E402
import glm  # noqa: E402
import moderngl as mgl  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402

W, H = 1100, 760
VERT = """
#version 330
in vec3 in_position;
uniform mat4 m_proj, m_view, m_model;
void main() { gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0); }
"""
VERT_INST = """
#version 330
in vec3 in_cub;                 // vertex del cub unitat (0..1)
in vec3 in_p0, in_e1, in_e2, in_h;   // per instancia: cantonada, costats i altura (km, relatius a l'origen)
uniform mat4 m_proj, m_view, m_model;
void main() {
    vec3 p = in_p0 + in_cub.x * in_e1 + in_cub.y * in_e2 + in_cub.z * in_h;
    gl_Position = m_proj * m_view * m_model * vec4(p, 1.0);
}
"""
FRAG = """
#version 330
out vec4 c;
void main() { c = vec4(0.8, 0.7, 0.6, 1.0); }
"""
# cub unitat: 12 triangles cap a fora
_CARES = [(0, 1, 3, 2, (0, 0, -1)), (4, 6, 7, 5, (0, 0, 1)), (0, 4, 5, 1, (0, -1, 0)), (2, 3, 7, 6, (0, 1, 0)),
          (0, 2, 6, 4, (-1, 0, 0)), (1, 5, 7, 3, (1, 0, 0))]
_V = np.array([(x, y, z) for z in (0, 1) for y in (0, 1) for x in (0, 1)], 'f4')
CUB = np.array([_V[i] for a, b, c, d, _ in _CARES for i in (a, b, c, a, c, d)], 'f4')


def caixes(contorns):
    """Rectangle minim orientat de cada part: (cantonada, costat 1, costat 2) en UTM (m)."""
    out = []
    for g in contorns:
        r = shapely.minimum_rotated_rectangle(g)
        c = np.asarray(r.exterior.coords)[:4] if r.geom_type == 'Polygon' else None
        if c is None or len(c) < 4:
            out.append(None)
            continue
        out.append((c[0], c[1] - c[0], c[3] - c[0]))
    return out


def a_ecef(x, y, z_m, origen):
    from pyproj import Transformer
    from dades import geodesia
    lon, lat = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True).transform(x, y)
    return geodesia.ecef(lat, lon, np.asarray(z_m) / 1000.0) - origen


def main():
    llocs = [a for a in sys.argv[1:] if not a.startswith('-')] or ['UAB', 'Vic']
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    from dades.edificis import preparar_malla, perfil_edificis, arestes
    from dades.observador import UBICACIONS
    import geopandas as gpd

    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - estudi d\'instancing', use_ui_panel=True)
    ctx = app.ctx
    fb = ctx.simple_framebuffer((W, H))

    def fotograma(n=1):
        for _ in range(n):
            fb.use()
            app.dt = 1 / 30
            app.render()
            ctx.finish()

    # ---- temps de GPU de les passades del programa (A)
    temps = {}

    def cronometrat(nom, obj, metode):
        original = getattr(obj, metode)

        def f(*a, **k):
            q = ctx.query(time=True)
            with q:
                r = original(*a, **k)
            temps.setdefault(nom, []).append(q.elapsed / 1e6)
            return r
        setattr(obj, metode, f)

    for lloc in llocs:
        nom, lat, lon = next(u for u in UBICACIONS if lloc.lower() in u[0].lower())
        print(f'\n== {nom}', flush=True)
        app.triar_ubicacio(lat, lon, nom)
        als_ulls(app)
        t0 = time.time()
        while time.time() - t0 < 600 and (app.edificis is None or not app.edificis.mesurades or app.detall.feines):
            fotograma(5)
        e = app.edificis
        if e is None:
            print('  sense edificis')
            continue
        print(f'  edificis: {e.n_parts} parts, {e.n_triangles} triangles, {e.memoria_gpu / 1e6:.1f} MB a la GPU, '
              f'1 crida de dibuix (+1 a cada mapa d\'ombres)', flush=True)
        objs = [('cel', app.cel, 'render'), ('Terra', app.terra, 'render'), ('edificis', e, 'render'),
                ('ombres (passada des del Sol)', app.ombres, 'actualitzar')]
        objs += [(f'terreny {i}', t, 'render') for i, t in enumerate(app.terrenys())]
        originals = [(o, m, getattr(o, m)) for _, o, m in objs]
        for etiqueta, o, m in objs:
            cronometrat(etiqueta, o, m)
        for vista, posar in (('carrer', lambda: (als_ulls(app), app.camera.orientar(285, 3))),
                             ('aire 400 m', lambda: posar_aire(app, geodesia))):
            posar()
            fotograma(10)
            temps.clear()
            t1 = time.perf_counter()
            for _ in range(30):
                app.ombres.clau = None          # la passada des del Sol, a cada fotograma (per mesurar-la)
                fotograma()
            total = (time.perf_counter() - t1) / 30 * 1000
            print(f'  [{vista}] fotograma {total:.1f} ms (CPU + GPU, ombres forcades); GPU per passada (mediana): '
                  + ', '.join(f'{k} {np.median(v):.2f} ms' for k, v in temps.items()), flush=True)
        for o, m, f in originals:
            setattr(o, m, f)

        # ---- B: malla actual contra caixes (amb i sense instancing), mateix shader i camera
        m = preparar_malla(e.zona, app.zona.cami, mesurades=e.mesurades, nomes_llegir=True)
        contorns, cota_sol, cota_cob = e.contorns, np.asarray(m['cota_sol']), np.asarray(m['cota_coberta'])
        cx = caixes(contorns)
        ok_c = [i for i, c in enumerate(cx) if c is not None]
        p0 = np.array([cx[i][0] for i in ok_c])
        e1 = np.array([cx[i][1] for i in ok_c])
        e2 = np.array([cx[i][2] for i in ok_c])
        zs, zt = cota_sol[ok_c], cota_cob[ok_c]
        o = e.origen_ecef
        P0 = a_ecef(p0[:, 0], p0[:, 1], zs, o)
        E1 = a_ecef(p0[:, 0] + e1[:, 0], p0[:, 1] + e1[:, 1], zs, o) - P0
        E2 = a_ecef(p0[:, 0] + e2[:, 0], p0[:, 1] + e2[:, 1], zs, o) - P0
        HH = a_ecef(p0[:, 0], p0[:, 1], zt, o) - P0
        inst = np.hstack([P0, E1, E2, HH]).astype('f4')
        copiats = (P0[:, None, :] + CUB[None, :, 0:1] * E1[:, None, :] + CUB[None, :, 1:2] * E2[:, None, :]
                   + CUB[None, :, 2:3] * HH[:, None, :]).reshape(-1, 3).astype('f4')
        malla = np.asarray(m['triangles'], 'f4').reshape(-1, 3)
        prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        prog_i = ctx.program(vertex_shader=VERT_INST, fragment_shader=FRAG)
        b_malla, b_copiats = ctx.buffer(malla.tobytes()), ctx.buffer(copiats.tobytes())
        b_cub, b_inst = ctx.buffer(CUB.tobytes()), ctx.buffer(inst.tobytes())
        vao_malla = ctx.vertex_array(prog, [(b_malla, '3f', 'in_position')])
        vao_copiats = ctx.vertex_array(prog, [(b_copiats, '3f', 'in_position')])
        vao_inst = ctx.vertex_array(prog_i, [(b_cub, '3f', 'in_cub'), (b_inst, '3f 3f 3f 3f/i', 'in_p0', 'in_e1',
                                                                               'in_e2', 'in_h')])
        fbo = ctx.simple_framebuffer((W, H))
        for vista, posar in (('carrer', lambda: (als_ulls(app), app.camera.orientar(285, 3))),
                             ('aire 400 m', lambda: posar_aire(app, geodesia))):
            posar()
            fotograma(3)
            cam = app.camera
            mm = glm.translate(glm.vec3(*(o - cam.posicio)))
            res = {}
            for etiqueta, vao, p_, n_inst in (('malla del Catastro', vao_malla, prog, None),
                                              ('caixes copiades', vao_copiats, prog, None),
                                              ('caixes instanciades', vao_inst, prog_i, len(inst))):
                p_['m_proj'].write(cam.m_proj)
                p_['m_view'].write(cam.m_view)
                p_['m_model'].write(mm)
                fbo.use()
                ctx.enable(mgl.DEPTH_TEST | mgl.CULL_FACE)
                ts = []
                for _ in range(30):
                    fbo.clear(depth=1.0)
                    q = ctx.query(time=True)
                    with q:
                        vao.render(instances=n_inst) if n_inst else vao.render()
                    ts.append(q.elapsed / 1e6)
                ctx.disable(mgl.CULL_FACE)
                res[etiqueta] = np.median(ts)
            print(f'  [{vista}] GPU (mediana de 30): ' + ', '.join(f'{k} {v:.3f} ms' for k, v in res.items()),
                  flush=True)
        print(f'  memoria: malla {malla.nbytes / 1e6:.1f} MB ({len(malla) // 3} triangles, sense els atributs); '
              f'caixes copiades {copiats.nbytes / 1e6:.1f} MB; instanciades {(CUB.nbytes + inst.nbytes) / 1e6:.2f} MB '
              f'({len(inst)} caixes x 48 B + el cub)', flush=True)
        for obj in (vao_malla, vao_copiats, vao_inst, b_malla, b_copiats, b_cub, b_inst, prog, prog_i, fbo):
            obj.release()

        # ---- C: fidelitat
        area = np.array([contorns[i].area for i in ok_c])
        area_c = np.abs(np.cross(e1, e2))
        rel = area_c / np.maximum(area, 1e-6)
        print(f'  area de la caixa / area del contorn: mediana {np.median(rel):.2f}, 90 % {np.percentile(rel, 90):.2f}, '
              f'maxim {rel.max():.1f}', flush=True)
        caixes_geom = gpd.GeoDataFrame(dict(cota_coberta=zt), geometry=[
            shapely.Polygon([p, p + a, p + a + b, p + b]) for p, a, b in zip(p0, e1, e2)], crs='EPSG:25830')
        vores_reals = m['vores']
        vores_caixes = arestes(caixes_geom)
        rng = np.random.default_rng(5)
        from pyproj import Transformer
        x0, y0 = Transformer.from_crs('EPSG:4326', 'EPSG:25830', always_xy=True).transform(lon, lat)
        punts, tots = [], shapely.union_all(list(contorns))
        shapely.prepare(tots)
        while len(punts) < 10:
            x, y = x0 + rng.uniform(-300, 300), y0 + rng.uniform(-300, 300)
            if not tots.intersects(shapely.Point(x, y).buffer(2.0)):     # al carrer, a 2 m de qualsevol edifici
                punts.append((x, y))
        dif_tot, dif_posta, canvis = [], [], 0
        a_ll = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
        for x, y in punts:
            lo, la = a_ll.transform(x, y)
            ull = geodesia.ecef(la, lo, app.altitud_terra_km(la, lo) + 0.0017)
            pr, pc = perfil_edificis(vores_reals, ull), perfil_edificis(vores_caixes, ull)
            amb = (pr > -90) | (pc > -90)
            d = np.abs(np.where(pr > -90, pr, 0) - np.where(pc > -90, pc, 0))[amb]
            dif_tot.append(np.median(d) if len(d) else 0.0)
            az = np.arange(len(pr)) * 0.01
            sel = amb & (az >= 260) & (az <= 300)
            if sel.any():
                dd = np.abs(np.where(pr > -90, pr, 0) - np.where(pc > -90, pc, 0))[sel]
                dif_posta.append(dd.max())
                canvis += int((dd > 0.27).any())
        print(f'  horitzo dels edificis, caixes - malla (10 punts del carrer a < 300 m): mediana de la diferencia '
              f'{np.median(dif_tot):.2f} graus; als azimuts de la posta (260-300 graus), diferencia maxima mediana '
              f'{np.median(dif_posta) if dif_posta else 0:.2f} graus, maxima {max(dif_posta) if dif_posta else 0:.2f}; '
              f'{canvis} de {len(dif_posta)} punts amb una diferencia > 0,27 graus (el radi del Sol)', flush=True)
    return 0


def posar_aire(app, geodesia):
    o = app.observador
    _, nord, amunt = geodesia.base_local(o.lat, o.lon)
    lliure(app)
    app.camera_exploracio.posicio = app.ulls() - 0.4 * nord + 0.4 * amunt
    app.camera_exploracio.orientar(0.0, -45.0)


if __name__ == '__main__':
    sys.exit(main())
