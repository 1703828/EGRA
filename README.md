# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez).

Visualitzem en 3D l'**eclipsi total de Sol del 12 d'agost de 2026** sobre el relleu real d'Espanya,
amb el model digital del terreny (MDT) de l'IGN i les dades oficials de l'eclipsi del CNIG.
Ara mateix hi ha la **vista exterior** del terreny a diverses escales, amb les dades de l'eclipsi
superposades. La posició del Sol i la Lluna al llarg del temps, la vista d'observador i la barra
temporal són els passos següents.

---

## 1. Posar-ho en marxa

### Entorn (un sol cop)

```bash
conda create -n egra -c conda-forge python=3.11 numpy scipy rasterio pyproj requests fiona geopandas
conda activate egra
pip install glfw moderngl PyGLM slimgui tifffile PyOpenGL trimesh Pillow
```

(La llista completa és a `requirements.txt`.)

### Executar

Des de l'arrel del repositori:

```bash
conda activate egra
python main.py
```

S'obre una finestra amb el terreny i un panell **Opcions**. La primera vegada que s'obre cada terreny
es calculen uns fitxers auxiliars (5–7 s per terreny); a partir de llavors es carrega en menys d'un
segon. Si es vol, es poden calcular tots d'entrada amb:

```bash
python scripts/preparar_dades.py
```

També es pot obrir qualsevol altre MDT en EPSG:25830, que s'afegeix al selector:

```bash
python main.py data/mdt05/PNOA_MDT05_ETRS89_HU30_0011_LID.tif
```

---

## 2. Què es pot fer al programa

### Controls de la càmera

| Acció | Control |
|---|---|
| Girar la càmera | arrossegar amb el **botó esquerre** |
| Desplaçar el punt on mira la càmera | arrossegar amb el **botó dret** (o **Maj + esquerre**) |
| Zoom (cap al punt del cursor) | **roda** del ratolí |
| Triar un punt d'observació (i centrar-hi la càmera) | **doble clic** sobre el terreny |
| Tornar a la vista inicial | botó **Reiniciar camera** |

### Panell d'opcions

- **Terreny**: `Peninsula` (200 m), `Asturies` (25 m), `Picos` (5 m) i `Luarca` (5 m). Si el punt on
  mira la càmera també és dins del terreny nou, la vista es manté al mateix lloc.
- **Zones de detall**: rectangles de Picos i Luarca sobre la península i Astúries.
- **Curvatura de la Terra**: el terreny es corba (a les cantonades de la península baixa uns 39 km).
- **Camera**: gir, inclinació i distància; coordenades del punt on mira la càmera.
- **Punt d'observacio** (doble clic): coordenades UTM i lat/lon, altitud i les dades de l'eclipsi en
  aquell punt (posició del Sol al màxim, enfosquiment, hores de cada fase en hora local CEST, durada de la
  totalitat i visibilitat segons el relleu). El botó **Sol al maxim de l'eclipsi** hi posa el Sol.
- **Eclipsi sobre el terreny**: capes superposades (una de cada vegada, amb opacitat i llegenda):
  enfosquiment màxim, durada de la totalitat i ombres del relleu del CNIG; i línia dels límits de la
  franja de totalitat.
- **Terreny**: exageració vertical, boira i filferros. **Sol**: azimut i elevació.

---

## 3. Què hi ha a cada carpeta

```
main.py              Programa principal: finestra, selecció de terrenys i panell d'opcions
camera.py            Càmera orbital controlada amb el ratolí, enganxada al terreny
terrain.py           El terreny: textures, graella de vèrtexs, faldilles i capes de l'eclipsi
shaders/             Shaders del terreny (terrain.vert i terrain.frag)
data_io.py           Lectura dels MDT, neteja de les dades i fitxers auxiliars (data/cache/)
eclipse_data.py      Lectura de les dades de l'eclipsi del CNIG
scripts/             Scripts per preparar dades i fer captures (veure secció 5)
basecode/            Codi base de l'assignatura (el mateix dels reptes; no es modifica)
data/                Dades (veure secció 4)
requirements.txt     Llibreries de Python
```

Com als reptes de classe, `main.py` defineix un `GraphicsEngine` que hereta del `GraphicsEngineBase` de
`basecode/`, i cada objecte que es dibuixa té els seus buffers, el seu shader i un mètode `render()`.
Els shaders són fitxers a part i es carreguen amb `basecode.shaders.load_program`.

Unitats i coordenades de l'escena: quilòmetres, amb X = est, Y = altitud i Z = sud. Les dades fan
servir el sistema ETRS89 / UTM 30N (EPSG:25830).

---

## 4. Dades (`data/`)

```
data/
  mdt/                  Models digitals del terreny que fa servir el programa (EPSG:25830)
    peninsula_200m.tif    Península Ibèrica, 200 m             (5488 x 4465 px)
    asturias_25m.tif      Astúries, 25 m                       (8819 x 3807 px)
    picos_5m.tif          Picos de Europa, 20 x 20 km, 5 m     (4000 x 4000 px)
    luarca_5m.tif         Luarca, 20 x 20 km, 5 m              (4000 x 4000 px)
  mdt05/
    PNOA_MDT05_ETRS89_HU30_0011_LID.tif   Fulla 0011 (Luarca) del MDT05, 5 m (exemple de fulla original)
  eclipsi2026/          Dades oficials de l'eclipsi del 12/08/2026 (CNIG)
    10bandas2026_3857_COG.tiff      Efemèrides: posició del Sol, enfosquiment i hores de cada fase
    terrain_shadows_2026_..._.tif   Visibilitat del Sol al màxim segons el relleu (4 classes)
    Eclipses_2026.gpkg              Corbes de nivell (durada, enfosquiment, avanç de l'ombra)
    LLEGENDA.md                     Què conté cada banda, classe i capa
    doc/                            Documentació original del CNIG
  cache/                (no es puja al git) fitxers que genera el programa
```

- Els MDT de `data/mdt/` provenen del **servei WCS de l'IGN**. El mar i les zones de fora d'Espanya
  (Portugal, França) valen 0 m, perquè el servei només té dades d'Espanya.
- Les hores del dataset de l'eclipsi són en temps universal; el programa les mostra en hora local
  (CEST = TU + 2).
- `data/cache/` es crea sol: hi van els fitxers auxiliars de cada terreny (`*.derivats.npz`, ~1 GB en
  total) i les rajoles de les descàrregues. Es pot esborrar sense perill.

---

## 5. Scripts (`scripts/`)

Tots s'executen des de l'arrel del repositori, amb l'entorn `egra` activat.

| Script | Per a què serveix |
|---|---|
| `preparar_dades.py` | Calcula els fitxers auxiliars de tots els terrenys (`data/cache/`) |
| `descarregar_mdt.py` | Torna a descarregar un MDT del WCS de l'IGN, o en descarrega un de nou |
| `captura.py` | Desa una imatge del terreny en PNG sense obrir cap finestra |

Descàrrega d'MDT (els de `data/mdt/` ja hi són; només cal per refer-los o per a zones noves):

```bash
python scripts/descarregar_mdt.py peninsula     # 200 m -> data/mdt/peninsula_200m.tif
python scripts/descarregar_mdt.py asturias      #  25 m -> data/mdt/asturias_25m.tif
python scripts/descarregar_mdt.py picos         #   5 m -> data/mdt/picos_5m.tif
python scripts/descarregar_mdt.py luarca        #   5 m -> data/mdt/luarca_5m.tif
python scripts/descarregar_mdt.py --res 5 --centre 43.30 -5.00 --sortida zona_5m.tif   # zona nova de 20 x 20 km
```

Captures (exemples; `python scripts/captura.py -h` mostra totes les opcions):

```bash
python scripts/captura.py data/mdt/picos_5m.tif captures/picos.png --sol-maxim --gir -115 --inclinacio 30
python scripts/captura.py data/mdt/peninsula_200m.tif captures/peninsula.png --overlay enfosquiment --limits --gir -35 --inclinacio 45
```

---

## 6. Fonts i llicències

- **MDT**: servei WCS de models digitals del terreny de l'IGN (`https://servicios.idee.es/wcs-inspire/mdt`)
  i MDT05 del Centre de Descàrregues del CNIG. MDT © Instituto Geográfico Nacional (CC BY 4.0).
- **Eclipsi**: dades de l'eclipsi del 12/08/2026 del CNIG (`https://visualizadores.ign.es/eclipses`).
  "Official astronomical information provided by the National Geographic Institute based on
  calculations made by the National Astronomical Observatory" (CC BY 4.0).
