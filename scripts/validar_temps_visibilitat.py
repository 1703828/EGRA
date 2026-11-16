"""
Comprova la resolucio temporal del format del mapa de visibilitat (dades/visibilitat.py, VERSIO 4; D95 del pla):
si els intervals desats conserven les interrupcions (el Sol s'amaga darrere d'un obstacle i torna a sortir) i amb
quin error en surten els moments de transicio i el temps observable.

Referencia independent: per a cada pixel de la mostra, el marge cada PAS_S segons entre C1 i C4 amb el raig exacte
de scripts/validar_visibilitat.py (ECEF, azimut geografic exacte del Sol de ModelEclipsi a cada instant, sense
direccions cada grau ni interpolacio entre minuts). D'aqui, els intervals amb alguna part del Sol lliure (marge > -r)
i amb el Sol sencer lliure (marge > +r), com al mapa.

La mostra barreja pixels a l'atzar i pixels on el mapa troba 2 o mes intervals (els casos amb interrupcions).
Executa (des de l'arrel, amb l'entorn egra):
    python scripts/validar_temps_visibilitat.py [--punts 40] [--rect x0 y0 x1 y1]
Per defecte: 1 x 1 km de la UAB amb la superficie dels obstacles (ICGC, 2 m) de la cel·la cel_927000_4608000.
"""
import argparse
import math
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, 'scripts'))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402

from dades import alcaries, eclipsis, visibilitat as vis  # noqa: E402
from dades.model_eclipsi import ModelEclipsi  # noqa: E402
from validar_visibilitat import Relleu, horitzo_exacte  # noqa: E402

PAS_S = 10.0
CEL = 'cel_927000_4608000'
ZONA = os.path.join(ARREL, 'data', 'mdt', 'zones', 'valles_5m.tif')
PENINSULA = os.path.join(ARREL, 'data', 'mdt', 'peninsula_200m.tif')
# Tolerancies (objectius provisionals, justificats per la mostra del mapa): els creuaments del mapa s'interpolen entre
# minuts i l'horitzo es llegeix cada PAS_AZIMUT (1 grau ~ 5 min de moviment del Sol a la posta): un obstacle estret
# (un pal, una branca) pot no apareixer o apareixer mes ample. Es demana:
#  - temps observable (fraccio de C1-C4): diferencia mediana < 2 % i el 90 % < 8 %
#  - moments de transicio aparellats: diferencia mediana < 60 s
#  - interrupcions (2 o mes intervals al calcul exacte): el mapa en troba la majoria; les que perd duren poc
TOL_FRAC_MEDIANA, TOL_FRAC_P90 = 0.02, 0.08
TOL_TRANSICIO_S = 60.0


def intervals(hs, f):
    """Intervals (inici, final) en hores on f > 0, interpolant els creuaments entre mostres."""
    out, obert = [], None
    for i in range(len(hs)):
        if f[i] > 0 and obert is None:
            obert = hs[i] if i == 0 else hs[i - 1] + (hs[i] - hs[i - 1]) * f[i - 1] / (f[i - 1] - f[i])
        if f[i] <= 0 and obert is not None:
            out.append((obert, hs[i - 1] + (hs[i] - hs[i - 1]) * f[i - 1] / (f[i - 1] - f[i])))
            obert = None
    if obert is not None:
        out.append((obert, hs[-1]))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--punts', type=int, default=40)
    p.add_argument('--rect', nargs=4, type=float, default=(926000, 4607500, 927000, 4608500))
    p.add_argument('--eclipsi', default='2026')
    p.add_argument('--pas-azimut', type=float, default=vis.PAS_AZIMUT)
    a = p.parse_args()
    eclipsis.triar(a.eclipsi)
    sup, ulls_c = alcaries.cami_superficie(CEL, 'superficie'), alcaries.cami_superficie(CEL, 'ulls')
    lluny = [ZONA, PENINSULA]
    rect = tuple(a.rect)
    import time
    t0 = time.time()
    r = vis.llegir(sup, a.eclipsi, rect, a.pas_azimut) or vis.calcular(sup, a.eclipsi, lluny=lluny, cami_ulls=ulls_c,
                                                                       rect=rect, pas_azimut=a.pas_azimut, avis=lambda t: None)
    print(f'mapa: pas d\'azimut {a.pas_azimut:g} graus, {r["obs"].shape[0]} x {r["obs"].shape[1]} px, calculat en '
          f'{float(r["segons"]):.0f} s (llegit en {time.time() - t0:.0f} s)')
    with rasterio.open(ulls_c) as f:
        ulls = f.read(1)
        tr_c, crs = f.transform, f.crs
    tr = rasterio.Affine(*r['transform'])
    a_latlon = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    inici, rs = float(r['inici']), float(r['radi_sol'])
    errors = []

    def ok(c, text):
        print(('OK    ' if c else 'FALLA ') + text, flush=True)
        if not c:
            errors.append(text)

    rng = np.random.default_rng(3)
    valid = r['obs'] != vis.SENSE
    multi = np.argwhere(valid & (r['n_iv'][0] >= 2))
    atzar = np.argwhere(valid)
    n_m = min(len(multi), a.punts // 2)
    mostra = np.concatenate([multi[rng.choice(len(multi), n_m, replace=False)] if n_m else np.zeros((0, 2), int),
                             atzar[rng.choice(len(atzar), a.punts - n_m, replace=False)]])
    relleu = Relleu([sup] + lluny)
    print(f'{len(mostra)} pixels ({n_m} amb 2 o mes intervals al mapa); referencia cada {PAS_S:.0f} s')
    d_frac, d_trans, n_ex, n_mapa, perdudes, ex_multi, mapa_multi = [], [], [], [], [], 0, 0
    for fila, col in mostra:
        x, y = tr * (col + 0.5, fila + 0.5)
        lon, lat = a_latlon.transform(x, y)
        cc, ff = ~tr_c * (x, y)
        h0 = float(ulls[int(ff), int(cc)])
        m = ModelEclipsi(lat, lon, h0 / 1000.0)
        c1, c4 = m.hores['c1'], m.hores['c4']
        hs = np.arange(c1, c4, PAS_S / 3600.0)
        marge = []
        for h in hs:
            az, el = m.sol(h)
            marge.append(el - horitzo_exacte(relleu, lat, lon, az, h0, tr.a) if el > -2 else -10.0)
        marge = np.array(marge)
        ex = intervals(hs, marge + rs)
        obs_ex = sum(b - a_ for a_, b in ex) / (c4 - c1)
        obs_mapa = r['obs'][fila, col] / vis.FRAC
        d_frac.append(obs_mapa - obs_ex)
        nm = int(r['n_iv'][0, fila, col])
        mp = [(inici + r['iv'][0, i, 0, fila, col] / 3600, inici + r['iv'][0, i, 1, fila, col] / 3600)
              for i in range(min(nm, vis.K_IV)) if r['iv'][0, i, 0, fila, col] != vis.SENSE]
        n_ex.append(len(ex))
        n_mapa.append(nm)
        ex_multi += len(ex) >= 2
        mapa_multi += nm >= 2
        # aparellar cada transicio exacta amb la mes propera del mapa
        tm = np.array([t for iv in mp for t in iv])
        for iv in ex:
            for t in iv:
                if t in (hs[0], hs[-1]):
                    continue       # C1 o C4: no es una transicio per obstacle
                if len(tm):
                    d_trans.append(abs(tm - t).min() * 3600)
        # interrupcions del calcul exacte que el mapa no veu: forats entre intervals exactes no coberts pel mapa
        for (a1, b1), (a2, b2) in zip(ex[:-1], ex[1:]):
            mig = (b1 + a2) / 2
            if any(a_ <= mig <= b for a_, b in mp):
                perdudes.append((a2 - b1) * 3600)
    d_frac = np.abs(d_frac)
    print(f'intervals (alguna part del Sol): exacte {np.bincount(n_ex).tolist()}, mapa {np.bincount(n_mapa).tolist()} '
          f'(index = nombre d\'intervals)')
    ok(np.median(d_frac) < TOL_FRAC_MEDIANA and np.percentile(d_frac, 90) < TOL_FRAC_P90,
       f'temps observable (fraccio de C1-C4): diferencia mediana {np.median(d_frac) * 100:.2f} %, 90 % '
       f'{np.percentile(d_frac, 90) * 100:.2f} %, maxima {d_frac.max() * 100:.1f} %')
    d_trans = np.array(d_trans)
    ok(len(d_trans) and np.median(d_trans) < TOL_TRANSICIO_S,
       f'moments de transicio ({len(d_trans)}): diferencia mediana {np.median(d_trans):.0f} s, 90 % '
       f'{np.percentile(d_trans, 90):.0f} s, maxima {d_trans.max():.0f} s')
    print(f'interrupcions: {ex_multi} pixels amb 2 o mes intervals al calcul exacte, {mapa_multi} al mapa; '
          f'{len(perdudes)} interrupcions exactes que el mapa no veu' +
          (f' (durada mediana {np.median(perdudes):.0f} s, maxima {max(perdudes):.0f} s)' if perdudes else ''))
    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
