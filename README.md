# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez).

Visualitzem en 3D l'**eclipsi total de Sol del 12 d'agost de 2026** sobre el relleu real d'Espanya,
amb el model digital del terreny (MDT) de l'IGN i les dades oficials de l'eclipsi del CNIG.
El programa funciona com un videojoc: un personatge camina pels Picos de Europa (MDT de 5 m), en
tercera o en primera persona, i amb la barra de temps es veu com el Sol baixa cap a l'horitzó i la
Lluna el tapa. La tecla **P** reprodueix l'eclipsi des del punt on som, mirant el Sol.
De moment es carrega una sola regió; més endavant volem un zoom progressiu (com Google Maps) en què el
terreny guanyi detall a mesura que t'hi apropes.

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

S'obre una finestra amb el terreny, el panell **Opcions** i la barra de temps. La primera vegada es
calculen uns fitxers auxiliars del terreny (5–7 s); a partir de llavors es carrega en menys d'un
segon. Si es vol, es poden calcular tots d'entrada amb:

```bash
python scripts/preparar_dades.py
```

També es pot obrir un altre MDT en EPSG:25830 en lloc dels Picos:

```bash
python main.py data/mdt05/PNOA_MDT05_ETRS89_HU30_0011_LID.tif
```

---

## 2. Què es pot fer al programa

### Controls (com en un videojoc)

| Acció | Tercera persona | Primera persona |
|---|---|---|
| Caminar | `W` `A` `S` `D` | `W` `A` `S` `D` |
| Saltar / córrer | `Espai` / `Ctrl` | `Espai` / `Ctrl` |
| Girar la càmera / mirar | arrossegar o fletxes | arrossegar o fletxes |
| Zoom | roda (s'allunya del personatge) | roda (com uns prismàtics) |
| Anar a un punt | doble clic al terreny | — |
| Canviar de vista | `V` | `V` |
| Veure l'eclipsi des d'aquí | `P` | `P` |

Amb la `P` la càmera passa a primera persona, segueix el Sol amb una mica de zoom i el temps avança
sol des de l'inici de l'eclipsi: ràpid a les fases parcials i lent a la totalitat. Si gires la
càmera, deixa de seguir el Sol.

### Panell i barra de temps

- **Barra de temps** (a baix): play/pausa, ±5 min, velocitat (x1, x10, x60, x300 o *Auto*) i l'hora
  (CEST) amb la fase de l'eclipsi. A sota, les hores de contacte del CNIG en aquell punt.
- **Ara mateix**: hora, fase, percentatge del Sol tapat per la Lluna i posició del Sol.
- **Aquest punt (dades del CNIG)**: coordenades, hores de cada fase, posta del Sol, durada de la
  totalitat i visibilitat segons el relleu.
- **Capes sobre el terreny**: enfosquiment màxim, durada de la totalitat i ombres del relleu del CNIG
  (amb opacitat i llegenda), i els límits de la franja de totalitat.
- **Avançat**: FPS, exageració vertical, boira, distància de la Lluna, filferros, curvatura, eixos,
  zoom i el botó *Mirar des de darrere la Lluna*.

### Com es calcula el cel (`model_eclipsi.py`)

- **Sol**: algorisme de la NOAA per a la data i el punt, corregit perquè al màxim coincideixi amb
  l'azimut i l'elevació del CNIG (la correcció és de menys de 0,1°).
- **Lluna** (primera aproximació): es mou en línia recta respecte del Sol, en la direcció de
  l'eclíptica, i passa a la distància mínima a l'hora del màxim. La velocitat i la distància mínima
  s'ajusten amb les hores de contacte del CNIG en aquell punt; fora de la franja, amb l'enfosquiment
  màxim. Es comprova que a l'inici i al final de la totalitat la Lluna tapa el 100 % del Sol.
- **Mides**: el Sol i la Lluna tenen la seva mida aparent real (~0,5°). La Lluna es dibuixa a la
  distància que es tria al panell; el Sol, "a l'infinit".
- **Llum**: el terreny i el cel s'enfosqueixen segons la part del Sol que queda visible i segons
  l'altura del Sol (crepuscle). A la totalitat es veu la corona.

---

## 3. Què hi ha a cada carpeta

```
main.py              Programa principal: el joc (teclat, temps, llum), el panell i la barra de temps
sol.py               El Sol: la llum de l'escena (Light del basecode amb azimut i elevació)
model_eclipsi.py     On són el Sol i la Lluna a cada hora, vistos des d'un punt
camera.py            Càmera orbital enganxada al terreny (tercera persona)
camera_primera_persona.py  Càmera dels ulls del personatge (primera persona)
personatge.py        El personatge: camina i salta
astres.py            Esferes de la Lluna, el Sol i la seva resplendor (halo i corona)
terrain.py           El terreny: textures, graella de vèrtexs, faldilles i capes de l'eclipsi
data_io.py           Lectura dels MDT, neteja de les dades i fitxers auxiliars (data/cache/)
eclipse_data.py      Lectura de les dades de l'eclipsi del CNIG
scripts/             Scripts per preparar dades i fer captures (veure secció 5)
basecode/            Codi base de l'assignatura (el del repte 4), amb tots els shaders a
                     basecode/shaders/ (gouraud, phong, terrain i esfera)
models/              Models .obj, cadascun a la seva carpeta (com al repte 4)
data/                Dades (veure secció 4)
requirements.txt     Llibreries de Python
```

Com al repte 4, `main.py` defineix un `GraphicsEngine` que hereta del `GraphicsEngineBase` de
`basecode/`: `on_init` crea la llum (el Sol, `self.light`), la càmera, els eixos i el terreny;
`drawables()` són els objectes als quals la càmera escriu `m_proj` i `m_view`; `render()` els dibuixa i
`build_ui()` fa el panell. Cada objecte té `get_vbo`, `get_vao`, `get_shader_program`, `on_init`,
`render` i `destroy`. Els shaders són fitxers de `basecode/shaders/` i es carreguen amb
`basecode.shaders.load_program(ctx, nom)`.

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
