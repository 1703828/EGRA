"""
Trajectoria guiada per allunyar-se del punt d'observacio fins a l'espai (la fa servir la camera guiada,
basecode/camera_guiada.py). Sense OpenGL: nomes geometria en coordenades terrestres (ECEF, km, float64).

La posicio depen d'un sol parametre, el progres s (de 0 a 1), i no de cap a on es mira. Punts clau:
  s = 0     a prop del punt: a 300 m del punt d'observacio, sobre una recta que en surt amb 70 graus
            d'elevacio, d'esquena al Sol (el terreny que es veu queda il·luminat).
  s = S1    a 100 km del punt per la mateixa recta. Es una sortida segura: tota la recta queda per sobre
            del pla tangent al punt, i l'el·lipsoide (convex) queda tot a l'altre costat d'aquest pla.
            (No es retrocedeix en la direccio de la mirada: mirant el cel, retrocedir faria entrar sota terra.)
  s = S2    la Terra: a 30.000 km d'altura, entre la vertical del punt i el Sol (la cara de dia, com el boto
            "Veure l'ombra des de l'espai").
  s = S3    el sistema Terra-Lluna: de costat respecte de la recta Terra-Lluna, a 1,6 vegades la distancia
            Terra-Lluna del punt mig; la Terra i la Lluna caben al camp de visio (separades ~35 graus).
  s = 1     vista ampla amb el Sol: a 1,2 milions de km, a 40 graus de la direccio oposada al Sol. El Sol,
            la Lluna i la Terra caben al camp (~40 graus entre la Terra i el Sol). Des d'aqui la Terra es veu
            com un creixent: no hi ha cap lloc des d'on es vegin alhora el Sol i la cara de dia de la Terra.
De S1 a 1 l'altura (distancia al centre de la Terra menys la del punt) creix en escala logaritmica i la
direccio vista des del centre gira (slerp) entre els punts clau en proporcio a l'altura guanyada a cada tram:
a prop de la Terra gira poc i el desplacament lateral es de l'ordre de l'altura. Des de S1, la camera es a
mes de 6.400 km del centre (fora de la Terra) i lluny de la Lluna (scripts/prova_trajectoria.py).

Escala: cada pas de roda (1/40 del recorregut) multiplica la distancia per ~1,2-1,6: es passa dels metres als
milions de km en uns 40 passos, i el mateix nombre de passos enrere torna exactament al mateix lloc.

La mirada de referencia (davant) segueix els punts clau: cap al punt d'observacio fins a S2; despres cap al
punt mig entre la Terra i la Lluna; al final, a mig cami entre la Terra i el Sol. El vector "amunt" de
referencia es transporta al llarg del cami (gir minim d'un punt al seguent), aixi no hi ha girs bruscos ni
inversions; a prop del terra es la vertical del lloc (l'horitzo surt horitzontal).
Les posicions del Sol i la Lluna son les d'un instant fix (el de l'ancora): la trajectoria no canvia sola
quan passa el temps.
"""
import math

import numpy as np

from . import geodesia

H0_KM = 0.3                 # distancia al punt a s = 0
H1_KM = 100.0               # distancia al punt a s = S1 (final de la sortida en recta)
ELEVACIO_SORTIDA = 70.0     # graus sobre l'horitzo del punt de la recta de sortida
ALCADA_TERRA_KM = 30000.0   # altura de la vista de la Terra
FACTOR_TERRA_LLUNA = 1.6    # distancia al punt mig Terra-Lluna, en distancies Terra-Lluna
ANGLE_SOL = 40.0            # graus entre la camera final i la direccio oposada al Sol (vist des de la Terra)
DIST_FINAL_KM = 1.2e6       # distancia final al centre de la Terra
S1, S2, S3 = 0.3, 0.55, 0.8
N_MOSTRES = 2001            # mostres del vector amunt transportat


def unitari(v):
    return v / np.linalg.norm(v)


def slerp(a, b, t):
    """Interpolacio esferica entre dos vectors unitaris."""
    angle = math.acos(min(1.0, max(-1.0, float(a @ b))))
    if angle < 1e-9:
        return a
    return (math.sin((1 - t) * angle) * a + math.sin(t * angle) * b) / math.sin(angle)


def suau(t):
    return t * t * (3 - 2 * t)


def orientacio(davant, amunt, gir, inclinacio):
    """Mirada a partir d'una referencia (davant, amunt perpendiculars i unitaris) i dos angles en graus: gir
    cap a la dreta i inclinacio cap amunt. Retorna (direccio, amunt de la camera), perpendiculars: lookAt
    no te mai cap singularitat (l'amunt mai es paral·lel a la direccio) i no hi ha cap gir sobre l'eix."""
    dreta = np.cross(davant, amunt)
    g, i = math.radians(gir), math.radians(inclinacio)
    girat = math.cos(g) * davant + math.sin(g) * dreta
    return math.cos(i) * girat + math.sin(i) * amunt, -math.sin(i) * girat + math.cos(i) * amunt


def angles_cap_a(davant, amunt, direccio):
    """El contrari d'orientacio(): (gir, inclinacio) en graus que miren en la direccio donada."""
    d = unitari(direccio)
    dreta = np.cross(davant, amunt)
    inclinacio = math.degrees(math.asin(min(1.0, max(-1.0, float(d @ amunt)))))
    return math.degrees(math.atan2(float(d @ dreta), float(d @ davant))), inclinacio


class Trajectoria:
    def __init__(self, lat, lon, ulls, sol, lluna):
        """lat, lon: punt d'observacio; ulls, sol, lluna: posicions ECEF (km) a l'instant de l'ancora."""
        self.ulls = np.asarray(ulls, dtype=float)
        self.radi_punt = float(np.linalg.norm(self.ulls))      # distancia del punt al centre de la Terra
        self.sol, self.lluna = np.asarray(sol, dtype=float), np.asarray(lluna, dtype=float)
        _, nord, amunt = geodesia.base_local(lat, lon)
        self.amunt_punt = amunt
        # 1. sortida en recta, d'esquena al Sol (sense component horitzontal, cap al nord)
        cap_al_sol = unitari(self.sol - self.ulls)
        horitzontal = cap_al_sol - (cap_al_sol @ amunt) * amunt
        esquena = -unitari(horitzontal) if np.linalg.norm(horitzontal) > 1e-6 else nord
        e = math.radians(ELEVACIO_SORTIDA)
        self.sortida = math.sin(e) * amunt + math.cos(e) * esquena
        # 2. la Terra: entre la vertical del punt i el Sol
        s_dir = unitari(self.sol)
        u2 = amunt + s_dir
        u2 = unitari(u2) if np.linalg.norm(u2) > 0.1 else amunt
        # 3. de costat respecte de la recta Terra-Lluna, del costat de la vista de la Terra
        m_dir = unitari(self.lluna)
        costat = u2 - (u2 @ m_dir) * m_dir
        costat = unitari(costat) if np.linalg.norm(costat) > 1e-3 else unitari(np.cross(m_dir, nord))
        self.mig = self.lluna / 2
        p3 = self.mig + FACTOR_TERRA_LLUNA * np.linalg.norm(self.lluna) * costat
        # 4. a ANGLE_SOL graus de la direccio oposada al Sol, del mateix costat
        w = costat - (costat @ s_dir) * s_dir
        w = unitari(w) if np.linalg.norm(w) > 1e-3 else costat
        a = math.radians(ANGLE_SOL)
        p4 = DIST_FINAL_KM * unitari(-math.cos(a) * s_dir + math.sin(a) * w)
        self.claus = [(S1, self.ulls + H1_KM * self.sortida),
                      (S2, (geodesia.A_KM + ALCADA_TERRA_KM) * u2), (S3, p3), (1.0, p4)]
        self._amunts = self._transportar_amunt()

    def posicio(self, s):
        """Posicio de la camera (ECEF, km) al progres s (es limita a 0..1)."""
        s = min(max(float(s), 0.0), 1.0)
        if s <= S1:
            return self.ulls + H0_KM * (H1_KM / H0_KM) ** (s / S1) * self.sortida
        for (sa, pa), (sb, pb) in zip(self.claus, self.claus[1:]):
            if s <= sb:
                # altura sobre el radi del punt en escala logaritmica (cada pas multiplica la distancia pel
                # mateix factor) i la direccio girant en proporcio a l'altura guanyada: a prop de la Terra
                # gira poc (el desplacament lateral es de l'ordre de l'altura) i lluny, mes
                t = (s - sa) / (sb - sa)
                aa, ab = np.linalg.norm(pa) - self.radi_punt, np.linalg.norm(pb) - self.radi_punt
                alcada = aa * (ab / aa) ** t
                return (self.radi_punt + alcada) * slerp(unitari(pa), unitari(pb), (alcada - aa) / (ab - aa))
        return self.claus[-1][1].copy()

    def davant(self, s):
        """Direccio de referencia de la mirada al progres s (unitaria)."""
        s = min(max(float(s), 0.0), 1.0)
        p = self.posicio(s)
        if s <= S1:
            return -self.sortida              # la recta de sortida mira exactament el punt
        cap_al_punt = unitari(self.ulls - p)
        if s <= S2:
            return cap_al_punt
        cap_al_mig = unitari(self.mig - p)
        if s <= S3:
            return slerp(cap_al_punt, cap_al_mig, suau((s - S2) / (S3 - S2)))
        terra_sol = unitari(unitari(-p) + unitari(self.sol - p))
        return slerp(cap_al_mig, terra_sol, suau((s - S3) / (1.0 - S3)))

    def _transportar_amunt(self):
        """Vector amunt a N_MOSTRES valors de s: comenca a la vertical del punt (perpendicular a davant) i, de
        mostra en mostra, gira amb el gir minim que porta un davant al seguent (transport paral·lel)."""
        f = self.davant(0.0)
        up = unitari(self.amunt_punt - (self.amunt_punt @ f) * f)
        amunts = [up]
        for s in np.linspace(0.0, 1.0, N_MOSTRES)[1:]:
            g = self.davant(s)
            eix = np.cross(f, g)
            sin_a, cos_a = np.linalg.norm(eix), float(f @ g)
            if sin_a > 1e-12:
                k = eix / sin_a
                up = up * cos_a + np.cross(k, up) * sin_a + k * (k @ up) * (1 - cos_a)
            up = unitari(up - (up @ g) * g)
            amunts.append(up)
            f = g
        return np.array(amunts)

    def marc(self, s):
        """(davant, amunt) de referencia al progres s: unitaris i perpendiculars."""
        s = min(max(float(s), 0.0), 1.0)
        f = self.davant(s)
        x = s * (N_MOSTRES - 1)
        i = min(int(x), N_MOSTRES - 2)
        t = x - i
        up = (1 - t) * self._amunts[i] + t * self._amunts[i + 1]
        return f, unitari(up - (up @ f) * f)
