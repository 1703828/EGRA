"""
Descarrega les textures de la Terra i la Lluna (NASA, domini public) a data/textures/.

- Terra: "Blue Marble: Land Surface, Shallow Water, and Shaded Topography" (NASA Visible Earth,
  2002), 2048 x 1024, projeccio equirectangular (longitud -180..180, latitud 90..-90).
- Lluna: "CGI Moon Kit", color de la LRO (NASA Scientific Visualization Studio), 1024 x 512,
  equirectangular, longitud 0 (la cara que mira la Terra) al centre.

Executa (des de l'arrel):  python scripts/descarregar_textures.py
"""
import os
import sys

import requests

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ARREL, 'data', 'textures')
TEXTURES = {
    'terra_2048.jpg': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57752/land_shallow_topo_2048.jpg',
    'lluna_1024.jpg': 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_1k.jpg',
}


def main():
    os.makedirs(DIR, exist_ok=True)
    for nom, url in TEXTURES.items():
        cami = os.path.join(DIR, nom)
        if os.path.exists(cami):
            print(f"{nom}: ja hi es")
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(cami + '.tmp', 'wb') as f:
            f.write(r.content)
        os.replace(cami + '.tmp', cami)
        print(f"{nom}: {len(r.content) / 1e3:.0f} kB de {url}")


if __name__ == '__main__':
    sys.exit(main())
