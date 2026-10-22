"""
Model geometric de l'eclipsi del 12/08/2026 vist des d'un punt de la Terra.

No s'ajusta a cap dada del CNIG. Per a cada instant:
  1. Les posicions del Sol i la Lluna surten de JPL Horizons (dades/efemerides.py), en coordenades
     terrestres (ECEF, km).
  2. La posicio de l'observador surt de la seva latitud, longitud i altitud sobre l'el·lipsoide WGS84
     (dades/geodesia.py).
  3. Des de l'observador, el Sol i la Lluna es veuen com dos discs. La mida aparent de cadascun
     (radi angular) es radi / distancia, i la separacio es l'angle entre les dues direccions.
  4. La part del Sol tapada es l'area on els dos discs se solapen, dividida per l'area del Sol.
Els contactes surten d'aquesta geometria: C1 i C4 quan els discs es toquen per fora, C2 i C3 quan la
Lluna cobreix el Sol del tot, i el maxim quan la separacio es minima.

Aproximacions: la vora de la Lluna es un cercle (sense muntanyes, ~1-3 s als contactes); no
s'inclou la refraccio als contactes (afecta igual el Sol i la Lluna); l'elevacio del Sol que es
mostra inclou la refraccio estandard (com la del CNIG). Hores en TU decimals; CEST = TU + 2.
"""
import math

import glm
import numpy as np

from . import geodesia
from .efemerides import Efemerides, RADI_SOL_KM, RADI_LLUNA_KM

# mides aparents de referencia (radi angular des del centre de la Terra, al maxim): per dibuixar a
# l'escena antiga. El model fa servir les distancies reals de cada instant.
RADI_ANGULAR_SOL = RADI_SOL_KM / 151.6e6
RADI_ANGULAR_LLUNA = RADI_LLUNA_KM / 364200.0

_EFEMERIDES = None


def efemerides():
    """Les efemerides es llegeixen un sol cop (fitxer petit) i es comparteixen."""
    global _EFEMERIDES
    if _EFEMERIDES is None:
        _EFEMERIDES = Efemerides()
    return _EFEMERIDES


def area_tapada(d, r1, r2):
    """Fraccio del disc del Sol (radi r1) tapada per la Lluna (radi r2) amb els centres a distancia d
    (tot en radians)."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r2 - r1):
        return min(1.0, (r2 / r1) ** 2)
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    a3 = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return (a1 + a2 - a3) / (math.pi * r1 * r1)


def angle_entre(a, b):
    """Angle entre dos vectors (rad), precis tambe per a angles molt petits."""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    return 2 * math.asin(min(1.0, np.linalg.norm(a - b) / 2))


class ModelEclipsi:
    def __init__(self, lat, lon, alt_km=0.0):
        self.lat, self.lon, self.alt_km = lat, lon, alt_km
        self.posicio = geodesia.ecef(lat, lon, alt_km)        # observador, ECEF (km)
        self.ef = efemerides()
        self.hores = self._contactes()
        self.valid = self.hores['c1'] is not None
        self.durada = ((self.hores['c3'] - self.hores['c2']) * 3600.0
                       if self.hores['c2'] is not None else None)

    # ------------------------------------------------------------ geometria a cada instant

    def discs(self, hora_tu):
        """(separacio, radi del Sol, radi de la Lluna), tot en radians, vistos des de l'observador."""
        sol, lluna = self.ef.posicions(hora_tu)
        s, l = sol - self.posicio, lluna - self.posicio
        rs = math.asin(RADI_SOL_KM / np.linalg.norm(s))
        rl = math.asin(RADI_LLUNA_KM / np.linalg.norm(l))
        return angle_entre(s, l), rs, rl

    def fraccio_tapada(self, hora_tu):
        d, rs, rl = self.discs(hora_tu)
        return area_tapada(d, rs, rl)

    def sol(self, hora_tu, refraccio=True):
        """(azimut, elevacio) del Sol en graus; l'elevacio, aparent (amb refraccio) si refraccio=True."""
        sol, _ = self.ef.posicions(hora_tu)
        az, el = geodesia.azimut_elevacio(sol - self.posicio, self.lat, self.lon)
        return az, el + (geodesia.refraccio_graus(el) if refraccio else 0.0)

    def _local(self, direccio_ecef):
        """Direccio ECEF -> vector de l'escena antiga (x = est, y = amunt, z = sud)."""
        est, nord, amunt = geodesia.base_local(self.lat, self.lon)
        d = direccio_ecef / np.linalg.norm(direccio_ecef)
        return glm.vec3(float(d @ est), float(d @ amunt), float(-(d @ nord)))

    def direccio_sol(self, hora_tu):
        sol, _ = self.ef.posicions(hora_tu)
        return self._local(sol - self.posicio)

    def direccio_lluna(self, hora_tu):
        _, lluna = self.ef.posicions(hora_tu)
        return self._local(lluna - self.posicio)

    # ------------------------------------------------------------ contactes

    def _arrel(self, f, a, b):
        """Instant entre a i b (hores) on f canvia de signe (biseccio fins a ~1 ms)."""
        fa = f(a)
        for _ in range(40):
            m = (a + b) / 2
            fm = f(m)
            if (fm > 0) == (fa > 0):
                a, fa = m, fm
            else:
                b = m
        return (a + b) / 2

    def _contactes(self):
        ef = self.ef
        hores = np.arange(ef.inici, ef.final, 1 / 60)
        mostres = [self.discs(h) for h in hores]
        exterior = [d - (rs + rl) for d, rs, rl in mostres]          # < 0: els discs se solapen
        interior = [d - (rl - rs) for d, rs, rl in mostres]          # < 0: la Lluna cobreix el Sol
        h = dict(c1=None, c2=None, maxim=None, c3=None, c4=None, posta=None)
        for i in range(len(hores) - 1):
            for f, inici, final, valors in ((lambda t: self.discs(t)[0] - sum(self.discs(t)[1:]), 'c1', 'c4', exterior),
                                            (lambda t: (lambda d, rs, rl: d - (rl - rs))(*self.discs(t)), 'c2', 'c3', interior)):
                if valors[i] > 0 >= valors[i + 1]:
                    h[inici] = self._arrel(f, hores[i], hores[i + 1])
                elif valors[i] <= 0 < valors[i + 1]:
                    h[final] = self._arrel(f, hores[i], hores[i + 1])
        if h['c1'] is not None:
            # maxim: separacio minima (seccio aurea entre C1 i C4)
            a, b = h['c1'], h['c4'] if h['c4'] is not None else ef.final
            g = (math.sqrt(5) - 1) / 2
            for _ in range(60):
                c, d = b - g * (b - a), a + g * (b - a)
                if self.discs(c)[0] < self.discs(d)[0]:
                    b = d
                else:
                    a = c
            h['maxim'] = (a + b) / 2
        # posta: centre del Sol a -0,833° (refraccio estandard + radi aparent), com a les efemerides habituals
        el = [self.sol(t, refraccio=False)[1] + 0.833 for t in hores]
        for i in range(len(hores) - 1):
            if el[i] > 0 >= el[i + 1]:
                h['posta'] = self._arrel(lambda t: self.sol(t, refraccio=False)[1] + 0.833, hores[i], hores[i + 1])
        return h

    # ------------------------------------------------------------ per a la interficie

    def fase(self, hora_tu):
        h = self.hores
        if not self.valid:
            return 'Sense eclipsi en aquest punt'
        if hora_tu < h['c1']:
            return "Abans de l'eclipsi"
        if h['c2'] is not None and h['c2'] <= hora_tu <= h['c3']:
            return 'TOTALITAT'
        if h['c4'] is None or hora_tu <= h['c4']:
            return 'Eclipsi parcial'
        return "Despres de l'eclipsi"

    def interval(self, marge=0.25):
        """(inici, final) en hores TU per a la barra de temps: de C1 a C4 amb un marge."""
        if not self.valid:
            return self.ef.inici, self.ef.final
        final = self.hores['c4'] if self.hores['c4'] is not None else self.ef.final
        return max(self.hores['c1'] - marge, self.ef.inici), min(final + marge, self.ef.final)
