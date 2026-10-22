"""
Model de l'eclipsi del 12/08/2026 vist des d'un punt (lat, lon): on son el Sol i la Lluna a cada hora.

- Sol: algorisme simplificat de la NOAA (precisio d'~0.01 graus), corregit amb un petit desplacament
  constant perque al maxim coincideixi exactament amb l'azimut i l'elevacio del CNIG.
- Lluna: primera aproximacio. Al cel, la Lluna es mou en linia recta respecte del Sol, en la
  direccio de l'ecliptica (cap a l'est), i passa a la distancia minima a l'hora del maxim. La
  velocitat i la distancia minima s'ajusten amb les hores de contacte del CNIG en aquell punt:
    - de l'inici al final de la parcialitat, la separacio va de (Rs + Rl) a -(Rs + Rl)
    - durant la totalitat, la separacio es menor que (Rl - Rs)
  Fora de la franja de totalitat, la distancia minima surt de l'enfosquiment maxim.
- Hores en TU decimals (p. ex. 18.47). L'hora local (CEST) es TU + 2.
"""
import math
from datetime import datetime, timezone

import glm

import eclipse_data
from astres import RADI_ANGULAR_SOL as RS, RADI_ANGULAR_LLUNA as RL

DATA = datetime(2026, 8, 12, tzinfo=timezone.utc)
JD_DATA = 2440587.5 + DATA.timestamp() / 86400.0  # dia julia a les 0 h TU


def direccio_local(azimut, elevacio):
    """Azimut i elevacio (graus) -> vector unitari del mon (X = est, Y = amunt, Z = sud)."""
    az, el = math.radians(azimut), math.radians(elevacio)
    return glm.vec3(math.cos(el) * math.sin(az), math.sin(el), -math.cos(el) * math.cos(az))


def posicio_sol(lat, lon, hora_tu, d_longitud=0.0):
    """Azimut i elevacio (graus, sense refraccio) del Sol a (lat, lon) a l'hora TU.
    d_longitud: graus afegits a la longitud ecliptica (per saber cap on va l'ecliptica)."""
    jd = JD_DATA + hora_tu / 24.0
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    c = (math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) + math.sin(2 * m) * (0.019993 - 0.000101 * t)
         + math.sin(3 * m) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * t)
    lam = math.radians(l0 + c - 0.00569 - 0.00478 * math.sin(omega) + d_longitud)
    eps = math.radians(23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
                       + 0.00256 * math.cos(omega))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t
    h = math.radians(gmst + lon) - ra   # angle horari
    fi = math.radians(lat)
    el = math.asin(math.sin(fi) * math.sin(dec) + math.cos(fi) * math.cos(dec) * math.cos(h))
    az = math.atan2(-math.cos(dec) * math.sin(h), math.sin(dec) * math.cos(fi) - math.cos(dec) * math.cos(h) * math.sin(fi))
    return math.degrees(az) % 360, math.degrees(el)


def area_tapada(d, r1=RS, r2=RL):
    """Fraccio del disc del Sol (radi r1) tapada per la Lluna (radi r2) amb els centres a distancia d."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r2 - r1):
        return min(1.0, (r2 / r1) ** 2)
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    a3 = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return (a1 + a2 - a3) / (math.pi * r1 * r1)


class ModelEclipsi:
    def __init__(self, lat, lon):
        self.lat, self.lon = lat, lon
        e = eclipse_data.punt(lat, lon) if eclipse_data.disponible() else None
        self.valid = e is not None and e['hores_tu']['c1'] is not None
        if not self.valid:  # sense eclipsi: la Lluna queda lluny del Sol
            self.hores = dict(c1=None, c2=None, maxim=18.5, c3=None, c4=None, posta=None)
            self.correccio = (0.0, 0.0)
            self.v, self.d_min = 0.0, 1.0
            return
        h = self.hores = e['hores_tu']
        self.durada = e['durada']

        # correccio del Sol: al maxim, el mateix azimut i elevacio que el CNIG
        az, el = posicio_sol(lat, lon, h['maxim'])
        self.correccio = (e['azimut'] - az, e['elevacio'] - el)

        # velocitat aparent v (rad/s) i distancia minima d_min (rad) entre els centres
        mig = (h['c4'] - h['c1']) / 2 * 3600.0  # s del maxim a cada contacte exterior
        if self.durada:
            mig_total = self.durada / 2
            self.v = math.sqrt(4 * RS * RL / (mig ** 2 - mig_total ** 2))
            self.d_min = math.sqrt(max(0.0, (RS + RL) ** 2 - (self.v * mig) ** 2))
        else:
            # distancia minima que dona l'enfosquiment maxim (cerca binaria: area_tapada decreix amb d)
            a, b = abs(RL - RS), RS + RL
            for _ in range(50):
                c = (a + b) / 2
                a, b = (c, b) if area_tapada(c) > e['enfosquiment'] else (a, c)
            self.d_min = (a + b) / 2
            self.v = math.sqrt(max(0.0, (RS + RL) ** 2 - self.d_min ** 2)) / mig
        # costat: si la linia central es al nord (la durada o l'enfosquiment creixen cap al nord),
        # som al sud de l'eix de l'ombra i la Lluna passa pel nord del Sol (i al reves)
        clau = 'durada' if self.durada else 'enfosquiment'
        nord, sud = eclipse_data.punt(lat + 0.05, lon), eclipse_data.punt(lat - 0.05, lon)
        if nord and sud and (nord[clau] or 0) < (sud[clau] or 0):
            self.d_min = -self.d_min

    # ------------------------------------------------------------ posicions a cada hora

    def sol(self, hora_tu):
        """(azimut, elevacio) del Sol en graus."""
        az, el = posicio_sol(self.lat, self.lon, hora_tu)
        return (az + self.correccio[0]) % 360, el + self.correccio[1]

    def direccio_sol(self, hora_tu):
        return direccio_local(*self.sol(hora_tu))

    def direccio_lluna(self, hora_tu):
        """Vector unitari cap a la Lluna: el Sol + un desplacament al pla tangent del cel."""
        s = self.direccio_sol(hora_tu)
        # direccio de l'ecliptica al Sol (cap on va la Lluna respecte del Sol)
        az2, el2 = posicio_sol(self.lat, self.lon, hora_tu, d_longitud=0.05)
        m = direccio_local(az2 + self.correccio[0], el2 + self.correccio[1]) - s
        m = glm.normalize(m - glm.dot(m, s) * s)
        # perpendicular a m al pla tangent, girada cap al pol nord celeste
        q = glm.normalize(glm.cross(m, s))
        fi = math.radians(self.lat)
        if glm.dot(q, glm.vec3(0, math.sin(fi), -math.cos(fi))) < 0:
            q = -q
        u = self.v * (hora_tu - self.hores['maxim']) * 3600.0
        return glm.normalize(s + u * m + self.d_min * q)

    def separacio(self, hora_tu):
        """Distancia angular (rad) entre els centres del Sol i la Lluna."""
        return math.sqrt((self.v * (hora_tu - self.hores['maxim']) * 3600.0) ** 2 + self.d_min ** 2)

    def fraccio_tapada(self, hora_tu):
        return area_tapada(self.separacio(hora_tu)) if self.valid else 0.0

    def fase(self, hora_tu):
        h = self.hores
        if not self.valid:
            return 'Sense eclipsi en aquest punt'
        if hora_tu < h['c1']:
            return "Abans de l'eclipsi"
        if h['c2'] is not None and h['c2'] <= hora_tu <= h['c3']:
            return 'TOTALITAT'
        if hora_tu <= h['c4']:
            return 'Eclipsi parcial'
        return "Despres de l'eclipsi"

    def interval(self, marge=0.25):
        """(inici, final) en hores TU per a la barra de temps: de C1 a C4 amb un marge."""
        if not self.valid:
            return 17.0, 20.0
        return self.hores['c1'] - marge, self.hores['c4'] + marge
