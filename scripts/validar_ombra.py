"""
Comprova que l'ombra de la Lluna del nostre model cau on diu el CNIG.

El CNIG publica el contorn de l'ombra total (umbra) cada 3,6 s entre les 18,293 i les 18,569 h TU
(capa shadows_merged del GeoPackage). Per a uns quants instants, calculem on talla l'eix de l'ombra
la superficie de la Terra (dades/model_eclipsi.centre_ombra) i mirem (1) si cau dins del poligon del
CNIG i (2) a quina distancia del centre geometric del poligon. El poligon pot estar retallat a les
vores de la zona d'estudi del CNIG (al principi i al final), on el centre geometric no es representatiu.

Executa (des de l'arrel):  python scripts/validar_ombra.py
"""
import os
import sys

import fiona
from pyproj import Geod
from shapely.geometry import shape, Point

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dades.model_eclipsi import centre_ombra  # noqa: E402

GPKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'eclipsi2026', 'Eclipses_2026.gpkg')


def main():
    capa = next(c for c in fiona.listlayers(GPKG) if 'shadow' in c)
    geod = Geod(ellps='WGS84')
    print(f"{'hora TU':>8s}  {'model (lat, lon)':>20s}  {'dins':>4s}  {'dist. al centre del CNIG':>24s}")
    dists = []
    with fiona.open(GPKG, layer=capa) as c:
        for i, feat in enumerate(c):
            if i % 30 != 15:
                continue
            hora = next(float(k.split('_')[-1]) for k, v in feat['properties'].items()
                        if k.startswith('mancha_ut_') and v is not None)
            poligon = shape(feat['geometry'])
            m = centre_ombra(hora)
            if m is None:
                print(f"{hora:8.3f}  l'eix no toca la Terra")
                continue
            dins = poligon.contains(Point(m[1], m[0]))
            _, _, dist = geod.inv(m[1], m[0], poligon.centroid.x, poligon.centroid.y)
            dists.append(dist / 1000)
            print(f"{hora:8.3f}  {m[0]:8.3f}, {m[1]:8.3f}    {'si' if dins else 'NO':>4s}  {dist / 1000:20.1f} km")
    print(f"Distancia maxima al centre del poligon: {max(dists):.1f} km")


if __name__ == '__main__':
    main()
