"""
Lectura georeferenciada dels MDT (GeoTIFF) i neteja de les dades.

- llegir_geotiff():      altituds + georeferencia (transform, CRS) + mascara de mar
- mascara_mar():         mar = sense dades o 0 m connectat a la vora del fitxer
- omplir_forats():       forats interiors sense dades -> mitjana dels veins valids
- submostrejar_blocs():  reduir la resolucio fent la mitjana de blocs factor x factor
- gradient():            pendents dh/dx i dh/dz (per a les normals) a la resolucio del fitxer
- distancia_costa():     distancia amb signe a la linia de costa (mar > 0, terra < 0)
- carregar_terreny():    tot el que necessita el Terrain, amb cache .npz a data/cache/
"""
import json
import math
import os
import time

import numpy as np
import rasterio
from rasterio.crs import CRS
from scipy import ndimage

DIR_DADES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')  # data/ es a l'arrel del projecte
DIR_MDT = os.path.join(DIR_DADES, 'mdt')       # MDT descarregats (scripts/descarregar_mdt.py)
DIR_CACHE = os.path.join(DIR_DADES, 'cache')   # fitxers generats (no es versionen)
# terrenys del selector: (nom al panell, fitxer, es zona de detall)
TERRENYS = [
    ('Peninsula', os.path.join(DIR_MDT, 'peninsula_200m.tif'), False),
    ('Asturies', os.path.join(DIR_MDT, 'asturias_25m.tif'), False),
    ('Picos', os.path.join(DIR_MDT, 'picos_5m.tif'), True),
    ('Luarca', os.path.join(DIR_MDT, 'luarca_5m.tif'), True),
]
VERSIO_CACHE = 5  # canviar-la si canvia la manera de calcular els derivats (invalida les caches)


def llegir_geotiff(cami):
    """Llegeix un MDT i el deixa net per dibuixar-lo.

    Retorna (alt, transform, crs, mar):
      alt        array float32 d'altituds en metres (fila 0 = nord); el mar val 0
      transform  rasterio.Affine: de (columna, fila) a coordenades del CRS (vora del pixel)
      crs        rasterio.crs.CRS (p. ex. EPSG:25830)
      mar        array bool, True on hi ha mar (o zona sense dades connectada a la vora)
    """
    with rasterio.open(cami) as d:
        alt = d.read(1).astype('f4')
        transform, crs, nodata = d.transform, d.crs, d.nodata

    sense_dades = ~np.isfinite(alt)
    if nodata is not None:
        sense_dades |= alt == nodata

    mar = mascara_mar(alt, sense_dades)
    forats = sense_dades & ~mar
    n_forats = omplir_forats(alt, forats, valid=~sense_dades & ~mar)
    alt[mar] = 0.0
    print(f"  {n_forats} forats interiors omplerts ({forats.sum()} pixels)")
    return alt, transform, crs, mar


def mascara_mar(alt, sense_dades):
    """Mar = zones sense dades o a 0 m que estan connectades a la vora del fitxer.
    Les zones iguals pero tancades dins de terra (forats, rius, embassaments) NO son mar."""
    candidat = sense_dades | (alt == 0)
    etiquetes, _ = ndimage.label(candidat)  # regions connectades (4 veins)
    # etiquetes que toquen alguna de les 4 vores (0 = no candidat)
    vores = np.concatenate([etiquetes[0], etiquetes[-1], etiquetes[:, 0], etiquetes[:, -1]])
    etiquetes_mar = np.unique(vores[vores > 0])
    return np.isin(etiquetes, etiquetes_mar)


def omplir_forats(alt, forats, valid):
    """Omple (in situ) els pixels de `forats` amb la mitjana dels 4 veins valids, repetint-ho
    de fora cap a dins fins que el forat queda ple. Es treballa forat a forat, nomes dins del
    seu rectangle, perque sigui rapid encara que el fitxer sigui gran. Retorna el nombre de forats."""
    etiquetes, n = ndimage.label(forats)
    for i, finestra in enumerate(ndimage.find_objects(etiquetes)):
        # ampliar el rectangle 1 pixel per incloure els veins de la vora del forat
        finestra = tuple(slice(max(s.start - 1, 0), s.stop + 1) for s in finestra)
        a = alt[finestra]                       # vista: modificar 'a' modifica 'alt'
        pendent = etiquetes[finestra] == i + 1
        ok = valid[finestra].copy()
        while pendent.any():
            suma, quants = suma_veins(np.where(ok, a, 0.0)), suma_veins(ok.astype('f4'))
            nous = pendent & (quants > 0)
            if not nous.any():
                break  # no hauria de passar: un forat interior sempre te terra al voltant
            a[nous] = suma[nous] / quants[nous]
            ok |= nous
            pendent &= ~nous
    return n


def suma_veins(x):
    """Suma dels 4 veins (amunt, avall, esquerra, dreta) de cada pixel; fora del array compta 0."""
    p = np.pad(x, 1)
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]


def submostrejar_blocs(alt, mar, factor):
    """Redueix la resolucio fent la mitjana de cada bloc factor x factor.
    - L'altitud es la mitjana nomes de les cel.les de terra del bloc (el mar no la rebaixa).
    - Un bloc es mar si mes de la meitat de les seves cel.les son mar.
    Les files/columnes que sobren al final (si la mida no es multiple de factor) es descarten.
    Retorna (alt, mar) reduits. La nova mida de pixel es factor vegades l'original."""
    if factor == 1:
        return alt, mar
    f = factor
    files, cols = alt.shape[0] // f, alt.shape[1] // f
    blocs = alt[:files * f, :cols * f].reshape(files, f, cols, f)
    terra = ~mar[:files * f, :cols * f].reshape(files, f, cols, f)

    n_terra = terra.sum(axis=(1, 3))
    suma = np.where(terra, blocs, 0.0).sum(axis=(1, 3))
    mar_s = n_terra * 2 < f * f
    alt_s = np.where(mar_s, 0.0, suma / np.maximum(n_terra, 1)).astype('f4')
    return alt_s, mar_s


def gradient(alt, mar, res_m):
    """Pendents de l'altitud a la resolucio del fitxer, sense unitats (metres per metre).
    Retorna un array (files, cols, 2) float32 amb (dh/dx, dh/dz):
      x = est  (columnes creixents)
      z = sud  (files creixents, perque la fila 0 es el nord)
    Al mar el pendent es 0 (aigua plana)."""
    dh_dz, dh_dx = np.gradient(alt, res_m)  # np.gradient torna primer l'eix de files
    grad = np.dstack([dh_dx, dh_dz]).astype('f4')
    grad[mar] = 0.0
    return grad


def distancia_costa(mar, res_m):
    """Distancia amb signe a la linia de costa, en km: positiva al mar, negativa a terra.
    La costa (valor 0) queda just a la vora entre un pixel de mar i un de terra.
    Com que varia suaument, en filtrar-la a la GPU la costa surt llisa i sense escales."""
    if not mar.any():
        return np.full(mar.shape, -1000.0, dtype='f4')  # sense mar: tot es terra lluny de la costa
    dins_mar = ndimage.distance_transform_edt(mar)     # pixels de mar: distancia a la terra mes propera
    dins_terra = ndimage.distance_transform_edt(~mar)  # pixels de terra: distancia al mar mes proper
    d = np.where(mar, dins_mar - 0.5, -(dins_terra - 0.5))
    # la mascara es de pixels i la costa fa escales: un suavitzat de ~2 pixels arrodoneix els esglaons
    d = ndimage.gaussian_filter(d.astype('f4'), sigma=2.0)
    return (d * res_m / 1000.0).astype('f4')


def mida_graella(cols, files, max_vertexs):
    """Vertexs de la graella (n_cols, n_files): com a maxim max_vertexs per costat, amb la proporcio del terreny."""
    escala = min(1.0, max_vertexs / max(cols, files))
    return max(2, round(cols * escala)), max(2, round(files * escala))


def carregar_terreny(cami, max_textura, max_vertexs):
    """Prepara tot el que necessita el Terrain a partir d'un MDT. La primera vegada ho calcula i
    ho desa a data/cache/<nom>.derivats.npz; les seguents ho llegeix d'alla (molt mes rapid).
    La cache es refa sola si canvia el fitxer d'origen, els parametres o VERSIO_CACHE.

    Retorna un dict amb:
      alt          altituds (m), float32, potser reduides per cabre en una textura
      grad         pendents (dh/dx, dh/dz), float16
      costa        distancia amb signe a la costa (km), float16
      alt_vertexs  altituds mitjanades per blocs, com les llegeix la graella (nivell de mipmap)
      ecl_efem, ecl_ombres  overlays de l'eclipsi reprojectats al terreny (eclipse_data.py);
                   arrays buits si no hi ha el dataset de l'eclipsi
      res_m, transform, crs, n_cols, n_files (vertexs de la graella), lod_vertexs
    """
    from . import eclipse_data  # aqui dins: data_io tambe es pot fer servir sense les dades de l'eclipsi
    t0 = time.time()
    st = os.stat(cami)
    clau = dict(versio=VERSIO_CACHE, fitxer=os.path.abspath(cami), mida=st.st_size, mtime=st.st_mtime,
                max_textura=max_textura, max_vertexs=max_vertexs,
                eclipsi=[os.stat(f).st_mtime for f in eclipse_data.FITXERS] if eclipse_data.disponible() else None)
    nom = os.path.splitext(os.path.basename(cami))[0]
    cami_cache = os.path.join(DIR_CACHE, nom + '.derivats.npz')

    if os.path.exists(cami_cache):
        with np.load(cami_cache) as z:
            if json.loads(str(z['clau'])) == clau:
                d = {k: z[k] for k in ('alt', 'grad', 'costa', 'alt_vertexs', 'ecl_efem', 'ecl_ombres')}
                meta = json.loads(str(z['meta']))
                d.update(meta)
                d['transform'] = rasterio.Affine(*meta['transform'])
                d['crs'] = CRS.from_wkt(meta['crs'])
                print(f"Llegit de la cache {cami_cache} ({time.time() - t0:.1f} s)")
                return d
        print(f"La cache {cami_cache} no correspon al fitxer actual: es torna a calcular")

    print(f"Llegint {cami}")
    alt, transform, crs, mar = llegir_geotiff(cami)
    files, cols = alt.shape
    res_m = transform.a
    terra = alt[~mar]
    print(f"  CRS {crs}  origen UTM (NO) x={transform.c:.1f} y={transform.f:.1f}")
    print(f"  mida {cols} x {files} px de {res_m:g} m ({cols * res_m / 1000:.1f} x {files * res_m / 1000:.1f} km)")
    print(f"  altituds de terra {terra.min():.1f} .. {terra.max():.1f} m, mar {mar.mean() * 100:.1f}%")

    factor = math.ceil(max(files, cols) / max_textura)
    if factor > 1:
        alt, mar = submostrejar_blocs(alt, mar, factor)
        res_m *= factor
        transform = transform * rasterio.Affine.scale(factor)
        files, cols = alt.shape
        print(f"  AVIS: no cap en una textura de {max_textura} px; reduit {factor}x{factor} "
              f"-> {cols} x {files} px de {res_m:g} m")

    n_cols, n_files = mida_graella(cols, files, max_vertexs)
    lod_vertexs = max(0.0, math.log2(cols / n_cols))
    # mitjana per blocs com el nivell de mipmap que llegeix el vertex shader (la geometria dibuixada)
    bloc = 2 ** round(lod_vertexs)
    fb, cb = files // bloc, cols // bloc
    d = dict(alt=alt,
             grad=gradient(alt, mar, res_m).astype('f2'),
             costa=distancia_costa(mar, res_m).astype('f2'),
             alt_vertexs=alt[:fb * bloc, :cb * bloc].reshape(fb, bloc, cb, bloc).mean(axis=(1, 3)).astype('f4'))
    if eclipse_data.disponible():
        t1 = time.time()
        d['ecl_efem'], d['ecl_ombres'] = eclipse_data.reprojectar_a_graella(transform, crs, alt.shape)
        print(f"  dades de l'eclipsi reprojectades a {d['ecl_ombres'].shape[1]} x {d['ecl_ombres'].shape[0]} px "
              f"({time.time() - t1:.1f} s)")
    else:
        print("  AVIS: no hi ha el dataset de l'eclipsi a data/eclipsi2026/: sense overlays")
        d['ecl_efem'], d['ecl_ombres'] = np.zeros((0, 0, 4), 'f2'), np.zeros((0, 0), 'u1')
    meta = dict(res_m=res_m, transform=list(transform)[:6], crs=crs.to_wkt(),
                n_cols=n_cols, n_files=n_files, lod_vertexs=lod_vertexs)

    os.makedirs(DIR_CACHE, exist_ok=True)
    tmp = cami_cache + '.tmp.npz'  # primer amb un altre nom: si es talla, no queda una cache a mitges
    np.savez(tmp, clau=json.dumps(clau), meta=json.dumps(meta), **d)
    os.replace(tmp, cami_cache)
    print(f"  derivats desats a {cami_cache} ({time.time() - t0:.1f} s)")

    d.update(meta)
    d['transform'], d['crs'] = transform, crs
    return d
