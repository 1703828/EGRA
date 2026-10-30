"""
Descarrega les textures de la Terra i la Lluna (NASA, domini public) a data/textures/.

- Terra: "Blue Marble: Land Surface, Shallow Water, and Shaded Topography" (NASA Visible Earth,
  2002), 2048 x 1024, projeccio equirectangular (longitud -180..180, latitud 90..-90).
- Lluna: "CGI Moon Kit" (NASA Scientific Visualization Studio), equirectangular, longitud 0 (la cara que mira la
  Terra) al centre:
  - color de la LRO a 1024 x 512 (al Git, 139 kB): el que fa servir el programa si no hi ha els d'alta resolucio;
  - amb --alta: color a 8192 x 4096 (~1,3 km per pixel, 51 MB) i mapa d'altituds del LOLA a 16 pixels per grau
    (5760 x 2880, ~1,9 km per pixel, 33 MB). Es baixen a data/textures/originals/ i es converteixen a
    lluna_8k.jpg i lluna_altitud.npy (altitud en km, float16), que llegeix basecode/astres.py. Fora del Git.

Executa (des de l'arrel):  python scripts/descarregar_textures.py [--alta]
"""
import os
import sys

import numpy as np
import requests
from PIL import Image

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ARREL, 'data', 'textures')
KIT_LLUNA = 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/'
TEXTURES = {
    'terra_2048.jpg': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57752/land_shallow_topo_2048.jpg',
    'lluna_1024.jpg': KIT_LLUNA + 'lroc_color_poles_1k.jpg',
}
ORIGINALS_ALTA = {'lroc_color_poles_8k.tif': KIT_LLUNA + 'lroc_color_poles_8k.tif',
                  'ldem_16_uint.tif': KIT_LLUNA + 'ldem_16_uint.tif'}


def baixar(cami, url):
    if os.path.exists(cami):
        print(f"{os.path.basename(cami)}: ja hi es")
        return
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    with open(cami + '.tmp', 'wb') as f:
        f.write(r.content)
    os.replace(cami + '.tmp', cami)
    print(f"{os.path.basename(cami)}: {len(r.content) / 1e6:.1f} MB de {url}")


def preparar_alta():
    """Converteix els originals de la Lluna als fitxers que llegeix el programa."""
    originals = os.path.join(DIR, 'originals')
    Image.MAX_IMAGE_PIXELS = None            # 8192 x 4096: mes gran que el limit de seguretat de PIL
    color = os.path.join(DIR, 'lluna_8k.jpg')
    if not os.path.exists(color):
        Image.open(os.path.join(originals, 'lroc_color_poles_8k.tif')).convert('RGB').save(color, quality=92)
        print(f"lluna_8k.jpg: {os.path.getsize(color) / 1e6:.1f} MB")
    altitud = os.path.join(DIR, 'lluna_altitud.npy')
    if not os.path.exists(altitud):
        # ldem_16_uint: enters de 16 bits en mitjos metres, amb 10 km sumats (el minim de la Lluna es -9,1 km):
        # altitud (km) = valor * 0,0005 - 10, respecte d'una esfera de 1737,4 km
        v = np.array(Image.open(os.path.join(originals, 'ldem_16_uint.tif')), dtype=np.float64)
        np.save(altitud, (v * 0.0005 - 10.0).astype(np.float16))
        print(f"lluna_altitud.npy: {v.shape[1]} x {v.shape[0]}, de {v.min() * 0.0005 - 10:.1f} a "
              f"{v.max() * 0.0005 - 10:.1f} km")


def main():
    os.makedirs(DIR, exist_ok=True)
    for nom, url in TEXTURES.items():
        baixar(os.path.join(DIR, nom), url)
    if '--alta' in sys.argv:
        os.makedirs(os.path.join(DIR, 'originals'), exist_ok=True)
        for nom, url in ORIGINALS_ALTA.items():
            baixar(os.path.join(DIR, 'originals', nom), url)
        preparar_alta()


if __name__ == '__main__':
    sys.exit(main())
