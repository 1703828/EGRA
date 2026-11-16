"""
Blocs del relleu de 25 m per al nivell N1 dels mapes de l'eclipsi (basecode/mapes.py; tasca 42.6 del pla), sense
OpenGL.

Entre la vista de la peninsula (relleu de 200 m) i la dels carrers (5 m), a l'escala d'una comarca un pixel de la
pantalla fa de 30 a 150 m sobre el terra: el mapa de 200 m es veuria engrandit. El nivell N1 es calcula amb el MDT de
25 m de l'IGN (el mateix servei WCS que el de 5 m dels llocs, cobertura Elevacion25830_25): es veuen les valls i les
serres que la graella de 200 m no resol.

Quadricula: blocs de MIDA_M x MIDA_M alineats a multiples de MIDA_M (EPSG:25830). Per a cada bloc es baixa el MDT amb
MARGE_M al voltant (l'horitzo de les vores necessita el relleu de fora; mes enlla, el de la peninsula), una sola
peticio de (24 + 6) km / 25 m = 1.200 pixels per costat (~3 MB comprimit). Es guarden com a molt MAX_BLOCS (els mes
antics s'esborren, amb el seu mapa): espai limitat al disc de l'equip.

MDT (c) Instituto Geografico Nacional (CC BY 4.0).
"""
import glob
import math
import os
import time

from . import data_io, mdt_wcs

MIDA_M = 24000.0
MARGE_M = 3000.0
RES_M = 25
MAX_BLOCS = 12
DIR_BLOCS = os.path.join(data_io.DIR_MDT, 'blocs25')      # ignorada pel Git (com data/mdt/llocs)


def clau(x, y):
    """Clau del bloc que conte el punt (x, y), EPSG:25830."""
    return f'bloc_{math.floor(x / MIDA_M) * MIDA_M:.0f}_{math.floor(y / MIDA_M) * MIDA_M:.0f}'


def rect(clau_bloc):
    """(x0, y0, x1, y1) del bloc (sense el marge): la part on es calcula el mapa."""
    _, x0, y0 = clau_bloc.split('_')
    x0, y0 = float(x0), float(y0)
    return x0, y0, x0 + MIDA_M, y0 + MIDA_M


def cami(clau_bloc):
    return os.path.join(DIR_BLOCS, f'{clau_bloc}_25m.tif')


def existeix(clau_bloc):
    return os.path.exists(cami(clau_bloc))


def preparar(clau_bloc, avis=print):
    """Baixa el MDT de 25 m del bloc amb el marge (si ja hi es, no fa res) i esborra els blocs mes antics."""
    if existeix(clau_bloc):
        os.utime(cami(clau_bloc))
        return cami(clau_bloc)
    x0, y0, x1, y1 = rect(clau_bloc)
    avis('Baixant el relleu de 25 m (IGN)...')
    alt, xmin, ymax = mdt_wcs.descarregar_rectangle(RES_M, (x0 - MARGE_M, y0 - MARGE_M, x1 + MARGE_M, y1 + MARGE_M))
    if not (alt > 0).any():
        raise RuntimeError('aqui el MDT de l\'IGN no te relleu (mar o fora d\'Espanya)')
    os.makedirs(DIR_BLOCS, exist_ok=True)
    mdt_wcs.desar_geotiff(cami(clau_bloc), alt, xmin, ymax, RES_M)
    esborrar_antics(protegit=clau_bloc)
    return cami(clau_bloc)


def esborrar_antics(protegit=None):
    """Com a molt MAX_BLOCS blocs: s'esborren els que fa mes temps que no es fan servir, amb els seus mapes."""
    blocs = sorted(glob.glob(os.path.join(DIR_BLOCS, 'bloc_*_25m.tif')), key=os.path.getmtime)
    sobren = len(blocs) - MAX_BLOCS
    for c in blocs:
        if sobren <= 0:
            break
        if protegit and os.path.basename(c).startswith(protegit + '_'):
            continue
        nom = os.path.splitext(os.path.basename(c))[0]
        for f in [c] + glob.glob(os.path.join(data_io.DIR_CACHE, f'visibilitat_*_{nom}_*.npz')):
            os.remove(f)
        sobren -= 1


def tocar(clau_bloc):
    """Marca el bloc com a fet servir ara (per esborrar els antics)."""
    if existeix(clau_bloc):
        os.utime(cami(clau_bloc), (time.time(), time.time()))
