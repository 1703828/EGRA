# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez).

Visualitzem en 3D l'**eclipsi total de Sol del 12 d'agost de 2026** sobre el relleu real d'Espanya.
L'escena és un model geomètric coherent: la Terra (el·lipsoide WGS84 amb textura de la NASA), el
relleu de la península (MDT de 200 m de l'IGN), una zona de detall de 5 m al voltant del punt
d'observació (Picos de Europa, Vic, l'Escala o el Vallès) i el Sol i la Lluna a les seves posicions i mides reals (efemèrides de JPL Horizons). L'ombra de la Lluna es
calcula per a cada punt de la superfície i es veu moure's sobre la Terra.

Es pot observar l'eclipsi des d'un punt, a 1,7 m sobre el terra, o explorar lliurement des del terreny
fins a l'espai. El temps es controla a part: **P** només reprodueix o pausa.

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

Les zones de detall de les ubicacions catalanes no són al Git (ocupen ~140 MB). Es descarreguen un
cop (uns minuts) amb:

```bash
python scripts/descarregar_mdt.py vic
python scripts/descarregar_mdt.py escala
python scripts/descarregar_mdt.py valles     # Cerdanyola, la UAB i Montmeló
```

Sense aquests fitxers el programa funciona igual, però en aquestes ubicacions només hi ha el relleu de
200 m (ho avisa a la consola).

S'obre una finestra amb la vista des del terra (Picos de Europa, uns minuts abans del màxim), el
panell i la barra de temps. La primera vegada es calculen uns fitxers auxiliars del terreny (uns
segons); a partir de llavors es carrega en un o dos segons. Es poden calcular d'entrada amb:

```bash
python scripts/preparar_dades.py
```

---

## 2. Què es pot fer al programa

### Controls

Hi ha dues vistes. **Observar des del terra** posa la càmera als ulls d'una persona al punt
d'observació, 1,7 m sobre el terra: els ulls no es mouen i la mirada es queda on la deixes (el Sol no
se segueix sol). **Explorar** és una càmera lliure que es pot moure del terreny fins a l'espai.

| Acció | Explorar | Observar des del terra |
|---|---|---|
| Girar la mirada | ratolí capturat (veure a sota), arrossegar o fletxes | ratolí capturat, arrossegar o fletxes (els ulls no es mouen) |
| Endavant / enrere on mires | `E` / `Q` | `E` / `Q`: passa a explorar, sense moure la càmera, i comença a moure's |
| Moure's en horitzontal | `W` `A` `S` `D` (endavant, enrere, costats) | — |
| Més ràpid | `Ctrl` (x5) | — |
| Roda o dos dits amunt/avall al trackpad | endavant / enrere on mires (mou la càmera) | zoom (com uns prismàtics) |
| Triar la Terra, la Lluna o el Sol | `1` `2` `3` (o al panell) | `1` `2` `3` |
| Mirar l'astre triat (un sol cop) | `F` | `F` (gira el cap) |
| Apropar-s'hi | `G` | `G` (passa a explorar) |
| Triar el punt d'observació | doble clic al terreny amb el ratolí lliure (la càmera no es mou), o la llista del panell | la llista del panell |
| Capturar / alliberar el ratolí | clic a l'escena / `Esc` | clic a l'escena / `Esc` |
| Canviar de vista | `V` | `V` |
| Reproduir / pausar el temps | `P` | `P` |
| Tornar als ulls (1,7 m) | botó *Tornar al punt d'observació* | — |

`W` i `S` també fan anar endavant i enrere, però en horitzontal (com caminant); `E` i `Q` segueixen la
mirada en tres dimensions: si mires el Sol, `E` t'hi acosta; si mires amunt des del terra, surts cap al
cel. Mirant a terra, `E` s'hi acosta però no el travessa. El programa no torna sol als ulls en passar a
prop del terra: cal el botó *Tornar al punt d'observació*.

**Mirar amb el ratolí (com en un joc en primera persona).** Un clic a l'escena (fora del panell) captura
el ratolí: el cursor s'amaga, al centre apareix un punt de mira petit i moure el ratolí (o un dit al
trackpad) gira la mirada sense prémer cap botó ni topar amb la vora. Quan no el mous, la mirada no es
mou. `Esc` l'allibera per fer servir el panell; `Esc` no tanca el programa (es tanca amb el botó de la
finestra o Cmd+Q). Canviar a una altra finestra també l'allibera. El clic espera 0,3 s abans de capturar:
si n'arriba un segon, és un doble clic (triar el punt). La sensibilitat és la mateixa a prop del terra i a
l'espai i no depèn dels fotogrames per segon.

**Velocitat.** És proporcional a la distància a la superfície més propera (el terra, la Lluna o el Sol):
precisa a prop i ràpida a l'espai, i es redueix a mesura que t'acostes a un astre. Mantenint `E` cap amunt
des del terra s'arriba a 20.000 km en ~15 s (~3 s amb `Ctrl`). La roda fa el mateix a passos: cada pas
acosta o allunya un 35 % de la distància a la superfície (com a molt 3 passos per fotograma).

**Astres.** El panell té un selector compacte Terra / Lluna / Sol amb dues accions. *Mirar* orienta la
càmera cap a l'astre un sol cop i no la mou. *Apropar-s'hi* la porta, en un viatge de 1–3,5 s, fins a una
distància des d'on l'astre es veu sencer (ocupa el 80 % del camp de visió més estret de la finestra); el
camí no travessa cap astre ni el terra, i qualsevol moviment (tecles, ratolí, roda) el cancel·la allà on
és. En acabar, la càmera queda quieta, sense seguir l'astre. Cap de les dues canvia l'hora. Sota els
botons es veu la distància a la superfície de l'astre triat.

**Trackpad del Mac:** lliscar amb dos dits amunt o avall fa el mateix que la roda. El gest de pessigar no
funciona: GLFW, la llibreria de finestres, no el rep a macOS (veure el pla, tasca 12.4).

**Espai de navegació.** La càmera d'exploració no pot sortir d'un cub fix que conté la Terra, la Lluna i
el Sol durant tot l'interval de la barra de temps; a la paret només s'atura el moviment cap a fora i es pot
lliscar al llarg de la cara. Les parets no es veuen: *Avançat → Depuració → Mostrar el cub de navegació*
les mostra (translúcides, amb ratlles). Dimensions (sistema ECEF, km):

| | Valor |
|---|---|
| Costat | 246.438.601 km = 1,6473 UA |
| X | de −116.133.088 a 130.305.513 km |
| Y | de −196.844.044 a 49.594.556 km |
| Z | de −103.452.898 a 142.985.702 km |
| Radi solar | 696.000 km |
| Marge | 1.122.736 km = 1,613 radis solars (des de la paret de darrere del Sol, el disc sencer ocupa el 90 % del camp vertical de 50°) |

El costat és més d'1 UA perquè, en coordenades terrestres (que giren amb la Terra), el Sol fa ~112° de volta
al voltant de la Terra entre les 14:00 i les 21:30 TU. La càmera s'atura a 1.000 km de cada paret.
Càlcul: `dades/navegacio.py`; comprovació: `python scripts/prova_controls.py`.

**Arrencada:** el programa comença pausat una hora abans de l'inici de l'eclipsi (C1, calculat pel model)
a Picos: a les 18:31:39 (hora d'estiu). Canviar d'ubicació no canvia l'hora.

**P** no canvia res de la càmera: congela el temps on és i el torna a posar en marxa des del mateix
instant. Per exemple: s'observa l'eclipsi des del terra, es prem P, es passa a explorar i s'allunya
fins a veure la Terra, i es prem P: l'eclipsi continua amb la càmera a l'espai.

Mentre es reprodueix, el punt d'observació queda bloquejat (el panell, el cel i el model són sempre
del mateix lloc). Quan es tria una ubicació de la llista, la càmera d'exploració es posa a sobre del lloc
nou, perquè en passar a explorar (V) es parteixi d'allà. (`E` o `Q` des del terra, en canvi, comencen a
explorar des dels ulls.)

Ubicacions de la llista (coordenades verificades el 26/10/2026, font a `PLA_DE_TREBALL.md` §10.3): Picos
de Europa (centre de la zona de 5 m, totalitat), plaça Major de Vic, ajuntament de l'Escala, ajuntament de
Cerdanyola, ajuntament de Montmeló i plaça Cívica de la UAB.

Botons:

- **Veure l'ombra des de l'espai**: porta la càmera d'exploració a 12.000 km, entre la vertical i el
  Sol, mirant el punt on l'ombra de la Lluna és més fosca a l'hora actual. És un sol enquadrament: la
  càmera no segueix l'ombra. Des de l'espai l'ombra real es distingeix poc (a Espanya l'eclipsi passa
  a prop de la posta, i l'ombra cau a prop del límit entre el dia i la nit); la casella **Ressaltar
  l'ombra amb línies (didàctic)** hi dibuixa les línies del 25, 50 i 75 % del Sol tapat i el límit de la
  totalitat, sense canviar la foscor de l'ombra.
- **Anar al màxim del punt seleccionat**: posa l'hora del màxim al punt d'observació i deixa el temps
  pausat.
- **Tornar al punt d'observació**: torna a la vista des del terra, amb la mirada que tenia.

### Relleu: nivells de detall

Al voltant del punt d'observació el relleu té més detall que lluny: la península sencera (un vèrtex
cada ~1 km), la península a 200 m en ~100 km al voltant del punt, la zona de 5 m que conté el punt (un
vèrtex cada ~20 m) i, en ~2,5 km al voltant del punt, un vèrtex per cada píxel de 5 m. A la vora de cada
nivell, l'altura passa suaument a la del nivell de sota. Els ulls de l'observador queden a 1,7 m dels
triangles que es dibuixen (l'altura de cada vèrtex la calcula la CPU).

### Ombres del relleu

Dins de la zona de 5 m de l'observador (16 km al voltant del punt), les muntanyes fan ombra amb la
tècnica del *shadow mapping* (`basecode/ombres_relleu.py`): primer es dibuixa el relleu vist des del Sol
en una textura de profunditat i, després, cada punt del terreny mira si és més lluny del Sol que el que hi
ha guardat. L'ombra del relleu només treu la llum directa del Sol; la del cel continua. És diferent de
l'ombra de la Lluna (la part del Sol que tapa la Lluna, a tota una regió). Es pot apagar a **Avançat**.
Fora de la zona de 5 m no hi ha ombres del relleu, i obstacles de menys de ~12 m no en fan.

### Panell i barra de temps

- **Panell**: reproduir o pausar, hora, fase, part del Sol tapada al punt triat i velocitat (x1 a x1000,
  o *Auto*, que va lenta a la totalitat); la vista; el punt d'observació (llista d'ubicacions, doble
  clic al terreny i *Tornar al punt d'observació*); una ajuda curta dels controls.
- **Avançat** (tancat per defecte): FPS i posició de la càmera, les dades del CNIG del punt amb les
  hores del nostre model al costat, les capes del CNIG sobre el terreny (enfosquiment, durada, ombres
  del relleu i límits de la totalitat), l'interruptor de les ombres del relleu i eines de depuració
  (exageració del relleu, filferros, mostrar el cub de navegació).
- **Barra de temps** (a baix): reproduir/pausar, ±5 min i l'hora, que es pot arrossegar, de 16:00 a
  23:30 (hora d'estiu). A sota, les hores de l'eclipsi al punt triat.

### Com es calcula l'eclipsi (`dades/`)

- **Posicions del Sol i la Lluna**: efemèrides de JPL Horizons (NASA/JPL), cada minut, passades a
  coordenades terrestres amb la precessió, la nutació i la rotació de la Terra (`dades/efemerides.py`).
- **Observador**: latitud, longitud i altitud sobre l'el·lipsoide WGS84 (`dades/geodesia.py`).
- **Part del Sol tapada**: des de cada punt, el Sol i la Lluna es veuen com dos discs; la part tapada
  és l'àrea on se solapen (`dades/model_eclipsi.py`). Els contactes (C1–C4), el màxim i la posta
  surten d'aquesta geometria; **no s'ajusten a cap dada del CNIG**.
- **Comprovació**: `python scripts/validar_model.py` compara les hores amb el CNIG a 9 punts (totes a
  ≤ 1,2 s), `python scripts/validar_ombra.py` comprova que l'eix de l'ombra cau dins de la umbra
  publicada pel CNIG i `python scripts/comparar_nasa.py` compara amb el calculador de la NASA amb les
  seves convencions (observador a 0 m, Sol sense refracció): hores a 2–4 s, explicades pel radi de la
  Lluna i el ΔT (pla, F11).
- **A l'escena**: la llum i l'ombra de la Lluna es calculen per a cada punt del terreny i de la Terra
  amb la mateixa fórmula, de manera que l'ombra es veu moure's i la resta de la cara de dia segueix
  il·luminada.
- **Il·lustratiu (no validat)**: el color del cel, el halo i la corona, el contorn blau de l'atmosfera
  de la Terra i la granulació animada del Sol. L'orientació de la Lluna és aproximada (sense libració).

---

## 3. Què hi ha a cada carpeta

```
main.py                  Programa principal: coordina l'escena (temps, astres, cel i teclat)
ui.py                    Interfície: el panell i la barra de temps (slimgui)
basecode/                Codi base de l'assignatura (el del repte 4, sense canvis) i els nostres objectes:
  engine.py, window.py, ui_panel.py, objects.py, camera.py, light.py, axis.py,
  meshloader.py, shaders.py       fitxers originals del professor (no es modifiquen)
  terra.py               La Terra (el·lipsoide amb textura, dia i nit, ombra de la Lluna)
  terrain.py             Relleu d'un MDT: mode globus (posat sobre la Terra) i mode pla (scripts)
  astres.py              El Sol (amb limbe i granulació), el seu halo i la Lluna (amb textura)
  ombres_relleu.py       Ombres del relleu (shadow mapping) a la zona de 5 m
  paret_cub.py           Les parets translúcides del cub de navegació
  control_ratoli.py      Ratolí capturat per mirar (amb el punt de mira), roda i trackpad
  sol.py                 La llum de l'escena (Light del basecode)
  camera_exploracio.py   Càmera lliure, del terreny fins a l'espai
  camera_observador.py   Càmera als ulls de l'observador (1,7 m sobre el terra)
  camera_orbital.py      Càmera orbital del mode pla (només per als scripts)
  programes.py           Carrega shaders amb opcions (#define)
  shaders/               gouraud i phong (originals); terrain, terra, esfera, ombra i paret (nostres)
dades/                   Lectura i càlcul de dades, sense OpenGL:
  efemerides.py          Posicions del Sol i la Lluna en coordenades terrestres
  geodesia.py            Latitud, longitud i altitud <-> coordenades terrestres (WGS84)
  model_eclipsi.py       Part del Sol tapada, contactes i centre de l'ombra
  observador.py          La ubicació de l'observador i la llista d'ubicacions
  navegacio.py           El cub de navegació i els trajectes dels viatges als astres
  data_io.py             Lectura dels MDT, neteja de les dades i fitxers auxiliars (data/cache/)
  eclipse_data.py        Lectura de les dades de l'eclipsi del CNIG
scripts/                 Descàrregues, captures, comprovacions i l'exercici 1.0 (veure secció 5)
models/                  Models .obj, cadascun a la seva carpeta (com al repte 4)
data/                    Dades (veure secció 4 i data/FONTS.md)
docs/                    Web de seguiment (obrir docs/index.html al navegador)
PLA_DE_TREBALL.md        Pla de treball: tasques, decisions i comprovacions
CLAUDE.md                Instruccions de treball de l'equip
requirements.txt         Llibreries de Python
```

Com al repte 4, `main.py` defineix un `GraphicsEngine` que hereta del `GraphicsEngineBase` de
`basecode/`: `on_init` crea la llum (el Sol, `self.light`), les càmeres, la Terra, el relleu i els astres;
`drawables()` són els objectes als quals la càmera escriu `m_proj` i `m_view`; `render()` els dibuixa i
`build_ui()` crida el panell de `ui.py`. Els objectes gràfics propis són fitxers nous dins de
`basecode/` (els originals del professor no es toquen) i el que no depèn d'OpenGL és a `dades/`. Cada objecte té `get_vbo`, `get_vao`, `get_shader_program`, `on_init`,
`render` i `destroy`. Els shaders són fitxers de `basecode/shaders/` i es carreguen amb
`basecode.shaders.load_program(ctx, nom)` (o amb `basecode/programes.py`, si cal activar opcions).

Unitats i coordenades de l'escena: quilòmetres, en coordenades terrestres (ECEF: X cap a la longitud 0,
Y cap a 90° E, Z cap al pol nord), que la CPU calcula en doble precisió; la GPU rep cada objecte relatiu
a la càmera. El mode pla dels scripts fa servir X = est, Y = altitud i Z = sud. Les dades fan
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
    zones/                (no es puja al git) zones de detall de les ubicacions catalanes, 5 m
      vic_5m.tif            Vic, 20 x 20 km                    (4000 x 4000 px)
      escala_5m.tif         L'Escala, 20 x 20 km               (4000 x 4000 px)
      valles_5m.tif         Cerdanyola, UAB i Montmeló, 31,7 x 28,5 km (6331 x 5692 px)
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
| `descarregar_efemerides.py` | Descarrega les posicions del Sol i la Lluna de JPL Horizons (`data/efemerides/`) |
| `descarregar_textures.py` | Descarrega les textures de la Terra i la Lluna (NASA, `data/textures/`) |
| `validar_model.py` | Compara les hores de l'eclipsi del nostre model amb les del CNIG a 9 punts |
| `validar_ombra.py` | Comprova que l'ombra de la Lluna cau dins de la umbra publicada pel CNIG |
| `prova_vistes.py` | Prova el programa a les sis ubicacions (ulls, mirar avall, pausa, allunyar-se comprovant la superfície, P a l'espai, botons, ombra) i la seqüència sencera amb el bucle real i el teclat i el ratolí simulats; captures a `captures/proves/`. Amb `--visible`, es veu a la finestra |
| `prova_navegacio.py` | Recorreguts de navegació (del terra al cel amb E, E/Q girant, mirar i apropar-se al Sol, la Lluna i la Terra, cancel·lar, sensibilitat, velocitat, P, tornar al punt): comprova salts, sobrepassaments i suavitat |
| `prova_controls.py` | Arrencada, cub de navegació (sis cares, teclat, roda, botons), enquadrar el Sol, ratolí capturat, panell, P i roda |
| `comparar_nasa.py` | Compara el model amb el calculador de circumstàncies locals de la NASA (`--calcular`: torna a executar el calculador, macOS i xarxa; sense opcions: fa servir `data/nasa/circumstancies_nasa.csv`) |
| `validar_horitzo.py` | Horitzó cap al Sol a les sis ubicacions: calculat sobre el MDT i sobre els triangles dibuixats, i llegit de la imatge; si el relleu tapa el Sol al màxim |
| `validar_ombres_relleu.py` | Ombres del relleu: GPU contra un càlcul de la CPU i comparació amb la capa d'ombres del CNIG (`--totes`: les sis ubicacions) |

Descàrrega d'MDT (els de `data/mdt/` ja hi són; només cal per refer-los o per a zones noves):

```bash
python scripts/descarregar_mdt.py peninsula     # 200 m -> data/mdt/peninsula_200m.tif
python scripts/descarregar_mdt.py asturias      #  25 m -> data/mdt/asturias_25m.tif
python scripts/descarregar_mdt.py picos         #   5 m -> data/mdt/picos_5m.tif
python scripts/descarregar_mdt.py luarca        #   5 m -> data/mdt/luarca_5m.tif
python scripts/descarregar_mdt.py vic           #   5 m -> data/mdt/zones/vic_5m.tif
python scripts/descarregar_mdt.py escala        #   5 m -> data/mdt/zones/escala_5m.tif
python scripts/descarregar_mdt.py valles        #   5 m -> data/mdt/zones/valles_5m.tif
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
- **Posicions del Sol i la Lluna**: JPL Horizons (NASA/JPL), `https://ssd.jpl.nasa.gov/horizons/`.
- **Comprovació externa**: calculador de circumstàncies locals de la NASA. "Eclipse Predictions by Fred
  Espenak, NASA's GSFC"; calculador de Xavier Jubier.
- **Coordenades de les ubicacions**: geocodificador de l'ICGC i OpenStreetMap (© col·laboradors
  d'OpenStreetMap, ODbL).
- **Textures**: NASA Visible Earth ("Blue Marble", la Terra) i NASA SVS ("CGI Moon Kit", la Lluna),
  domini públic.

El detall de cada fitxer (zona, resolució, CRS, llicència i com es torna a descarregar) és a
`data/FONTS.md`.
