"""
Captura del terreny renderitzada fora de pantalla (sense finestra) i desada en PNG.

Fa servir les mateixes classes Terrain i Camera que main.py, amb un context OpenGL
"standalone" i un framebuffer propi (amb antialiasing 4x).

Exemples (des de l'arrel del projecte):
    python scripts/captura.py data/mdt/picos_5m.tif captures/picos.png --azimut 281.4 --elevacio 9.6
    python scripts/captura.py data/mdt/peninsula_200m.tif captures/peninsula.png --overlay enfosquiment --limits
"""
import argparse
import os
import sys

import glm
import moderngl as mgl
import numpy as np
from PIL import Image
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from camera import Camera  # noqa: E402
from sol import Sol  # noqa: E402
from data_io import TERRENYS  # noqa: E402
from terrain import Terrain, COLOR_CEL, limits_utm, zones_de_detall  # noqa: E402
import eclipse_data  # noqa: E402


class AppSenseFinestra:
    """El minim que necessiten Terrain i Camera: ctx, WIN_SIZE, light, camera i drawables()."""
    def __init__(self, amplada, alcada):
        self.WIN_SIZE = (amplada, alcada)
        self.ctx = mgl.create_standalone_context(require=330)
        self.light = Sol()
        self.terrain = None

    def drawables(self):
        return [self.terrain]


def main():
    p = argparse.ArgumentParser(description='Captura del terreny en PNG (fora de pantalla).')
    p.add_argument('fitxer', help='MDT en GeoTIFF (EPSG:25830)')
    p.add_argument('sortida', help='fitxer PNG de sortida')
    p.add_argument('--mida', type=int, nargs=2, default=(1600, 1000), metavar=('AMPLADA', 'ALCADA'))
    p.add_argument('--azimut', type=float, default=285.0, help='azimut del Sol (graus des del nord)')
    p.add_argument('--elevacio', type=float, default=12.0, help='elevacio del Sol (graus)')
    p.add_argument('--gir', type=float, default=30.0, help='gir de la camera (graus)')
    p.add_argument('--inclinacio', type=float, default=35.0, help='inclinacio de la camera (graus)')
    p.add_argument('--distancia', type=float, default=1.0, help='distancia, en mides del terreny')
    p.add_argument('--exageracio', type=float, help="exageracio vertical (per defecte, la del terreny)")
    p.add_argument('--boira', type=float, help='densitat de boira 0..1 (per defecte, la del terreny)')
    p.add_argument('--curvatura', action='store_true', help='activar la curvatura de la Terra')
    p.add_argument('--zones', action='store_true', help='dibuixar els rectangles de les zones de detall')
    p.add_argument('--objectiu', type=float, nargs=2, metavar=('LAT', 'LON'),
                   help='punt on mira la camera (per defecte, el centre del terreny)')
    p.add_argument('--overlay', choices=['cap', 'enfosquiment', 'durada', 'ombres'], default='cap',
                   help="overlay de l'eclipsi")
    p.add_argument('--opacitat', type=float, default=0.6, help="opacitat de l'overlay (0..1)")
    p.add_argument('--limits', action='store_true', help='dibuixar els limits de la franja de totalitat')
    p.add_argument('--sol-maxim', action='store_true',
                   help="posar el Sol al maxim de l'eclipsi a l'objectiu (dades del CNIG)")
    a = p.parse_args()

    app = AppSenseFinestra(*a.mida)
    ctx = app.ctx
    ctx.enable_only(mgl.DEPTH_TEST)
    app.terrain = terrain = Terrain(app, a.fitxer)
    app.light.azimut, app.light.elevacio = a.azimut, a.elevacio
    terrain.curvatura = a.curvatura
    if a.zones:
        llista = [t for t in TERRENYS if os.path.exists(t[1])]
        terrain.zones = zones_de_detall(terrain, llista, limits_utm(llista))
    if a.exageracio is not None:
        terrain.exaggeration = a.exageracio  # abans de la camera: l'objectiu s'enganxa a l'altitud exagerada
    app.camera = camera = Camera(app, terrain)
    camera.yaw, camera.pitch = a.gir, a.inclinacio
    camera.distance = a.distancia * max(terrain.mida)
    if a.objectiu:
        x_utm, y_utm = Transformer.from_crs('EPSG:4326', terrain.crs, always_xy=True).transform(a.objectiu[1], a.objectiu[0])
        punt = terrain.mon_de_utm(x_utm, y_utm)
        if punt is None:
            sys.exit(f"El punt {a.objectiu} queda fora del terreny")
        camera.target = glm.vec3(punt[0], 0.0, punt[1])
    camera.update()
    terrain.overlay = ['cap', 'enfosquiment', 'durada', 'ombres'].index(a.overlay)
    terrain.opacitat = a.opacitat
    terrain.limits_totalitat = a.limits
    if a.sol_maxim:
        info = terrain.info_punt(camera.target.x, camera.target.z)
        e = eclipse_data.punt(info['lat'], info['lon'])
        app.light.azimut, app.light.elevacio = e['azimut'], e['elevacio']
        print(f"Sol al maxim de l'eclipsi a {info['lat']:.4f}, {info['lon']:.4f}: "
              f"azimut {e['azimut']:.1f}, elevacio {e['elevacio']:.1f}")
    if a.boira is not None:
        terrain.boira = a.boira

    # renderitzar amb antialiasing (4 mostres) i copiar a un framebuffer normal per llegir-lo
    fbo_ms = ctx.simple_framebuffer(app.WIN_SIZE, samples=4)
    fbo = ctx.simple_framebuffer(app.WIN_SIZE)
    fbo_ms.use()
    fbo_ms.clear(*COLOR_CEL)
    terrain.render()
    ctx.copy_framebuffer(fbo, fbo_ms)

    imatge = np.frombuffer(fbo.read(), np.uint8).reshape(a.mida[1], a.mida[0], 3)[::-1]  # GL: fila 0 = baix
    os.makedirs(os.path.dirname(os.path.abspath(a.sortida)), exist_ok=True)
    Image.fromarray(imatge).save(a.sortida)
    print(f"Desat {a.sortida}")


if __name__ == '__main__':
    main()
