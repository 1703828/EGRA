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


# ------------------------------------------------------------ viatges cap a un astre

def distancia_enquadrar(radi, fov_vertical_graus, aspecte, fraccio=0.8):
    """Distancia al centre (km) des d'on un astre de radi donat es veu sencer: el disc ocupa la fraccio
    indicada del camp de visio mes estret (el vertical o l'horitzontal, segons la proporcio de la finestra)."""
    fov_v = math.radians(fov_vertical_graus)
    fov_h = 2 * math.atan(math.tan(fov_v / 2) * aspecte)
    return radi / math.sin(fraccio * min(fov_v, fov_h) / 2)


def suavitzat(t):
    """0..1 -> 0..1 amb velocitat i acceleracio nul·les als extrems (polinomi de grau 5, 'smootherstep')."""
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def _unitari(v):
    return v / np.linalg.norm(v)


def _slerp(a, b, s):
    """Interpolacio esferica entre dos vectors unitaris."""
    c = float(np.clip(np.dot(a, b), -1.0, 1.0))
    angle = math.acos(c)
    if angle < 1e-9:
        return a.copy()
    return (math.sin((1 - s) * angle) * a + math.sin(s * angle) * b) / math.sin(angle)


def _girar(v, eix, angle):
    """Rotacio de Rodrigues del vector v al voltant de l'eix unitari."""
    return v * math.cos(angle) + np.cross(eix, v) * math.sin(angle) + eix * np.dot(eix, v) * (1 - math.cos(angle))


@dataclass
class Trajecte:
    """Cami d'un viatge, relatiu al centre de l'astre de desti (que es pot moure): a cada instant la camera
    es a centre + u(s) * r(s), amb u entre u0 i u1 (interpolacio esferica) i r entre r0 i r1 en escala
    logaritmica (a distancies astronomiques, cada segon redueix la distancia en la mateixa proporcio)."""
    u0: np.ndarray
    u1: np.ndarray
    r0: float
    r1: float
    durada: float

    def posicio_relativa(self, s):
        """s = 0..1 (ja suavitzat): posicio relativa al centre del desti."""
        r = math.exp(math.log(self.r0) + s * (math.log(self.r1) - math.log(self.r0)))
        return _unitari(_slerp(self.u0, self.u1, s)) * r


def planificar_trajecte(p0, centre, r_final, obstacles, evitar_terra=True, mostres=200):
    """Trajecte de p0 fins a r_final del centre del desti sense travessar cap obstacle: els altres astres
    (centre, radi) i, si evitar_terra, el terra (la Terra no es una esfera: es comprova l'altitud geodesica
    de cada punt del cami, que no pot baixar de 10 km ni de l'altitud inicial si ja es mes avall). Un obstacle
    en que la camera ja es a prop no es compta per sota de la distancia inicial.
    Primer es prova d'arribar pel mateix costat (u1 = u0: cami recte cap al centre); si hi ha un obstacle,
    es gira la direccio final allunyant-la'n (20, 40... 160 graus) i es tria la primera que no el travessa."""
    u0 = _unitari(p0 - centre)
    r0 = float(np.linalg.norm(p0 - centre))
    alt0 = float(geodesia.geodesiques(np.asarray(p0))[2])
    alt_min = min(10.0, alt0) - 1e-6

    def bloqueig(u1):
        """None si el cami es lliure; si no, el centre de l'obstacle que travessa."""
        t = Trajecte(u0, u1, r0, r_final, 1.0)
        punts = np.array([centre + t.posicio_relativa(suavitzat(i / mostres)) for i in range(mostres + 1)])
        if evitar_terra and (geodesia.geodesiques(punts)[2] < alt_min).any():
            return np.zeros(3)
        for c, radi in obstacles:
            limit = min(radi * 1.05, float(np.linalg.norm(p0 - c)) * (1 - 1e-9))
            if (np.linalg.norm(punts - c, axis=1) < limit).any():
                return np.asarray(c, dtype=float)
        return None

    u1, obstacle = u0, bloqueig(u0)
    if obstacle is not None:
        b = obstacle - centre
        eix = np.cross(u0, b) if np.linalg.norm(b) > 0 else np.zeros(3)
        if np.linalg.norm(eix) < 1e-9 * max(np.linalg.norm(b), 1.0):   # obstacle just al davant o darrere
            eix = np.cross(u0, [0.0, 0.0, 1.0] if abs(u0[2]) < 0.9 else [1.0, 0.0, 0.0])
        eix = _unitari(eix)
        for graus in range(20, 180, 20):
            candidat = _unitari(_girar(u0, eix, -math.radians(graus)))   # angle negatiu: lluny de l'obstacle
            if bloqueig(candidat) is None:
                u1 = candidat
                break
    durada = min(max(1.2 + 0.25 * abs(math.log(r0 / r_final)), 1.2), 3.5)
    return Trajecte(u0, u1, r0, r_final, durada)
