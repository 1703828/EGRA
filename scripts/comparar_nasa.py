"""
Comprovacio independent del model de l'eclipsi amb el calculador de circumstancies locals de la NASA
(tasca 3.8 del pla; convencions a §6.3.1).

Font: https://eclipse.gsfc.nasa.gov/SEgoogle/SEgoogle2001/SE2026Aug12Tgoogle.html
"Eclipse Predictions by Fred Espenak, NASA's GSFC"; calculador de Xavier Jubier (SEcirc.js).

El mapa calcula les circumstancies d'un punt quan s'hi fa clic, amb el seu propi codi JavaScript
(SEcirc.js) i els elements de Bessel escrits a la pagina. En lloc de fer clic, aquest script executa
aquell mateix codi sense canvis amb les coordenades exactes de cada punt. S'hi afegeix nomes una funcio
que llegeix els resultats sense arrodonir (el globus els mostra arrodonits a 0,1 s i 0,1 graus).

Dos passos:
  python scripts/comparar_nasa.py --calcular   descarrega la pagina i SEcirc.js a data/cache/nasa/,
                                               els executa amb JavaScriptCore (osascript, nomes macOS)
                                               i desa data/nasa/circumstancies_nasa.csv
  python scripts/comparar_nasa.py              compara el CSV amb el nostre model i amb el CNIG
Amb --eclipsi 2027 o 2028 (dades/eclipsis.py), la pagina d'aquell eclipsi, un CSV propi
(circumstancies_nasa_<any>.csv) i punts de la seva franja; el CNIG nomes te dades del 2026.

Convencions de la NASA (llegides al codi): hores en TU amb un dT = TT - TU de 71,4 s (previst quan es
va fer el mapa); observador a 0 m (nivell del mar); elevacio del Sol geometrica (sense refraccio);
azimut des del nord en sentit horari; vora mitjana de la Lluna (sense muntanyes).
Per comparar en les mateixes condicions, el nostre model es calcula a 0 m i amb l'elevacio geometrica.
"""
import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
from dades import eclipse_data, eclipsis  # noqa: E402
from dades.model_eclipsi import ModelEclipsi  # noqa: E402
from dades.observador import UBICACIONS  # noqa: E402

PAGINES = {'2026': 'SE2026Aug12Tgoogle.html', '2027': 'SE2027Aug02Tgoogle.html', '2028': 'SE2028Jan26Agoogle.html'}
URL_PAGINA = 'https://eclipse.gsfc.nasa.gov/SEgoogle/SEgoogle2001/SE2026Aug12Tgoogle.html'
URL_CODI = 'https://eclipse.gsfc.nasa.gov/SEgoogle/SEcirc.js'
DIR_CACHE = os.path.join(ARREL, 'data', 'cache', 'nasa')
CSV = os.path.join(ARREL, 'data', 'nasa', 'circumstancies_nasa.csv')
# les sis ubicacions del programa i tres punts mes (els mateixos que scripts/validar_model.py)
PUNTS = [(nom.split(',')[0].split(' (')[0], lat, lon) for nom, lat, lon in UBICACIONS] + [
    ('Burgos', 42.3439, -3.6969), ('Valencia', 39.4699, -0.3763), ('Palma', 39.5696, 2.6502)]
# 2027 i 2028: punts de la franja central i de fora, al sud i a l'est
PUNTS_NOUS = [('Tarifa', 36.014, -5.604), ('Cadis', 36.529, -6.292), ('Malaga', 36.721, -4.421),
              ('Sevilla', 37.389, -5.984), ('Valencia', 39.4699, -0.3763), ('Barcelona', 41.387, 2.170),
              ('UAB', 41.5022, 2.1042), ('Picos', 43.262, -4.949)]
CONTACTES = ('c1', 'c2', 'maxim', 'c3', 'c4')

# s'afegeix al final de SEcirc.js: calcula un punt (les mateixes funcions que el clic al mapa) i en
# retorna els valors sense arrodonir. Hora TU = hora TD de la pagina - dT (com gettime(), sense el 0,05 s
# d'arrodoniment); altura i azimut en graus (circumstances[31] i [32], com getalt() i getazi()).
LECTURA_JS = """
function tu(c) { return c[1] + elements[1] - elements[4] / 3600.0; }
function punt(lat, lon) {
  readdata(lat, lon); getall();
  var r = {tipus: mid[36], magnitud: mid[34], obscuracio: parseFloat(getcoverage()) / 100.0, dT: elements[4]};
  var cs = {c1: c1, c2: c2, maxim: mid, c3: c3, c4: c4};
  for (var k in cs) {
    var total = (k == 'c2' || k == 'c3');
    if (mid[36] == 0 || (total && mid[36] < 2)) { r[k] = null; continue; }
    var az = cs[k][32] * R2D; if (az < 0) az += 360.0;
    r[k] = [tu(cs[k]), cs[k][31] * R2D, az];
  }
  return r;
}
"""


def descarregar(url, fitxer):
    if not os.path.exists(fitxer):
        with urllib.request.urlopen(url, timeout=60) as r, open(fitxer, 'wb') as f:
            f.write(r.read())
    return open(fitxer, encoding='latin-1').read()


def calcular():
    """Executa el calculador de la NASA per a cada punt i desa el CSV."""
    os.makedirs(DIR_CACHE, exist_ok=True)
    pagina = descarregar(URL_PAGINA, os.path.join(DIR_CACHE, os.path.basename(URL_PAGINA)))
    codi = descarregar(URL_CODI, os.path.join(DIR_CACHE, 'SEcirc.js'))
    elements = re.search(r'var elements = new Array\((.*?)\);', pagina, re.S).group(1)
    elements = re.sub(r'//[^\n]*', '', elements)   # comentaris de JavaScript
    crides = ', '.join(f'punt({lat}, {lon})' for _, lat, lon in PUNTS)
    js = f'var elements = new Array({elements});\n{codi}\n{LECTURA_JS}\nJSON.stringify([{crides}]);\n'
    fitxer_js = os.path.join(DIR_CACHE, 'executar.js')
    with open(fitxer_js, 'w') as f:
        f.write(js)
    sortida = subprocess.run(['osascript', '-l', 'JavaScript', fitxer_js], capture_output=True, text=True,
                             check=True).stdout
    resultats = json.loads(sortida)
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with open(CSV, 'w', newline='') as f:
        f.write(f'# Calculador de circumstancies locals de la NASA (Espenak/GSFC, Jubier), executat el '
                f'{datetime.date.today()} amb scripts/comparar_nasa.py --calcular\n')
        f.write(f'# {URL_PAGINA}\n')
        f.write(f'# Hores TU (decimals) amb dT = {resultats[0]["dT"]} s; observador a 0 m; elevacio geometrica '
                f'(sense refraccio); azimut des del nord en sentit horari. tipus: 1 parcial, 2 anular, 3 total\n')
        w = csv.writer(f)
        w.writerow(['punt', 'lat', 'lon', 'tipus', 'magnitud', 'obscuracio']
                   + [f'{k}_{x}' for k in CONTACTES for x in ('tu', 'elev', 'azimut')])
        for (nom, lat, lon), r in zip(PUNTS, resultats):
            fila = [nom, lat, lon, r['tipus'], f"{r['magnitud']:.5f}", f"{r['obscuracio']:.4f}"]
            for k in CONTACTES:
                fila += ['', '', ''] if r[k] is None else [f'{r[k][0]:.7f}', f'{r[k][1]:.4f}', f'{r[k][2]:.4f}']
            w.writerow(fila)
    print(f'Desat {CSV}')


def llegir():
    with open(CSV) as f:
        return list(csv.DictReader(fila for fila in f if not fila.startswith('#')))


def comparar():
    files = llegir()
    print('Model (a 0 m, elevacio geometrica) - NASA. Hores en segons; part tapada al maxim en punts '
          'percentuals; elevacio i azimut al maxim en graus.')
    print(f"{'Punt':16s}" + ''.join(f'{k:>7s}' for k in CONTACTES) + f"{'tapat':>8s}{'elev.':>8s}{'azim.':>8s}"
          + '   | CNIG - NASA:' + ''.join(f'{k:>7s}' for k in CONTACTES))
    pitjor, pitjor_cnig = {}, {}
    for r in files:
        lat, lon = float(r['lat']), float(r['lon'])
        m = ModelEclipsi(lat, lon, 0.0)
        cnig = eclipse_data.punt(lat, lon) if eclipsis.actiu() == '2026' else {'hores_tu': {}}
        cols, cols_cnig = '', ''
        for k in CONTACTES:
            nasa = float(r[f'{k}_tu']) if r[f'{k}_tu'] else None
            for valor, text, p in ((m.hores[k], 'cols', pitjor), (cnig['hores_tu'].get(k), 'cnig', pitjor_cnig)):
                if valor is None or nasa is None:
                    s = f"{'-':>7s}" if valor is None and nasa is None else f"{'?':>7s}"
                else:
                    d = (valor - nasa) * 3600
                    p[k] = max(p.get(k, 0.0), abs(d))
                    s = f'{d:+7.1f}'
                if text == 'cols':
                    cols += s
                else:
                    cols_cnig += s
        hm = m.hores['maxim']
        az, el = m.sol(hm, refraccio=False)
        tapat = (m.fraccio_tapada(hm) - float(r['obscuracio'])) * 100
        d_el, d_az = el - float(r['maxim_elev']), (az - float(r['maxim_azimut']) + 180) % 360 - 180
        for clau, v in (('tapat', abs(tapat)), ('elev', abs(d_el)), ('azim', abs(d_az))):
            pitjor[clau] = max(pitjor.get(clau, 0.0), v)
        cnig_text = f'   |             {cols_cnig}' if eclipsis.actiu() == '2026' else ''
        print(f"{r['punt']:16s}{cols}{tapat:+8.2f}{d_el:+8.3f}{d_az:+8.3f}{cnig_text}")
    print('Diferencia maxima model - NASA:', ', '.join(f'{k} {v:.3f}' if k in ('elev', 'azim', 'tapat')
                                                         else f'{k} {v:.1f} s' for k, v in pitjor.items()))
    if pitjor_cnig:
        print('Diferencia maxima CNIG - NASA:', ', '.join(f'{k} {v:.1f} s' for k, v in pitjor_cnig.items()))
    sensibilitat_radi(files)


def sensibilitat_radi(files):
    """Prova de sensibilitat (no canvia el model): la NASA fa servir dos radis de la Lluna, k = 0,2725076
    radis terrestres per a C1 i C4 i k = 0,272281 per a C2 i C3; el nostre model, 1737,4 km per a tots.
    Es repeteix la comparacio amb els radis de la NASA canviant temporalment la constant del modul: si el
    que queda es la mateixa diferencia a tots els contactes, la resta es una diferencia d'escala de temps
    (dT = TT - TU), no del model geometric."""
    from dades import model_eclipsi
    original = model_eclipsi.RADI_LLUNA_KM
    difs = []
    try:
        for k, claus in ((0.2725076, ('c1', 'maxim', 'c4')), (0.272281, ('c2', 'c3'))):
            model_eclipsi.RADI_LLUNA_KM = k * 6378.137
            for r in files:
                m = ModelEclipsi(float(r['lat']), float(r['lon']), 0.0)
                difs += [(m.hores[c] - float(r[f'{c}_tu'])) * 3600 for c in claus
                         if m.hores[c] is not None and r[f'{c}_tu']]
    finally:
        model_eclipsi.RADI_LLUNA_KM = original
    mitjana = sum(difs) / len(difs)
    print(f'Amb els radis de la Lluna de la NASA: model - NASA = {mitjana:+.2f} s de mitjana a tots els '
          f'contactes (de {min(difs):+.2f} a {max(difs):+.2f} s). Una diferencia constant com aquesta es la que '
          f'donaria un dT de {71.4 - mitjana:.1f} s a les efemerides de JPL (la NASA en fa servir 71,4 s).')


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--calcular', action='store_true', help='executar el calculador de la NASA (macOS, xarxa)')
    p.add_argument('--eclipsi', default='2026', choices=list(PAGINES))
    a = p.parse_args()
    global URL_PAGINA, CSV, PUNTS
    eclipsis.triar(a.eclipsi)
    if a.eclipsi != '2026':
        URL_PAGINA = URL_PAGINA.replace(PAGINES['2026'], PAGINES[a.eclipsi])
        CSV = CSV.replace('.csv', f'_{a.eclipsi}.csv')
        PUNTS = PUNTS_NOUS
    if a.calcular:
        calcular()
    comparar()


if __name__ == '__main__':
    main()
