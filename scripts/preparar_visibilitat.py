"""
Precalcula el mapa de visibilitat (dades/visibilitat.py, objectiu O3) de la peninsula (nivell N0, 200 m), perque el
programa no l'hagi de calcular la primera vegada que es demana. Si ja hi es (i correspon al MDT i a la versio
actuals), no es torna a calcular. Els nivells de mes detall (N1-N3) els calcula el programa per peces, a mesura que
es miren (basecode/mapes.py); --zones calcula, a mes, les zones de 5 m fetes a ma senceres (lent: hores al Valles).

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
    claus = [a for a in sys.argv[1:] if not a.startswith('-')] or ['2026']
    peninsula = next(c for n, c, _ in TERRENYS if n == 'Peninsula')
    mdts = [peninsula] + ([c for _, c, _ in ZONES_DETALL if os.path.exists(c)] if '--zones' in sys.argv else [])
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
