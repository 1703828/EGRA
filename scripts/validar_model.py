"""
Comprova el model geometric de l'eclipsi contra les dades del CNIG en diversos punts.

El model (dades/model_eclipsi.py) no fa servir cap hora del CNIG: calcula, a partir de les posicions
del Sol i la Lluna de JPL Horizons i de la posicio de l'observador sobre l'el·lipsoide, quan la Lluna
comenca a tapar el Sol (C1), quan el tapa del tot (C2), el maxim, quan el destapa (C3) i quan se'n
separa (C4). Per tant, la comparacio amb el CNIG es una comprovacio independent.

Convencions: hores en TU; altitud de l'observador = MDT de la peninsula (200 m) en aquell punt (el
CNIG fa servir el GMTED2010 d'~800 m); radi de la Lluna 1737,4 km (sense les muntanyes de la vora);
elevacio del Sol aparent (refraccio de Bennett, com la banda 1 del CNIG).

Executa (des de l'arrel):  python scripts/validar_model.py
"""
import os
import sys

import rasterio
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dades import eclipse_data  # noqa: E402
from dades.model_eclipsi import ModelEclipsi  # noqa: E402
from dades.observador import UBICACIONS_PROVES as UBICACIONS  # noqa: E402

MDT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'mdt', 'peninsula_200m.tif')
# les sis ubicacions del programa (dades/observador.py) i tres punts mes de comprovacio (centres de ciutat
# aproximats: nomes serveixen per comparar el model amb el CNIG en altres llocs)
PUNTS = [(nom.split(',')[0].split(' (')[0], lat, lon) for nom, lat, lon in UBICACIONS] + [
    ('Burgos', 42.3439, -3.6969), ('Valencia', 39.4699, -0.3763), ('Palma', 39.5696, 2.6502)]


def altitud_km(lat, lon):
    x, y = Transformer.from_crs(4326, 25830, always_xy=True).transform(lon, lat)
    with rasterio.open(MDT) as d:
        return max(float(next(d.sample([(x, y)]))[0]), 0.0) / 1000.0


def main():
    print(f"{'Punt':16s} {'C1':>7s} {'C2':>7s} {'max':>7s} {'C3':>7s} {'C4':>7s}  {'tapat':>6s}  {'elev.':>6s}   (diferencies amb el CNIG, en segons; tapat i elevacio: model - CNIG)")
    pitjor = {}
    for nom, lat, lon in PUNTS:
        m = ModelEclipsi(lat, lon, altitud_km(lat, lon))
        e = eclipse_data.punt(lat, lon)['hores_tu']
        cnig = eclipse_data.punt(lat, lon)
        cols = []
        for k in ('c1', 'c2', 'maxim', 'c3', 'c4'):
            if m.hores[k] is None or e[k] is None:
                cols.append('   -   ' if m.hores[k] is None and e[k] is None else '  ???  ')
                continue
            d = (m.hores[k] - e[k]) * 3600
            pitjor[k] = max(pitjor.get(k, 0), abs(d))
            cols.append(f"{d:+7.1f}")
        tapat = (m.fraccio_tapada(m.hores['maxim']) - cnig['enfosquiment']) * 100
        _, el = m.sol(m.hores['maxim'])
        print(f"{nom:16s} {' '.join(cols)}  {tapat:+5.2f}%  {el - cnig['elevacio']:+6.3f}°")
    print('Diferencia maxima (s):', ', '.join(f'{k} {v:.1f}' for k, v in pitjor.items()))


if __name__ == '__main__':
    main()
