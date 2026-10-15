# Llegenda del dataset de l'eclipsi del 12/08/2026 (CNIG)

Font: `doc/Description_eclipses.pdf` (CNIG). Els rangs mesurats són els que hem llegit nosaltres dels fitxers.

Atribució obligatòria (CC BY 4.0), tal com la dona el document: *"Official astronomical information
provided by the National Geographic Institute based on calculations made by the National Astronomical
Observatory"* (informació astronòmica oficial de l'IGN a partir de càlculs de l'Observatori Astronòmic
Nacional).

## `10bandas2026_3857_COG.tiff` — efemèrides

- EPSG:3857 (WGS 84 / Pseudo-Mercator), 3328×3328 px, ~1223 m/píxel, float32, nodata -1000.
- Cobreix d'uns -25,3° a 11,2° de longitud i de 21,9° a 50,7° de latitud.
- Calculat amb el model GMTED2010 a 30" (~800 m), que inclou l'altitud de cada punt.
- Totes les hores són en **TU decimal** (p. ex. 18,5 = 18:30 TU = 20:30 hora d'estiu peninsular).

| Banda | Contingut | Rang mesurat |
|---|---|---|
| 1 | Elevació del centre del Sol al màxim de l'eclipsi (graus, corregida per refracció) | -1,3 … 24,1° |
| 2 | Azimut del centre del Sol al màxim (graus) | 264,9 … 292,6° |
| 3 | Enfosquiment (*obscuration*) al màxim (0–1) | 0 … 1 |
| 4 | Sortida del Sol el dia de l'eclipsi | 4,13 … 7,10 h |
| 5 | Posta del Sol el dia de l'eclipsi | 17,93 … 20,88 h |
| 6 | Inici de l'eclipsi parcial | 17,26 … 18,11 h |
| 7 | Moment del màxim | 18,25 … 19,01 h |
| 8 | Final de l'eclipsi parcial | 19,09 … 19,85 h |
| 9 | Inici de la totalitat (només dins la franja; fora és nodata) | 18,29 … 18,57 h |
| 10 | Final de la totalitat (només dins la franja; fora és nodata) | 18,31 … 18,57 h |

- Durada de la totalitat = (banda 10 − banda 9) × 3600 s.
- Si la posta (banda 5) és abans d'alguna fase, aquella fase no es veu.

## `terrain_shadows_2026_3857_COG_DEF_OVERSx6_8704x8192.tif` — ombres del relleu al màxim

- EPSG:3857, 8960×8448 px, ~306 m/píxel, uint8, nodata 61.
- Calculat amb GMTED2010 a 7,5" (~200 m) i la rutina `insol` (J. G. Corripio).
- Només té en compte el relleu (ni edificis ni arbres).

| Valor | Significat | Píxels |
|---|---|---|
| 0 | El relleu tapa completament el Sol al moment del màxim | 12 974 667 |
| 1 | El relleu només deixa veure part de la meitat superior del Sol | 1 580 185 |
| 2 | Es veu la meitat superior del Sol i part de la inferior | 1 801 720 |
| 3 | El relleu no tapa gens el disc solar | 54 945 209 |
| 4 | **No documentat.** Són píxels dispersos (0,002 %); els tractarem com a "sense dades" | 1 387 |
| 61 | Sense dades | 4 390 912 |

## `Eclipses_2026.gpkg` — corbes (EPSG:4326, MultiPolygon)

El document parla de fitxers GeoJSON, però al GeoPackage són capes. Els noms reals de les capes són:

| Capa | Elements | Camps | Contingut |
|---|---|---|---|
| `durtot_estandard_2026 — contour` | 13 | `DuracionTotalSegMin`, `DuracionTotalSegMax` | Franges de durada de la totalitat cada 10 s (0–123 s), calculades amb les bandes 9, 10 i 5 |
| `oscurez_estandard_2026 — contour` | 40 | `OscurecimientoMin`, `OscurecimientoMax` | Franges d'enfosquiment màxim cada 10 %, calculades amb les bandes 3 i 5 |
| `shadows_merged_18.293-18.569-2026-simplified-0.0001 — shadows_merged_18` | 277 | `ID`, `mancha_ut_<hora>` | Ombra de la Lluna (umbra) de 18,293 a 18,569 h TU, cada 0,001 h (3,6 s) |

- Cada polígon de `durtot` és una franja (de Min a Max), no una corba niada.
  Per exemple, Luarca (43,54 °N, 6,54 °O) cau a la franja de 100–110 s.
- **Atenció:** el polígon 0–10 s (756 graus²) inclou també tota la zona sense totalitat (durada 0).
  Per tant, la capa no dona la vora exacta de la franja. Al programa, la franja i les corbes de durada
  es calculen a partir de les bandes 9, 10 i 5 del GeoTIFF (`eclipse_data.py`), que són les dades amb
  què es va fer la capa.
- Es pot llegir amb fiona + shapely o amb geopandas (a `egra` ja hi ha geopandas 1.2).
