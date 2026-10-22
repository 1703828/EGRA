# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez).

Visualitzem en 3D l'**eclipsi total de Sol del 12 d'agost de 2026** sobre el relleu real d'Espanya,
amb el model digital del terreny (MDT) de l'IGN i les dades oficials de l'eclipsi del CNIG.
Amb la càmera d'exploració es recorre el terreny dels Picos de Europa (MDT de 5 m) i, amb un doble
clic, es tria un punt d'observació. Des d'aquell punt, a 1,7 m sobre el terra, es veu com el Sol baixa
cap a l'horitzó i la Lluna el tapa. La tecla **P** reprodueix l'eclipsi des del punt triat, mirant el Sol.
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

### Controls

Hi ha dues vistes. La **d'exploració** és una càmera lliure per inspeccionar el terreny i triar el punt
d'observació, que es marca amb una esfera taronja. La **d'observador** posa la càmera als ulls d'una
persona en aquell punt, 1,7 m sobre el terra.

| Acció | Exploració | Observador |
|---|---|---|
| Girar la càmera / mirar al voltant | arrossegar o fletxes | arrossegar o fletxes |
| Desplaçar la càmera | botó dret (o Maj + esquerre), o `W` `A` `S` `D` (`Ctrl`: més ràpid) | — |
| Zoom | roda (cap al punt del cursor) | roda (com uns prismàtics) |
| Triar el punt d'observació | doble clic al terreny | — (cal tornar a l'exploració) |
| Canviar de vista | `V` | `V` |
| Veure l'eclipsi des del punt triat | `P` | `P` |

Amb la `P` la càmera passa a la vista d'observador, segueix el Sol amb una mica de zoom i el temps avança
sol des de l'inici de l'eclipsi: ràpid a les fases parcials i lent a la totalitat. Si gires la
càmera, deixa de seguir el Sol.

**Mentre es reprodueix l'eclipsi, el punt d'observació queda bloquejat**: es pot mirar al voltant, fer
zoom i moure la càmera d'exploració, però el doble clic no canvia el punt. Així el cel, el model i les
dades del panell són sempre del mateix lloc. Per triar-ne un altre, cal posar la barra de temps en pausa.

### Panell i barra de temps

- **Barra de temps** (a baix): play/pausa, ±5 min, velocitat (x1, x10, x60, x300 o *Auto*) i l'hora
  (CEST) amb la fase de l'eclipsi. A sota, les hores de contacte del CNIG en aquell punt.
- **Ara mateix**: hora, fase, percentatge del Sol tapat per la Lluna i posició del Sol.
- **Punt d'observació (dades del CNIG)**: coordenades, hores de cada fase, posta del Sol, durada de la
  totalitat i visibilitat segons el relleu.
- **Capes sobre el terreny**: enfosquiment màxim, durada de la totalitat i ombres del relleu del CNIG
  (amb opacitat i llegenda), i els límits de la franja de totalitat.
- **Avançat**: FPS, exageració vertical, boira, distància de la Lluna, filferros, curvatura, eixos,
  zoom i el botó *Mirar des de darrere la Lluna*.

### Com es calcula el cel (`dades/model_eclipsi.py`)

- **Sol**: algorisme de la NOAA per a la data i el punt, corregit perquè al màxim coincideixi amb
  l'azimut i l'elevació del CNIG. La correcció d'elevació va d'uns 0,09° a 0,26° segons el punt i és
  compatible amb la refracció atmosfèrica, que el CNIG inclou (veure `PLA_DE_TREBALL.md`, §6).
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
main.py                  Programa principal: coordina l'escena (crea els objectes, temps, llum i teclat)
ui.py                    Interfície: el panell "Opcions" i la barra de temps (slimgui)
basecode/                Codi base de l'assignatura (el del repte 4, sense canvis) i els nostres objectes:
  engine.py, window.py, ui_panel.py, objects.py, camera.py, light.py, axis.py,
  meshloader.py, shaders.py       fitxers originals del professor (no es modifiquen)
  sol.py                 El Sol: la llum de l'escena (Light del basecode amb azimut i elevació)
  terrain.py             El terreny: textures, graella de vèrtexs, faldilles i capes de l'eclipsi
  astres.py              Esferes de la Lluna, el Sol i la seva resplendor (halo i corona)
  camera_exploracio.py   Càmera orbital per explorar el terreny i triar el punt d'observació
  camera_observador.py   Càmera als ulls de l'observador (1,7 m sobre el terra)
  shaders/               gouraud i phong (originals) i terrain i esfera (nostres)
dades/                   Lectura i càlcul de dades, sense OpenGL:
  observador.py          La ubicació de l'observador (només dades: punt, latitud, longitud, altitud)
  data_io.py             Lectura dels MDT, neteja de les dades i fitxers auxiliars (data/cache/)
  eclipse_data.py        Lectura de les dades de l'eclipsi del CNIG
  model_eclipsi.py       On són el Sol i la Lluna a cada hora, vistos des d'un punt
scripts/                 Scripts per preparar dades, fer captures i l'exercici 1.0 (veure secció 5)
models/                  Models .obj, cadascun a la seva carpeta (com al repte 4)
data/                    Dades (veure secció 4)
docs/                    Web de seguiment (obrir docs/index.html al navegador)
PLA_DE_TREBALL.md        Pla de treball: tasques, decisions i comprovacions
CLAUDE.md                Instruccions de treball de l'equip
requirements.txt         Llibreries de Python
```

Com al repte 4, `main.py` defineix un `GraphicsEngine` que hereta del `GraphicsEngineBase` de
`basecode/`: `on_init` crea la llum (el Sol, `self.light`), la càmera, els eixos i el terreny;
`drawables()` són els objectes als quals la càmera escriu `m_proj` i `m_view`; `render()` els dibuixa i
`build_ui()` crida el panell de `ui.py`. Els objectes gràfics propis són fitxers nous dins de
`basecode/` (els originals del professor no es toquen) i el que no depèn d'OpenGL és a `dades/`. Cada objecte té `get_vbo`, `get_vao`, `get_shader_program`, `on_init`,
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
| `exercici_fotograma.py` | Exercici 1.0: segueix un vèrtex del terreny fins al píxel de la pantalla (`docs/exercici_1_0_vertex_a_pixel.md`) |

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
