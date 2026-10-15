# CLAUDE.md — Projecte EGRA: simulació d'un eclipsi sobre terreny real

## El projecte

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez). Simulem l'eclipsi total de
Sol del **12 d'agost de 2026** sobre terreny real d'Espanya, a partir del MDT de l'IGN/CNIG.
L'objectiu final té dues vistes:

1. **Vista exterior**: el terreny en 3D, la posició del Sol i la Lluna i l'evolució de les ombres.
2. **Vista d'observador**: la càmera a l'altura d'una persona sobre el terreny, de manera que el relleu
   pot tapar el Sol.

També tindrà una barra temporal (play/pausa, avançar, retrocedir, hora:minut) i, més endavant,
condicions meteorològiques (dia clar, boira, núvols). Els detalls són a `acta1.pdf`.

## Feina actual

**Les tasques del terreny són a `TASQUES_TERRENY.md`; segueix-les en ordre.**
Fes una sola tasca cada vegada. Quan l'acabis, executa el programa, explica els canvis en poques línies i
atura't fins que l'usuari ho provi i et demani la següent.

## Entorn i execució

- Entorn conda **`egra`** (Python 3.11). Executar sempre amb `conda activate egra` i `python ...`, o
  sense activar-lo amb `~/anaconda3/envs/egra/bin/python ...`. **No fer servir l'anaconda base.**
  - Programa: `python terreny.py`
  - Descàrrega del MDT: `python scripts/descarregar_mdt.py <peninsula|asturias|detall>` (des de l'arrel)
- Llibreries instal·lades a `egra`: numpy, scipy, rasterio, pyproj, requests, fiona, geopandas 1.2 (conda-forge)
  i glfw, moderngl, PyGLM, slimgui, tifffile, PyOpenGL, trimesh (pip).
  **Pregunta abans d'instal·lar res més** i afegeix-ho a `requirements.txt`.
- macOS: només OpenGL 3.3 core (no hi ha compute shaders ni GL 4.x).

## Organització del codi (la de classe, cal mantenir-la)

- `basecode/` (`engine.py`, `window.py`, `ui_panel.py`): el `GraphicsEngineBase` dels reptes.
  **No el modifiquis.** El projecte en fa una subclasse i sobreescriu `on_init`, `drawables`,
  `render`, `build_ui` i `on_destroy`.
- Cada objecte visible té VBO/IBO + VAO + shader program, uniforms `m_proj`, `m_view` i `m_model`,
  un mètode `render()` i un mètode `destroy()` que allibera els recursos.
- La interfície es fa amb slimgui dins de `build_ui` (finestra "Opcions").
- L'estructura de mòduls objectiu (`main.py`, `camera.py`, `terrain.py`, `data_io.py`,
  `eclipse_data.py`, `shaders/`, `scripts/`) és a la T7 de `TASQUES_TERRENY.md`.

## Convencions

- Comentaris, noms de la UI i missatges en **català**. A la UI, sense accents (la font de slimgui
  no els mostra bé).
- Món 3D en **km**: X = est, Y = altitud, Z = sud. Les altituds dels fitxers estan en metres.
- CRS de treball: **EPSG:25830** (ETRS89 / UTM 30N). La fulla 0011 de `data/mdt05/` ja està en EPSG:25830.
- Azimut del Sol en graus des del nord, en sentit horari. Elevació en graus sobre l'horitzó.
- Res de peticions de xarxa dins del bucle de render. Les dades es descarreguen o preprocessen amb
  scripts i es guarden a `data/cache/`.
- Codi senzill i entenedor: és un projecte de curs i l'equip l'ha d'entendre i explicar.

## Dades (`data/`)

- `data/mdt05/PNOA_MDT05_ETRS89_HU30_0011_LID.tif`: fulla 0011 (Luarca), 5 m, **EPSG:25830**,
  5569×3965 px. Nodata -32767 (el mar fora de la costa), i també hi ha mar amb valor 0. Està
  georeferenciada com a `PixelIsPoint` (l'origen és el centre del primer píxel; rasterio ja ho corregeix).
- `data/mdt05/altres/`: fulles que no fem servir (la 0011 en EPSG:25829 i la 0296 en EPSG:25831).
- `data/eclipsi2026/`: dataset del CNIG de l'eclipsi, tot en EPSG:3857 o EPSG:4326:
  La llegenda (bandes, classes i capes), confirmada amb `doc/Description_eclipses.pdf`, és a
  **`data/eclipsi2026/LLEGENDA.md`**.
  - `10bandas2026_3857_COG.tiff`: 10 bandes float32 (efemèrides), ~1223 m/píxel, nodata -1000.
  - `terrain_shadows_2026_3857_…tif`: uint8, ~306 m/píxel, classes 0–3 (+ un valor 4 no documentat), nodata 61.
  - `Eclipses_2026.gpkg` (EPSG:4326): capes d'avanç de la taca, d'enfosquiment i de durada de la totalitat.
    El polígon 0–10 s de `durtot` inclou la zona sense totalitat: la vora de la franja es treu del GeoTIFF.
  - `eclipse_data.py` reprojecta les dades a cada terreny (overlays) i llegeix els valors exactes en un
    punt (punt d'observació). Hores en CEST = TU+2.
- `data/cache/`: fitxers generats (MDT descarregats per WCS, etc.). No es versiona.
  - `peninsula_200m.tif`, `asturias_25m.tif` i `detall_5m.tif` es generen amb
    `scripts/descarregar_mdt.py` (T0). Les rajoles ja baixades es guarden a `data/cache/rajoles/`.
  - `detall_5m.tif` és **Picos de Europa** (centre 43.262, -4.949; totalitat 100–110 s).
    `detall_5m_luarca.tif` és la zona de detall antiga de Luarca (centre 43.54, -6.54).
  - `<nom>.derivats.npz`: cache dels derivats de cada MDT (gradient, distància a la costa, altitud
    mitjanada i overlays de l'eclipsi reprojectats), generada per `data_io.carregar_terreny()`. Es refà sola si canvia el fitxer o
    `VERSIO_CACHE`; es pot esborrar sense perill (ocupen ~1 GB en total).
- El MDT de zones grans es baixa del **WCS de l'IGN** (`https://servicios.idee.es/wcs-inspire/mdt`),
  no fulla a fulla (veure la T0). L'script demana el format `ArcGrid` perquè `image/tiff` torna int16
  (sense decimals). El WCS no té nodata: el mar i les zones de fora d'Espanya (Portugal, França)
  valen 0. El de 25 m, a més, ve en metres enters a l'origen.
- Atribució obligatòria: "MDT i dades de l'eclipsi © Instituto Geográfico Nacional / CNIG" (CC BY 4.0).

## Què NO fer

- No modificar `basecode/`.
- No avançar tasques sense que l'usuari ho demani.
- No implementar encara el càlcul propi del Sol i la Lluna, les ombres de l'eclipsi, la vista
  d'observador completa ni la meteorologia. Venen després de les tasques del terreny.
- No fer commits de dades grans (`data/`).
