"""
Els edificis com a obstacles (sense OpenGL): per caminar, per volar a prop del terra i per triar on queden els
ulls de l'observador.

Geometria: cada part d'edifici del Catastro (contorn en EPSG:25830, metres) es un prisma vertical des del terra
fins a la cota de la coberta, igual que es dibuixa (dades/edificis.py). Per tant el problema es pot fer al pla
horitzontal (coordenades UTM): una posicio es dins d'un edifici si el contorn la conte i, si cal tenir en
compte l'altura, si es per sota de la coberta.

- Cos: un cercle de radi RADI_COS_M (caminant) al pla horitzontal. Una posicio es valida si es fora de tots els
  contorns i a RADI o mes de les seves vores.
- Moure's (moure): el desplacament es fa en passos de radi / 2 com a molt, i a cada pas el cercle s'empeny
  fora de les vores que toca (empenyer): la component del moviment cap a la paret desapareix i la paral·lela
  continua (lliscar). Com que cap pas es mes llarg que el radi, el centre no pot arribar a l'altre costat
  d'una paret, encara que el fotograma sigui llarg; i si per algun motiu el resultat quedes dins, el pas no
  es fa. Sense velocitat ni inercia: res no vibra, i a les cantonades el cercle hi llisca.
- Punt exterior (punt_exterior): el lloc mes proper amb un marge a les facanes dins de l'espai obert que
  continua fins a fora d'un quadrat de 300 m (carrers i places), no dins d'un pati tancat. Es fa servir per
  als punts d'observacio que cauen dins d'un edifici i per recuperar la camera si mai hi queda.
"""
import math

import numpy as np
import shapely
from pyproj import Transformer
from shapely.ops import nearest_points

CRS = 'EPSG:25830'
RADI_COS_M = 0.3            # radi del cos caminant (m)
MARGES_EXTERIOR_M = (3.0, 1.5, 0.5)   # marges a les facanes que es proven, de mes comode a mes just
ABAST_EXTERIOR_M = 150.0    # mig costat del quadrat on es busca un punt exterior
ITERACIONS = 6              # empentes per pas (cantonades: una paret i despres l'altra)


class Obstacles:
    def __init__(self, contorns, cota_coberta_m):
        """contorns: array de poligons shapely (EPSG:25830, m); cota_coberta_m: cota de cada coberta (m)."""
        self.contorns = np.asarray(contorns)
        self.coberta = np.asarray(cota_coberta_m, dtype=float)
        self.coberta_max = float(self.coberta.max()) if len(self.coberta) else -1e9
        self.vores = shapely.boundary(self.contorns)
        shapely.prepare(self.contorns)
        self.arbre = shapely.STRtree(self.contorns)
        self.de_latlon = Transformer.from_crs('EPSG:4326', CRS, always_xy=True)
        self.a_latlon = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True)

    # ------------------------------------------------------------ coordenades
    def utm(self, lat, lon):
        return self.de_latlon.transform(lon, lat)

    def latlon(self, x, y):
        lon, lat = self.a_latlon.transform(x, y)
        return lat, lon

    # ------------------------------------------------------------ consultes
    def _properes(self, geom, distancia, alt_m):
        """Parts a menys de `distancia` de geom; amb alt_m, nomes les de coberta mes alta que alt_m."""
        idx = self.arbre.query(geom, predicate='dwithin', distance=distancia)
        if alt_m is not None and len(idx):
            idx = idx[self.coberta[idx] > alt_m]
        return idx

    def dins(self, x, y, alt_m=None):
        """Index de la part que conte (x, y) (la de coberta mes alta), o None. Amb alt_m, nomes si la coberta
        es mes alta que alt_m."""
        idx = self.arbre.query(shapely.Point(x, y), predicate='within')
        if alt_m is not None and len(idx):
            idx = idx[self.coberta[idx] > alt_m]
        return int(idx[np.argmax(self.coberta[idx])]) if len(idx) else None

    def separacio(self, x, y, alt_m=None, abast=5.0):
        """Distancia (m) a la facana mes propera: negativa si el punt es dins d'un edifici; `abast` si no n'hi
        ha cap mes a prop."""
        p = shapely.Point(x, y)
        idx = self._properes(p, abast, alt_m)
        if not len(idx):
            return abast
        d = float(shapely.distance(self.vores[idx], p).min())
        return -d if self.dins(x, y, alt_m) is not None else d

    def empenyer(self, x, y, radi, alt_m=None, anterior=None):
        """Treu el cercle (x, y, radi) de les parets que toca. Retorna (x, y, valid): valid si al final es
        fora de tots els edificis i a radi (menys 1 mm) o mes de les vores."""
        p = np.array([x, y], dtype=float)
        for _ in range(ITERACIONS):
            pt = shapely.Point(*p)
            idx = self._properes(pt, radi, alt_m)
            mogut = False
            for i in idx:
                q = np.asarray(shapely.shortest_line(self.vores[i], pt).coords[0])
                v = p - q
                d = float(np.hypot(*v))
                dins = self.contorns[i].contains(pt)
                if d < 1e-9:                       # just a la vora: s'empeny cap a d'on venia
                    if anterior is None:
                        continue
                    v = np.asarray(anterior, dtype=float) - q
                    d = float(np.hypot(*v))
                    if d < 1e-9:
                        continue
                    dins = False
                if dins:
                    p = q - v / d * radi           # sortir per la vora mes propera
                elif d < radi:
                    p = q + v / d * radi
                else:
                    continue
                mogut, pt = True, shapely.Point(*p)
            if not mogut:
                break
        valid = self.dins(*p, alt_m) is None and self.separacio(*p, alt_m, abast=radi) >= radi - 1e-3
        return p[0], p[1], valid

    def moure(self, x0, y0, x1, y1, radi=RADI_COS_M, alt_m=None):
        """Mou el cercle de (x0, y0) cap a (x1, y1) lliscant per les parets. Retorna (x, y, xoc)."""
        cami = shapely.LineString([(x0, y0), (x1, y1)])
        if not len(self._properes(cami, radi + 0.01, alt_m)):
            return x1, y1, False                    # cap edifici a prop del cami: tal qual
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / (radi / 2)))
        pas = np.array([x1 - x0, y1 - y0]) / n
        p, xoc = np.array([x0, y0], dtype=float), False
        for _ in range(n):
            c = p + pas
            x, y, valid = self.empenyer(*c, radi, alt_m, anterior=p)
            if not valid:
                xoc = True
                break                               # no es fa el pas (mai no queda dins)
            if math.hypot(x - c[0], y - c[1]) > 1e-9:
                xoc = True
            p = np.array([x, y])
        return p[0], p[1], xoc

    def punt_exterior(self, x, y, marges=MARGES_EXTERIOR_M, abast=ABAST_EXTERIOR_M):
        """(x, y, distancia, marge) del punt mes proper a (x, y) a `marge` o mes de totes les facanes, dins de
        l'espai obert que arriba a la vora d'un quadrat de 2 x abast (carrers i places, no patis tancats). Es
        prova cada marge en ordre; None si no se'n troba cap."""
        p = shapely.Point(x, y)
        caixa = shapely.box(x - abast, y - abast, x + abast, y + abast)
        idx = self.arbre.query(caixa)
        for marge in marges:
            ocupat = shapely.union_all(shapely.buffer(self.contorns[idx], marge)) if len(idx) else shapely.Polygon()
            lliure = shapely.difference(caixa, ocupat)
            trossos = [g for g in shapely.get_parts(lliure) if g.intersects(caixa.exterior)]
            if not trossos:
                continue
            obert = shapely.union_all(trossos)
            if obert.contains(p):
                return x, y, 0.0, marge
            q = nearest_points(obert, p)[0]
            return q.x, q.y, float(q.distance(p)), marge
        return None
