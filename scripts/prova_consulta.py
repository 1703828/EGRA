"""
Consulta d'un punt del mapa (tasques 43.5 i 43.6) amb el programa real (finestra amagada):

1. Per a cada lloc (per defecte la UAB i Cerdanyola, de la llista del panell): s'hi posa el punt d'observacio, la
   camera d'exploracio a sobre (inclinada) i el mapa "Temps observable"; s'espera que hi hagi el detall dels
   obstacles (N3) i es desa una captura (terreny i terrats pintats).
2. La consulta del punt (Mapes.consulta) contra un calcul independent: el marge cada minut entre C1 i C4 amb el raig
   exacte (scripts/validar_visibilitat.py) sobre la mateixa superficie d'obstacles i des dels mateixos ulls; temps
   amb alguna part del Sol lliure (D91). Tolerancia: 3 punts percentuals (el raig es mostreja cada minut; el mapa,
   cada minut i cada 0,25 graus d'azimut; scripts/validar_temps_visibilitat.py).
3. Exportacio: la fila del CSV te les metadades (tipus d'observacio, eclipsi, dades, obstacles, criteri).
Captures a captures/proves/consulta_*.png; CSV de la prova a captures/proves/consultes_prova.csv.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/prova_consulta.py [UAB] [Cerdanyola] [Vic] [Montmelo]
"""
import csv
import os
import sys
import time

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ARREL)
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, 'scripts'))

import glfw  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

SORTIDA = os.path.join(ARREL, 'captures', 'proves')
W, H = 1000, 700
TOL_PUNTS = 3.0
# el millor de milers de pixels tendeix a ser on el mapa sobreestima mes (biaix de seleccio): mes tolerancia, i els
# punts a l'atzar mesuren l'error de debo
TOL_MILLOR = 5.0


def main():
    llocs_demanats = [a for a in sys.argv[1:] if not a.startswith('-')] or ['UAB', 'Cerdanyola']
    os.makedirs(SORTIDA, exist_ok=True)
    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    sys.argv = ['main.py']
    import main as programa
    from dades import alcaries, geodesia, visibilitat as vis
    from dades.observador import UBICACIONS
    from dades.model_eclipsi import ModelEclipsi
    from validar_visibilitat import Relleu, horitzo_exacte

    app = programa.GraphicsEngine(win_size=(W, H), title='EGRA - prova de la consulta', use_ui_panel=True)
    fb = app.ctx.simple_framebuffer((W, H))
    errors = []

    def ok(c, text):
        print(('OK    ' if c else 'FALLA ') + text, flush=True)
        if not c:
            errors.append(text)
        return c

    def fotograma(n=1):
        for _ in range(n):
            fb.use()
            app.dt = 1 / 30
            app.render()
            app.ctx.finish()

    cami_csv = os.path.join(SORTIDA, 'consultes_prova.csv')
    if os.path.exists(cami_csv):
        os.remove(cami_csv)
    app.mapes.mostrar('durada')
    resum = []
    for part in llocs_demanats:
        nom, lat, lon = next(u for u in UBICACIONS if part.lower() in u[0].lower())
        print(f'== {nom}', flush=True)
        app.triar_ubicacio(lat, lon, nom)
        o = app.observador
        u = app.ulls()
        cam = app.camera_exploracio
        _, nord, amunt = geodesia.base_local(o.lat, o.lon)
        cam.posicio = u - 0.5 * nord + 0.35 * amunt
        cam.orientar(0.0, -35.0)
        t0 = time.time()
        r = None
        while time.time() - t0 < 900:
            fotograma(5)
            r = app.mapes.consulta(o.lat, o.lon, app.model)
            if r is not None and r['nivell'] == 3 and not app.mapes.ocupat():
                break
        fotograma(5)
        Image.frombytes('RGB', (W, H), fb.read(components=3)).transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(SORTIDA, f'consulta_{part.lower()}.png'))
        if not ok(r is not None and r['nivell'] == 3, f'{nom}: consulta amb el detall dels obstacles '
                  f'({r["dades"] if r else "cap"}, {time.time() - t0:.0f} s)'):
            continue
        # el punt del lloc i el millor punt de carrer a menys de 500 m (el mapa ho permet comparar)
        punts = [(nom, o.lat, o.lon, r)]
        for terrat in (False, True):
            tipus = 'terrat' if terrat else 'carrer'
            millor = millor_proper(app, o.lat, o.lon, 500.0, terrat)
            if millor is not None:
                la, lo = millor
                rm = app.mapes.consulta(la, lo, ModelEclipsi(la, lo, app.altitud_terra_km(la, lo)))
                if rm is not None:
                    punts.append((f'{nom}: millor {tipus} a < 500 m', la, lo, rm, TOL_MILLOR))
            for k, (la, lo) in enumerate(punts_atzar(app, o.lat, o.lon, 500.0, terrat, 3)):
                rm = app.mapes.consulta(la, lo, ModelEclipsi(la, lo, app.altitud_terra_km(la, lo)))
                if rm is not None:
                    punts.append((f'{nom}: {tipus} a l\'atzar {k + 1}', la, lo, rm, TOL_PUNTS))
        for etiqueta, la, lo, rr, tol in [(*p_, TOL_PUNTS) if len(p_) == 4 else p_ for p_ in punts]:
            frac_e = exacte(app, la, lo)
            ok(abs(frac_e - rr['frac']) * 100 < tol,
               f"{etiqueta}: temps visible del mapa {100 * rr['frac']:.1f} % ({rr['minuts']:.0f} min) contra el raig "
               f"exacte {100 * frac_e:.1f} % (tolerancia {tol:.0f} punts); {rr['tipus']}")
            app.mapes.exportar(rr, cami_csv)
            resum.append((etiqueta, rr))
    with open(cami_csv, encoding='utf-8') if os.path.exists(cami_csv) else open(os.devnull) as fh:
        files = list(csv.DictReader(fh))
    ok(len(files) == len(resum) and all(f['criteri'] and f['tipus'] and f['obstacles'] and f['dades'] for f in files),
       f'exportacio: {len(files)} files amb les metadades ({cami_csv})')
    print('\nComparacio:')
    for nom, r in sorted(resum, key=lambda nr: -nr[1]['frac']):
        print(f"  {nom:22s} {r['minuts']:5.0f} min ({100 * r['frac']:4.1f} %) de C1-C4; intervals "
              + ', '.join(f'{app_hl(a)}-{app_hl(b)}' for a, b in r['intervals']))
    print(f"\n{'Tot correcte' if not errors else f'{len(errors)} condicions fallen'}")
    return 1 if errors else 0


def punts_atzar(app, lat, lon, radi_m, terrat, n, llavor=11):
    """n pixels a l'atzar de carrer (o de terrat) a menys de radi_m, de les peces N3 carregades: [(lat, lon)]."""
    from basecode.mapes import BIT_EDIFICI, _A_UTM, _A_LATLON
    from dades import visibilitat as vis
    x, y = _A_UTM.transform(lon, lat)
    cand = []
    for p in app.mapes.peces.values():
        if p.nivell != 3:
            continue
        c0 = p.dades['capa0']
        files, cols = c0.shape[:2]
        cc, ff = np.meshgrid(p.rect[0] + (np.arange(cols) + 0.5) * p.res, p.rect[3] - (np.arange(files) + 0.5) * p.res)
        dins = (c0[..., 3] & BIT_EDIFICI) != 0
        ok = (np.hypot(cc - x, ff - y) < radi_m) & (c0[..., 0] != vis.SENSE) & (dins if terrat else ~dins)
        cand += list(zip(cc[ok], ff[ok]))
    if not cand:
        return []
    rng = np.random.default_rng(llavor)
    tria = rng.choice(len(cand), size=min(n, len(cand)), replace=False)
    out = []
    for i in tria:
        lo, la = _A_LATLON.transform(*cand[i])
        out.append((float(la), float(lo)))
    return out


def millor_proper(app, lat, lon, radi_m, terrat=False):
    """El pixel de carrer (o de terrat) amb mes temps observable a menys de radi_m, de les peces carregades."""
    from basecode.mapes import BIT_EDIFICI, _A_UTM, _A_LATLON
    from dades import visibilitat as vis
    x, y = _A_UTM.transform(lon, lat)
    millor, valor = None, -1
    for p in app.mapes.peces.values():
        if p.nivell != 3:
            continue
        c0 = p.dades['capa0']
        files, cols = c0.shape[:2]
        x0, y1 = p.rect[0], p.rect[3]
        cc, ff = np.meshgrid(x0 + (np.arange(cols) + 0.5) * p.res, y1 - (np.arange(files) + 0.5) * p.res)
        dins = (c0[..., 3] & BIT_EDIFICI) != 0
        ok = (np.hypot(cc - x, ff - y) < radi_m) & (c0[..., 0] != vis.SENSE) & (dins if terrat else ~dins)
        if ok.any():
            v = np.where(ok, c0[..., 0].astype(int), -1)
            k = np.unravel_index(np.argmax(v), v.shape)
            if v[k] > valor:
                valor, millor = v[k], (cc[k], ff[k])
    if millor is None:
        return None
    lo, la = _A_LATLON.transform(*millor)
    return float(la), float(lo)


def exacte(app, lat, lon):
    """Fraccio de C1-C4 amb alguna part del Sol lliure (D91) amb el raig exacte cada minut, des dels mateixos ulls
    i sobre la mateixa superficie que el mapa."""
    import rasterio
    from dades import alcaries, visibilitat as vis
    from dades.model_eclipsi import ModelEclipsi
    from validar_visibilitat import Relleu, horitzo_exacte
    from basecode.mapes import _A_UTM
    x, y = _A_UTM.transform(lon, lat)
    cx, cy = alcaries.centre_cel(x, y)
    cel = f'cel_{cx:.0f}_{cy:.0f}'
    sup, ulls_c = alcaries.cami_superficie(cel, 'superficie'), alcaries.cami_superficie(cel, 'ulls')
    relleu = Relleu([sup, app.mapes._mdt_5m((cx - 1500, cy - 1500, cx + 1500, cy + 1500)), app.peninsula.cami])
    with rasterio.open(ulls_c) as f:
        c_, f_ = ~f.transform * (x, y)
        h0 = float(f.read(1)[int(f_), int(c_)])
    m = ModelEclipsi(lat, lon, h0 / 1000.0)
    vis_e = []
    for h in np.arange(m.hores['c1'], m.hores['c4'], 1 / 60):
        az, el = m.sol(h)
        rs = float(np.degrees(np.arcsin(vis.RADI_SOL_KM / np.linalg.norm(app.ef.posicions(h)[0] - m.posicio))))
        vis_e.append(el - horitzo_exacte(relleu, lat, lon, az, h0, 2.0) > -rs if el > -2 else False)
    return float(np.mean(vis_e))


def app_hl(h):
    from dades import eclipsis
    return eclipsis.hora_local(h)[:5]


if __name__ == '__main__':
    sys.exit(main())
