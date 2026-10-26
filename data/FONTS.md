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
- **Com es reprodueix:** `python scripts/descarregar_efemerides.py`.
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
- **No accessibles en aquesta fase:** el *Modelo Digital de Superficies normalizado de Edificación* del
  CNIG (altures LiDAR, 2,5 m): el Centre de Descàrregues no responia; els models de l'ICGC es lliuren per
  enllaç per correu. Per això les altures són estimades i no mesurades.
- **Referència independent per a la validació:** OpenStreetMap (contorns i `building:levels`, © col·laboradors
  d'OpenStreetMap, ODbL), consultat amb l'API Overpass el 26/10/2026 (400 m al voltant de la UAB;
  `data/edificis/osm_uab.json`).

## Comprovació externa (NASA) — `data/nasa/`

- `circumstancies_nasa.csv` (2 kB, al Git): circumstàncies locals de l'eclipsi (tipus, magnitud,
  enfosquiment, C1–C4 i màxim en TU, altura i azimut del Sol) a les sis ubicacions i a Burgos, València i
  Palma, calculades el 26/10/2026 amb el codi del calculador de la NASA.
- **Font:** <https://eclipse.gsfc.nasa.gov/SEgoogle/SEgoogle2001/SE2026Aug12Tgoogle.html> i el seu
  `SEcirc.js`. "Eclipse Predictions by Fred Espenak, NASA's GSFC"; calculador de Xavier Jubier.
- **Com es reprodueix:** `python scripts/comparar_nasa.py --calcular` (descarrega la pàgina i el codi a
  `data/cache/nasa/`, que no és al Git, i l'executa amb JavaScriptCore, `osascript`, només a macOS).
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

## Fitxers generats — `data/cache/` (no al Git)

Derivats dels MDT (`*.derivats.npz`), posicions de la malla sobre el globus (`*.globus_*.npz`) i
rajoles de les descàrregues. Es poden esborrar: el programa els torna a calcular.
