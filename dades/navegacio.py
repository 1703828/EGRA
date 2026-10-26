"""
L'espai de navegacio: un cub fix que conte la Terra, la Lluna i el Sol durant tot l'interval que es pot
triar a la barra de temps. La camera d'exploracio no en pot sortir. Les distancies, mides i trajectories
dels astres son les del model: el cub nomes limita on pot anar la camera.

Com es calcula (cub_navegacio):
  1. Extrems en X, Y i Z de cada astre amb el seu radi, en coordenades terrestres (ECEF, km: X cap a la
     longitud 0, Y cap a 90 E, Z cap al pol nord), cada minut de l'interval de les efemerides. La Terra es
     l'el·lipsoide WGS84 (radi equatorial en X i Y, polar en Z).
  2. Un marge a cada costat. Com a minim un radi solar; pero amb un radi, des de la paret el Sol faria
     60 graus i no cabria a la pantalla. El marge es el que cal perque, des de la paret que hi ha darrere
     del Sol, el disc sencer ocupi com a molt el 90 % del camp de visio vertical de la camera
     d'exploracio: distancia al centre d = R / sin(0,45 * fov), marge = d - R.
  3. Les dimensions mes curtes s'amplien simetricament fins a la mes llarga: un cub.
El cub es calcula un sol cop i no canvia durant la sessio.

En ECEF la Terra no gira: es el Sol el que hi fa la volta. En les 7,5 h de l'interval (14:00-21:30 TU) el
Sol recorre ~112 graus al voltant de la Terra, i el cub ha de contenir tot aquest arc. Per aixo el costat es
d'~1,65 UA i no d'~1 UA.
"""
import math
from dataclasses import dataclass

import numpy as np

from . import geodesia
from .efemerides import RADI_SOL_KM, RADI_LLUNA_KM

UA_KM = 149_597_870.7          # unitat astronomica (IAU 2012)
FRACCIO_CAMP = 0.9             # el Sol sencer ha d'ocupar com a molt aquesta fraccio del camp vertical
DISTANCIA_PARET_KM = 1000.0    # la camera s'atura a aquesta distancia de la paret, no a sobre: si el pla
                               # d'una cara passes pels ulls, es veuria de cantell (rasteritzacio degenerada)


@dataclass(frozen=True)
class Cub:
    minim: np.ndarray          # (x, y, z) minims, km, ECEF
    maxim: np.ndarray          # (x, y, z) maxims
    costat_km: float
    marge_km: float            # marge afegit a cada costat dels extrems dels astres
    extrems_min: np.ndarray    # extrems dels astres (sense marge)
    extrems_max: np.ndarray

    def limitar(self, p):
        """El punt p dins del cub (a DISTANCIA_PARET_KM de les parets): cada coordenada que en surt es queda
        al limit. Les altres no canvien, de manera que a la paret nomes s'atura el moviment cap a fora."""
        return np.clip(p, self.minim + DISTANCIA_PARET_KM, self.maxim - DISTANCIA_PARET_KM)

    def distancia_a_les_parets(self, p):
        """Distancia (km) a la paret mes propera de cada cara: (x-, x+, y-, y+, z-, z+)."""
        return np.concatenate([p - self.minim, self.maxim - p])


def marge_per_enquadrar(fov_vertical_graus):
    """Marge (km) perque, des de la paret de darrere del Sol, el disc sencer hi capiga (veure a dalt)."""
    d = RADI_SOL_KM / math.sin(math.radians(FRACCIO_CAMP * fov_vertical_graus / 2))
    return max(RADI_SOL_KM, d - RADI_SOL_KM)


def cub_navegacio(ef, fov_vertical_graus):
    """Cub de navegacio a partir de les efemerides (ef) i del camp de visio de la camera d'exploracio."""
    hores = np.linspace(ef.inici, ef.final, int(round((ef.final - ef.inici) * 60)) + 1)   # cada minut
    sol, lluna = (np.array(v) for v in zip(*(ef.posicions(h) for h in hores)))
    terra = np.array([geodesia.A_KM, geodesia.A_KM, geodesia.B_KM])
    lo = np.minimum.reduce([sol.min(0) - RADI_SOL_KM, lluna.min(0) - RADI_LLUNA_KM, -terra])
    hi = np.maximum.reduce([sol.max(0) + RADI_SOL_KM, lluna.max(0) + RADI_LLUNA_KM, terra])
    marge = marge_per_enquadrar(fov_vertical_graus)
    centre = (lo + hi) / 2
    costat = float((hi - lo).max() + 2 * marge)
    return Cub(minim=centre - costat / 2, maxim=centre + costat / 2, costat_km=costat, marge_km=marge,
               extrems_min=lo, extrems_max=hi)
