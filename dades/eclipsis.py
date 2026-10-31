"""
Els eclipsis que es poden simular (sense OpenGL): data, tipus, interval de les efemerides i hora local.

Cada eclipsi te el seu fitxer d'efemerides de JPL Horizons (scripts/descarregar_efemerides.py <clau>), amb el
Sol i la Lluna cada minut de l'interval (hores TU del dia de l'eclipsi). L'eclipsi actiu (actiu(), triar()) el
fan servir dades/model_eclipsi.py (efemerides()) i l'hora local de la interficie.

El tipus (total o anular) es el del recorregut de l'ombra; en un punt concret el model ho calcula: a la totalitat
la Lluna es mes gran que el Sol i el tapa sencer; a l'anularitat es mes petita i en queda un anell.
"""
import datetime
import os

DIR_EFEMERIDES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'efemerides')

# clau: (titol, data, tipus, inici i final de les efemerides (hores TU), hores de diferencia de l'hora local, nom)
ECLIPSIS = {
    '2026': dict(titol="12 d'agost de 2026", data='2026-08-12', tipus='total', inici='14:00', final='21:30',
                 hores_local=2, nom_hora="hora d'estiu"),
    '2027': dict(titol="2 d'agost de 2027", data='2027-08-02', tipus='total', inici='06:00', final='12:00',
                 hores_local=2, nom_hora="hora d'estiu"),
    '2028': dict(titol='26 de gener de 2028', data='2028-01-26', tipus='anular', inici='13:00', final='19:30',
                 hores_local=1, nom_hora="hora d'hivern"),
}
_actiu = '2026'


def actiu():
    """Clau de l'eclipsi actiu."""
    return _actiu


def triar(clau):
    global _actiu
    if clau not in ECLIPSIS:
        raise KeyError(clau)
    _actiu = clau


def dades(clau=None):
    return ECLIPSIS[clau or _actiu]


def fitxer(clau=None):
    return os.path.join(DIR_EFEMERIDES, f"horizons_sol_lluna_{dades(clau)['data'].replace('-', '')}.csv")


def jd_0h(clau=None):
    """Dia julia de les 0 h TU del dia de l'eclipsi."""
    d = datetime.date.fromisoformat(dades(clau)['data'])
    return 2451544.5 + (d - datetime.date(2000, 1, 1)).days   # 01/01/2000 a les 0 h TU: JD 2451544,5


def disponibles():
    """Claus dels eclipsis amb el fitxer d'efemerides baixat."""
    return [c for c in ECLIPSIS if os.path.exists(fitxer(c))]


def hora_local(hores_tu, clau=None):
    """Hora TU decimal (p. ex. 18.4667) -> 'hh:mm:ss' en hora local (2026 i 2027: TU + 2; 2028: TU + 1)."""
    s = round((hores_tu + dades(clau)['hores_local']) * 3600) % 86400
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
