"""
Mosaic d'imatges aeries: la fotografia del PNOA (i Sentinel-2 on el PNOA no en te) com a color del terreny i
del globus, carregada a mesura que es necessita (dades/teselles.py baixa i desa les teselles).

Com un "clipmap": per a cada nivell de zoom de Web Mercator hi ha una finestra de 8 x 8 teselles (2048 x 2048 px)
centrada a sota de la camera, en una capa d'una textura de capes (TextureArray). Hi ha N_NIVELLS nivells actius,
del mes detallat que demana l'altura de la camera (zoom_fi) cap avall: cada un cobreix el doble que l'anterior,
de manera que a prop hi ha detall i lluny, la mateixa resolucio en pantalla amb menys memoria.
  - Cada zoom z va sempre a la capa z mod N_NIVELLS: quan la camera puja o baixa i entra un nivell nou, nomes
    s'omple aquella capa (la resta es conserva).
  - Dins de la capa, la tesella (x, y) va a la posicio (x mod 8, y mod 8) ("en anell"): quan la camera es mou
    una tesella, nomes cal escriure la fila o columna nova.
  - Per a cada nivell, 64 bits diuen quines posicions ja tenen la tesella que toca (mosaic_valides). Les que no
    (s'estan baixant) es completen amb el nivell seguent, menys detallat: la imatge sempre es continua i es va
    afinant, com a Google Earth.
  - Mipmaps: cada tesella arriba amb les seves reduccions (256, 128, ..., 1 px) i s'escriuen al nivell de mipmap
    corresponent (glTexSubImage3D de PyOpenGL: moderngl no permet escriure un nivell de mipmap d'una capa).
El shader (shaders/mosaic.glsl) tria per a cada pixel el nivell amb un texel per pixel de pantalla.
Memoria a la GPU: 12 capes x 2048^2 x 4 bytes x 4/3 (mipmaps) = ~270 MB.
Pujar teselles te un pressupost per fotograma (TEMPS_PUJADA_S): una arribada massiva no talla el moviment.
"""
import math
import time

import moderngl as mgl
import numpy as np
import OpenGL
OpenGL.ERROR_CHECKING = False   # PyOpenGL comprova glGetError despres de cada crida: aqui nomes en fem de pujada
from OpenGL import GL           # (glTexSubImage3D) i la comprovacio costava mes que la mateixa crida

from dades import geodesia, teselles
from dades.teselles import MIDA, NIVELLS_MIP

N_NIVELLS = 12          # nivells de zoom actius alhora (capes de la textura)
TESELLES = 8            # teselles per costat de cada finestra (com shaders/mosaic.glsl)
TEMPS_PUJADA_S = 0.004  # temps maxim per fotograma pujant teselles a la GPU
REVISIO_S = 0.5         # cada quant es tornen a demanar les teselles que falten (si la finestra no ha canviat)


class Mosaic:
    def __init__(self, app):
        self.app, self.ctx = app, app.ctx
        costat = TESELLES * MIDA
        self.textura = self.ctx.texture_array((costat, costat, N_NIVELLS), 4)
        self.textura.build_mipmaps(0, NIVELLS_MIP - 1)     # reserva els nivells de mipmap (fins a 1 px per tesella)
        self.textura.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textura.anisotropy = 16.0
        self.textura.repeat_x = self.textura.repeat_y = True   # les finestres son "en anell"
        self.actiu = True                   # el panell ho pot desactivar (es torna als colors d'abans)
        self.zoom_fi = 0
        self.finestres = {}                 # zoom -> (x0, y0): tesella de la cantonada nord-oest de la finestra
        self.contingut = {}                 # (capa, posicio x, posicio y) -> (z, x, y) de la tesella que hi ha
        self.cam_merc = (0.0, 0.0)
        self.cam_asinh = 0.0
        self.ultima_revisio = -1e9
        self.bits = {}                      # zoom -> bits de mosaic_valides (es tornen a calcular si canvien)
        self._uniforms = self.uniforms()
        self.descarregador = teselles.Descarregador(self.vigent)

    # ------------------------------------------------------------ quines teselles calen

    def vigent(self, z, x, y):
        """La tesella (z, x, y) encara cal: el seu zoom es actiu i es dins de la finestra (el crida un fil)."""
        f = self.finestres.get(z)
        if f is None:
            return False
        n = 1 << z
        return (x - f[0]) % n < TESELLES and f[1] <= y < f[1] + TESELLES

    def zoom_desitjat(self, alcada_km, lat):
        """El zoom amb un pixel de tesella com un pixel de pantalla a la vertical de la camera."""
        cam = self.app.camera
        _, _, _, alcada_px = self.ctx.viewport
        angle_pixel = math.radians(cam.fov) / max(alcada_px, 1)
        return teselles.zoom_per_resolucio(max(alcada_km, 0.001) * 1000.0 * angle_pixel, lat)

    def actualitzar(self):
        """Cada fotograma, abans de dibuixar: finestres al voltant de la camera, peticions de les teselles que
        falten (dels nivells on la finestra s'ha mogut, i de tots cada REVISIO_S), pujada de les que ja s'han
        preparat i uniforms per als shaders."""
        cam = self.app.camera
        lat, lon, alt = (float(v) for v in geodesia.geodesiques(cam.posicio))
        alcada = alt - self.app.altitud_terra_km(lat, lon)
        x, y = teselles.mercator(lat, lon)
        self.cam_merc = (float(x), float(y))
        self.cam_asinh = math.asinh(math.tan(math.radians(min(max(lat, -85.05112878), 85.05112878))))
        self.zoom_fi = self.zoom_desitjat(alcada, lat)
        finestres = {}
        for z in range(self.zoom_fi, max(self.zoom_fi - N_NIVELLS, -1), -1):
            n = 1 << z
            finestres[z] = (round(x * n) - TESELLES // 2, round(y * n) - TESELLES // 2)
        canviats = [z for z in finestres if finestres[z] != self.finestres.get(z)]
        self.finestres = finestres
        for z in canviats:
            self.bits.pop(z, None)
        if not self.actiu:              # desactivat al panell: no es baixa ni es puja res
            self._uniforms = self.uniforms()
            return
        ara = time.perf_counter()
        if ara - self.ultima_revisio > REVISIO_S:
            self.ultima_revisio = ara
            canviats = list(finestres)
        if canviats:
            self.demanar(canviats)
        self.pujar()
        self._uniforms = self.uniforms()

    def demanar(self, zooms):
        """Demana les teselles de les finestres d'aquests zooms que encara no hi son. Primer les del centre de cada
        finestra i, a igual distancia, les dels nivells menys detallats (es veu de seguida una imatge borrosa que
        s'afina)."""
        z_min = min(self.finestres)
        for z in zooms:
            x0, y0 = self.finestres[z]
            n = 1 << z
            cx, cy = self.cam_merc[0] * n - x0, self.cam_merc[1] * n - y0
            for j in range(TESELLES):
                ty = y0 + j
                if not 0 <= ty < n:
                    continue
                for i in range(TESELLES):
                    tx = (x0 + i) % n
                    if self.contingut.get(self.posicio(z, x0 + i, ty)) == (z, tx, ty):
                        continue
                    distancia = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
                    self.descarregador.demanar((z, tx, ty), distancia + 0.5 * (z - z_min))

    @staticmethod
    def posicio(z, x, y):
        return z % N_NIVELLS, x % TESELLES, y % TESELLES

    def pujar(self):
        """Escriu a la textura les teselles preparades, fins a TEMPS_PUJADA_S per fotograma."""
        t0 = time.perf_counter()
        lligada = False
        while time.perf_counter() - t0 < TEMPS_PUJADA_S:
            preparades = self.descarregador.preparades(1)
            if not preparades:
                break
            z, x, y, nivells = preparades[0]
            if not self.vigent(z, x, y):
                continue
            if not lligada:
                GL.glActiveTexture(GL.GL_TEXTURE0 + 15)     # una unitat que no fa servir cap altre objecte
                GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.textura.glo)
                GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
                lligada = True
            # la mateixa tesella pot ocupar mes d'una posicio si el mon es mes petit que la finestra (z < 3)
            x0 = self.finestres[z][0]
            for i in range(TESELLES):
                if (x0 + i) % (1 << z) != x:
                    continue
                capa, px, py = self.posicio(z, x0 + i, y)
                for nivell, img in enumerate(nivells):
                    m = img.shape[0]
                    GL.glTexSubImage3D(GL.GL_TEXTURE_2D_ARRAY, nivell, px * m, py * m, capa, m, m, 1,
                                       GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img)
                self.contingut[(capa, px, py)] = (z, x, y)
            self.bits.pop(z, None)
        if lligada:
            GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, 0)
            GL.glActiveTexture(GL.GL_TEXTURE0)

    # ------------------------------------------------------------ shaders

    def bits_valides(self, z, x0, y0):
        """64 bits (dos uint32): quines posicions de la capa tenen la tesella de la finestra actual."""
        n = 1 << z
        bits = 0
        for j in range(TESELLES):
            ty = y0 + j
            if not 0 <= ty < n:
                continue
            for i in range(TESELLES):
                capa, px, py = self.posicio(z, x0 + i, ty)
                if self.contingut.get((capa, px, py)) == (z, (x0 + i) % n, ty):
                    bits |= 1 << (py * TESELLES + px)
        return bits & 0xFFFFFFFF, bits >> 32

    def uniforms(self):
        """Valors dels uniforms de mosaic.glsl (es calculen un cop per fotograma i els fan servir tots els shaders)."""
        escala, centre, toro, capa, valides = [], [], [], [], []
        for z in sorted(self.finestres, reverse=True):
            x0, y0 = self.finestres[z]
            n = 1 << z
            escala.append(float(n))
            centre += [self.cam_merc[0] * n - x0, self.cam_merc[1] * n - y0]
            toro += [x0 % TESELLES, y0 % TESELLES]
            capa.append(float(z % N_NIVELLS))
            if z not in self.bits:
                self.bits[z] = self.bits_valides(z, x0, y0)
            valides += self.bits[z]
        falten = N_NIVELLS - len(escala)
        return dict(n=len(escala),
                    escala=np.array(escala + [1.0] * falten, 'f4'),
                    centre=np.array(centre + [0.0] * 2 * falten, 'f4'),
                    toro=np.array(toro + [0.0] * 2 * falten, 'f4'),
                    capa=np.array(capa + [0.0] * falten, 'f4'),
                    valides=np.array(valides + [0] * 2 * falten, 'u4'))

    def aplicar(self, sp, unitat):
        """Lliga la textura a la unitat i escriu els uniforms del mosaic."""
        if 'usar_mosaic' not in sp:
            return
        u = self._uniforms
        sp['usar_mosaic'].value = bool(self.actiu and u['n'] > 0)
        self.textura.use(unitat)
        sp['tex_mosaic'].value = unitat
        sp['mosaic_n'].value = u['n']
        for nom in ('escala', 'centre', 'toro', 'capa', 'valides'):
            if f'mosaic_{nom}' in sp:
                sp[f'mosaic_{nom}'].write(u[nom].tobytes())

    def estat(self):
        """(teselles pendents, baixades de la xarxa, llegides del disc, fallades) per al panell."""
        d = self.descarregador
        return d.pendents(), d.baixades, d.del_disc, d.fallades

    def destroy(self):
        self.descarregador.aturar()
        self.textura.release()
