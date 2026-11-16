"""
Mapa al maxim del 2026 contra la capa terrain_shadows del CNIG a cada escala (tasca 47.2 del pla), sobre una mateixa
area (per defecte, les peces de detall calculades a la UAB).

El CNIG calcula amb el GMTED2010 (~200-300 m) i nomes el relleu. Els nostres nivells: N0 (MDT de 200 m), N2 (5 m) i
N3 (terra + alcaria LiDAR: edificis i vegetacio, 2 m). Es compara la part de l'area on el Sol es veu menys de la meitat
(classes 0-1) i l'acord pixel a pixel amb el CNIG (cada valor nostre contra la cel·la del CNIG que el conte). No es
una validacio en el sentit estricte (dues fonts amb resolucions i obstacles diferents): explica com canvia el
resultat amb el detall.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/comparar_cnig_escales.py
Fa servir les peces ja calculades (data/cache/visibilitat_2026_*): no en calcula de noves.
"""
import glob
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.warp import reproject, Resampling  # noqa: E402

from dades import eclipse_data, visibilitat as vis  # noqa: E402


def classes(r):
    m = r['marge'] / 100.0
    rs = float(r['radi_sol'])
    c = np.select([m > rs, m > 0, m > -rs], [3, 2, 1], 0)
    return np.where(r['marge'] == vis.SENSE_MARGE, 255, c)


def cnig_a(tr, forma, crs):
    out = np.full(forma, 255, 'u1')
    with rasterio.open(eclipse_data.OMBRES) as f:
        reproject(f.read(1), out, src_transform=f.transform, src_crs=f.crs, dst_transform=tr, dst_crs=crs,
                  resampling=Resampling.nearest, dst_nodata=255)
    return out


def main():
    peces = sorted(glob.glob('data/cache/visibilitat_2026_cel_927000_4608000_superficie_25830_r*_a0.25.npz'))
    if not peces:
        print('No hi ha peces de detall de la UAB calculades (obre el programa a la UAB amb el mapa)')
        return 1
    print(f'{len(peces)} peces d\'1 km de la UAB (N3)')
    files = []
    for cami in peces:
        r = vis.llegir_npz(cami)
        rect = tuple(r['rect'])
        tr = rasterio.Affine(*r['transform'])
        c3 = classes(r)
        files.append(('N3 obstacles (2 m)', c3, tr, str(r['crs']), rect))
        # el mateix rectangle als altres nivells: N2 (cel·la de 5 m) i N0 (peninsula), retallats
        for etiqueta, patro in (('N2 relleu (5 m)', 'data/cache/visibilitat_2026_valles_5m_r*.npz'),
                                ('N0 relleu (200 m)', 'data/cache/visibilitat_2026_peninsula_200m.npz')):
            for c in glob.glob(patro):
                rr = vis.llegir_npz(c)
                t2 = rasterio.Affine(*rr['transform'])
                c2 = classes(rr)
                x0, y0, x1, y1 = rect
                (a0, b0), (a1, b1) = ~t2 * (x0, y1), ~t2 * (x1, y0)
                a0, a1, b0, b1 = int(np.floor(a0)), int(np.ceil(a1)), int(np.floor(b0)), int(np.ceil(b1))
                if a0 < 0 or b0 < 0 or a1 > c2.shape[1] or b1 > c2.shape[0]:
                    continue
                files.append((etiqueta, c2[b0:b1, a0:a1], t2 * t2.translation(a0, b0), str(rr['crs']), rect))
                break
    resum = {}
    for etiqueta, c, tr, crs, rect in files:
        cn = cnig_a(tr, c.shape, crs)
        ok = (c != 255) & (cn != 255)
        d = resum.setdefault(etiqueta, dict(n=0, tapat=0, tapat_cnig=0, acord=0, acord_mig=0))
        d['n'] += ok.sum()
        d['tapat'] += (c[ok] <= 1).sum()
        d['tapat_cnig'] += (cn[ok] <= 1).sum()
        d['acord'] += (c[ok] == cn[ok]).sum()
        d['acord_mig'] += ((c[ok] >= 2) == (cn[ok] >= 2)).sum()
    print(f'{"nivell":22s} {"pixels":>10s} {"menys de mig Sol":>17s} {"CNIG":>6s} {"acord classe":>13s} {"acord mig Sol":>14s}')
    for etiqueta, d in resum.items():
        n = max(d['n'], 1)
        print(f'{etiqueta:22s} {d["n"]:10d} {100 * d["tapat"] / n:16.1f}% {100 * d["tapat_cnig"] / n:5.1f}% '
              f'{100 * d["acord"] / n:12.1f}% {100 * d["acord_mig"] / n:13.1f}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
