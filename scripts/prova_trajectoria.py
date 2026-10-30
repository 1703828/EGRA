"""
Prova de la trajectoria guiada (dades/trajectoria.py) i dels limits de la mirada, sense finestra ni OpenGL.

Per a les sis ubicacions i per a l'ancora a moltes hores de l'interval (cada 30 min de 14:00 a 21:30 TU),
amb 4.001 valors del progres:
  1. Sense travessar res: fins a S1 la camera es per sobre del pla tangent al punt (fora de l'el·lipsoide,
     que es convex) i a 300 m o mes del punt; des de S1, a mes de 6.400 km del centre de la Terra (el radi
     mes gran de l'el·lipsoide mes la muntanya mes alta queda per sota). Lluny de la Lluna (> 50 radis) i del
     Sol; dins del cub de navegacio amb marge (sense dependre del seu limit).
  2. Continuitat: entre dos valors seguits, la camera es mou com a molt un 6 % de la seva distancia al punt;
     la mirada de referencia gira com a molt 1 grau i el vector amunt no s'inverteix.
  3. Enquadraments (mirada de referencia, camp vertical de 50 graus): el punt es veu (no queda darrere de la
     Terra) fins a S2; a S2 la Terra sencera dins del camp; a S3 la Terra i la Lluna; a 1 la Terra, la Lluna i
     el Sol (els centres a menys de 25 graus del centre de la imatge).
  4. Anada i tornada amb passos de roda fraccionaris (com el trackpad): s'arriba al final i es torna a
     exactament el punt inicial.
  5. Mirada: orientacio() i angles_cap_a() son inversos; als extrems (+-89 graus) la direccio i l'amunt son
     finits, unitaris i perpendiculars; limitar_orientacio normalitza el rumb, limita la inclinacio i rebutja
     valors no finits.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_trajectoria.py
"""
import math
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402

from dades import geodesia  # noqa: E402
from dades.efemerides import RADI_LLUNA_KM, RADI_SOL_KM  # noqa: E402
from dades.model_eclipsi import efemerides  # noqa: E402
from dades.navegacio import cub_navegacio  # noqa: E402
from dades.observador import UBICACIONS, ALCADA_ULLS_KM  # noqa: E402
from dades.trajectoria import Trajectoria, orientacio, angles_cap_a, S1, S2, S3, H0_KM  # noqa: E402

FOV = 50.0
MIG_CAMP = FOV / 2


def angle(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    return math.degrees(2 * math.asin(min(1.0, np.linalg.norm(a - b) / 2)))


def main():
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    ef = efemerides()
    cub = cub_navegacio(ef, FOV)
    ss = np.linspace(0.0, 1.0, 4001)
    hores = np.arange(ef.inici, ef.final + 1e-9, 0.5)
    pitjor = dict(pla=1e9, radi=1e9, lluna=1e9, sol=1e9, paret=1e9, pas=0.0, gir=0.0, amunt=1.0,
                  punt=1e9, terra=0.0, terra_lluna=0.0, tres=0.0)
    for nom, lat, lon in UBICACIONS:
        # l'altitud del terra no importa per a la geometria: es fa servir 0 m sobre l'el·lipsoide
        ulls = geodesia.ecef(lat, lon, ALCADA_ULLS_KM)
        _, _, amunt = geodesia.base_local(lat, lon)
        for h in hores:
            sol, lluna = ef.posicions(h)
            t = Trajectoria(lat, lon, ulls, sol, lluna)
            ps = np.array([t.posicio(s) for s in ss])
            marcs = [t.marc(s) for s in ss]
            fs = np.array([f for f, _ in marcs])
            ups = np.array([u for _, u in marcs])
            prop = ss <= S1
            pitjor['pla'] = min(pitjor['pla'], float(((ps[prop] - ulls) @ amunt).min()))
            pitjor['radi'] = min(pitjor['radi'], float(np.linalg.norm(ps[~prop], axis=1).min()))
            pitjor['lluna'] = min(pitjor['lluna'], float(np.linalg.norm(ps - lluna, axis=1).min()) / RADI_LLUNA_KM)
            pitjor['sol'] = min(pitjor['sol'], float(np.linalg.norm(ps - sol, axis=1).min()) / RADI_SOL_KM)
            pitjor['paret'] = min(pitjor['paret'], float(np.minimum(ps - cub.minim, cub.maxim - ps).min()))
            dist = np.linalg.norm(ps - ulls, axis=1)
            pitjor['pas'] = max(pitjor['pas'], float((np.linalg.norm(np.diff(ps, axis=0), axis=1) / dist[:-1]).max()))
            pitjor['gir'] = max(pitjor['gir'], max(angle(a, b) for a, b in zip(fs[:-1], fs[1:])))
            pitjor['amunt'] = min(pitjor['amunt'], float(np.einsum('ij,ij->i', ups[:-1], ups[1:]).min()))
            # el punt es veu des de la camera (per sobre del seu pla tangent) fins a S2
            fins_s2 = ss <= S2
            pitjor['punt'] = min(pitjor['punt'], float(((ps[fins_s2] - ulls) @ amunt).min()))
            # enquadraments amb la mirada de referencia
            def maxim_angle(s, objectius):
                p, (f, _) = t.posicio(s), t.marc(s)
                return max(angle(f, o - p) + (math.degrees(math.asin(r / np.linalg.norm(o - p))) if r else 0.0)
                           for o, r in objectius)
            pitjor['terra'] = max(pitjor['terra'], maxim_angle(S2, [(np.zeros(3), geodesia.A_KM)]))
            pitjor['terra_lluna'] = max(pitjor['terra_lluna'], maxim_angle(S3, [(np.zeros(3), 0), (lluna, 0)]))
            pitjor['tres'] = max(pitjor['tres'], maxim_angle(1.0, [(np.zeros(3), 0), (lluna, 0), (sol, 0)]))

    print(f'== {len(UBICACIONS)} ubicacions x {len(hores)} hores de l\'ancora x {len(ss)} valors del progres')
    ok(pitjor['pla'] >= H0_KM * math.sin(math.radians(70)) - 1e-9,
       f"fins a S1, per sobre del pla tangent al punt (minim {pitjor['pla'] * 1000:.0f} m): fora de la Terra")
    ok(pitjor['radi'] > 6400.0, f"des de S1, a {pitjor['radi']:,.0f} km o mes del centre de la Terra (> 6.400 km)")
    ok(pitjor['lluna'] > 50.0, f"la camera passa com a molt a {pitjor['lluna']:,.0f} radis lunars de la Lluna")
    ok(pitjor['sol'] > 50.0, f"i a {pitjor['sol']:,.0f} radis solars del Sol")
    ok(pitjor['paret'] > 1e7, f"dins del cub de navegacio, a {pitjor['paret']:,.0f} km o mes de les parets "
                              "(no fa servir el seu limit)")
    ok(pitjor['pas'] < 0.06, f"continuitat: cada 1/4000 del recorregut, com a molt un {pitjor['pas'] * 100:.1f} % "
                             "de la distancia al punt")
    ok(pitjor['gir'] < 1.0, f"la mirada de referencia gira com a molt {pitjor['gir']:.2f} graus entre valors seguits")
    ok(pitjor['amunt'] > 0.99, f"el vector amunt no s'inverteix (producte escalar minim {pitjor['amunt']:.4f})")
    ok(pitjor['punt'] > 0, 'fins a S2 el punt d\'observacio es veu (no queda darrere de la Terra)')
    ok(pitjor['terra'] < MIG_CAMP, f"S2: la Terra sencera dins del camp (fins a {pitjor['terra']:.1f} de {MIG_CAMP:.0f} graus)")
    ok(pitjor['terra_lluna'] < MIG_CAMP,
       f"S3: la Terra i la Lluna dins del camp (fins a {pitjor['terra_lluna']:.1f} de {MIG_CAMP:.0f} graus)")
    ok(pitjor['tres'] < MIG_CAMP,
       f"final: la Terra, la Lluna i el Sol dins del camp (fins a {pitjor['tres']:.1f} de {MIG_CAMP:.0f} graus)")

    # 4. anada i tornada amb passos fraccionaris (la camera fa progres = clip(progres - passos / 40))
    nom, lat, lon = UBICACIONS[1]
    sol, lluna = ef.posicions(ef.inici + 4)
    t = Trajectoria(lat, lon, geodesia.ecef(lat, lon, 0.5), sol, lluna)
    rng = np.random.default_rng(1)
    passos = rng.uniform(0.1, 1.7, 200)
    s, p0 = 0.0, t.posicio(0.0)
    for x in passos:
        s = min(max(s + x / 40, 0.0), 1.0)
    final = s
    for x in passos:
        s = min(max(s - x / 40, 0.0), 1.0)
    ok(final == 1.0 and s == 0.0 and np.array_equal(t.posicio(s), p0),
       f"anada i tornada amb {len(passos)} passos fraccionaris: s'arriba al final i es torna exactament al punt inicial")
    s = 0.0
    for x in passos[:30]:
        s = min(max(s + x / 40, 0.0), 1.0)
    mig = t.posicio(s)
    for x in passos[:30][::-1]:
        s = min(max(s - x / 40, 0.0), 1.0)
    for x in passos[:30]:
        s = min(max(s + x / 40, 0.0), 1.0)
    ok(np.linalg.norm(t.posicio(s) - mig) < 1e-9,
       f"tornar enrere i endavant pels mateixos passos: diferencia {np.linalg.norm(t.posicio(s) - mig) * 1e6:.3f} mm")

    # 5. mirada
    f, up = t.marc(0.5)
    maxim = 0.0
    for gir in np.linspace(-179, 180, 37):
        for inc in np.linspace(-89, 89, 19):
            d, u = orientacio(f, up, gir, inc)
            g2, i2 = angles_cap_a(f, up, d)
            maxim = max(maxim, abs((g2 - gir + 180) % 360 - 180), abs(i2 - inc))
    ok(maxim < 1e-9, f'orientacio i angles_cap_a son inversos (error maxim {maxim:.1e} graus)')
    extrems = [orientacio(f, up, g, i) for g in (0.0, 123.0) for i in (-89.0, 89.0)]
    ok(all(np.isfinite(d).all() and np.isfinite(u).all() and abs(np.linalg.norm(d) - 1) < 1e-12
           and abs(d @ u) < 1e-12 for d, u in extrems),
       'als extrems (+-89 graus) direccio i amunt finits, unitaris i perpendiculars (lookAt sense singularitat)')
    ok(all(abs(d @ up) <= math.sin(math.radians(89.0)) + 1e-12 for d, _ in extrems),
       'la mirada no arriba mai a la vertical de referencia')

    # limits de les cameres de l'aplicacio (sense OpenGL: nomes la funcio)
    from basecode.camera_exploracio import limitar_orientacio, INCLINACIO_MAX
    casos = [((370.0, 10.0), (10.0, 10.0)), ((-30.0, 95.0), (330.0, INCLINACIO_MAX)),
             ((720.5, -300.0), (0.5, -INCLINACIO_MAX)), ((float('nan'), 0.0), None), ((0.0, float('inf')), None)]
    ok(all((limitar_orientacio(*e) == r) if r is None else np.allclose(limitar_orientacio(*e), r) for e, r in casos),
       f'limitar_orientacio: rumb a [0, 360), inclinacio a +-{INCLINACIO_MAX:.0f} graus, valors no finits rebutjats')

    print('\nRESULTAT:', 'TOT CORRECTE' if not errors else f'{len(errors)} FALLADES')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
