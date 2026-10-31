"""
Descarrega les posicions del Sol i la Lluna d'un eclipsi (dades/eclipsis.py) del servei JPL Horizons (NASA/JPL).

Posicions geocentriques (centre de la Terra, '500@399') en km, en el sistema de referencia ICRF
(equador i equinocci de J2000), cada minut de 14:00 a 21:30 TU. Es demanen corregides pel temps
que triga la llum (VEC_CORR='LT'): es la posicio d'on surt la llum que arriba a la Terra en aquell
instant, que es la que compta per a l'ombra de la Lluna. El pas a coordenades terrestres
(precessio, nutacio i rotacio de la Terra) el fa dades/efemerides.py. L'interval de cada eclipsi (hores TU)
es a dades/eclipsis.py.

Sortida: data/efemerides/horizons_sol_lluna_<aaaammdd>.csv (~45 KB, es versiona al Git).

Executa (des de l'arrel del projecte):
    python scripts/descarregar_efemerides.py          # 2026
    python scripts/descarregar_efemerides.py 2027     # o 2028

Font: JPL Horizons, https://ssd.jpl.nasa.gov/horizons/ (efemerides DE440/441 de NASA/JPL).
"""
import csv
import os
import sys

import requests

URL = 'https://ssd.jpl.nasa.gov/api/horizons.api'
ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from dades import eclipsis  # noqa: E402

CLAU = sys.argv[1] if len(sys.argv) > 1 else '2026'
_e = eclipsis.dades(CLAU)
SORTIDA = eclipsis.fitxer(CLAU)
INICI, FINAL, PAS = f"{_e['data']} {_e['inici']}", f"{_e['data']} {_e['final']}", '1 m'
COSSOS = {'sol': '10', 'lluna': '301'}


def vectors(cos):
    """Llista de (jd_ut, x, y, z) en km per al cos donat (codi de Horizons)."""
    params = dict(format='text', COMMAND=f"'{cos}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
                  EPHEM_TYPE="'VECTORS'", CENTER="'500@399'", REF_PLANE="'FRAME'", REF_SYSTEM="'ICRF'",
                  START_TIME=f"'{INICI}'", STOP_TIME=f"'{FINAL}'", STEP_SIZE=f"'{PAS}'",
                  VEC_TABLE="'1'", VEC_CORR="'LT'", TIME_TYPE="'UT'", OUT_UNITS="'KM-S'", CSV_FORMAT="'YES'")
    r = requests.get(URL, params=params, timeout=120)
    r.raise_for_status()
    text = r.text
    if '$$SOE' not in text:
        raise RuntimeError(f"Resposta inesperada de Horizons:\n{text[:1500]}")
    files = []
    for linia in text.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines():
        camps = [c.strip() for c in linia.split(',')]
        files.append((float(camps[0]), float(camps[2]), float(camps[3]), float(camps[4])))
    capcalera = text.split('$$SOE')[0]
    return files, capcalera


def main():
    dades = {}
    for nom, codi in COSSOS.items():
        files, capcalera = vectors(codi)
        dades[nom] = files
        print(f"{nom}: {len(files)} posicions")
        for linia in capcalera.splitlines():
            if any(k in linia for k in ('Ephemeris', 'Reference frame', 'Center geodetic', 'Output units', 'Time')):
                print('   ', linia.strip()[:110])
    assert [f[0] for f in dades['sol']] == [f[0] for f in dades['lluna']], "els instants no coincideixen"
    os.makedirs(os.path.dirname(SORTIDA), exist_ok=True)
    with open(SORTIDA, 'w', newline='') as f:
        w = csv.writer(f)
        f.write("# JPL Horizons (NASA/JPL), posicions geocentriques ICRF en km, corregides pel temps de la llum (LT)\n")
        f.write(f"# del {INICI} al {FINAL} TU, cada {PAS}; jd_ut = dia julia (UT)\n")
        w.writerow(['jd_ut', 'sol_x', 'sol_y', 'sol_z', 'lluna_x', 'lluna_y', 'lluna_z'])
        for s, l in zip(dades['sol'], dades['lluna']):
            w.writerow([f"{s[0]:.8f}"] + [f"{v:.4f}" for v in s[1:]] + [f"{v:.4f}" for v in l[1:]])
    print(f"Desat {SORTIDA}")


if __name__ == '__main__':
    sys.exit(main())
