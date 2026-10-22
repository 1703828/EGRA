"""
Exercici 1.0 -- Seguir un vertex dibuixat del terreny fins a un pixel de la pantalla.

Que fa (sense finestra i sense canviar el programa):
  1. Tria un vertex de la graella que dibuixa la GPU (columna, fila) i en calcula l'altura
     tal com la llegeix el vertex shader (terrain.vert): textureLod sobre els mipmaps.
  2. Repeteix a ma el cami del vertex shader:  p_mon -> m_view -> m_proj -> /w -> pixel.
  3. Renderitza el terreny, llegeix la profunditat del pixel predit i la compara.
  4. Desa una captura amb una creu al pixel predit.

Executa (des de l'arrel del projecte):
    python scripts/exercici_fotograma.py
    python scripts/exercici_fotograma.py --distancia 0.5     (la modificacio proposada a l'activitat)

Explicacio de l'activitat: docs/exercici_1_0_vertex_a_pixel.md
"""
import argparse
import math
import os
import sys

import glm
import moderngl as mgl
import numpy as np
from PIL import Image

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, 'scripts'))
from captura import AppSenseFinestra  # noqa: E402  (el mateix "app" minim que fa servir captura.py)
from basecode.camera_exploracio import CameraExploracio  # noqa: E402
from basecode.terrain import Terrain, COLOR_CEL  # noqa: E402
from basecode.shaders import SHADERS_DIR  # noqa: E402

MDT = os.path.join(ARREL, 'data', 'mdt', 'picos_5m.tif')
PAS_DEPTH_24 = 2.0 ** -24   # un pas del depth buffer si te 24 bits (format habitual)


# ------------------------------------------------------------ 1. altura del vertex, com la GPU

def mostra_bilineal(nivell, u, v):
    """Com texture() en un nivell de la textura: interpolacio bilineal amb els centres dels
    texels a +0.5 i "clamp to edge" a les vores (el mateix conveni que terrain.altitud_m)."""
    files, cols = nivell.shape
    c = min(max(u * cols - 0.5, 0.0), cols - 1.0)
    f = min(max(v * files - 0.5, 0.0), files - 1.0)
    c0, f0 = min(int(c), cols - 2), min(int(f), files - 2)
    tc, tf = c - c0, f - f0
    a = nivell[f0:f0 + 2, c0:c0 + 2]
    return (a[0, 0] * (1 - tc) + a[0, 1] * tc) * (1 - tf) + (a[1, 0] * (1 - tc) + a[1, 1] * tc) * tf


def altura_gpu(terrain, nivells, u, v):
    """Altura (m) que llegeix textureLod(tex_altitud, uv, lod_vertexs) al vertex shader.
    Amb el filtre LINEAR_MIPMAP_LINEAR, un lod de 1.97 vol dir: 3 % del nivell 1 i 97 % del
    nivell 2 (cada nivell es la mitjana 2x2 de l'anterior)."""
    lod = terrain.lod_vertexs
    n0 = int(math.floor(lod))
    pes = lod - n0
    h0 = mostra_bilineal(nivells[n0], u, v)
    h1 = mostra_bilineal(nivells[min(n0 + 1, len(nivells) - 1)], u, v)
    return h0 * (1 - pes) + h1 * pes


def llegir_nivells(terrain, quants):
    """Llegeix de la GPU els primers nivells de mipmap de la textura d'altituds (float32)."""
    nivells, w, h = [], terrain.tex_altitud.width, terrain.tex_altitud.height
    for n in range(quants):
        dades = np.frombuffer(terrain.tex_altitud.read(level=n), dtype='f4')
        nivells.append(dades.reshape(h, w))
        w, h = max(1, w // 2), max(1, h // 2)
    return nivells


def posicio_mon(terrain, u, v, h_m):
    """La mateixa formula que terrain.vert: x, z a partir de la UV; y = altura en km."""
    x = (u - 0.5) * terrain.mida.x
    z = (v - 0.5) * terrain.mida.y
    y = max(h_m, 0.0) / 1000.0 * terrain.exaggeration - terrain.caiguda(x, z)
    return glm.vec3(x, y, z)


def posicio_mon_segons_la_gpu(ctx, terrain, u, v):
    """Comprovacio: executa el vertex shader real (terrain.vert) per a aquest sol vertex i
    recupera la posicio que calcula (pos_mon) amb "transform feedback"."""
    with open(os.path.join(SHADERS_DIR, 'terrain.vert'), encoding='utf-8') as f:
        prog = ctx.program(vertex_shader=f.read(), varyings=['pos_mon'])
    sp = terrain.shader_program
    for nom in ('mida_km', 'lod_vertexs', 'exaggeration', 'cota_base', 'curvatura',
                'centre_curvatura', 'm_model', 'm_view', 'm_proj'):
        if nom in prog and nom in sp:
            prog[nom].write(sp[nom].read())
    prog['tex_altitud'].value = 0
    terrain.tex_altitud.use(0)
    entrada = ctx.buffer(np.array([u, v], dtype='f4'))
    sortida = ctx.buffer(reserve=3 * 4)
    vao = ctx.vertex_array(prog, [(entrada, '2f', 'in_uv')])
    vao.transform(sortida, mgl.POINTS, vertices=1)
    p = glm.vec3(*np.frombuffer(sortida.read(), dtype='f4'))
    for obj in (vao, entrada, sortida, prog):
        obj.release()
    return p


# ------------------------------------------------------------ 2. del mon a la pantalla

def a_pantalla(p_mon, m_model, m_view, m_proj, amplada, alcada):
    """El cami del vertex fins a la pantalla. Retorna un dict amb totes les etapes."""
    p = glm.vec4(p_mon, 1.0)                 # punt del mon (km), amb w = 1
    p_model = m_model * p                    # m_model: del model al mon (aqui, la identitat)
    p_camera = m_view * p_model              # m_view: el mon vist des de la camera
    clip = m_proj * p_camera                 # m_proj: la perspectiva (aixo surt a gl_Position)
    ndc = glm.vec3(clip) / clip.w            # divisio per w: el que es lluny es fa petit
    x = (ndc.x + 1) / 2 * amplada            # NDC (-1..1) -> pixels (0..amplada)
    y = (ndc.y + 1) / 2 * alcada             # origen a baix a l'esquerra, com OpenGL
    profunditat = (ndc.z + 1) / 2            # NDC (-1..1) -> depth buffer (0..1)
    return dict(model=p_model, camera=p_camera, clip=clip, ndc=ndc, x=x, y=y, profunditat=profunditat)


def distancia_de_profunditat(d, near, far):
    """Inversa de la perspectiva: profunditat (0..1) -> distancia al llarg de l'eix de la camera (km)."""
    ndc_z = 2 * d - 1
    return 2 * near * far / ((far + near) - ndc_z * (far - near))


def amagat(terrain, nivells, cam_pos, p_mon, passos=2000):
    """Hi ha relleu entre la camera i el punt? Recorre el raig i compara la seva altura amb
    la superficie dibuixada (la mateixa altura que la GPU) en cada pas."""
    for k in range(1, passos):
        t = k / passos
        if t > 0.995:                     # els ultims metres son el mateix punt
            break
        q = cam_pos + (p_mon - cam_pos) * t
        u, v = q.x / terrain.mida.x + 0.5, q.z / terrain.mida.y + 0.5
        if 0 <= u <= 1 and 0 <= v <= 1 and q.y < posicio_mon(terrain, u, v, altura_gpu(terrain, nivells, u, v)).y:
            return True
    return False


# ------------------------------------------------------------ programa

def main():
    p = argparse.ArgumentParser(description='Exercici 1.0: un vertex del terreny fins a un pixel.')
    p.add_argument('--col', type=int, default=640, help='columna del vertex a la graella (0 = oest)')
    p.add_argument('--fila', type=int, default=512, help='fila del vertex a la graella (0 = nord)')
    p.add_argument('--distancia', type=float, default=1.0, help='distancia de la camera, en mides del terreny')
    p.add_argument('--gir', type=float, default=30.0, help='gir de la camera (graus)')
    p.add_argument('--inclinacio', type=float, default=35.0, help='inclinacio de la camera (graus)')
    p.add_argument('--mida', type=int, nargs=2, default=(1200, 800), metavar=('AMPLADA', 'ALCADA'))
    p.add_argument('--sortida', default=os.path.join(ARREL, 'captures', 'exercici_1_0.png'))
    a = p.parse_args()
    W, H = a.mida

    # --- l'escena: la mateixa que captura.py, amb el relleu real (exageracio 1, com a main.py)
    app = AppSenseFinestra(W, H)
    ctx = app.ctx
    ctx.enable_only(mgl.DEPTH_TEST)
    app.terrain = terrain = Terrain(app, MDT)
    terrain.exaggeration = 1.0
    app.camera = cam = CameraExploracio(app, terrain)
    cam.yaw, cam.pitch, cam.distance = a.gir, a.inclinacio, a.distancia * max(terrain.mida)
    cam.update()   # calcula m_view i m_proj i les escriu al shader del terreny

    # --- 1. el vertex triat i la seva altura, tal com la dibuixa la GPU
    n_cols, n_files = terrain.n_cols, terrain.n_files
    if not (0 <= a.col < n_cols and 0 <= a.fila < n_files):
        sys.exit(f"El vertex ha d'estar dins de la graella: col 0..{n_cols - 1}, fila 0..{n_files - 1}")
    u, v = a.col / (n_cols - 1), a.fila / (n_files - 1)   # igual que build_grid (linspace 0..1)
    nivells = llegir_nivells(terrain, int(math.floor(terrain.lod_vertexs)) + 2)
    h_gpu = altura_gpu(terrain, nivells, u, v)
    h_mdt = terrain.altitud_m((u - 0.5) * terrain.mida.x, (v - 0.5) * terrain.mida.y)  # MDT de 5 m
    p_mon = posicio_mon(terrain, u, v, h_gpu)

    print("\n=== 1. EL VERTEX ===")
    print(f"Graella de {n_cols} x {n_files} vertexs; triat: columna {a.col}, fila {a.fila}  ->  uv = ({u:.5f}, {v:.5f})")
    print(f"Altura al MDT de 5 m:              {h_mdt:9.2f} m")
    print(f"Altura que dibuixa la GPU:         {h_gpu:9.2f} m   (mipmaps, lod {terrain.lod_vertexs:.2f})")
    print(f"Posicio al mon (km):  x = {p_mon.x:.4f} (est)   y = {p_mon.y:.4f} (amunt)   z = {p_mon.z:.4f} (sud)")

    # --- 2. el cami fins a la pantalla, pas a pas
    e = a_pantalla(p_mon, terrain.m_model, cam.m_view, cam.m_proj, W, H)
    print("\n=== 2. DEL MON A LA PANTALLA ===")
    print(f"Camera a ({cam.position.x:.3f}, {cam.position.y:.3f}, {cam.position.z:.3f}) km, "
          f"mirant ({cam.target.x:.3f}, {cam.target.y:.3f}, {cam.target.z:.3f})")
    print(f"m_view * p  (vist des de la camera): x = {e['camera'].x:8.4f}  y = {e['camera'].y:8.4f}  "
          f"z = {e['camera'].z:8.4f}   (z negativa = davant de la camera; profunditat segons l'eix de visio {-e['camera'].z:.3f} km)")
    print(f"m_proj * ...  (clip, gl_Position):   x = {e['clip'].x:8.4f}  y = {e['clip'].y:8.4f}  "
          f"z = {e['clip'].z:8.4f}  w = {e['clip'].w:8.4f}")
    print(f"/ w  (NDC, de -1 a 1):               x = {e['ndc'].x:8.4f}  y = {e['ndc'].y:8.4f}  z = {e['ndc'].z:8.6f}")
    print(f"Pixel (origen a baix a l'esquerra):  x = {e['x']:.2f}   y = {e['y']:.2f}   "
          f"(la pantalla fa {W} x {H}; el centre es ({W / 2:.0f}, {H / 2:.0f}))")
    print(f"Profunditat predita (0 = near, 1 = far): {e['profunditat']:.7f}   "
          f"near = {cam.near * 1000:.1f} m, far = {cam.far:.1f} km")
    px, py = int(math.floor(e['x'])), int(math.floor(e['y']))
    if not (1 <= px < W - 1 and 1 <= py < H - 1) or e['clip'].w <= 0:
        sys.exit("El vertex queda fora de la pantalla: tria'n un altre (--col, --fila)")
    if amagat(terrain, nivells, cam.position, p_mon):
        sys.exit("Hi ha relleu entre la camera i el vertex (no es visible): tria'n un altre")

    # --- 3. renderitzar i llegir la profunditat (sense antialiasing: un sol valor per pixel)
    fbo = ctx.simple_framebuffer((W, H))
    fbo.use()
    fbo.clear(*COLOR_CEL)
    terrain.render()   # aqui el terreny escriu els uniforms de cada fotograma (p. ex. l'exageracio)
    # el mateix vertex, pero calculat pel vertex shader real: confirma que el pas 1 es correcte
    p_shader = posicio_mon_segons_la_gpu(ctx, terrain, u, v)
    finestra = (px - 1, py - 1, 3, 3)
    d = np.frombuffer(fbo.read(viewport=finestra, components=1, attachment=-1, dtype='f4'), 'f4').reshape(3, 3)
    d_llegida = float(d[1, 1])

    # tolerancia: el vertex no cau al centre del pixel; alla la GPU dona la profunditat del triangle
    gx, gy = (d[1, 2] - d[1, 0]) / 2, (d[2, 1] - d[0, 1]) / 2       # canvi de profunditat per pixel
    dx, dy = (px + 0.5) - e['x'], (py + 0.5) - e['y']                 # del vertex al centre del pixel
    t_pixel = abs(gx * dx) + abs(gy * dy)
    t_buffer = PAS_DEPTH_24
    t_float = 8 * np.finfo('f4').eps * max(d_llegida, e['profunditat'])
    t_altura = abs(a_pantalla(p_shader, terrain.m_model, cam.m_view, cam.m_proj, W, H)['profunditat'] - e['profunditat'])
    tolerancia = t_pixel + t_buffer + t_float + t_altura
    diferencia = abs(d_llegida - e['profunditat'])
    silueta = max(abs(d[1, 2] - d[1, 1]), abs(d[1, 1] - d[1, 0])) > 3 * max(min(abs(d[1, 2] - d[1, 1]), abs(d[1, 1] - d[1, 0])), 1e-7)

    dist_predita = distancia_de_profunditat(e['profunditat'], cam.near, cam.far)
    dist_llegida = distancia_de_profunditat(d_llegida, cam.near, cam.far)
    print("\n=== 3. EL QUE HA DIBUIXAT LA GPU ===")
    print(f"Posicio del vertex segons el vertex shader real: diferencia amb el pas 1 de "
          f"{glm.length(p_shader - p_mon) * 1e5:.2f} cm")
    print(f"Pixel ({px}, {py}): profunditat llegida {d_llegida:.7f}   predita {e['profunditat']:.7f}   "
          f"diferencia {diferencia:.2e}")
    print(f"Profunditat segons l'eix de visio: predita {dist_predita * 1000:.1f} m, llegida {dist_llegida * 1000:.1f} m  "
          f"(diferencia {abs(dist_llegida - dist_predita) * 1000:.2f} m)")
    print(f"Tolerancia calculada {tolerancia:.2e} = centre del pixel {t_pixel:.1e} (desplacament {dx:+.2f}, {dy:+.2f} px)"
          f" + depth buffer {t_buffer:.1e} + float32 {t_float:.1e} + altura {t_altura:.1e}")
    if silueta:
        print("AVIS: la profunditat canvia de cop al voltant del pixel: pot ser una silueta. Tria un altre vertex.")
    print("RESULTAT:", "COINCIDEIX (dins de la tolerancia)" if diferencia <= tolerancia else "NO COINCIDEIX")

    # --- 4. captura amb una creu vermella al pixel predit (la imatge te la fila 0 a dalt)
    img = np.frombuffer(fbo.read(components=3), np.uint8).reshape(H, W, 3)[::-1].copy()
    fila_img = H - 1 - py
    for k in range(-25, 26):
        if abs(k) < 5:   # deixem lliure el centre per veure el terreny just a sota
            continue
        for gruix in (-1, 0, 1):
            img[min(max(fila_img + gruix, 0), H - 1), min(max(px + k, 0), W - 1)] = (255, 0, 0)
            img[min(max(fila_img + k, 0), H - 1), min(max(px + gruix, 0), W - 1)] = (255, 0, 0)
    os.makedirs(os.path.dirname(os.path.abspath(a.sortida)), exist_ok=True)
    Image.fromarray(img).save(a.sortida)
    print(f"\nCaptura amb la creu al pixel predit: {a.sortida}")


if __name__ == '__main__':
    main()
