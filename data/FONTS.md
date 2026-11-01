# Fonts de les dades

D'on surt cada fitxer de `data/`, amb quina llicència i com es torna a obtenir. Les comandes
s'executen des de l'arrel del repositori amb l'entorn `egra`.

## Relleu (MDT) — `data/mdt/`

| Fitxer | Zona | Resolució | CRS | Al Git | Com es reprodueix |
|---|---|---|---|---|---|
| `peninsula_200m.tif` | lat 35,9–43,9, lon −9,5–3,4 | 200 m | EPSG:25830 | Sí | `python scripts/descarregar_mdt.py peninsula` |
| `picos_5m.tif` | 20 × 20 km centrats a 43,262, −4,949 | 5 m | EPSG:25830 | Sí | `python scripts/descarregar_mdt.py picos` |
| `asturias_25m.tif` | Astúries | 25 m | EPSG:25830 | Sí | `python scripts/descarregar_mdt.py asturias` (no el fa servir el programa; es retirarà) |
| `luarca_5m.tif` | 20 × 20 km centrats a 43,54, −6,54 | 5 m | EPSG:25830 | Sí | `python scripts/descarregar_mdt.py luarca` (no el fa servir el programa; es retirarà) |
| `zones/vic_5m.tif` | 20 × 20 km centrats a 41,9302, 2,2546 | 5 m | EPSG:25830 | No | `python scripts/descarregar_mdt.py vic` |
| `zones/escala_5m.tif` | 20 × 20 km centrats a 42,1250, 3,1330 | 5 m | EPSG:25830 | No | `python scripts/descarregar_mdt.py escala` |
| `zones/valles_5m.tif` | lat 41,39–41,63, lon 2,00–2,36 (31,7 × 28,5 km) | 5 m | EPSG:25830 | No | `python scripts/descarregar_mdt.py valles` |
| `llocs/lloc_<x>_<y>_5m.tif` | 6 × 6 km centrats al punt (x, y) en EPSG:25830: x i y múltiples de 3 km (quadrícula; els antics, del doble clic, arrodonits a 100 m) | 5 m | EPSG:25830 | No | el programa, en navegar o triar un punt (`dades/llocs.py`, `basecode/detall.py`) |

- **Font:** servei WCS de models digitals del terreny de l'IGN, `https://servicios.idee.es/wcs-inspire/mdt`
  (cobertures `Elevacion25830_200`, `_25` i `_5`), demanat en format ArcGrid per conservar els decimals.
- **Llicència:** CC BY 4.0. Atribució: "MDT © Instituto Geográfico Nacional".
- **Cobertura:** només Espanya. Portugal, França i el mar valen 0 m: el programa no hi dibuixa relleu
  i hi deixa veure el globus.
- Les altituds són sobre el geoide (nivell del mar); el programa les posa sobre l'el·lipsoide WGS84
  sense corregir l'ondulació del geoide (~50 m a Espanya).
- `data/mdt05/PNOA_MDT05_ETRS89_HU30_0011_LID.tif`: fulla 0011 original del MDT05 (CNIG), d'exemple.
- Els MDT nous són a `data/mdt/zones/`, ignorada pel Git (tasca 4.1 del pla). Les zones catalanes es
  van descarregar el 22/10/2026 en EPSG:25830, el mateix CRS que la península: el servei les reprojecta
  des del fus 31, i així totes les zones encaixen amb la península per coordenades UTM.
- Els **llocs** (`data/mdt/llocs/`, ignorada pel Git) els baixa el programa en segon pla quan la càmera s'acosta
  a menys de 15 km d'un lloc d'Espanya sense relleu de 5 m (o quan s'hi volen edificis i no n'hi ha): una sola
  petició al mateix WCS (`dades/mdt_wcs.py`). Els centres són a una quadrícula de 3 km: tornar al mateix lloc fa
  servir el mateix fitxer. `lloc_<x>_<y>.json` hi desa la font, la data i les etapes fetes. Com a molt 6 llocs; els
  que fa més temps que no es fan servir s'esborren sols (es tornen a baixar si cal).

## Eclipsi (CNIG) — `data/eclipsi2026/`

- `10bandas2026_3857_COG.tiff`, `terrain_shadows_2026_3857_….tif` i `Eclipses_2026.gpkg`: paquet de
  dades de l'eclipsi del 12/08/2026 del CNIG (descàrrega manual del Centre de Descàrregues).
  Contingut i convencions: `data/eclipsi2026/LLEGENDA.md` i `doc/Description_eclipses.pdf`.
- **Llicència:** CC BY 4.0. Atribució: "Official astronomical information provided by the National
  Geographic Institute based on calculations made by the National Astronomical Observatory".

## Posicions del Sol i la Lluna — `data/efemerides/`

- `horizons_sol_lluna_20260812.csv` (44 kB, al Git): posicions geocèntriques del Sol i la Lluna en km,
  sistema ICRF, corregides pel temps de la llum, cada minut del 12/08/2026 de 14:00 a 21:30 TU.
- **Font:** JPL Horizons (NASA/JPL), `https://ssd.jpl.nasa.gov/horizons/`, descarregat el 22/10/2026.
- `horizons_sol_lluna_20270802.csv` (36 kB) i `horizons_sol_lluna_20280126.csv` (40 kB, al Git): el mateix
  per al 02/08/2027 (de 06:00 a 12:00 TU) i el 26/01/2028 (de 13:00 a 19:30 TU), descarregats el 30/10/2026.
- **Com es reprodueix:** `python scripts/descarregar_efemerides.py [2026|2027|2028]` (intervals a
  `dades/eclipsis.py`).
- **Ús:** dades públiques de NASA/JPL.

## Edificis (Catastro INSPIRE) — `data/edificis/` (no al Git)

- **Font:** Dirección General del Catastro, servei de descàrrega ATOM INSPIRE del conjunt *Buildings*
  (<https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml>), un ZIP per municipi amb
  els GML d'edificis, parts d'edifici i altres construccions. Descarregat el 26/10/2026. Les versions de les
  parts van del 2001 al 2026 (camp `beginLifespanVersion`).
- **Llicència:** dades obertes del Catastro, ús lliure amb citació de la font ("Dirección General del
  Catastro").
- **Contingut que fem servir:** les **parts d'edifici** (`BuildingPart`): contorn (precisió horitzontal
  declarada de 0,1 m) i nombre de plantes sobre rasant (`numberOfFloorsAboveGround`). **No hi ha l'altura en
  metres:** l'estimem amb plantes × 3,0 m (`dades/edificis.py`).
- **CRS:** EPSG:25831 a Catalunya i EPSG:25830 a Picos; es reprojecta a EPSG:25830 (el del terreny): canvi de
  fus UTM dins del mateix datum ETRS89.
- **Zones:** les parts a menys de 2 km dels punts d'observació. Vallès (UAB, Cerdanyola i Montmeló, un sol
  fitxer): 49.797 parts de 13 municipis (Cerdanyola, Sant Cugat, Barberà, Badia, Sabadell, Ripollet, Montcada,
  Montmeló, Montornès, Parets, Mollet, Granollers, la Llagosta; alguns hi aporten 0 parts). Vic: 16.987 parts
  (Vic, Gurb, Calldetenes, Santa Eugènia de Berga). L'Escala: 15.091. Picos: **0** (cap edifici a menys de
  2 km del punt; s'han comprovat Posada de Valdeón, Camaleño i Cabrales).
- **Com es reprodueix:** `python scripts/descarregar_edificis.py` (o amb el nom d'una zona: `valles`, `vic`,
  `escala`, `picos`). Baixa els ZIP a `data/edificis/catastro/` (~45 MB), desa `data/edificis/<zona>.gpkg` i la
  malla a `data/cache/edificis_<zona>.npz`.
- **Llocs (en navegar o triar un punt, `dades/llocs.py` i `dades/catastro.py`):** les parts d'edifici de la cel·la
  de 3 × 3 km del lloc (els antics, del doble clic: 2 × 2 km al voltant del punt). Els municipis que el toquen es busquen als canals ATOM (el general, una
  entrada per gerència amb el seu rectangle, i el de cada gerència, una entrada per municipi), que es desen a
  `data/edificis/catastro/`. Els ZIP dels municipis s'esborren després de llegir-los (si no hi eren abans); es
  desa `data/edificis/lloc_<x>_<y>.gpkg`. Navarra i el País Basc no hi són (cadastres propis). El servei WFS per
  rectangle (`https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx`) s'ha descartat: com a molt ~1 km² per petició i
  2,5 min per 1 km² del centre de Manresa (24 MB), contra 20 s per al ZIP de tot el municipi (6,6 MB); comprovat
  el 30/10/2026.
- **Altures:** primer s'estimen (plantes × 3 m) i, quan es veuen, es mesuren amb les alçàries LiDAR (secció
  següent). El 26/10 es va escriure aquí que el MDS normalitzat de l'IGN no era accessible (el Centre de
  Descàrregues no responia); el 31/10/2026 s'ha trobat el seu servei WCS, que sí que funciona.
- **Referència independent per a la validació:** OpenStreetMap (contorns i `building:levels`, © col·laboradors
  d'OpenStreetMap, ODbL), consultat amb l'API Overpass el 26/10/2026 (400 m al voltant de la UAB;
  `data/edificis/osm_uab.json`).

## Alçàries mesurades (models LiDAR normalitzats) — `data/alcaries/` (no al Git)

Altura sobre el terra dels edificis i de la vegetació, per a les altures dels edificis i el mapa de visibilitat de
detall (`dades/alcaries.py`). Es demanen per cel·les de 3 × 3 km (la quadrícula dels llocs), a mesura que la càmera
s'hi acosta, i es desen a `data/alcaries/cel_<x>_<y>_alcaria.npz` (float16, comprimit; 1–15 MB per cel·la).

| Font | Servei i cobertura | Resolució i data | Llicència | Ús |
|---|---|---|---|---|
| ICGC, *Model d'alçàries* (LiDAR territorial) | Un sol GeoTIFF de Catalunya (98 GB) en format COG: <https://datacloud.icgc.cat/datacloud/model-alcaries/tif_unzip/model-alcaries-lidar-catalunya-1m-2021-2023.tif>, llegit **per finestres** amb peticions HTTP de rang (GDAL `/vsicurl/`): 2 × 2 km en ~15 s, sense baixar el fitxer. EPSG:25831, sense dades −9999. Fora de Catalunya, tot sense dades | 1 m, vols 2021–2023. Alçada màxima de qualsevol objecte a cada metre (no separa edificis i arbres) | CC BY 4.0 (ICGC) | Catalunya |
| IGN/CNIG, *MDS normalizado* (PNOA-LiDAR, 1a cobertura) | WCS <https://wcs-mds.idee.es/mds>, cobertures `mdsn_e025` (edificació) i `mdsn_v025` (vegetació), EPSG:3042 (els números de 25830). Format ArcGrid (amb decimals; `image/tiff` dona enters). 3 × 3 km en ~25 s per cobertura | 2,5 m, vols 2008–2015 (segons la zona) | CC BY 4.0 scne.es (`AccessConstraints`; `Fees`: no s'hi apliquen condicions) | Resta d'Espanya |

- **Consultat** el 31/10/2026 (GetCapabilities i DescribeCoverage de l'IGN; llistat del *datacloud* de l'ICGC).
- **Altura d'una part:** percentil 90 de l'alçària dins del contorn del Catastro (reduït 0,5–1 m), si més de la
  meitat de les cel·les tenen objecte (> 1,5 m); si no, l'estimació, marcada com a tal.
- **Comprovació** (`python scripts/validar_alcaries.py`, 1.078 parts a 2 × 2 km de la UAB, 31/10/2026): el model de
  l'ICGC contra el núvol de punts del mateix vol (secció següent), diferència mediana +0,10 m (error absolut mitjà
  0,9 m); l'IGN contra l'ICGC (dues fonts), −0,48 m (1,6 m); l'estimació per plantes queda 2–3 m per sota.
- **Limitacions:** l'IGN pot tenir 10–15 anys (edificis nous o enderrocats); a 2,5 m els patis i els carrers
  estrets es barregen; l'ICGC no distingeix un arbre d'un edifici. Ceuta i Melilla no tenen LiDAR. Navarra i el
  País Basc tenen MDSn, però no edificis al Catastro estatal.
- **Superfície per al mapa** (`data/alcaries/cel_<x>_<y>_{superficie,ulls}_25830.tif` i `.json`): terra (MDT de
  5 m del lloc, bilineal) + alçària, a 2 m (ICGC, cada cel·la pren l'objecte més alt) o 2,5 m (IGN).

## Noms de lloc — `data/cache/noms/` (no al Git)

- **Nucli de població més proper:** Nomenclàtor Geogràfic Bàsic d'Espanya (NGBE) de l'IGN, WFS INSPIRE
  <https://www.ign.es/wfs-inspire/ngbe>, capa `GN:NamedPlace`, filtrada als tipus de població (capital de
  municipi, entitat singular, nucli de població, capital d'EATIM, entitat col·lectiva). CC BY 4.0 (ign.es). Es
  desa per cel·les de 0,1° (`ngbe_<i>_<j>.json`).
- **Municipi (i població de l'adreça):** geocodificador invers de CartoCiudad (IGN),
  <https://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode?lat=..&lon=..>. CC BY 4.0 (scne.es). Si
  l'adreça més propera (a menys de 300 m) pertany a un nucli, aquell és el nucli del punt ("dins de València").
  En camp obert pot no tornar res (Picos). Consultats el 31/10/2026.

## LiDAR de l'ICGC, núvol de punts (altures mesurades) — `data/lidar/` (no al Git)

- **Font:** Institut Cartogràfic i Geològic de Catalunya (ICGC), *LiDAR territorial* v3r1, 3a cobertura
  (vols 2021–2023): núvol de punts LAS 1.4 classificat segons l'ASPRS, ≥ 8 punts/m², fulls d'1 × 1 km en LAZ,
  EPSG:25831. Pàgina: <https://www.icgc.cat/en/Geoinformation-and-Maps/Data-and-products/Elevations/Territorial-elevations/Territorial-LiDAR>.
  Índex de fulls: <https://datacloud.icgc.cat/datacloud/lidar-territorial/json/lidar-territorial-tall.json>;
  fitxers a `https://datacloud.icgc.cat/datacloud/lidar-territorial/laz_unzip/full10km<ID10K>/`.
- **Llicència:** CC BY 4.0 (ICGC). Atribució: "Geoinformació de l'Institut Cartogràfic i Geològic de Catalunya".
- **Què es guarda:** cada full (280–470 MB) es baixa, es converteix en rasters d'1 m i s'esborra. Rasters
  (`<zona>_mds_1m.tif`, `_terra_1m.tif`, `_edificis_1m.tif`, EPSG:25831, sense reprojectar): la cota més alta
  dels punts que no són soroll (superfície: edificis, arbres i terra), la mitjana dels punts de terra (classe 2) i
  la més alta dels punts d'edifici (classe 6). `<zona>.json`: fulls, URL, mides, punts i data.
- **Zona:** UAB, 3 × 3 km centrats a la plaça Cívica (9 fulls, ~3 GB baixats d'un en un), descarregada el
  30/10/2026 amb autorització de l'equip (D81).
- **Com es reprodueix:** `python scripts/descarregar_lidar.py uab` (cal `laspy` i `lazrs`, a `requirements.txt`).

## Comprovació externa (NASA) — `data/nasa/`

- `circumstancies_nasa.csv` (2 kB, al Git): circumstàncies locals de l'eclipsi (tipus, magnitud,
  enfosquiment, C1–C4 i màxim en TU, altura i azimut del Sol) a les sis ubicacions i a Burgos, València i
  Palma, calculades el 26/10/2026 amb el codi del calculador de la NASA.
- **Font:** <https://eclipse.gsfc.nasa.gov/SEgoogle/SEgoogle2001/SE2026Aug12Tgoogle.html> i el seu
  `SEcirc.js`. "Eclipse Predictions by Fred Espenak, NASA's GSFC"; calculador de Xavier Jubier.
- **Com es reprodueix:** `python scripts/comparar_nasa.py --calcular` (descarrega la pàgina i el codi a
  `data/cache/nasa/`, que no és al Git, i l'executa amb JavaScriptCore, `osascript`, només a macOS).
- `circumstancies_nasa_2027.csv` i `circumstancies_nasa_2028.csv`: el mateix per als eclipsis del 2027 i el
  2028 (pàgines `SE2027Aug02Tgoogle.html` i `SE2028Jan26Agoogle.html`), a Tarifa, Cadis, Màlaga, Sevilla,
  València, Barcelona, la UAB i Picos, calculats el 30/10/2026 (`comparar_nasa.py --calcular --eclipsi 2027`).
- **Convencions:** ΔT = 71,4 s; observador a 0 m; altura del Sol geomètrica (sense refracció); vora mitjana
  de la Lluna; valors sense arrodonir (el globus del mapa els arrodoneix a 0,1 s i 0,1°).

## Coordenades de les ubicacions — `dades/observador.py`

Consultades el 26/10/2026. Ajuntaments (l'Escala, Cerdanyola, Montmeló): geocodificador de l'ICGC,
`https://eines.icgc.cat/geocodificador/cerca?text=...`, comparat amb OpenStreetMap (Nominatim) a menys de
20 m. Places (plaça Major de Vic, plaça Cívica de la UAB): centre del polígon d'OpenStreetMap (© col·laboradors
d'OpenStreetMap, ODbL). Detall a `PLA_DE_TREBALL.md` §10.3.

## Textures — `data/textures/`

| Fitxer | Font | Llicència | Com es reprodueix |
|---|---|---|---|
| `terra_2048.jpg` (2048 × 1024, 239 kB) | NASA Visible Earth, "Blue Marble: Land Surface, Shallow Water, and Shaded Topography" (2002) | Domini públic (NASA) | `python scripts/descarregar_textures.py` |
| `lluna_1024.jpg` (1024 × 512, 139 kB) | NASA Scientific Visualization Studio, "CGI Moon Kit" (color de la LRO) | Domini públic (NASA) | `python scripts/descarregar_textures.py` |
| `lluna_8k.jpg` (8192 × 4096, 8,6 MB; no al Git) | El mateix kit: `lroc_color_poles_8k.tif` (51 MB, a `originals/`), convertit a JPEG (qualitat 92) | Domini públic (NASA) | `python scripts/descarregar_textures.py --alta` |
| `lluna_altitud.npy` (5760 × 2880, float16, 33 MB; no al Git) | El mateix kit: `ldem_16_uint.tif` (LOLA, 16 px/grau, 33 MB, a `originals/`): enters en mitjos metres amb 10 km sumats; altitud (km) = valor × 0,0005 − 10, respecte d'una esfera de 1737,4 km (de −9,0 a +10,7 km) | Domini públic (NASA) | `python scripts/descarregar_textures.py --alta` |

Totes dues textures de la Lluna són equirectangulars amb la longitud 0 (la cara que mira la Terra) al centre.
Kit: https://svs.gsfc.nasa.gov/4720 (baixat el 28/10/2026, amb autorització de l'equip per la mida).

## Ortofoto (PNOA) — `data/ortofoto/` (no al Git)

| Fitxer | Font | Llicència | Com es reprodueix |
|---|---|---|---|
| `vic_5m.tif` (4000 × 4000 px, 5,3 MB, JPEG) | IGN, WMS "PNOA máxima actualidad" (`https://www.ign.es/wms-inspire/pnoa-ma`), capa `OI.OrthoimageCoverage`, demanada en EPSG:25830 amb exactament la graella del MDT de la zona (el servei reprojecta) | CC BY 4.0 (`AccessConstraints` del GetCapabilities: "CC BY 4.0 scne.es"; `Fees`: "No se aplican condiciones"). Atribució: "Ortofoto PNOA cedida por © Instituto Geográfico Nacional" | `python scripts/descarregar_ortofoto.py vic` |
| `vic_vic_0p5m.tif` (8000 × 8000 px a 0,5 m, 4 × 4 km al voltant de la plaça Major, 19,8 MB) | El mateix servei, en quatre peticions de 4000 px (màxim del servei: 4096). Vol al punt: juliol de 2024, 0,25 m; "Ortoimagen verdadera: NO" (GetFeatureInfo de `OI.MosaicElement`) | Ídem | Ídem |

Consultat el 27/10/2026. La data, la resolució i el sha256 de cada fitxer es desen a `data/ortofoto/<zona>.json`.
L'ortofoto de l'ICGC (`geoserveis.icgc.cat`, 25 cm, anys 2009–2025) és una alternativa per a Catalunya; el
GetCapabilities hi diu "copyright" i remet a les condicions generals, on no s'ha pogut confirmar la llicència
concreta: no s'ha fet servir.

## Fotografia aèria per teselles — `data/cache/teselles/` (no al Git)

El programa demana la fotografia aèria a mesura que la necessita (`dades/teselles.py`, `basecode/mosaic.py`), en
teselles JPEG de 256 × 256 px de la quadrícula Web Mercator (EPSG:3857, `GoogleMapsCompatible`), i les desa a
`data/cache/teselles/<font>/<z>/<x>/<y>.jpg` (es poden esborrar: es tornen a baixar).

| Font | Servei | Llicència i atribució | Ús |
|---|---|---|---|
| PNOA màxima actualitat (IGN) | WMTS `https://www.ign.es/wmts/pnoa-ma`, capa `OI.OrthoimageCoverage`, zooms 12–19 (el servei arriba a z = 20, però el vol és de 0,25 m: z = 19 ja dona ~0,22 m/px i z = 20 seria la mateixa imatge ampliada) | CC BY 4.0. "PNOA cedido por © Instituto Geográfico Nacional" | Espanya. On no té imatge, el servei dona un lila uniforme (32, 26, 38): aquests píxels es prenen de Sentinel-2 |
| Sentinel-2 cloudless 2020 (EOX IT Services) | WMTS `https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/...`, fins a z = 15 (per sobre s'amplia) | CC BY-NC-SA 4.0 (ús no comercial). "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2020)" | Tot el món, 10 m per píxel; zooms 0–11 a tot arreu i forats del PNOA |

Consultat el 28/10/2026. Les atribucions es mostren al peu del panell mentre la fotografia aèria és activa.
Resolució del vol (GetFeatureInfo de `OI.MosaicElement`, 31/10/2026): 0,25 m a Vic i la UAB (juliol 2024), València
(maig 2024), Tona (juliol 2024) i Picos (setembre 2023). L'ortofoto de Vic (`data/ortofoto/`, 0,5 m) és la mateixa
font a la meitat de resolució: allà on hi ha teselles, el mosaic (fins a z = 19) es dibuixa a sobre i n'hi dona més.
Les imatges de Google Earth no es poden fer servir: les condicions d'ús no permeten descarregar-ne les teselles.

## Fitxers generats — `data/cache/` (no al Git)

Derivats dels MDT (`*.derivats.npz`), posicions de la malla sobre el globus (`*.globus3_*.npz`; les versions
anteriors es van esborrar el 30/10/2026), malles dels edificis (`edificis_*.npz`, comprimides), rajoles de les
descàrregues de `descarregar_mdt.py` (`rajoles/`) i teselles de la fotografia aèria (`teselles/`, veure a sobre).
Es poden esborrar: el programa els torna a calcular (les rajoles i les teselles, tornant-les a baixar).
