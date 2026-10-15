"""
Prepara les caches de tots els terrenys del selector (data/cache/<nom>.derivats.npz):
gradient, distancia a la costa, altitud mitjanada i overlays de l'eclipsi.

Els MDT son a data/mdt/ (o es descarreguen amb scripts/descarregar_mdt.py). Despres d'executar aquest
script, el programa (python main.py) carrega cada terreny en una fraccio de segon.

Executa (des de l'arrel del projecte):
    python scripts/preparar_dades.py
"""
import os
import sys
import time

import moderngl as mgl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data_io  # noqa: E402
from terrain import MAX_VERTEXS  # noqa: E402


def main():
    # la cache depen de la mida maxima de textura de la GPU: la consultem igual que el programa
    max_textura = mgl.create_standalone_context(require=330).info['GL_MAX_TEXTURE_SIZE']
    for nom, cami, _ in data_io.TERRENYS:
        if not os.path.exists(cami):
            print(f"AVIS: no hi ha {cami}; descarrega'l amb scripts/descarregar_mdt.py")
            continue
        t0 = time.time()
        print(f"== {nom}")
        data_io.carregar_terreny(cami, max_textura, MAX_VERTEXS)
        print(f"   {time.time() - t0:.1f} s")


if __name__ == '__main__':
    main()
