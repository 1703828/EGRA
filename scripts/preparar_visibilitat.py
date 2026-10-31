"""
Precalcula els mapes de visibilitat (dades/visibilitat.py, objectiu O3) de la peninsula i de les zones de detall
descarregades, perque el programa no els hagi de calcular la primera vegada que es demanen. Els que ja hi son
(i corresponen al MDT actual) no es tornen a calcular.

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/preparar_visibilitat.py                 # eclipsi del 2026
    python scripts/preparar_visibilitat.py 2026 2027 2028  # tots
"""
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from dades import eclipsis, visibilitat  # noqa: E402
from dades.data_io import TERRENYS, ZONES_DETALL  # noqa: E402


def main():
    claus = sys.argv[1:] or ['2026']
    peninsula = next(c for n, c, _ in TERRENYS if n == 'Peninsula')
    mdts = [peninsula] + [c for _, c, _ in ZONES_DETALL if os.path.exists(c)]
    for clau in claus:
        eclipsis.triar(clau)
        for cami in mdts:
            nom = os.path.basename(cami)
            if visibilitat.llegir(cami, clau) is not None:
                print(f'{clau} {nom}: ja hi es')
                continue
            t0 = time.time()
            visibilitat.calcular(cami, clau, peninsula, avis=lambda text: print(f'  {text}', flush=True))
            mida = os.path.getsize(visibilitat.cami_cache(clau, cami)) / 1e6
            print(f'{clau} {nom}: {time.time() - t0:.0f} s, {mida:.0f} MB', flush=True)


if __name__ == '__main__':
    main()
