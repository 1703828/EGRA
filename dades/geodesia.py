"""
Geodesia: passar de latitud, longitud i altitud a coordenades terrestres i al reves.

Fem servir l'el·lipsoide WGS84 (practicament igual que el GRS80 de l'ETRS89 dels MDT). Les
coordenades terrestres (ECEF, "Earth-centered, Earth-fixed") tenen l'origen al centre de la Terra:
  X cap a la longitud 0 a l'equador, Y cap a la longitud 90° E, Z cap al pol nord. Unitats: km.
Tot es fa en float64 (doble precisio): a 6.400 km del centre, el float32 nomes arriba al mig metre.
"""
import math

import numpy as np

A_KM = 6378.137                    # radi equatorial (WGS84)
F = 1 / 298.257223563              # aplatament
B_KM = A_KM * (1 - F)              # radi polar (6356,752 km)
E2 = F * (2 - F)                   # excentricitat al quadrat


def ecef(lat, lon, alt_km=0.0):
    """Latitud i longitud geodesiques (graus) i altitud sobre l'el·lipsoide (km) -> (x, y, z) en km.
    Funciona amb nombres o amb arrays de numpy."""
    fi, la = np.radians(lat), np.radians(lon)
    n = A_KM / np.sqrt(1 - E2 * np.sin(fi) ** 2)       # radi de curvatura en el primer vertical
    x = (n + alt_km) * np.cos(fi) * np.cos(la)
    y = (n + alt_km) * np.cos(fi) * np.sin(la)
    z = (n * (1 - E2) + alt_km) * np.sin(fi)
    return np.stack([x, y, z], axis=-1)


def geodesiques(p):
    """(x, y, z) en km -> (lat, lon, alt_km), amb el metode iteratiu habitual (convergeix en 3-4 passos)."""
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    lon = np.arctan2(y, x)
    r = np.hypot(x, y)
    lat = np.arctan2(z, r * (1 - E2))
    for _ in range(6):
        n = A_KM / np.sqrt(1 - E2 * np.sin(lat) ** 2)
        alt = r / np.cos(lat) - n
        lat = np.arctan2(z, r * (1 - E2 * n / (n + alt)))
    n = A_KM / np.sqrt(1 - E2 * np.sin(lat) ** 2)
    alt = r / np.cos(lat) - n
    return np.degrees(lat), np.degrees(lon), alt


def base_local(lat, lon):
    """Vectors unitaris (est, nord, amunt) en ECEF al punt (lat, lon). "Amunt" es la vertical del
    lloc (perpendicular a l'el·lipsoide), que es la que marca una plomada."""
    fi, la = math.radians(lat), math.radians(lon)
    est = np.array([-math.sin(la), math.cos(la), 0.0])
    nord = np.array([-math.sin(fi) * math.cos(la), -math.sin(fi) * math.sin(la), math.cos(fi)])
    amunt = np.array([math.cos(fi) * math.cos(la), math.cos(fi) * math.sin(la), math.sin(fi)])
    return est, nord, amunt


def azimut_elevacio(direccio, lat, lon):
    """Direccio en ECEF (no cal que sigui unitaria) -> (azimut des del nord en sentit horari, elevacio), en graus."""
    est, nord, amunt = base_local(lat, lon)
    d = np.asarray(direccio, dtype=float)
    d = d / np.linalg.norm(d)
    e, n, u = d @ est, d @ nord, d @ amunt
    return math.degrees(math.atan2(e, n)) % 360.0, math.degrees(math.asin(max(-1.0, min(1.0, u))))


def refraccio_graus(elevacio):
    """Refraccio astronomica estandard (formula de Bennett, 10 °C i 1010 hPa): quant mes alt es veu un
    astre del que es en realitat, en graus. Per sota de -1° no te sentit i es retorna 0."""
    if elevacio < -1.0:
        return 0.0
    return 1.0 / math.tan(math.radians(elevacio + 7.31 / (elevacio + 4.4))) / 60.0
