"""
Atmosfera (sense OpenGL): color del cel, color de la llum del Sol i color de la boira, per al cel i la llum des
de la superficie. El mateix calcul que basecode/shaders/cel.frag (aquest fitxer el fa a la CPU per a uns quants
raigs: la boira, el color del disc del Sol i les proves).

Model de dispersio simple (Nishita, 1993), en km:
  - Atmosfera esferica al voltant del centre de la Terra, fins a ALCADA_ATMOSFERA_KM. La densitat de l'aire
    decreix exponencialment amb l'altura: Rayleigh (molecules, escala 8 km) i Mie (aerosols, escala 1,2 km).
  - Per a cada raig de la camera, s'integra (N_VISTA mostres) la llum del Sol dispersada cap a la camera a cada
    punt: la que arriba al punt (atenuada pel cami fins al Sol, N_LLUM mostres; zero si la Terra la tapa) i la
    que en surt fins a la camera (atenuada pel cami de tornada). Rayleigh dispersa mes el blau (cel blau, Sol
    vermell a la posta); Mie, cap endavant (resplendor al voltant del Sol, horitzo blanquinos).
  - Eclipsi: la llum que arriba a cada punt del raig es multiplica per la part del Sol que no tapa la Lluna vista
    des d'aquell punt (la mateixa formula que el terreny, dades/model_eclipsi.area_tapada). Dins de l'ombra el cel
    s'enfosqueix; a la totalitat, l'atmosfera de fora de l'ombra, lluny, encara rep el Sol: el resplendor de
    l'horitzo.
  - Altitud de la camera: el raig comenca a la camera (o a l'entrada de l'atmosfera, des de l'espai). Com mes
    amunt, menys aire hi ha i mes fosc es el cel.
  - Ozo: absorbeix (no dispersa) sobretot el taronja; fa que el cel del crepuscle i el de la banda oposada al
    Sol siguin blaus i rosats i no grocs.
  - Dins de l'ombra s'afegeix una llum minima (LLUM_DIFOSA) en lloc de la dispersio multiple.
Aproximacions (il·lustratives, no una mesura): Terra esferica de radi local; sense dispersio multiple (el
crepuscle profund queda massa fosc); coeficients habituals d'una atmosfera clara; l'exposicio i
l'adaptacio de l'ull (ADAPTACIO) es trien perque es vegi be a la pantalla.
"""
import math

import numpy as np

ALCADA_ATMOSFERA_KM = 80.0
BETA_R = np.array([5.802e-3, 13.558e-3, 33.1e-3])    # dispersio de Rayleigh a nivell del mar (1/km), R G B
ESCALA_R_KM = 8.0
BETA_M = 3.996e-3                                     # dispersio de Mie (1/km)
EXTINCIO_M = 4.40e-3                                  # extincio de Mie (dispersio + absorcio)
ESCALA_M_KM = 1.2
G_MIE = 0.8                                           # asimetria de Mie: dispersa cap endavant
BETA_O = np.array([0.650e-3, 1.881e-3, 0.085e-3])     # absorcio de l'ozo (1/km): treu taronja, deixa blau i rosa
OZO_CENTRE_KM, OZO_AMPLE_KM = 25.0, 15.0              # capa d'ozo: densitat en triangle entre 10 i 40 km
SOL = 20.0                                            # intensitat del Sol (unitats arbitraries)
EXPOSICIO = 3.0
ADAPTACIO = 0.6       # l'ull s'adapta a la foscor de l'eclipsi: el cel es multiplica per visible^-ADAPTACIO
VISIBLE_MIN = 0.01    # (com a molt x16: a la totalitat el cel es fosc, pero l'horitzo encara es veu)
LLUM_DIFOSA = 0.003   # dins de l'ombra de la Lluna, una mica de llum dispersada des de l'atmosfera de fora
                      # (dispersio multiple, que aquest model no calcula): el cel de la totalitat es blau molt
                      # fosc i no negre. Il·lustratiu.
N_VISTA, N_LLUM = 12, 4


def _esfera(o, d, r):
    """Interseccions (t0, t1) del raig o + t d (d unitari) amb l'esfera de radi r centrada a l'origen, o None."""
    b = float(o @ d)
    c = float(o @ o) - r * r
    disc = b * b - c
    if disc < 0:
        return None
    s = math.sqrt(disc)
    return -b - s, -b + s


def _ozo(h):
    return max(0.0, 1.0 - abs(h - OZO_CENTRE_KM) / OZO_AMPLE_KM)


def _tapat(p, sol, lluna, radi_sol, radi_lluna):
    from .model_eclipsi import area_tapada, angle_entre
    s, l = sol - p, lluna - p
    rs = math.asin(min(1.0, radi_sol / np.linalg.norm(s)))
    rl = math.asin(min(1.0, radi_lluna / np.linalg.norm(l)))
    return area_tapada(angle_entre(s, l), rs, rl)


def radi_terra(posicio, alcada_km):
    """Radi de l'esfera de la Terra per al calcul: el geocentric sota la camera (a prop del terra) o el mitja."""
    return float(np.linalg.norm(posicio)) - alcada_km if alcada_km < 100.0 else 6371.0


def llum_dispersada(posicio, d, sol, lluna, radi_sol, radi_lluna, alcada_km):
    """Llum del cel (RGB, sense exposicio) que arriba a la camera (ECEF, km) des de la direccio unitaria d."""
    r = radi_terra(posicio, alcada_km)
    o = posicio / np.linalg.norm(posicio) * (r + alcada_km)        # camera a la seva altura sobre l'esfera
    tt = _esfera(o, d, r + ALCADA_ATMOSFERA_KM)
    if tt is None or tt[1] <= 0:
        return np.zeros(3)
    t0, t1 = max(tt[0], 0.0), tt[1]
    terra = _esfera(o, d, r)
    if terra is not None and terra[0] > 0:
        t1 = min(t1, terra[0])
    longitud = t1 - t0
    s_dir = (sol - posicio) / np.linalg.norm(sol - posicio)
    mu = float(d @ s_dir)
    fase_r = 3.0 / (16 * math.pi) * (1 + mu * mu)
    g2 = G_MIE * G_MIE
    fase_m = 3.0 / (8 * math.pi) * (1 - g2) * (1 + mu * mu) / ((2 + g2) * (1 + g2 - 2 * G_MIE * mu) ** 1.5)
    od_r = od_m = od_o = 0.0
    suma_r, suma_m = np.zeros(3), 0.0 * np.zeros(3)
    for i in range(N_VISTA):
        # mostres mes denses a prop de la camera (t = longitud x f^2): mirant cap a l'horitzo, l'aire proper es
        # el que conserva el blau, i amb mostres uniformes (una cada ~80 km) quedaria mal representat
        fa, fb = i / N_VISTA, (i + 1) / N_VISTA
        ds = longitud * (fb * fb - fa * fa)
        x = o + d * (t0 + longitud * ((fa + fb) / 2) ** 2)
        h = float(np.linalg.norm(x)) - r
        dr, dm = math.exp(-h / ESCALA_R_KM) * ds, math.exp(-h / ESCALA_M_KM) * ds
        od_r += dr
        od_m += dm
        od_o += _ozo(h) * ds
        if _esfera(x, s_dir, r) is not None and _esfera(x, s_dir, r)[0] > 0:
            continue                                                  # la Terra tapa el Sol en aquest punt
        tl = _esfera(x, s_dir, r + ALCADA_ATMOSFERA_KM)[1]
        dsl = tl / N_LLUM
        ol_r = ol_m = ol_o = 0.0
        for j in range(N_LLUM):
            hl = float(np.linalg.norm(x + s_dir * (j + 0.5) * dsl)) - r
            ol_r += math.exp(-hl / ESCALA_R_KM) * dsl
            ol_m += math.exp(-hl / ESCALA_M_KM) * dsl
            ol_o += _ozo(hl) * dsl
        transm = np.exp(-(BETA_R * (od_r + ol_r) + EXTINCIO_M * (od_m + ol_m) + BETA_O * (od_o + ol_o)))
        visible = max(1.0 - _tapat(posicio + (x - o), sol, lluna, radi_sol, radi_lluna), LLUM_DIFOSA)
        suma_r += dr * transm * visible
        suma_m += dm * transm * visible
    return SOL * (BETA_R * fase_r * suma_r + BETA_M * fase_m * suma_m)


LUMA = np.array([0.2126, 0.7152, 0.0722])
SATURACIO = 0.85      # el color final es barreja un 15 % amb el gris de la mateixa lluminositat


def to(llum, visible_camera):
    """Del calcul (llum) al color de la pantalla (0..1). Exposicio i adaptacio a la foscor de l'eclipsi; despres,
    meitat i meitat de dues compressions: per canal (1 - e^-x, conserva els daurats de la posta pero satura) i
    sobre la lluminositat (conserva la proporcio entre colors, pero blanqueja el resplendor del Sol); al final,
    un 15 % de desaturacio. Funcions continues: cap salt de color."""
    c = llum * EXPOSICIO * max(visible_camera, VISIBLE_MIN) ** -ADAPTACIO
    canal = 1.0 - np.exp(-c)
    y = float(c @ LUMA)
    if y <= 1e-9:
        return np.zeros(3)
    yt = 1.0 - math.exp(-y)
    lum = c * (yt / y)
    m = float(lum.max())
    if m > 1.0:                        # el canal que passa d'1: cap al blanc conservant la lluminositat
        lum = lum + (1.0 - lum) * min(1.0, (m - 1.0) / max(m - yt, 1e-6))
    r = 0.5 * (canal + np.clip(lum, 0.0, 1.0))
    g = float(r @ LUMA)
    return np.clip(g + SATURACIO * (r - g), 0.0, 1.0)


def color_cel(posicio, d, sol, lluna, radi_sol, radi_lluna, alcada_km, visible_camera):
    """Color del cel (0..1) en la direccio d, tal com el dibuixa cel.frag."""
    return to(llum_dispersada(posicio, d, sol, lluna, radi_sol, radi_lluna, alcada_km), visible_camera)


def transmissio_sol(sin_elevacio, alcada_km=0.0):
    """Part de la llum del Sol (RGB) que travessa l'atmosfera fins a un punt a alcada_km, amb el Sol a l'elevacio
    donada: massa d'aire de Kasten i Young (1989) per la profunditat optica vertical a aquella altura. El Sol
    baix travessa molt mes aire: perd el blau (vermellos) i es mes feble. La mateixa formula que els shaders."""
    el = math.degrees(math.asin(max(-1.0, min(1.0, sin_elevacio))))
    if el < -1.0:
        return np.zeros(3)
    massa = 1.0 / (max(sin_elevacio, 0.0) + 0.50572 * (max(el, -0.9) + 6.07995) ** -1.6364)
    vertical = BETA_R * ESCALA_R_KM * math.exp(-alcada_km / ESCALA_R_KM) + \
        EXTINCIO_M * ESCALA_M_KM * math.exp(-alcada_km / ESCALA_M_KM)
    return np.exp(-vertical * massa)


def color_llum_cel(sin_elevacio):
    """Color de la llum del cel (ambient), aproximacio il·lustrativa: blavosa de dia, mes calida amb el Sol baix.
    La mateixa formula que els shaders (color_llum_cel)."""
    t = min(max(sin_elevacio / 0.3, 0.0), 1.0)
    t = t * t * (3 - 2 * t)
    return np.array([0.82, 0.70, 0.66]) + t * (np.array([0.72, 0.80, 0.95]) - np.array([0.82, 0.70, 0.66]))


def color_llum_sol(sin_elevacio, alcada_km=0.0):
    """Color de la llum directa del Sol per il·luminar (0..1): la transmissio relativa a la del Sol al zenit,
    comprimida (arrel quadrada) perque la posta no quedi negra. Blanc amb el Sol alt, daurat i vermellos baix."""
    t = transmissio_sol(sin_elevacio, alcada_km) / transmissio_sol(1.0, alcada_km)
    return np.sqrt(np.clip(t, 0.0, 1.0))
