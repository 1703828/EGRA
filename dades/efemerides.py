"""
Posicions del Sol i la Lluna en coordenades terrestres (ECEF, km) per a qualsevol instant de l'interval
d'un eclipsi (dades/eclipsis.py; el del 12/08/2026, de les 14:00 a les 21:30 TU).

Les posicions surten de JPL Horizons (scripts/descarregar_efemerides.py): geocentriques, en el
sistema ICRF (fix respecte de les estrelles) i corregides pel temps de la llum. Per posar-les en un
sistema que gira amb la Terra (el dels mapes) cal aplicar-hi tres girs:
  1. Precessio (IAU 1976): l'eix de la Terra s'ha mogut uns 0,36° des de l'any 2000.
  2. Nutacio (termes principals, error < 0,5"): petit balanceig de l'eix (fins a 17").
  3. Rotacio de la Terra (temps sideral aparent de Greenwich).
No s'inclou el moviment del pol (~0,3", uns 10 m a la superficie) ni UT1 - UTC (< 1 s).
Un error d'angle d'aquests girs mou els punts de la superficie, i l'ombra, uns R·angle: 0,5" son 15 m.
Entre dues files del fitxer (1 minut) s'interpola linealment; l'error es de l'ordre del metre.
"""
import csv
import math
import os

import numpy as np

FITXER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'data', 'efemerides', 'horizons_sol_lluna_20260812.csv')
JD_0H = 2461264.5          # dia julia del 12/08/2026 a les 0 h TU (per defecte; cada eclipsi te el seu)
TT_MENYS_UTC = 69.184      # s (TAI - UTC = 37 s, TT - TAI = 32,184 s)
RADI_SOL_KM = 696000.0     # radi del Sol
RADI_LLUNA_KM = 1737.4     # radi mitja de la Lluna
ARCSEG = math.pi / (180 * 3600)


def _r1(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, s], [0, -s, c]])


def _r2(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


def _r3(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def matriu_icrf_a_terrestre(hora_tu, jd_0h=JD_0H):
    """Matriu 3x3 que passa un vector ICRF a ECEF a l'hora TU donada (hores decimals des de les 0 h TU del dia
    jd_0h)."""
    jd_ut = jd_0h + hora_tu / 24.0
    t = (jd_ut + TT_MENYS_UTC / 86400.0 - 2451545.0) / 36525.0     # segles julians TT des de J2000
    # 1. precessio IAU 1976 (Lieske)
    zeta = (2306.2181 * t + 0.30188 * t ** 2 + 0.017998 * t ** 3) * ARCSEG
    z = (2306.2181 * t + 1.09468 * t ** 2 + 0.018203 * t ** 3) * ARCSEG
    theta = (2004.3109 * t - 0.42665 * t ** 2 - 0.041833 * t ** 3) * ARCSEG
    p = _r3(-z) @ _r2(theta) @ _r3(-zeta)
    # 2. nutacio (termes principals, Meeus cap. 22)
    om = math.radians(125.04452 - 1934.136261 * t)
    l_sol = math.radians(280.4665 + 36000.7698 * t)
    l_lluna = math.radians(218.3165 + 481267.8813 * t)
    dpsi = (-17.20 * math.sin(om) - 1.32 * math.sin(2 * l_sol) - 0.23 * math.sin(2 * l_lluna)
            + 0.21 * math.sin(2 * om)) * ARCSEG
    deps = (9.20 * math.cos(om) + 0.57 * math.cos(2 * l_sol) + 0.10 * math.cos(2 * l_lluna)
            - 0.09 * math.cos(2 * om)) * ARCSEG
    eps = (84381.448 - 46.8150 * t - 0.00059 * t ** 2 + 0.001813 * t ** 3) * ARCSEG
    n = _r1(-(eps + deps)) @ _r3(-dpsi) @ _r1(eps)
    # 3. rotacio de la Terra: temps sideral mitja (IAU 1982) + equacio dels equinoccis
    tu = (jd_ut - 2451545.0) / 36525.0
    gmst = math.radians((280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
                         + 0.000387933 * tu ** 2 - tu ** 3 / 38710000.0) % 360.0)
    gast = gmst + dpsi * math.cos(eps + deps)
    return _r3(gast) @ n @ p


class Efemerides:
    """Posicions del Sol i la Lluna (km, ECEF) a qualsevol hora TU de l'interval del fitxer."""

    def __init__(self, fitxer=FITXER, jd_0h=JD_0H):
        self.jd_0h = jd_0h
        files = []
        with open(fitxer) as f:
            for fila in csv.reader(l for l in f if not l.startswith('#')):
                if fila[0] == 'jd_ut':
                    continue
                files.append([float(v) for v in fila])
        d = np.array(files)
        self.hores = (d[:, 0] - jd_0h) * 24.0
        self.sol_icrf, self.lluna_icrf = d[:, 1:4], d[:, 4:7]
        self.inici, self.final = float(self.hores[0]), float(self.hores[-1])

    def _interpola(self, taula, hora_tu):
        h = min(max(hora_tu, self.inici), self.final)
        i = min(int((h - self.inici) / (self.hores[1] - self.hores[0])), len(self.hores) - 2)
        t = (h - self.hores[i]) / (self.hores[i + 1] - self.hores[i])
        return taula[i] * (1 - t) + taula[i + 1] * t

    def posicions(self, hora_tu):
        """(sol, lluna): posicions ECEF en km (arrays de numpy float64) a l'hora TU."""
        m = matriu_icrf_a_terrestre(hora_tu, self.jd_0h)
        return m @ self._interpola(self.sol_icrf, hora_tu), m @ self._interpola(self.lluna_icrf, hora_tu)
