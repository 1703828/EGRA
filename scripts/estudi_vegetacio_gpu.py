"""
Geometry shader contra instancing amb les mateixes dades (tasca 46.3 del pla): la vegetacio mesurada de la UAB
(basecode/vegetacio.py, ~1 milio de columnes de 2 m) dibuixada de tres maneres, amb el programa real i la mateixa
camera (des del carrer i des de 400 m):
  gs              el que fa el programa: un punt per columna; el geometry shader emet la coberta i nomes les cares
                  visibles (ni tapades per la columna del costat ni d'esquena), i res lluny o fora de la vista.
  inst            instancing: un cub compartit (36 vertexs) i 20 bytes per columna (glVertexAttribDivisor); totes les
                  cares de totes les columnes, sense descartar res.
  inst_descart    instancing amb el mateix descart que el gs, fet al vertex shader: els vertexs d'una cara que no
                  s'ha de dibuixar (o d'una columna lluny) van tots al mateix punt (triangles degenerats).
Es mesura el temps de GPU (consultes GL_TIME_ELAPSED, mediana de 30) i la memoria a la GPU.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/estudi_vegetacio_gpu.py
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import glfw  # noqa: E402
import glm  # noqa: E402
import moderngl as mgl  # noqa: E402
import numpy as np  # noqa: E402

W, H = 1100, 760
VERT_INST = """
#version 330
in vec3 in_cub;        // vertex del cub unitat (-1..1 en x i y, 0..1 en z)
in float in_cara;      // 0 coberta, 1 est, 2 oest, 3 nord, 4 sud, 5 base
in vec3 in_base;       // per instancia
in float in_alt;
in float in_cares;
uniform mat4 m_proj, m_view;
uniform vec3 origen_rel, est, nord, amunt;
uniform float meitat, dist_max;
uniform bool descartar;
void main() {
    vec3 b = in_base + origen_rel;
    vec3 p = b + in_cub.x * meitat * est + in_cub.y * meitat * nord + in_cub.z * in_alt * amunt;
    if (descartar) {
        int cara = int(in_cara + 0.5), mask = int(in_cares + 0.5);
        vec3 n = cara == 1 ? est : cara == 2 ? -est : cara == 3 ? nord : cara == 4 ? -nord : cara == 0 ? amunt : -amunt;
        bool fora = length(b) > dist_max || cara == 5;
        if (cara >= 1 && cara <= 4) fora = fora || (mask & (1 << (cara - 1))) == 0 || dot(b + n * meitat, n) > 0.0;
        if (cara == 0) fora = fora || dot(b + in_alt * amunt, amunt) > 0.0;
        if (fora) p = vec3(0.0, 0.0, -1e6);     // degenerat: el triangle no te area i no genera fragments
    }
    gl_Position = m_proj * m_view * vec4(p, 1.0);
}
"""
FRAG = """
#version 330
out vec4 c;
void main() { c = vec4(0.25, 0.35, 0.15, 1.0); }
"""


def cub():
    """36 vertexs (12 triangles) amb la cara de cadascun."""
    v = lambda x, y, z: (x, y, z)  # noqa: E731
    cares = [((v(-1, -1, 1), v(1, -1, 1), v(1, 1, 1), v(-1, 1, 1)), 0),
             ((v(1, -1, 0), v(1, 1, 0), v(1, 1, 1), v(1, -1, 1)), 1),
             ((v(-1, 1, 0), v(-1, -1, 0), v(-1, -1, 1), v(-1, 1, 1)), 2),
             ((v(1, 1, 0), v(-1, 1, 0), v(-1, 1, 1), v(1, 1, 1)), 3),
             ((v(-1, -1, 0), v(1, -1, 0), v(1, -1, 1), v(-1, -1, 1)), 4),
             ((v(-1, -1, 0), v(-1, 1, 0), v(1, 1, 0), v(1, -1, 0)), 5)]
    out = []
    for (a, b, c, d), k in cares:
        for q in (a, b, c, a, c, d):
            out.append((*q, k))
    return np.array(out, 'f4')


def main():
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import geodesia
    from basecode.vegetacio import DIST_MAX_KM
    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - gs i instancing', use_ui_panel=True)
    ctx = app.ctx
    fb = ctx.simple_framebuffer((W, H))

    def fotograma(n=1):
        for _ in range(n):
            fb.use()
            app.dt = 1 / 30
            app.render()
            ctx.finish()
    veg = app.vegetacio
    veg.actiu = True
    app.canviar_vista(1)
    t0 = time.time()
    while time.time() - t0 < 120 and not veg.cel_les:
        fotograma(3)
    c = next(iter(veg.cel_les.values()))
    dades = np.frombuffer(c['vbo'].read(), 'f4').reshape(-1, 5)
    print(f'{len(dades)} columnes; memoria a la GPU: gs {dades.nbytes / 1e6:.1f} MB (20 B per punt); instancing '
          f'{(dades.nbytes + cub().nbytes) / 1e6:.1f} MB (els mateixos 20 B + el cub); una malla amb les cares '
          f'copiades (sense descart) en faria {len(dades) * 30 * 12 / 1e6:.0f} MB', flush=True)
    prog = ctx.program(vertex_shader=VERT_INST, fragment_shader=FRAG)
    b_cub = ctx.buffer(cub().tobytes())
    vao = ctx.vertex_array(prog, [(b_cub, '3f 1f', 'in_cub', 'in_cara'),
                                  (c['vbo'], '3f 1f 1f/i', 'in_base', 'in_alt', 'in_cares')])
    o = c['origen']
    lat, lon, _ = geodesia.geodesiques(o)
    est, nord, amunt = geodesia.base_local(float(lat), float(lon))
    obs = app.observador
    _, nord_o, amunt_o = geodesia.base_local(obs.lat, obs.lon)
    vistes = [('carrer', lambda: (app.canviar_vista(1), app.camera_observador.mirar(100, 3))),
              ('aire 400 m', lambda: (app.canviar_vista(0), setattr(app.camera_exploracio, 'posicio',
                                                                     app.ulls() - 0.3 * nord_o + 0.25 * amunt_o),
                                      app.camera_exploracio.orientar(0, -40)))]
    for nom, posar in vistes:
        posar()
        fotograma(5)
        cam = app.camera
        res = {}
        fbo = ctx.simple_framebuffer((W, H))
        for variant in ('gs', 'inst', 'inst_descart'):
            ts = []
            for _ in range(30):
                fbo.use()
                fbo.clear(depth=1.0)
                ctx.enable(mgl.DEPTH_TEST)
                q = ctx.query(time=True)
                with q:
                    if variant == 'gs':
                        veg.render()
                    else:
                        prog['m_proj'].write(cam.m_proj)
                        prog['m_view'].write(cam.m_view)
                        prog['origen_rel'].write(glm.vec3(*(o - cam.posicio)))
                        for k, v in (('est', est), ('nord', nord), ('amunt', amunt)):
                            prog[k].write(glm.vec3(*v))
                        prog['meitat'].value = c['res'] / 2000.0
                        prog['dist_max'].value = DIST_MAX_KM
                        prog['descartar'].value = variant == 'inst_descart'
                        vao.render(instances=len(dades))
                ts.append(q.elapsed / 1e6)
            res[variant] = np.median(ts)
        fbo.release()
        print(f'[{nom}] GPU (mediana de 30): ' + ', '.join(f'{k} {v:.2f} ms' for k, v in res.items()), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
