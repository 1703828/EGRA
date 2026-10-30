"""
Teselles d'imatge aeria (sense OpenGL): coordenades, descarrega en segon pla i memoria cau al disc.

Les imatges es serveixen en teselles de 256 x 256 pixels de la quadricula Web Mercator (EPSG:3857, la de Google
Maps, OpenStreetMap i el WMTS de l'IGN): al nivell de zoom z, el mon (fins a +-85,05 graus de latitud) es parteix
en 2^z x 2^z teselles. Cada nivell te el doble de resolucio que l'anterior: a z = 19 un pixel fa ~0,3 m a
l'equador (~0,22 m a Catalunya). Coordenades "mercator" (X, Y) entre 0 i 1: X cap a l'est des de la longitud
-180, Y cap al sud des de 85,05 N. La tesella (x, y) del nivell z cobreix X de x/2^z a (x+1)/2^z.

Fonts (data/FONTS.md):
  - PNOA maxima actualitat (IGN, WMTS, CC BY 4.0): Espanya, fins a z = 19. Fora d'Espanya, a zooms baixos, l'IGN
    hi posa un mosaic de satel·lit; on no te res, la tesella surt d'un lila fosc uniforme (SENSE_DADES).
  - Sentinel-2 cloudless 2020 (EOX, WMTS, CC BY-NC-SA 4.0, us no comercial): tot el mon, 10 m per pixel. Omple
    els pixels SENSE_DADES del PNOA (mar obert, Portugal i Franca a alguns zooms) i es l'unica font per sota de
    ZOOM_MIN_PNOA (de lluny). Per sobre de ZOOM_MAX_EOX es fa servir la tesella d'aquell zoom, ampliada.
Cada tesella baixada es desa a DIR_TESELLES/<font>/<z>/<x>/<y>.jpg: el segon cop es llegeix del disc.

Les descarregues es fan en fils (Descarregador): el bucle de dibuix mai espera la xarxa; nomes recull les
teselles ja preparades (descodificades i amb les reduccions per als mipmaps).
"""
import math
import os
import queue
import threading
import time

import numpy as np

from .data_io import DIR_CACHE

MIDA = 256                      # pixels per costat d'una tesella
ZOOM_MAX = 19                   # el mes detallat que es demana (PNOA: ~0,22 m per pixel a Catalunya)
ZOOM_MAX_EOX = 15               # Sentinel-2 te 10 m per pixel: per sobre, s'amplia la tesella de z = 15
ZOOM_MIN_PNOA = 12              # per sota (de ~40 m per pixel cap amunt), Sentinel-2 a tot arreu: el PNOA a
                                # aquests zooms barreja mosaics (mon saturat, mar gris a z = 9-10, mar buit a z = 11)
                                # i, al canviar de nivell, el color del mar feia un cercle al voltant de la camera
NIVELLS_MIP = 9                 # reduccions de cada tesella: 256, 128, ..., 1 pixel
CIRCUMFERENCIA_M = 40075016.686 # equador (m): a z = 0, la tesella fa aixo d'ample
SENSE_DADES = np.array([32, 26, 38])  # color del PNOA on no hi ha imatge
DIR_TESELLES = os.path.join(DIR_CACHE, 'teselles')
FONTS = {
    'pnoa': 'https://www.ign.es/wmts/pnoa-ma?layer=OI.OrthoimageCoverage&style=default&tilematrixset='
            'GoogleMapsCompatible&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/jpeg'
            '&TileMatrix={z}&TileCol={x}&TileRow={y}',
    'eox': 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg',
}
AGENT = 'EGRA-eclipsi-2026 (projecte universitari)'
FILS = 8                        # descarregues alhora
ESPERA_ERROR_S = 30.0           # una tesella que no s'ha pogut baixar no es torna a demanar fins d'aqui a tant


def mercator(lat, lon):
    """Latitud i longitud (graus, WGS84) -> (X, Y) de Web Mercator entre 0 i 1 (Y cap al sud). Accepta arrays."""
    fi = np.radians(np.clip(lat, -85.05112878, 85.05112878))
    return (np.asarray(lon) + 180.0) / 360.0, 0.5 - np.arcsinh(np.tan(fi)) / (2.0 * math.pi)


def zoom_per_resolucio(metres_per_pixel, lat):
    """El zoom (enter, 0..ZOOM_MAX) amb pixels de tesella iguals o mes petits que metres_per_pixel a la latitud lat."""
    mida_pixel_z0 = CIRCUMFERENCIA_M * math.cos(math.radians(lat)) / MIDA
    z = math.ceil(math.log2(mida_pixel_z0 / max(metres_per_pixel, 1e-3)))
    return int(min(max(z, 0), ZOOM_MAX))


def cami_cau(font, z, x, y):
    return os.path.join(DIR_TESELLES, font, str(z), str(x), f'{y}.jpg')


def llegir(font, z, x, y, sessio):
    """Bytes JPEG de la tesella (del disc o, si no hi es, de la xarxa i es desa). Llanca una excepcio si falla."""
    cami = cami_cau(font, z, x, y)
    if os.path.exists(cami):
        with open(cami, 'rb') as f:
            return f.read()
    r = sessio.get(FONTS[font].format(z=z, x=x, y=y), timeout=15, headers={'User-Agent': AGENT})
    r.raise_for_status()
    if not r.headers.get('Content-Type', '').startswith('image/'):
        raise IOError(f'{font} {z}/{x}/{y}: resposta {r.headers.get("Content-Type")}')
    os.makedirs(os.path.dirname(cami), exist_ok=True)
    temporal = f'{cami}.{threading.get_ident()}.tmp'      # dos fils no poden deixar un fitxer a mitges
    with open(temporal, 'wb') as f:
        f.write(r.content)
    os.replace(temporal, cami)
    return r.content


def descodificar(dades):
    from io import BytesIO
    from PIL import Image
    return np.asarray(Image.open(BytesIO(dades)).convert('RGB'))


def tesella_eox(z, x, y, sessio):
    """Tesella de Sentinel-2 (RGB); per sobre de ZOOM_MAX_EOX, el tros corresponent de la de z = 15 ampliat."""
    if z <= ZOOM_MAX_EOX:
        return descodificar(llegir('eox', z, x, y, sessio))
    d = z - ZOOM_MAX_EOX
    pare = descodificar(llegir('eox', ZOOM_MAX_EOX, x >> d, y >> d, sessio))
    n = MIDA >> d                                            # pixels del pare que corresponen a aquesta tesella
    i, j = (x & ((1 << d) - 1)) * n, (y & ((1 << d) - 1)) * n
    from PIL import Image
    tros = Image.fromarray(np.ascontiguousarray(pare[j:j + max(n, 1), i:i + max(n, 1)]))
    return np.asarray(tros.resize((MIDA, MIDA), Image.BILINEAR))


def tesella(z, x, y, sessio):
    """Imatge RGB (MIDA x MIDA) de la tesella: el PNOA i, als pixels on el PNOA no te imatge, Sentinel-2. Per
    sota de ZOOM_MIN_PNOA, nomes Sentinel-2."""
    if z < ZOOM_MIN_PNOA:
        return tesella_eox(z, x, y, sessio)
    rgb = descodificar(llegir('pnoa', z, x, y, sessio))
    # pixels sense dades: el color lila del PNOA (amb marge per la compressio JPEG)
    buit = np.abs(rgb.astype(np.int16) - SENSE_DADES).sum(axis=-1) < 14
    if buit.mean() > 0.002:
        from scipy import ndimage
        # les ombres molt fosques de la foto poden tenir aquest mateix color en punts solts: nomes compten les
        # zones sense imatge de 7 x 7 px o mes (les reals son blocs grans), i la seva vora, tenyida pel JPEG
        buit = ndimage.binary_opening(buit, iterations=3)
        buit = ndimage.binary_dilation(buit, iterations=2)
        rgb = np.where(buit[..., None], tesella_eox(z, x, y, sessio), rgb)
    return rgb


def reduccions(rgb):
    """Les NIVELLS_MIP versions de la tesella (RGBA, de 256 a 1 pixel) per als nivells de mipmap: cada una, la
    mitjana de 2 x 2 pixels de l'anterior (el mateix que faria glGenerateMipmap dins d'una tesella)."""
    a = np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]).astype(np.float32)
    nivells = []
    for _ in range(NIVELLS_MIP):
        nivells.append(np.ascontiguousarray(np.round(a).astype(np.uint8)))
        if a.shape[0] > 1:
            a = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
    return nivells


class Descarregador:
    """Prepara teselles en FILS fils. demanar() posa una tesella a la cua (la de prioritat mes petita va primer);
    abans de comencar-la, el fil pregunta a vigent(z, x, y) si encara cal (la camera s'ha pogut moure). Les
    preparades (z, x, y, reduccions) es recullen amb preparades(). Si la xarxa falla, la tesella es pot tornar a
    demanar passats ESPERA_ERROR_S segons."""

    def __init__(self, vigent, fils=FILS):
        self.vigent = vigent
        self.cua = queue.PriorityQueue()
        self.fetes = queue.Queue()
        self.en_curs = set()           # demanades i no recollides
        self.errors = {}               # tesella -> temps de l'ultim error
        self.bloqueig = threading.Lock()
        self.n = 0                     # comptador: desempata la prioritat (ordre d'arribada)
        self.baixades = self.del_disc = self.fallades = 0
        self.actiu = True
        self.fils = [threading.Thread(target=self.treballar, daemon=True) for _ in range(fils)]
        for f in self.fils:
            f.start()

    def demanar(self, clau, prioritat):
        with self.bloqueig:
            if clau in self.en_curs or time.time() - self.errors.get(clau, -1e9) < ESPERA_ERROR_S:
                return
            self.en_curs.add(clau)
            self.n += 1
            self.cua.put((prioritat, self.n, clau))

    def pendents(self):
        return len(self.en_curs)

    def treballar(self):
        import requests
        sessio = requests.Session()        # una connexio per fil (es reutilitza: mes rapid)
        while self.actiu:
            try:
                _, _, clau = self.cua.get(timeout=0.5)
            except queue.Empty:
                continue
            z, x, y = clau
            if not self.vigent(z, x, y):
                with self.bloqueig:
                    self.en_curs.discard(clau)
                continue
            al_disc = os.path.exists(cami_cau('pnoa', z, x, y))
            try:
                nivells = reduccions(tesella(z, x, y, sessio))
            except Exception:
                with self.bloqueig:
                    self.errors[clau] = time.time()
                    self.en_curs.discard(clau)
                    self.fallades += 1
                continue
            with self.bloqueig:
                if al_disc:
                    self.del_disc += 1
                else:
                    self.baixades += 1
            self.fetes.put((z, x, y, nivells))

    def preparades(self, maxim):
        """Fins a maxim teselles ja preparades (z, x, y, reduccions). Les treu de la llista de demanades."""
        sortida = []
        while len(sortida) < maxim:
            try:
                t = self.fetes.get_nowait()
            except queue.Empty:
                break
            sortida.append(t)
            with self.bloqueig:
                self.en_curs.discard(t[:3])
        return sortida

    def aturar(self):
        self.actiu = False
