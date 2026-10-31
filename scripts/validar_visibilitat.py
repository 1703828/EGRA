"""
Comprova el mapa de visibilitat (dades/visibilitat.py, objectiu O3) amb calculs independents.

1. Circumstancies de la graella contra el model punt a punt (dades/model_eclipsi.py, ModelEclipsi): C1, C2,
   maxim, C3 i C4 en punts de la graella (mateixes efemerides, pero un altre metode per trobar els contactes).
2. Marge al maxim i hores de visibilitat en pixels a l'atzar contra un calcul exacte i lent: des dels ulls
   (ECEF, 1,7 m sobre el MDT), un raig horitzontal en l'azimut geografic del Sol (base local est-nord-amunt,
   sense la quadricula UTM ni la formula de la curvatura), cada 5 m fins a 1 km i despres a distancies
   creixents fins a 200 km; a cada punt, latitud i longitud, l'altitud del MDT (bilineal; la zona de 5 m o la
   peninsula de 200 m) i l'elevacio d'aquell punt del terreny vista des dels ulls. L'elevacio del Sol surt de
   ModelEclipsi. Comprova la convergencia de meridians, la curvatura, les direccions intermedies i el pas.
3. (Amb --cnig, 2026, peninsula) Classes al maxim contra la capa terrain_shadows del CNIG (calculada a part, amb
   el GMTED2010 i la rutina insol): matriu de confusio, a la resolucio de la peninsula (200 m).

Executa (des de l'arrel, amb l'entorn egra):
    python scripts/validar_visibilitat.py <MDT> [--eclipsi 2026] [--punts 30] [--cnig]
Si la visibilitat del MDT no es a la memoria cau, es calcula (pot tardar minuts).
"""
import argparse
import math
import os
import sys

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402

from dades import eclipsis, geodesia, visibilitat as vis  # noqa: E402
from dades.model_eclipsi import ModelEclipsi  # noqa: E402

PENINSULA = os.path.join(ARREL, 'data', 'mdt', 'peninsula_200m.tif')
# Tolerancies (objectius provisionals):
#  - contactes i maxim: < 1 s (mateixes efemerides; C1 i C4, creuaments interpolats entre minuts; el maxim, C2 i C3,
#    amb la parabola de la separacio al quadrat).
#  - marge al maxim: mediana < 0,05 graus i el 95 % < 0,2 graus (el maxim s'informa). Tots dos calculs interpolen
#    el mateix MDT de maneres diferents (direccions cada grau i passos creixents, contra un raig cada mig pixel);
#    als vessants drets amb un obstacle a pocs metres i amb el relleu llunya de 200 m les diferencies arriben a
#    ~0,15 graus. Amb el LiDAR d'1 m (arbres), l'horitzo canvia fins a 1 grau entre azimuts separats 0,5 graus
#    (dins de l'amplada del Sol): alguns pixels aillats queden mes lluny; per aixo el 95 % i no el maxim. Per sota
#    del radi del Sol (0,26 graus) i de l'error del MDT (1-2 m a 500 m son 0,1-0,2 graus).
#  - hores: < 90 s (el raig exacte es mostreja cada minut; el Sol baixa ~0,15 graus per minut).
TOL_CONTACTES_S = 1.0
TOL_MARGE_MEDIANA, TOL_MARGE_P95 = 0.05, 0.2
TOL_MARGE_MAX = 0.2        # desacords amb el CNIG: el raig exacte confirma el nostre marge
TOL_HORES_S = 90.0


class Relleu:
    """Altitud (m) en una latitud i longitud: el MDT donat si hi es; si no, la peninsula."""

    def __init__(self, camins):
        self.mdts = []
        for c in camins:
            with rasterio.open(c) as f:
                self.mdts.append((np.maximum(np.nan_to_num(f.read(1).astype('f4')), 0), f.transform,
                                  Transformer.from_crs('EPSG:4326', f.crs, always_xy=True)))

    def __call__(self, lat, lon):
        h = np.full(np.shape(lat), np.nan)
        for dem, tr, t in self.mdts:
            x, y = t.transform(lon, lat)
            col, fila = (np.asarray(x) - tr.c) / tr.a - 0.5, (tr.f - np.asarray(y)) / -tr.e - 0.5
            dins = np.isnan(h) & (col >= 0) & (fila >= 0) & (col <= dem.shape[1] - 1) & (fila <= dem.shape[0] - 1)
            if dins.any():
                h[dins] = map_coordinates(dem, [fila[dins], col[dins]], order=1)
        return np.nan_to_num(h)


def horitzo_exacte(relleu, lat, lon, az, h0=None, res=5.0):
    """Elevacio (graus) de l'horitzo en l'azimut geografic az, des dels ulls al punt (lat, lon), a 1,7 m sobre h0
    (per defecte, el relleu en aquell punt)."""
    if h0 is None:
        h0 = float(relleu(np.array([lat]), np.array([lon]))[0])
    ulls = geodesia.ecef(lat, lon, (h0 + vis.ULLS_M) / 1000.0)
    est, nord, amunt = geodesia.base_local(lat, lon)
    u = math.sin(math.radians(az)) * est + math.cos(math.radians(az)) * nord
    # a prop, des d'un quart de pixel del MDT i cada mig pixel (com a molt 5 m) fins a 1 km o 50 pixels; despres,
    # distancies creixents (km)
    pas = min(5.0, 0.5 * res)
    lim = max(1000.0, 50 * res)
    d = np.concatenate([np.arange(0.25 * res, lim, pas), np.geomspace(lim, vis.DIST_MAX_M, 600)]) / 1000.0
    q = ulls[None, :] + d[:, None] * u[None, :]
    la, lo, _ = geodesia.geodesiques(q)
    t = geodesia.ecef(la, lo, relleu(la, lo) / 1000.0) - ulls
    return float(np.degrees(np.arcsin((t @ amunt) / np.linalg.norm(t, axis=1))).max())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mdt')
    p.add_argument('--eclipsi', default='2026')
    p.add_argument('--punts', type=int, default=30)
    p.add_argument('--cnig', action='store_true')
    p.add_argument('--ulls', help='raster amb la cota dels ulls (si no es el MDT: terrats i carrers amb el LiDAR)')
    p.add_argument('--lluny', nargs='*', help='MDT del relleu de fora (per defecte, la peninsula)')
    a = p.parse_args()
    lluny = a.lluny if a.lluny is not None else [PENINSULA]
    lluny = [c for c in lluny if os.path.abspath(c) != os.path.abspath(a.mdt)]
    eclipsis.triar(a.eclipsi)
    errors = []

    def ok(condicio, text):
        print(('OK    ' if condicio else 'FALLA ') + text)
        if not condicio:
            errors.append(text)

    r = vis.llegir(a.mdt) or vis.calcular(a.mdt, a.eclipsi, lluny=lluny, cami_ulls=a.ulls)
    with rasterio.open(a.mdt) as f:
        dem, tr, crs = f.read(1), f.transform, f.crs
    a_latlon = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    inici = float(r['inici'])
    print(f'Visibilitat de {os.path.basename(a.mdt)}, eclipsi {a.eclipsi} (calculada en {float(r["segons"]):.0f} s)')

    # pixels de terra a l'atzar, amb eclipsi
    rng = np.random.default_rng(1)
    terra = np.argwhere((dem > 0) & (r['marge'] > vis.SENSE_MARGE))
    mostra = terra[rng.choice(len(terra), size=min(a.punts, len(terra)), replace=False)]
    relleu = Relleu([a.mdt] + lluny)
    ulls = rasterio.open(a.ulls).read(1) if a.ulls else None

    print('\n== 1. Circumstancies de la graella contra ModelEclipsi (punt a punt)')
    lon, lat = a_latlon.transform(tr.c + (mostra[:, 1] + 0.5) * tr.a, tr.f + (mostra[:, 0] + 0.5) * tr.e)
    lat, lon = np.asarray(lat), np.asarray(lon)
    alt = np.maximum(dem[mostra[:, 0], mostra[:, 1]], 0).astype(float)
    from pyproj import Proj
    conv = np.asarray(Proj(crs.to_string()).get_factors(lon, lat).meridian_convergence)
    c = vis.circumstancies(lat, lon, alt, conv)
    pitjor = {}
    models = [ModelEclipsi(float(la), float(lo), float(al) / 1000.0) for la, lo, al in zip(lat, lon, alt)]
    for k in ('c1', 'c2', 'maxim', 'c3', 'c4'):
        for i, m in enumerate(models):
            if m.hores[k] is not None and not np.isnan(c[k][i]):
                pitjor[k] = max(pitjor.get(k, 0.0), abs(c[k][i] - m.hores[k]) * 3600)
            elif (m.hores[k] is None) != np.isnan(c[k][i]):
                pitjor[k] = math.inf
    ok(all(v < TOL_CONTACTES_S for v in pitjor.values()),
       'contactes: ' + ', '.join(f'{k} {v:.2f} s' for k, v in pitjor.items()) + f' (objectiu < {TOL_CONTACTES_S} s)')

    print(f'\n== 2. Marge al maxim i hores de visibilitat contra un raig exacte ({len(mostra)} pixels)')
    dif_m, dif_t, n_t = [], [], 0
    for (fila, col), m in zip(mostra, models):
        la, lo = float(lat[len(dif_m)]), float(lon[len(dif_m)])
        az, el = m.sol(m.hores['maxim'])
        h0 = float(ulls[fila, col]) if ulls is not None else None
        marge_exacte = el - horitzo_exacte(relleu, la, lo, az, h0, tr.a)
        dif_m.append(r['marge'][fila, col] / 100.0 - marge_exacte)
        # hores: el marge exacte cada minut entre C1 i C4
        hs = np.arange(m.hores['c1'], m.hores['c4'], 1 / 60)
        marges = []
        for h in hs:
            az, el = m.sol(h)
            marges.append(el - horitzo_exacte(relleu, la, lo, az, h0, tr.a) if el > -1.5 else -10.0)
        vis_e = np.array(marges) > 0
        ti, tf = r['t_ini'][fila, col], r['t_fi'][fila, col]
        if vis_e.any() and ti != vis.SENSE:
            e_ini, e_fi = hs[vis_e.argmax()], hs[len(vis_e) - 1 - vis_e[::-1].argmax()]
            dif_t += [(inici + ti / 3600 - e_ini) * 3600, (inici + tf / 3600 - e_fi) * 3600]
            n_t += 1
        elif vis_e.any() != (ti != vis.SENSE):
            dif_t.append(math.inf)
    dif_m = np.abs(dif_m)
    ok(np.median(dif_m) < TOL_MARGE_MEDIANA and np.percentile(dif_m, 95) < TOL_MARGE_P95,
       f'marge al maxim: diferencia mediana {np.median(dif_m):.3f} graus, 95 % {np.percentile(dif_m, 95):.3f}, maxima '
       f'{dif_m.max():.3f} (objectiu: mediana < {TOL_MARGE_MEDIANA}, 95 % < {TOL_MARGE_P95})')
    dif_t = np.abs(dif_t)
    ok(len(dif_t) and dif_t.max() < TOL_HORES_S, f'hores de visibilitat ({n_t} pixels): diferencia mediana '
       f'{np.median(dif_t):.0f} s, maxima {dif_t.max():.0f} s (objectiu < {TOL_HORES_S:.0f} s; el raig exacte es '
       f'mostreja cada minut)')

    if a.cnig:
        print('\n== 3. Classes al maxim contra terrain_shadows del CNIG')
        from rasterio.warp import reproject, Resampling
        from dades import eclipse_data
        with rasterio.open(eclipse_data.OMBRES) as f:
            cnig = np.full(dem.shape, 255, 'u1')
            reproject(f.read(1), cnig, src_transform=f.transform, src_crs=f.crs, dst_transform=tr, dst_crs=crs,
                      resampling=Resampling.nearest, dst_nodata=255)
        m = r['marge'] / 100.0
        rs = float(r['radi_sol'])
        nostra = np.select([m > rs, m > 0, m > -rs], [3, 2, 1], 0)
        valid = (dem > 0) & (r['marge'] > vis.SENSE_MARGE) & (cnig <= 3)
        mat = np.zeros((4, 4), int)
        np.add.at(mat, (cnig[valid], nostra[valid]), 1)
        print('files: CNIG, columnes: nostre (0 tot tapat ... 3 res tapat); % de cada fila')
        for i in range(4):
            print(f'  {i}: ' + '  '.join(f'{100 * mat[i, j] / max(mat[i].sum(), 1):5.1f}' for j in range(4))
                  + f'   ({mat[i].sum():,} px)')
        acord = np.trace(mat) / mat.sum()
        visible_igual = ((cnig[valid] >= 2) == (nostra[valid] >= 2)).mean()
        print(f'  acord de classe: {acord * 100:.1f} %; "es veu mes de mig Sol" (classes 2-3) igual: '
              f'{visible_igual * 100:.1f} %')
        print(f'  objectiu provisional de coincidencia (> 90 %): {"assolit" if visible_igual > 0.9 else "NO assolit"}')
        # els desacords grans (el CNIG diu tot tapat i nosaltres mes d'1 grau de marge) es comproven amb el raig
        # exacte: si el confirma, la diferencia ve de les dades o del metode del CNIG, no del nostre calcul
        des = np.argwhere(valid & (cnig == 0) & (m > 1.0))
        dif = []
        for fila, col in des[rng.choice(len(des), size=min(10, len(des)), replace=False)]:
            lo, la = a_latlon.transform(tr.c + (col + 0.5) * tr.a, tr.f + (fila + 0.5) * tr.e)
            mo = ModelEclipsi(la, lo, max(float(dem[fila, col]), 0.0) / 1000.0)
            az, el = mo.sol(mo.hores['maxim'])
            dif.append(abs(m[fila, col] - (el - horitzo_exacte(relleu, la, lo, az, res=tr.a))))
        ok(max(dif) < TOL_MARGE_MAX, f'desacords amb el CNIG (CNIG: tot tapat; nostre marge > 1 grau): el raig exacte '
           f'confirma el nostre marge a {len(dif)} de {len(dif)} pixels (diferencia maxima {max(dif):.3f} graus)')

    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
