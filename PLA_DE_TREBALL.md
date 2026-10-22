# PLA DE TREBALL — Projecte EGRA (eclipsi del 12/08/2026 sobre terreny real)

Aquest fitxer és **la referència del pla**. S'actualitza cada vegada que acordem un canvi o
completem una tasca. Estats possibles d'una tasca:

| Estat | Significat |
|---|---|
| `PENDENT` | No s'ha començat |
| `EN CURS` | S'hi està treballant |
| `FET` | Implementat i amb les comprovacions de Claude descrites; pendent de revisió de l'equip |
| `VALIDAT` | L'equip ha fet i confirmat la comprovació indicada |

Una tasca **només** passa a `VALIDAT` quan l'equip ha fet la comprovació de la seva fitxa i n'ha
entès el resultat. Executar una ordre sense entendre'n la sortida no la valida.

Les instruccions estables de treball són a `CLAUDE.md`. Aquest pla en recull l'aplicació concreta:
tasques, decisions, dependències, comprovacions i estat.

Darrera actualització: 2026-10-22 (`CLAUDE.md` nou; P12 resolta).

---

## 0. Regles de treball

1. **Una tasca petita cada vegada.** En acabar: una explicació entenedora i una comprovació que
   pugui fer l'equip. No es continua fins que l'equip ho prova i ho demana.
2. **Tres tipus de canvis, mai barrejats en una mateixa tasca:**
   - **R — reorganització:** mou fitxers o codi **sense canviar el comportament**. Es comprova
     amb captures de la mateixa escena, fetes al mateix ordinador i en les mateixes condicions
     (idèntiques píxel a píxel en aquest entorn controlat; no és una garantia entre GPUs), i amb
     la llista de proves manuals.
   - **C — correcció / canvi de comportament:** el comportament canvia a propòsit. Té una
     comprovació numèrica o visual abans/després.
   - **N — funcionalitat nova.**
3. Cap representació visual es presenta com a simulació validada. A la interfície i a la web,
   tot el que sigui il·lustratiu s'etiqueta com a **"il·lustratiu"**, i les eines de depuració
   com a **"depuració"**.
4. No es fan commits, push, instal·lacions, descàrregues grans, eliminacions de dades ni
   reescriptures de l'historial sense autorització explícita. Una autorització ja donada per a
   una acció concreta no cal repetir-la.
5. `TASQUES_TERRENY.md` no és la cua de treball vigent: només és un antecedent. `CLAUDE_ANTIC.md`
   és l'arxiu històric de les instruccions antigues (només local, fora del Git).
6. Senzillesa: no s'afegeixen capes ni abstraccions sense una necessitat concreta. No es complica
   el model només per fer encaixar decimals: primer s'explica quin efecte visible té cada error.

---

## 1. Decisions

### 1.1 Preses

| # | Decisió | Data |
|---|---|---|
| D1 | La prioritat és **entendre i poder explicar** el projecte, abans que afegir funcionalitats. | 22/10 |
| D2 | Estructura senzilla, semblant a la de classe (repte 4). Els fitxers originals de `basecode/` es conserven idèntics; els objectes propis s'hi poden **afegir** com a fitxers nous. | 22/10 |
| D3 | **Fora el personatge** (les dues esferes), els salts i l'enfocament de videojoc. | 22/10 |
| D4 | Dues maneres de mirar: **càmera d'exploració** (inspeccionar el terreny i triar un punt) i **vista d'observació** a l'altura dels ulls, sense ninot. La **ubicació de l'observador** és una dada separada de qualsevol representació visual. | 22/10 |
| D5 | **Durant la reproducció des del terreny, la ubicació de l'observador queda bloquejada.** Es pot girar la mirada i fer zoom. Per canviar de punt cal aturar la reproducció. Les coordenades, les dades del CNIG i el model sempre corresponen al mateix punt. | 22/10 |
| D6 | **Mode normal:** curvatura terrestre activa i exageració vertical = 1. Desactivar la curvatura o exagerar el relleu són **eines didàctiques / de depuració**, clarament etiquetades. | 22/10 |
| D7 | La retirada del personatge és un **canvi de comportament (C)**, separat de la reorganització de fitxers (R). | 22/10 |
| D8 | Ubicacions objectiu: **Vic, l'Escala, Cerdanyola, Montmeló i la UAB** (eclipsi parcial). **Picos** es manté provisionalment com a cas de totalitat. | 22/10 |
| D9 | Cal distingir sempre **la cobertura de la Lluna** (quant Sol tapa) de **l'ocultació del Sol pel relleu**. | 22/10 |
| D10 | Les descàrregues grans i les caches no han de fer créixer el Git, però les dades han de ser reproduïbles (font, zona, resolució, CRS, llicència, comanda). **No es reescriu l'historial.** Abans d'eliminar un mapa se'n comproven les dependències. | 22/10 |
| D11 | Web de seguiment **per objectius i subobjectius desplegables (tipus Notion)**. Comença senzilla i creix amb cada tasca. Els percentatges responen a criteris verificables. | 22/10 |
| D12 | Les correccions del model s'han d'entendre i defensar. Abans de corregir, cal confirmar les convencions de les dades de referència (veure §6). | 22/10 |
| D13 | MDS (arbres i edificis): només **estudi** com a ampliació (§9). El MDT es conserva per situar l'observador. | 22/10 |
| D14 | Vista des de la Lluna i textura del Sol: es volen explorar, separant el que és **il·lustratiu** del que seria **astronòmicament coherent** (§8). | 22/10 |
| D15 | (P1, P2) Preservació: branca `reorganitzacio-projecte`, commit de l'estat actual i etiqueta `abans-reorganitzacio`, **sense push**. `PLA_DE_TREBALL.md` es versiona; `CLAUDE_ANTIC.md` es queda **només local** (fora del commit). Res de `git add .`: fitxers revisats un a un. | 22/10 |
| D16 | (P7) S'accepta l'estructura de §4 (`ui.py`, `dades/`, `camera_exploracio.py`, `camera_observador.py`), conservant els originals del professor. Res d'abstraccions sense necessitat. | 22/10 |
| D17 | (P3) Les coordenades es verifiquen amb una font cartogràfica fiable o un geocodificador, i se'n documenta la font. Volem **punts concrets** (plaça Major, ajuntament, plaça Cívica...), no el centre del municipi. Si un punt és ambigu, es pregunta només per aquell. | 22/10 |
| D18 | (P4) **No** s'aplica k ≈ 0,13 al terreny. Punt de partida: terreny amb **curvatura geomètrica** (R = 6371 km) i exageració 1; el Sol amb la seva elevació aparent (refracció astronòmica). Les aproximacions atmosfèriques es documenten (§7). El renderitzat i els scripts d'horitzó segueixen la mateixa convenció. | 22/10 |
| D19 | (P5) Els llindars de §6.4 són **objectius provisionals de comprovació**, no una garantia de precisió. Es separen tres tipus d'error (§6.4). | 22/10 |
| D20 | (P6) Comprovació independent: una **font externa fiable consultada a mà** en uns quants punts i moments, **sense noves dependències**. Les dades del CNIG no usades a l'ajust són una comprovació complementària, **de la mateixa font**. Cada comparació documenta hora, coordenades, refracció i definició dels contactes. | 22/10 |
| D21 | (P8) MDT nous a una carpeta ignorada per Git; Picos continua versionat com a exemple inicial. Fonts i instruccions de descàrrega documentades. Sense reescriure l'historial. | 22/10 |
| D22 | (P9) Primer la **vista il·lustrativa** des de la Lluna, identificada com a tal. La vista coherent és una ampliació posterior. El Sol amb textura es manté al pla, i més endavant una animació **visual** de la superfície (sense simular el plasma). | 22/10 |
| D23 | (P10) Font externa per a la comprovació independent: el **calculador de circumstàncies locals de la NASA** per a l'eclipsi de 2026 (convencions a §6.3.1). | 22/10 |
| D24 | (P11) Si en verificar les coordenades un punt és ambigu, es pregunta a l'equip **només per aquell punt**. | 22/10 |
| D25 | (P12) `CLAUDE.md` substituït per la versió nova de l'equip (instruccions estables de treball). `CLAUDE_ANTIC.md` es conserva sense canvis com a arxiu històric local. En aquell moment el nou `CLAUDE.md` mantenia la política de versionament (ignorat pel Git); canviat a D27. | 22/10 |
| D26 | Ritme: avançar amb **tasques reals** del projecte. Els conceptes s'expliquen quan apareixen a la implementació, amb explicacions curtes lligades al codi. No s'afegeixen exercicis independents ni passos d'aprovació nous si l'equip no els demana. | 22/10 |
| D27 | `CLAUDE.md` passa a versionar-se (instruccions compartides de l'equip): es treu la regla corresponent del `.gitignore`. `CLAUDE_ANTIC.md` continua fora dels commits. | 22/10 |
| D28 | Compartir la feina: push de la branca `reorganitzacio-projecte` i de l'etiqueta `abans-reorganitzacio` a `origin`, **sense fusionar amb `main`** ni canviar la visibilitat del repositori. | 22/10 |
| D29 | Web de seguiment: primera versió **local** a `docs/` (HTML, CSS i JavaScript mínim, sense frameworks ni WebGL) abans de la reorganització del codi. **No es publica encara** amb GitHub Pages. | 22/10 |
| D30 | La web es basa en els objectius **1 i 2 de l'acta 3 final** (PDF del 15/10). L'antic O3 ("Del dada oficial a la GPU", de l'esborrany `acta3.md`, que ja no hi és a `actes/`) es mostra com a objectiu propi del pla, **marcat com a no inclòs a l'acta final**. Substituït per D31. | 22/10 |
| D31 | (P13) **Es retira l'O3.** Els seus subobjectius es reparteixen: la reproduïbilitat de les dades va a **O1.1** (dades del terreny), la validació del model a un nou **O1.12** i l'organització del codi i del treball a un nou **O2.6**. | 22/10 |

### 1.2 Pendents

Cap pregunta oberta en aquest moment. (Historial: P1–P13 resoltes a D15–D25 i D31.)

---

## 2. Funcionalitats existents (codi actual, després de la F2)

El **comportament** és el mateix que el de la fotografia guardada a l'etiqueta
`abans-reorganitzacio`: la fase F2 només ha mogut fitxers i codi (veure F2 a §11). Les rutes
d'aquesta taula són les **actuals**; a l'etiqueta els fitxers eren a l'arrel del projecte.

Res d'aquesta llista no està validat formalment per l'equip.

| Funcionalitat | On és | Estat / observacions |
|---|---|---|
| Terreny 3D d'un MDT (heightmap a textura, graella de 1024² vèrtexs, faldilles, colors per altitud, mar, boira) | `basecode/terrain.py`, `basecode/shaders/terrain.*`, `dades/data_io.py` | Funciona (captura sense finestra comprovada) |
| Overlays del CNIG (enfosquiment, durada, ombres del relleu, límits de la totalitat) | `dades/eclipse_data.py`, `terrain.frag` | Funciona |
| Una sola regió carregada (Picos, 5 m, 20×20 km) | `main.py` (`REGIO`) | Sense relleu fora dels 20 km |
| Càmera orbital (arrossegar, roda, doble clic) | `basecode/camera_exploracio.py` | Funciona. Ara segueix el personatge |
| **Personatge** de dues esferes que camina (WASD) i salta | `basecode/personatge.py`, `main.py` | **Es retirarà (D3)** |
| Primera persona als ulls del personatge (zoom de prismàtics, seguir el Sol) | `basecode/camera_observador.py` | Es convertirà en la vista d'observació |
| Tecla P: primera persona mirant el Sol i reproducció des de C1 | `main.py` (`eclipsi_des_d_aqui`) | Es mantindrà amb un altre nom/flux |
| Barra de temps (play, ±5 min, velocitats, Auto) | `ui.py` (`barra_temps`) | Funciona |
| Model del Sol (NOAA + correcció constant al màxim del CNIG) i de la Lluna (recta ajustada als contactes del CNIG) | `dades/model_eclipsi.py` | Errors coneguts (§6) |
| Llum del terreny i del cel segons el Sol visible i el crepuscle; halo i corona | `main.py` (`actualitzar_llum`), `basecode/astres.py`, `esfera.frag` | Il·lustratiu (no és un model físic del cel) |
| Lluna a distància artificial (per defecte, 2 × la mida del terreny), amb la mida aparent real | `main.py` (`distancia_lluna`), `basecode/astres.py` | **Il·lustratiu** (§8) |
| Botó "Mirar des de darrere la Lluna" | `ui.py` (`panell_avancat`) | **Il·lustratiu**: no és una vista des de la Lluna real |
| Curvatura (desactivada per defecte) i exageració (slider de 1 a 20) | `basecode/terrain.py`, `terrain.vert` | Per defecte, la curvatura està **desactivada** (contradiu D6) |
| Scripts: descàrrega WCS, caches, captura, exercici 1.0 | `scripts/` | Funcionen (captura, caches i exercici comprovats després de la F2; la descàrrega no s'ha tornat a executar) |

---

## 3. Funcionalitats proposades (resum)

| Funcionalitat | Tipus | Mínim / opcional | Fase |
|---|---|---|---|
| Càmera d'exploració lliure (sense personatge) | C | Mínim | F3 |
| Selecció d'un punt d'observació (marcador simple, no ninot) | C | Mínim | F3 |
| Vista d'observació als ulls (1,7 m sobre el MDT), amb la ubicació bloquejada durant la reproducció | C | Mínim | F3 |
| Curvatura activa i exageració 1 en mode normal; controls de depuració etiquetats | C | Mínim | F3 |
| Correccions del model (contactes, convergència UTM, refracció) | C | Mínim | F3 |
| Zona del Vallès (Cerdanyola, UAB, Montmeló) amb horitzó suficient; després Vic i l'Escala | N | Mínim | F4 |
| Web de seguiment desplegable | N | Mínim | F5 |
| Ombres del relleu (shadow mapping) i menú de meteorologia (acta 3) | N | Mínim (segons l'acta 3) | F6 |
| Textura del Sol (enfosquiment del limbe) | N | Opcional | F7 |
| Animació de la superfície del Sol | N | Opcional, il·lustratiu | F7 |
| Vista il·lustrativa des de la Lluna | N | Opcional, il·lustratiu | F7 |
| Vista coherent des de la Lluna | N | Opcional, gran | F8 |
| Nivells de detall per rajoles i descàrrega en segon pla | N | Opcional | F8 |
| MDS (arbres i edificis) | N | Opcional, només estudi ara | F8 |

---

## 4. Estructura de fitxers (acceptada: D16; feta a la F2)

**Conservar el basecode** vol dir que aquests fitxers queden **idèntics byte a byte** als de
`repte4/basecode/` (es comprova amb `diff -r`): `__init__.py`, `engine.py`, `window.py`,
`ui_panel.py`, `objects.py`, `camera.py`, `light.py`, `axis.py`, `meshloader.py`, `shaders.py`,
`requirements.txt`, `shaders/gouraud.*` i `shaders/phong.*`. Estat a 22/10: **tots idèntics**.

Al repte 4 real, les classes pròpies (`Sphere`, `MeshObject`...) són dins de `repte4.py`. Com que
el nostre projecte en té moltes, les posem en fitxers propis **afegits** a `basecode/`, tal com
demanàveu inicialment, sense tocar-ne cap d'original.

Estructura **actual** (després de la F2):

```
main.py                         GraphicsEngine: on_init, drawables, render (temps, llum, teclat)
ui.py                           build_ui(app): panell "Opcions" i barra de temps
basecode/                       ORIGINALS sense canvis, més els nostres objectes:
  sol.py                          Sol (Light amb azimut i elevacio)
  terrain.py                      Terrain
  astres.py                       Esfera, Lluna (Sol visible i halo)
  personatge.py                   Personatge (es retirara a la tasca 3.1)
  camera_exploracio.py            CameraExploracio (abans camera.py, classe Camera)
  camera_observador.py            CameraObservador (abans camera_primera_persona.py; encara va
                                  lligada al personatge)
  shaders/                        gouraud, phong (originals) + terrain, esfera (nostres)
dades/                          sense OpenGL: data_io.py, eclipse_data.py, model_eclipsi.py
scripts/                        descarregar_mdt.py, preparar_dades.py, captura.py, exercici_fotograma.py
models/                         .obj, com al repte 4
data/                           MDT, dataset del CNIG, cache (veure §10)
docs/                           web de seguiment
```

Previstos més endavant: `dades/observador.py` (ubicació de l'observador, sense dibuix; tasca 3.1)
i `scripts/validar_model.py` (tasca 0.2).

**Constants compartides:** les mides aparents del Sol i la Lluna (`RADI_*`, `DIST_*`) les fa servir
tant el model de l'eclipsi com el dibuix. Abans eren a `astres.py` i `model_eclipsi.py` les
importava d'allà, és a dir, les dades depenien d'un mòdul gràfic. Ara es defineixen una sola vegada
a `dades/model_eclipsi.py` i `basecode/astres.py` i `main.py` les importen d'allà. Les dependències
van en un sol sentit (gràfics → dades) i no hi ha cap import circular.

`basecode/personatge.py` desapareix a la tasca de retirada del personatge (C, F3), no a la reorganització.

---

## 5. Com es dibuixa un fotograma (resum per a l'equip; s'amplia a la web, subobjectiu O2.1)

1. `main.py` crea `GraphicsEngine` → `basecode/engine.py`: glfw obre la finestra amb un context
   OpenGL 3.3 core; `moderngl.create_context()` s'hi connecta; s'activa el test de profunditat;
   es crea imgui; es crida `on_init()` (el nostre).
2. `on_init()` crea el Sol (`Light`), el terreny (textures, VBO/IBO, VAO, programa), les càmeres,
   els astres i el model de l'eclipsi.
3. Bucle `run()`: esdeveniments → `dt` → `render()` → panell → `swap_buffers` (doble buffer).
4. `render()`: lògica (temps, llum) → la càmera calcula `m_view` (`lookAt`) i `m_proj`
   (`perspective`, near/far) i les escriu a tots els `drawables()` → `clear` → cada objecte fa
   `render()` (uniforms per fotograma, textures a les unitats 0–4, `vao.render()`).
5. **VBO**: les dades dels vèrtexs a la GPU (terreny: només UV). **IBO**: els índexs que reutilitzen
   vèrtexs. **VAO**: com es llegeix el VBO cap a les entrades del shader. **Programa**: vertex
   shader + fragment shader. **Uniforms**: valors comuns a una crida (`m_proj`, `m_view`,
   `m_model`, `sun_dir`...).
6. Al vertex shader del terreny, l'altura es llegeix d'una textura (desplaçament) i es calcula
   `gl_Position = m_proj · m_view · m_model · p`. Al fragment shader, la normal (a partir del
   gradient a 5 m), el color, la llum, la boira i els overlays.

---

## 6. El model de l'eclipsi: explicacions prèvies a les correccions

### 6.1 Què llegim del CNIG i què calculem nosaltres

Exemple: Picos (43,2620 N; 4,9490 O).

| Dada | D'on surt | Valor |
|---|---|---|
| Hores de C1, C2, màxim, C3, C4, sortida i posta del Sol | **CNIG** (bandes 4–10), al píxel (~920 m) que conté el punt | C1 19:31:39, màx. 20:28:02, C4 21:20:55 (CEST) |
| Enfosquiment (*obscuration*) al màxim | **CNIG** (banda 3) | 1,0000 |
| Elevació i azimut del Sol al màxim | **CNIG** (bandes 1 i 2) | 9,596°, 281,4° |
| Ombres del relleu al màxim | **CNIG** (`terrain_shadows`, ~230 m sobre el terreny) | classe 1 |
| Posició del Sol a **qualsevol** hora | **Nosaltres**: algorisme de la NOAA + una correcció constant perquè al màxim coincideixi amb el CNIG | |
| Posició de la Lluna a qualsevol hora | **Nosaltres**: la Lluna es mou en línia recta i a velocitat constant respecte del Sol; la velocitat i la distància mínima s'**ajusten** amb les hores del CNIG | |
| % de Sol tapat a qualsevol hora | **Nosaltres**: àrea de solapament de dos discos | |
| Horitzó i ocultació pel relleu a qualsevol hora | **Nosaltres** (pendent d'implementar al programa; de moment només un script de prova) | |

### 6.2 Per què l'aproximació actual desplaça C1 i C4

El model suposa que la Lluna fa una recta a velocitat constant, i que el punt més proper al Sol
és al **màxim**. Llavors C1 i C4 queden **simètrics** respecte del màxim:
C1 = màx − w i C4 = màx + w, amb w = (C4 − C1)/2.

Però al CNIG, a Picos, la meitat d'abans dura **56 min 23 s** (C1 → màx.) i la d'després **52 min
53 s** (màx. → C4). La diferència és de 3 min 30 s. El model reparteix els 109 min 16 s en dues
meitats iguals de 54 min 38 s, i per tant posa C1 a 19:33:24 (**105 s tard**) i C4 a 21:22:40
(**105 s tard**). A la resta de punts provats passa el mateix (de 93 a 105 s tard).

C2 i C3 sí que surten bé (errors ≤ 0,1 s), perquè la totalitat dura menys de 2 minuts i en un
interval tan curt la recta a velocitat constant és una bona aproximació.

Causa probable de l'asimetria (encara **no demostrada**, cal estudiar-la): l'observador gira amb la
Terra, de manera que el moviment aparent de la Lluna respecte del Sol no és ni recte ni uniforme
durant gairebé dues hores (la paral·laxi canvia amb l'altura del Sol).

### 6.3 Ajust a les dades vs. comprovació independent

- **Ajust:** fem servir unes dades per fixar els paràmetres del model. Per exemple, la velocitat
  de la Lluna i la distància mínima surten de C1, C4 i la durada de la totalitat. Que el model
  reprodueixi **aquestes** dades **no demostra res**: ho fa per construcció. Ara mateix, la
  coincidència de l'enfosquiment al màxim (4 decimals) i de C2/C3 és, en bona part, un ajust.
- **Comprovació independent:** comparar el model amb dades que **no** s'han fet servir per
  ajustar-lo. Opcions (decisió D20: es comença per la 2, sense noves dependències; la 1 és complementària i de la mateixa font; la 3 queda descartada de moment):
  1. Del mateix CNIG: ajustar sense una dada (p. ex. sense C4) i predir-la; comparar l'hora de la
     posta (banda 5) amb la del nostre Sol; comparar amb l'ombra de la Lluna del GeoPackage
     (corbes cada 3,6 s).
  2. Una font externa (NASA/Espenak, efemèrides de l'OAN) consultada a mà en pocs punts.
  3. Una llibreria d'efemèrides (p. ex. Skyfield amb JPL). Caldria permís per instal·lar-la.

### 6.3.1 Font externa: el calculador de la NASA (D23)

Verificat el 22/10/2026 (pàgina i codi del calculador llegits):

- **Enllaç exacte:** <https://eclipse.gsfc.nasa.gov/SEgoogle/SEgoogle2001/SE2026Aug12Tgoogle.html>
  ("Total Solar Eclipse of 2026 Aug 12", mapa interactiu de la NASA/GSFC).
- **Com es consulta:** es fa clic al mapa i un globus mostra les circumstàncies locals d'aquell punt.
  No hi ha cap camp per escriure coordenades: el punt es col·loca a mà i el globus en mostra la
  latitud i la longitud decimals. **A cada comparació s'han d'anotar les coordenades que mostra el
  globus**, no les que volíem, i comparar-les amb les del CNIG en aquell mateix punt.
- **Què dona:** tipus d'eclipsi, durada de la totalitat, magnitud (fracció del **diàmetre** tapada),
  enfosquiment (*obscuration*, fracció de l'**àrea**; és la que es compara amb la banda 3 del CNIG),
  i per a C1, C2, màxim, C3 i C4: data, hora en **TU** i altura i azimut del Sol.
- **Convencions (de la pàgina i del fitxer `SEcirc.js`):**
  - Prediccions de Fred Espenak (NASA/GSFC), efemèrides VSOP87/ELP2000-85, elements de Bessel.
  - **ΔT = 71,4 s** (valor previst quan es va fer el mapa). Si el ΔT real d'aquell dia va ser diferent
    (valor a consultar a l'IERS), totes les hores es desplacen aquesta diferència.
  - **Altitud de l'observador = 0 m** (nivell del mar) fixa al codi (`obsvconst[2] = 0`). El CNIG fa
    servir l'altitud del GMTED. És una diferència coneguda de convenció.
  - **Altura del Sol sense refracció** (geomètrica): el codi la calcula directament
    (`Math.asin(...)`), sense cap terme de refracció. El CNIG (banda 1) sí que la inclou: per
    comparar-les cal treure la refracció del CNIG o afegir-la a la NASA, i documentar-ho.
  - Azimut des del nord cap a l'est (N = 0°, E = 90°, S = 180°, O = 270°), la mateixa convenció
    que fem servir nosaltres.
  - **Limbe mitjà de la Lluna:** les prediccions *no* inclouen les muntanyes i valls de la vora de la
    Lluna. La mateixa pàgina avisa que això canvia els contactes i les durades ~1–3 s.
  - Si el Sol és sota l'horitzó en un contacte, el globus hi afegeix un asterisc.
- **Atribució obligatòria:** "Eclipse Predictions by Fred Espenak, NASA's GSFC". El calculador del
  mapa és de Xavier Jubier.
- **Conseqüència per als llindars (§6.4):** amb una incertesa de ~1–3 s pel limbe i ~1–2 s pel ΔT,
  l'objectiu de ≤ 5 s als contactes té sentit; demanar menys no.

### 6.4 Quina precisió necessitem (objectius provisionals, D19)

Dades mesurades a la UAB i a Picos al voltant del màxim:
- El Sol baixa **0,18° per minut**. El seu diàmetre és ~0,53°.
- La Lluna es mou ~**0,010° per minut** respecte del Sol: tarda ~53 min a recórrer un diàmetre solar.

| Magnitud | Precisió proposada | Per què |
|---|---|---|
| Hores de contacte (C1–C4) | ≤ 5 s | 5 s de Lluna ≈ 0,001°: no es veu a la pantalla; l'hora mostrada (hh:mm:ss) ha de coincidir amb el CNIG |
| Elevació del Sol | ≤ 0,02° | ≈ 7 s de descens del Sol; és ≈ 1/25 del seu diàmetre |
| Azimut del Sol a l'escena | ≤ 0,05° | Ara l'error és de 1,3° a 4,1° (convergència UTM, §7) |
| Angle de l'horitzó | ≤ 0,05° (objectiu), ≤ 0,1° (acceptable) | Amb el Sol a 4°, decidir si el relleu el tapa requereix una fracció del seu diàmetre |
| % de Sol tapat | ≤ 0,5 punts percentuals | El panell en mostra un decimal |

Aquests llindars són **objectius de comprovació**, no una garantia que el resultat sigui tan precís
com la realitat. Cada comparació indicarà a quin dels tres tipus d'error pertany:

1. **Error respecte de les dades de l'ajust:** comparar amb C1, C4, la durada o el Sol al màxim del
   CNIG, que són les dades amb què s'ha construït el model. Detecta errors de programació, però no
   valida el model.
2. **Error respecte d'una referència independent:** una font externa (D20) o dades del CNIG no
   usades a l'ajust (aquestes últimes, identificades com a "mateixa font").
3. **Limitacions que no són del model:** la resolució del terreny (5 m, malla de 20 m, 200 m), la
   ubicació de l'observador (coordenades, altitud de l'ull, MDT sense edificis) i l'atmosfera
   (refracció real desconeguda).

### 6.4.1 Quin efecte visible té cada error i què aporta més corregir-lo

| Error actual | Efecte visible | Valor de corregir-lo |
|---|---|---|
| **Azimut del Sol i la Lluna girats 1,3°–4,1°** (convergència UTM) | El Sol es pon darrere d'una muntanya que no és la correcta; a l'Escala, el desplaçament lateral és de ~8 diàmetres solars | **Molt alt**, i la correcció és senzilla (un gir) |
| **Terreny limitat a 20 km i malla de 20 m** | L'horitzó canvia fins a 3° segons la resolució (Picos); fora dels 10 km no hi ha relleu | **Molt alt** per a la vista d'observació (F4) |
| **Correcció de refracció constant** | El Sol és correcte al màxim però queda massa baix a prop de la posta: a la UAB, ~0,38° a l'horitzó, i la posta s'avança ~2 min. A Catalunya la posta és abans de C4, o sigui que es nota | **Alt** a les ubicacions catalanes |
| **C1 i C4 ~100 s tard** | El rellotge diu que l'eclipsi comença 1 min 45 s més tard que el CNIG; la posició de la Lluna es desvia ~0,018° (~3 % del diàmetre del Sol), que no es nota a simple vista | **Mitjà**: es veu al rellotge, gairebé no a la imatge |
| **`durada` inexistent sense dades** | Cap ara mateix (el curtcircuit l'amaga), però és un error latent | **Baix cost**: s'arregla amb una línia |

Ordre proposat de correccions: convergència (3.5) → curvatura i horitzó coherents (3.4) → refracció
del Sol (3.6) → contactes (3.7). La `durada` (3.3) es pot fer en qualsevol moment.

### 6.5 Convencions de les dades de referència (comprovades)

Font: `data/eclipsi2026/doc/Description_eclipses.pdf` (CNIG).
- **Banda 1:** *"elevation of the centre of the Sun in degrees, corrected for refraction, at the
  moment of maximum eclipse"*. **Confirmat per la documentació:** l'elevació del CNIG és
  l'**aparent** (amb refracció). La documentació no diu amb quina pressió i temperatura es calcula.
- **Banda 2:** azimut del centre del Sol al màxim. La documentació no diu la convenció; els valors
  (265°–293°, Sol a l'oest al vespre) són compatibles amb "des del nord, en sentit horari".
- Les efemèrides es calculen per a la latitud, la longitud i l'**altitud** del GMTED2010 (~800 m)
  de cada punt.
- Les ombres del relleu es calculen amb el GMTED2010 de ~200 m i la rutina `insol`, sense edificis
  ni arbres, **només al màxim**.
- **No documentat:** si les hores de contacte tenen en compte la refracció. Pendent d'esbrinar
  (p. ex. a https://eclipses.ign.es/condiciones-de-observacion.html).

**La diferència d'elevació (CNIG − NOAA geomètrica)** és compatible amb la refracció estàndard
(fórmula de Bennett), però això **no la demostra**: només és coherent.

| Punt | Elev. NOAA (geomètrica) | CNIG | Diferència | Bennett | Residu |
|---|---|---|---|---|---|
| Picos | 9,502° | 9,596° | +0,094° | 0,094° | +0,000° |
| Burgos | 8,185° | 8,294° | +0,110° | 0,108° | +0,001° |
| València | 4,371° | 4,548° | +0,176° | 0,183° | −0,007° |
| UAB | 3,824° | 4,016° | +0,192° | 0,202° | −0,010° |
| L'Escala | 3,496° | 3,698° | +0,201° | 0,216° | −0,014° |
| Palma | 2,365° | 2,624° | +0,260° | 0,277° | −0,017° |

El residu creix com més baix és el Sol, cosa esperable perquè la refracció a prop de l'horitzó
depèn de la pressió i la temperatura. Les diferències d'azimut són ≤ 0,004°.

Conseqüència per al codi actual: la correcció és **constant** al llarg del temps, però la
refracció canvia amb l'altura del Sol (≈0,09° a 10°, ≈0,57° a l'horitzó). Per tant, el nostre Sol
és correcte al màxim i s'equivoca cada vegada més a prop de la posta.

### 6.6 Validació: estat a 22/10/2026

**Comprovat executant** (scripts de prova fora del repositori; es passaran a `scripts/validar_model.py` a la tasca 0.2):
- Tots els `.py` compilen; `captura.py` renderitza Picos sense finestra.
- A 9 punts (Picos, Burgos, València, Palma i els 5 catalans): C2/C3 a ≤ 0,1 s; C1 i C4 de 93 a
  105 s tard; enfosquiment al màxim igual (per construcció).
- `ModelEclipsi` en un punt sense dades (55 N, 0): l'atribut `durada` **no existeix**.
  `main.py:220` no falla només pel curtcircuit de `and`.
- Convergència de meridians (UTM 30): −1,34° a Picos, de +3,4° a +4,1° a Catalunya. Signe
  comprovat: l'azimut de quadrícula = azimut geogràfic − γ (γ de pyproj). El codi fa servir l'azimut
  geogràfic com si fos de quadrícula.
- Resolució de la geometria: a Picos, 5 m a la textura i blocs de 20 m a la malla. Horitzó cap al Sol
  des del centre de Picos (amb la convergència corregida): 5,82° (5 m), 5,56° (malla), 2,70° (200 m).
- Variació dins dels 20 km de Picos: C2 ±8 s, durada de 98,7 a 102,2 s.

**Deduït llegint el codi:**
- Si es camina durant la reproducció, el model queda congelat al punt antic i el panell barreja
  coordenades noves amb dades velles (`main.py:262`). Es resol amb D5.
- La direcció de la Lluna també està girada γ graus (mateix marc geogràfic).
- `centre_curvatura` només l'actualitza la càmera orbital (`basecode/camera_exploracio.py`, `update()`). A la vista de primera
  persona, la curvatura es mesura des de l'últim objectiu de la càmera orbital, no des de
  l'observador.
- El renderitzat fa servir la curvatura **geomètrica** (d²/2R, sense refracció). El script
  d'horitzó feia servir el radi efectiu (k = 0,13). **Encara no són coherents** (§7).
- El MDT és de terreny nu: no hi ha edificis ni arbres.
- `eclipse_data.punt()` obre els fitxers i crea un `Transformer` a cada crida.

**Pendent:**
- Provar el programa amb finestra (ho ha de fer l'equip).
- Comprovació independent del model (D20, font pendent P10, tasca 3.8).
- Costat per on passa la Lluna (nord/sud del Sol).
- Si les hores de contacte del CNIG inclouen refracció.
- Coordenades exactes de les ubicacions (D17, tasca 0.3).

---

## 7. Curvatura, horitzó i orientació: convencions que han de coincidir

### 7.1 Dues refraccions diferents

- **Refracció astronòmica (del Sol):** la llum del Sol travessa **tota** l'atmosfera i es corba;
  el Sol sembla més alt del que és. A 10° són ~0,09°; a l'horitzó, ~0,57°. Depèn de la pressió i la
  temperatura. L'elevació del CNIG (banda 1) ja la inclou.
- **Refracció terrestre (del relleu):** la llum d'una muntanya llunyana travessa només la capa
  baixa de l'atmosfera, entre la muntanya i l'observador; la muntanya sembla una mica més alta.
  Es modela amb un coeficient k (0,13 és un valor "típic", però canvia molt amb el gradient de
  temperatura prop del terra, fins i tot de signe). L'efecte sobre l'angle d'un punt a distància d
  és ≈ k·d/(2R).

Són **dos efectes diferents** sobre **dos raigs diferents** (el del Sol i el de la muntanya). Per
tant, aplicar la refracció astronòmica al Sol i, a més, la terrestre al relleu **no és comptar dues
vegades** el mateix efecte. Però tampoc no està justificat aplicar k = 0,13 només perquè el Sol
porta refracció: el valor de k real és desconegut i variable.

### 7.2 Convenció adoptada (D18)

- **Sol:** elevació aparent (geomètrica + refracció astronòmica). És la mateixa convenció que el CNIG.
- **Terreny:** **geometria pura**, amb curvatura geomètrica (R = 6371 km, k = 0) i exageració 1. La
  refracció terrestre **no s'aplica** i es documenta com a aproximació.
- **Magnitud de l'aproximació** (si la k real fos 0,13): el relleu quedaria massa baix en
  ≈ 0,0006° a 1 km, 0,003° a 5 km, 0,006° a 10 km, 0,03° a 50 km i 0,06° a 100 km. Per als horitzons
  propers (< 20 km) és molt menor que el llindar de 0,05°; per a horitzons llunyans s'hi acosta.
- En comparació, la caiguda per curvatura geomètrica és molt més gran: ≈ 0,045° a 10 km, 0,22° a
  50 km i 0,45° a 100 km. Per això ha d'estar activa.

### 7.3 Què han de compartir el renderitzat i els scripts d'horitzó

1. **El mateix origen de la curvatura: l'observador** (ara és l'objectiu de la càmera orbital, i a
   la primera persona no s'actualitza). La caiguda d'un punt a distància d és d²/(2R).
2. **El mateix radi**: R = 6371 km, k = 0 (D18). Els números d'horitzó de §6.6 i §10.3 es van
   calcular amb k = 0,13 i **s'han de tornar a calcular amb k = 0** a la tasca 0.2.
3. **La mateixa altitud de l'ull**: altitud del MDT a resolució completa + 1,7 m (ara el programa
   fa servir la malla mitjanada de 20 m).
4. **El mateix nord**: Sol i Lluna girats −γ per passar de l'azimut geogràfic al de la quadrícula UTM.
5. **Exageració 1** en el mode normal (D6).

Comprovació (tasca 3.4): per a un punt i un azimut, l'angle de l'horitzó que dona el script ha de
coincidir (≤ 0,05°) amb l'angle de la vora del terreny llegida del depth buffer a la vista
d'observació.

---

## 8. Vistes: compatibilitat amb el model actual

| Vista desitjada | Compatible ara? | Què caldria |
|---|---|---|
| Desplaçar la càmera i inspeccionar el terreny | **Sí** (càmera orbital) | Treure el lligam amb el personatge (F3) |
| Seleccionar un punt i observar a l'altura dels ulls | **Sí** (el doble clic + la primera persona) | Separar l'observador (dada) del dibuix (F3); bloquejar-lo durant la reproducció (D5) |
| Vista des de la Lluna **il·lustrativa** | **Sí** (ja hi ha "Mirar des de darrere la Lluna") | Etiquetar-la com a il·lustrativa: la Lluna és a ~40 km i no a ~370 000 km |
| Vista des de la Lluna **coherent** | **No** | Veure més avall |
| Sol amb textura (enfosquiment del limbe) | **Sí** | Al shader `esfera.frag` (mode emissiu): I(μ) = 1 − u(1 − μ), amb u ≈ 0,6. És un efecte físic real i documentable |
| Animació de la superfície del Sol (granulació, taques) | **Sí**, com a efecte visual | Soroll procedural animat amb un uniform de temps. **Il·lustratiu**: no representa el Sol real d'aquell dia |

**Per què la Lluna actual no permet una vista coherent:** el model només dona la **direcció** de la
Lluna vista des de l'observador. No té la seva posició 3D ni la distància real. Es dibuixa a la
distància que tria el panell (per defecte, 2 × la mida del terreny) amb un radi que en conserva la
mida aparent. Des de l'observador es veu bé; des de qualsevol altre lloc, la geometria és falsa.

**Què caldria per a una vista coherent des de la Lluna (feina gran, opcional, F8):**
1. Efemèrides 3D de la Lluna i del Sol (posició geocèntrica i distància), no només la direcció.
2. La Terra com a esfera (R = 6371 km), amb el terreny posat al seu lloc sobre l'esfera.
3. L'ombra de la Lluna sobre la Terra (umbra i penombra), comparable amb les corbes
   `moon_shadow` del GeoPackage del CNIG (cada 3,6 s).
4. Rang de profunditats enorme (de 0,5 m a ~384 000 km): cal dibuixar en diverses passades
   o fer servir profunditat logarítmica al shader.
5. Des de la Lluna, una zona de 20 km fa ~11″ d'arc: per veure-la cal un teleobjectiu extrem, i per
   veure la Terra sencera cal una textura de tot el planeta.
6. Una comprovació: l'ombra calculada ha de coincidir amb les corbes del CNIG.

---

## 9. Estudi (sense implementar): MDS per a arbres i edificis

- **Què és:** un model digital de **superfícies** (MDS) inclou la vegetació i els edificis; el MDT
  és el terra nu. Fonts candidates (a verificar la resolució i les condicions exactes abans de
  descarregar res): el MDS del PNOA (CNIG, a partir del LiDAR) i els models de superfícies de
  l'ICGC.
- **Què permetria:** un horitzó realista a les zones urbanes i boscoses (Cerdanyola, la UAB,
  Montmeló), on el Sol a 4° pot quedar darrere d'edificis o arbres propers.
- **Com:** l'observador sempre es col·loca sobre el **MDT** (el terra); el MDS només serveix com a
  **obstacle** per a l'horitzó i per al dibuix proper.
- **Limitacions:** el MDS és 2,5D (no té voladissos; un arbre és una "taca" alta); depèn de la data
  del vol LiDAR (arbres que ja no hi són, edificis nous); amb el Sol molt baix, els obstacles
  determinants són a pocs centenars de metres i necessiten resolució ≤ 2 m; si l'observador cau
  dins d'un edifici al MDS, cal triar el punt amb cura.
- **Cost:** més dades (a 2 m, 5×5 km són 6,25 M de píxels per zona), una segona textura i decidir on
  es fa servir (només a prop de l'observador).
- **Prova petita proposada (F8):** 2×2 km al voltant de la UAB amb MDS i MDT, calcular l'horitzó amb
  tots dos i comparar-lo.

---

## 10. Dades

### 10.1 Inventari i dependències (22/10/2026)

| Fitxer | Mida | Al git | Qui en depèn | Proposta |
|---|---|---|---|---|
| `data/mdt/picos_5m.tif` | 49 MB | Sí | `main.py` (regió per defecte), `TERRENYS` | Mantenir (cas de totalitat, D8) |
| `data/mdt/peninsula_200m.tif` | 40 MB | Sí | `TERRENYS`, scripts, README | Mantenir (cobreix Catalunya; horitzó llunyà) |
| `data/mdt/luarca_5m.tif` | 27 MB | Sí | `TERRENYS`, `preparar_dades.py`, `captura.py --zones`, preajust de `descarregar_mdt.py`, README | Retirar a la 4.2, editant abans aquestes referències |
| `data/mdt/asturias_25m.tif` | 32 MB | Sí | Ídem | Retirar a la 4.2 |
| `data/mdt05/…HU30_0011_LID.tif` | 32 MB | Sí | Només el README | Retirar a la 4.2 |
| `data/mdt05/altres/` | 101 MB | No (ignorat) | Ningú | Esborrar a la 4.2 |
| `data/eclipsi2026/` | 67 MB | Sí | `dades/eclipse_data.py` | Mantenir |
| `data/cache/` | 1,5 GB | No | Es regenera sola | Es pot esborrar sencera |

Retirar un fitxer del git (`git rm --cached`) atura el creixement, però **no** fa més petit
l'historial (D10: no es reescriu).

### 10.2 Reproduïbilitat

Es crearà `data/FONTS.md` (tasca 4.1), on cada fitxer tindrà: la font i el servei (p. ex. el WCS de
l'IGN, cobertura `Elevacion25830_5`), la zona en UTM i en lat/lon, la resolució, el CRS, la
llicència (CC BY 4.0, amb l'atribució), la comanda exacta, la data de descàrrega i el `sha256`.

### 10.3 Ubicacions (coordenades provisionals; es verifiquen a la tasca 0.3)

Les coordenades d'aquesta taula són **aproximades i no verificades**. A la tasca 0.3 se
substituiran per les dels punts concrets (plaça Major de Vic, ajuntament de Cerdanyola, plaça
Cívica de la UAB...) amb la font cartogràfica documentada, i es tornaran a calcular els valors.
Resultats: CNIG (efemèrides, píxel de ~920 m; ombres, ~230 m). L'horitzó és el nostre script
amb el MDT de 200 m, la convergència corregida i **k = 0,13** (cal refer-lo amb k = 0, D18).

| Lloc | Lat, lon | C1 | Màxim | Posta | C4 | Sol tapat (Lluna) | Elev. al màx. | Relleu (CNIG) | Horitzó (200 m) |
|---|---|---|---|---|---|---|---|---|---|
| Picos | 43.2620, −4.9490 | 19:31:39 | 20:28:02 | 21:27:13 | 21:20:55 | 100 % (100,4 s) | 9,60° | 1 | 2,70° (5 m: 5,82°) |
| Vic, pl. Major | 41.9302, 2.2546 | 19:34:11 | 20:28:27 | 20:55:37 | després de la posta | 99,25 % | 4,15° | 3 | 2,85° |
| L'Escala, centre | 42.1250, 3.1330 | 19:33:48 | 20:27:52 | 20:52:30 | després de la posta | 98,67 % | 3,70° | 3 | 2,27° (poc fiable) |
| Cerdanyola, ajuntament | 41.4912, 2.1406 | 19:34:56 | 20:29:10 | 20:55:11 | després de la posta | 99,74 % | 3,99° | 3 | no calculat |
| Montmeló, centre | 41.5517, 2.2483 | 19:34:49 | 20:29:02 | 20:54:53 | després de la posta | 99,64 % | 3,95° | 3 | no calculat |
| UAB, pl. Cívica | 41.5020, 2.1040 | 19:34:54 | 20:29:09 | 20:55:21 | després de la posta | 99,73 % | 4,02° | 3 | 2,92° |

Hores en CEST (TU + 2). A tots els punts catalans el Sol es pon abans del final de l'eclipsi.

---

## 11. Fases i tasques

Cada tasca té aquests camps: **Tipus**, **Aprenem**, **Canvia**, **Depèn**, **Comprovació**,
**Documentem**, **Estat**.

### F0 — Preservar i fixar la línia base (mínim)

**0.1 Preservar l'estat actual** — Tipus: Git. Estat: `VALIDAT` (22/10/2026: l'equip ha fet les tres comprovacions i n'ha entès el resultat: codi guardat al commit `d515dc4`, etiqueta `abans-reorganitzacio`; els canvis posteriors del pla encara no són a cap commit)
- Aprenem: l'àrea de preparació (*staging*), els moviments de fitxers, les branques i les etiquetes.
- Canvia: només el Git: la branca `reorganitzacio-projecte`, un commit amb l'estat actual (fitxers
  revisats un a un, sense `git add .`) i l'etiqueta `abans-reorganitzacio`. Sense push.
  `CLAUDE_ANTIC.md` queda fora del commit (D15).
- Depèn: D15.
- Comprovació (equip): `git branch` mostra `reorganitzacio-projecte`; `git show --stat abans-reorganitzacio`
  llista els fitxers esperats; `git status` només mostra `CLAUDE_ANTIC.md` com a no seguit.
- Documentem: un registre a la web (O2.6) i aquí (§12).

**0.3 Verificar les coordenades de les ubicacions** — Tipus: dades. Estat: `PENDENT`
- Aprenem: geocodificació, sistemes de coordenades (ETRS89/WGS84), d'on surt una coordenada "oficial".
- Canvia: la taula de §10.3, amb la font de cada coordenada (nom del servei o mapa, data de
  consulta), i els valors del CNIG recalculats per als punts concrets.
- Depèn: D17; permís per fer peticions de xarxa a un geocodificador (no és una descàrrega de dades).
- Comprovació: cada punt es pot obrir al mapa de la font i cau al lloc indicat (plaça, edifici).
- Documentem: §10.3 i la web (O1.2).

**0.2 Línia base de comportament** — Tipus: N (només scripts de prova). Estat: `PENDENT`
- Aprenem: què vol dir "el mateix comportament" i com es demostra.
- Canvia: s'afegeixen `scripts/validar_model.py` (contactes, convergència, horitzó) i captures de
  referència a `captures/referencia/`, i una llista de proves manuals a la web.
- Depèn: 0.1.
- Comprovació: l'equip executa els scripts i obté els mateixos números que §6.6 (els de l'horitzó,
  recalculats amb k = 0 segons D18).
- Documentem: les evidències de partida (O1.12).

### F1 — Entendre el programa (mínim)

**1.0 Seguir un vèrtex dibuixat fins a un píxel** — Tipus: aprenentatge (sense canviar el codi del programa). Estat: `VALIDAT` (22/10/2026: l'equip l'ha executat amb `COINCIDEIX` i ha donat l'activitat per tancada; la predicció de la modificació queda com a opcional per decisió de l'equip, D26)

Resultat: `scripts/exercici_fotograma.py` (nou) i l'activitat documentada a
`docs/exercici_1_0_vertex_a_pixel.md` (pàgina provisional fins que hi hagi la web, 5.1). Comprovat
per Claude: dues execucions (per defecte i `--distancia 0.5`) amb `RESULTAT: COINCIDEIX`, la
posició del vèrtex a 1,37 cm de la del vertex shader real, i la creu sobre el terreny a les dues
captures. Cap altre fitxer del programa s'ha modificat.

Tres conceptes que cal distingir:
- **Vèrtex:** un punt de la malla que entra al vertex shader. Al terreny n'hi ha 1024 × 1024, i
  cadascun surt amb una posició a la pantalla (`gl_Position`).
- **Fragment:** un candidat a pintar un píxel. La GPU el genera en rasteritzar un triangle, per a
  cada píxel que el triangle cobreix, amb els valors interpolats entre els seus 3 vèrtexs
  (profunditat, UV...). Passa pel fragment shader i el test de profunditat el pot descartar.
- **Píxel:** una cel·la del framebuffer que guarda el color i la profunditat del fragment guanyador.
  Un vèrtex gairebé mai cau exactament al centre d'un píxel.

Per què no serveix el cim del MDT original: la GPU no dibuixa el MDT de 5 m, sinó una malla de
1024² vèrtexs on l'altura de cada vèrtex es llegeix amb `textureLod(tex_altitud, uv, lod_vertexs)`.
A Picos, `lod_vertexs` ≈ 1,97: la GPU barreja els nivells de mipmap 1 (mitjanes de 2×2) i 2 (de 4×4).
El cim de 2647 m del MDT no existeix a la superfície dibuixada.

- Aprenem: coordenades del món (km), `m_model`, `m_view` (`lookAt`), `m_proj` (`perspective`),
  coordenades de clip, divisió per w, NDC, viewport, profunditat no lineal, i la diferència entre
  vèrtex, fragment i píxel.
- Canvia: res del programa. Un script de prova (`scripts/exercici_fotograma.py`):
  1. Tria **un vèrtex de la graella** (índexs i, j) i n'obté l'altura **tal com la llegeix la GPU**:
     llegeix de la textura els nivells de mipmap que fa servir (`texture.read(level=…)`) i els
     barreja com `textureLod`.
  2. Comprova que és **visible i sense obstacles**: ha d'estar a la zona central de la imatge, en una
     vessant que miri cap a la càmera, i un recorregut des de la càmera fins al vèrtex sobre la malla
     dibuixada no ha de trobar cap punt més alt que el raig. A més, els píxels del voltant han de
     tenir una profunditat contínua (no és una silueta).
  3. Calcula a mà `m_proj · m_view · m_model · p` amb la mateixa càmera que `captura.py`, i en
     treu la posició a la pantalla (amb decimals) i la profunditat.
  4. Renderitza **sense antialiasing** (per poder llegir la profunditat d'un sol mostreig), llegeix
     la profunditat del píxel que conté el punt i en marca la posició a la captura.
- **Tolerància (es calcula, no es fixa):** la diferència esperada entre la profunditat predita i la
  llegida és la suma de:
  - **El desplaçament dins del píxel:** el centre del píxel és fins a ~0,7 px del vèrtex, i allà la
    profunditat és la del triangle interpolat. Error ≈ |gradient de profunditat a la pantalla| ×
    desplaçament; el gradient es mesura amb els píxels veïns.
  - **La quantificació del depth buffer:** amb 24 bits, un pas és 2⁻²⁴ ≈ 6·10⁻⁸ (cal confirmar els
    bits reals del framebuffer).
  - **L'arrodoniment float32** de les matrius i de la posició (relatiu ~10⁻⁷).

  Com que la profunditat no és lineal (té molta més precisió a prop del pla *near*), el resultat
  també es dona convertit a **metres de profunditat segons l'eix de visió** (que és el que val la w; no és la distància en línia recta fins al punt), que és més fàcil d'interpretar.
- Depèn: 0.1 (validada per l'equip).
- Comprovació: l'equip executa el script. (a) La marca cau sobre el vèrtex triat a la captura.
  (b) La diferència de profunditat és menor que la tolerància calculada per a aquell punt, i el
  script mostra tots dos números i els tres termes de la tolerància.
- Documentem: O2.1 i O2.2 a la web (teoria de vèrtex/fragment/píxel, captura amb la marca, números).

**1.1 Com es dibuixa un fotograma** — Tipus: documentació. Estat: `PENDENT`
- Aprenem: el pipeline gràfic, les matrius model/vista/projecció, VBO/IBO/VAO, shaders, uniforms,
  textures, el depth buffer.
- Canvia: una pàgina a la web (O2.1), ampliant §5, amb referències al llibre de Rougier.
- Depèn: F5.1 (l'esquelet de la web), o es pot escriure primer en Markdown.
- Comprovació: cada membre de l'equip prediu l'efecte d'un canvi petit (p. ex. el color del cel o
  `m_model` dels eixos) i el prova en local, sense desar-lo.
- Documentem: la teoria i les prediccions.

### F2 — Reorganització (R, sense canvis de comportament; mínim)

Per a totes les tasques de la F2:
- Aprenem: mòduls i imports de Python, i responsabilitats separades.
- Depèn: 0.2, D16.
- Comprovació: captures de la mateixa escena idèntiques a les de 0.2 (al mateix ordinador i en
  les mateixes condicions), la llista de proves manuals passa i
  `diff -r` amb `repte4/basecode` no mostra canvis als originals.
- Documentem: l'arbre i la responsabilitat de cada fitxer (O2.6).

Ordre executat (un commit local per pas; l'ordre es va canviar perquè `dades/` havia d'existir abans
de moure `astres.py`, per la qüestió de les constants):

| Tasca | Canvia | Estat |
|---|---|---|
| 2.1 | `sol.py` → `basecode/sol.py` | `FET` |
| 2.2 | `data_io.py`, `eclipse_data.py`, `model_eclipsi.py` → `dades/`; constants del Sol i la Lluna a `dades/model_eclipsi.py` | `FET` |
| 2.3 | `astres.py` i `personatge.py` → `basecode/` | `FET` |
| 2.4 | `terrain.py` → `basecode/` (i els imports dels scripts) | `FET` |
| 2.5 | `camera.py` → `basecode/camera_exploracio.py` (`CameraExploracio`); `camera_primera_persona.py` → `basecode/camera_observador.py` (`CameraObservador`); el codi de dins no canvia | `FET` |
| 2.6 | `build_ui` i les funcions del panell de `main.py` → funcions de `ui.py` | `FET` |
| 2.7 | README, pla i web amb les rutes noves | `FET` |

`personatge.py` s'ha **mogut** a `basecode/` però **no** s'ha retirat (D7): la retirada és la tasca 3.1.

**Com s'ha comprovat cada pas (Claude, 22/10/2026):**
- Un script de prova (fora del repositori) executa el `GraphicsEngine` real amb una finestra
  amagada en 5 escenaris fixos: l'inici, prop de la totalitat, la capa d'enfosquiment, la tecla P
  (120 fotogrames reproduint l'eclipsi) i la tornada a la tercera persona amb zoom. Desa una
  captura i l'estat (hora, Sol, % tapat, càmera, personatge, Lluna, color del cel, fase). Al pas
  2.6, també amb totes les seccions del panell obertes, comparat amb el codi del pas anterior.
- També s'executen `captura.py` (Picos i península amb zones), `exercici_fotograma.py` i
  `preparar_dades.py`, i es compara la sortida de text (sense els temps).
- **Criteri:** l'estat i els textos han de ser **idèntics**. Les imatges poden diferir pel soroll de
  la GPU: amb el **mateix codi**, dues execucions de `captura.py` (antialiasing 4x) difereixen de 0 a
  503 píxels d'1,6 milions, i el primer fotograma del programa varia 39 píxels entre sessions. Es
  van acceptar com a iguals les imatges amb ≤ 1000 píxels diferents.
- `diff -r basecode repte4/basecode`: els originals del professor, idèntics.
- El bucle real `run()` (90 fotogrames, amb el panell dibuixat) funciona sense errors.
- **No s'ha provat:** la finestra visible, el teclat ni el ratolí (ho ha de fer l'equip).

### F3 — Canvis de comportament i correccions (C; mínim)

| Tasca | Canvia | Comprovació | Estat |
|---|---|---|---|
| 3.1 Retirar el personatge | Fora `basecode/personatge.py`, salts i WASD del ninot. Nou `dades/observador.py` (lat, lon, x, z, altitud del MDT, sense dibuix). La càmera d'exploració es mou lliurement; un marcador senzill indica el punt triat. | Llista de proves: es pot explorar, triar un punt i passar a la vista d'observació; les coordenades del panell = les del punt triat | `PENDENT` |
| 3.2 Bloquejar l'observador durant la reproducció (D5) | Durant la reproducció no es pot canviar el punt; es pot girar i fer zoom | Prova: amb la reproducció en marxa, intentar canviar de punt no fa res; coordenades, CNIG i model són del mateix punt | `PENDENT` |
| 3.3 `durada = None` sense dades vàlides | `dades/model_eclipsi.py` | `validar_model.py`: el punt (55, 0) no dona error en accedir a `durada` | `PENDENT` |
| 3.4 Curvatura i horitzó coherents (D6, D18, §7) | Mode normal amb curvatura geomètrica activa (centrada a l'observador, k = 0) i exageració 1; controls de depuració etiquetats; ull a altitud del MDT complet + 1,7 m | Horitzó del script = horitzó del depth buffer (≤ 0,05°), tots dos amb k = 0 | `PENDENT` |
| 3.5 Convergència UTM | Sol i Lluna girats −γ | `validar_model.py`: el nord geogràfic té azimut de quadrícula −γ a l'escena | `PENDENT` |
| 3.6 Refracció del Sol | Substituir la correcció constant per una fórmula de refracció documentada (§6.5), només si l'explicació és defensable | Error tipus 1: elev. al màxim ≤ 0,02° del CNIG als 9 punts. Error tipus 2 (mateixa font): posta ≤ 1 min de la banda 5 | `PENDENT` |
| 3.7 Contactes asimètrics | Primer: explicar la causa de l'asimetria. Després, només si aporta valor (§6.4.1), un model de la Lluna amb C1 i C4 correctes | Error tipus 1: C1–C4 ≤ 5 s als 9 punts | `PENDENT` |
| 3.8 Comprovació independent (D20, D23) | Consulta manual del calculador de la NASA (§6.3.1) en uns quants punts (Picos, un punt de totalitat més, 2 punts catalans) i moments (C1, màxim, C4, posta). Taula amb les convencions de cada valor: hora (TU), coordenades i altitud, refracció inclosa o no, definició dels contactes | Error tipus 2 dins dels objectius de §6.4, o explicació de la diferència | `PENDENT` |

Per a la F3:
- Aprenem: càmeres (orbital i de primera persona), geodèsia bàsica (convergència, curvatura,
  refracció), validació (ajust vs. predicció).
- Documentem: una taula d'errors abans i després a la web (O1.3) i aquí.

### F4 — Dades i ubicacions (N; mínim)

| Tasca | Canvia | Depèn | Comprovació | Estat |
|---|---|---|---|---|
| 4.1 `data/FONTS.md` i política del `.gitignore` (MDT nous a una carpeta ignorada; Picos versionat) | Documentació i `.gitignore` | D21 | Cada fitxer de `data/` hi surt amb la seva comanda | `PENDENT` |
| 4.2 Retirar Luarca, Astúries i la fulla `mdt05` | `TERRENYS`, scripts, README; retirar del git; esborrar `altres/` | 4.1, permís | `preparar_dades.py`, `captura.py` i `main.py` funcionen | `PENDENT` |
| 4.3 Zona del Vallès | 5 m en ~25 km (Cerdanyola, UAB, Montmeló) + anell de 25 m fins a ~100 km (dos `Terrain`; el shader ja té les "zones" per amagar el llunyà on hi ha el proper) | 3.4, 0.3; l'equip fa la descàrrega | Horitzó del programa = script (≤ 0,05°); ombra del CNIG al màxim coherent | `PENDENT` |
| 4.4 Vic i l'Escala | Ídem | 4.3 | Ídem | `PENDENT` |

- Aprenem: CRS, resolució, nivells de detall senzills, reproduïbilitat.
- Documentem: fitxes de dades (O1.1) i resultats per ubicació (O1).

### F5 — Web de seguiment (N; mínim; en paral·lel des de la F1)

**5.1 Primera versió local** — Estat: `FET` (22/10/2026, pendent de revisió de l'equip)

Resultat: `docs/index.html`, `docs/estil.css`, `docs/progres.js` i `docs/img/` (5 captures JPEG,
~520 KB en total, generades amb `scripts/captura.py` i `scripts/exercici_fotograma.py`; les comandes
són al peu de cada imatge). S'obre fent doble clic a `docs/index.html` (no cal servidor). No es
publica amb GitHub Pages (D29). El contingut surt de les actes 1 i 3 (PDF), de l'acta 2 (md) i
d'aquest pla. Comprovat per Claude: estructura HTML correcta, cap enllaç local trencat, 41 criteris
(a la versió inicial, 4 validats, 10 fets, 25 pendents i 2 que no compleixen; després de la F2,
4 validats, 11 fets, 24 pendents i 2 que no compleixen) i renderitzat amb Chrome sense finestra.
Pendent de l'equip: revisar-ne el contingut. L'O3 s'ha retirat (D31).

Disseny previst inicialment (es manté):
- Canvia: `docs/index.html` (HTML i CSS, sense llibreries) + `docs/objectius.json`; publicació amb
  GitHub Pages (opcional, pendent de permís).
- Estructura, amb desplegables tipus Notion (`<details>`):

  ```
  Objectiu (O1, O2)                estat · % (criteris validats / total)
    └ Subobjectiu                  estat · %
        ▸ Què es vol aconseguir
        ▸ Estat i criteris de comprovació
        ▸ Teoria apresa
        ▸ Implementació al projecte
        ▸ Fitxers relacionats      (enllaços al codi)
        ▸ Captures
        ▸ Comprovacions / evidències   (criteri, comanda, resultat, data)
        ▸ Limitacions
  ```

- Objectius (els dos de l'acta 3 final; D30, D31), tal com són a la web:
  - **O1** Simulador: O1.1 dades del terreny (inclou la reproduïbilitat), O1.2 dades de l'eclipsi,
    O1.3 terreny 3D, O1.4 exploració, O1.5 observació des del terra, O1.6 el Sol, O1.7 la Lluna,
    O1.8 il·luminació, O1.9 ombres del relleu, O1.10 interfície i barra temporal,
    O1.11 meteorologia, O1.12 validació del model.
  - **O2** Conceptes gràfics: O2.1 fotograma, O2.2 càmeres i transformacions, O2.3 textures i
    mipmaps, O2.4 normals i il·luminació, O2.5 shadow mapping, O2.6 organització del codi i del treball.
- Percentatge: cada subobjectiu té una llista de criteris comprovables, i
  % = criteris `VALIDAT` / total. Res de percentatges a ull.
- Comprovació: s'obre al navegador; cada desplegable s'obre; els percentatges coincideixen amb
  el JSON.

**5.2 Creixement** — a cada tasca validada s'afegeixen la teoria, els fitxers, la captura i
l'evidència corresponents.

### F6 — Resta del projecte final (mínim segons l'acta 3; es detallarà després de la F4)
- 6.1 Ombres del relleu (shadow mapping) i comparació amb `terrain_shadows` del CNIG.
- 6.2 Menú de meteorologia (clar, boira, núvols).

### F7 — Ampliacions visuals (opcional)
- 7.1 Textura del Sol amb enfosquiment del limbe (físic, documentable).
- 7.2 Animació de la superfície del Sol (**il·lustratiu**).
- 7.3 Vista il·lustrativa des de la Lluna, etiquetada com a tal a la interfície i a la web
  ("il·lustrativa: distàncies no reals"). És la primera de les vistes de la Lluna (D22).
- 7.4 Exemples interactius (WebGL) a la web, quan aportin valor.

### F8 — Ampliacions grans (opcional)
- 8.1 Vista coherent des de la Lluna (§8).
- 8.2 Piràmide de rajoles (5/25/200 m) i quadtree (antiga T8).
- 8.3 Descàrrega en segon pla cap a la cache (mai al bucle de render).
- 8.4 Prova petita amb MDS a la UAB (§9).
- 8.5 Completar Portugal i França (Copernicus DEM).

---

## 12. Registre de canvis del pla

| Data | Canvi |
|---|---|
| 22/10/2026 | Versió inicial. Creada la còpia `CLAUDE_ANTIC.md` (idèntica a `CLAUDE.md`, sha256 `e61f9986…4f33`). |
| 22/10/2026 | Resoltes P1–P9 (D15–D22). Convenció de refracció (§7), tipus d'error i efecte visible (§6.4). Noves tasques 0.3 (coordenades) i 1.0 (seguir un punt fins a un píxel). Pas 0.1 executat: branca `reorganitzacio-projecte`, etiqueta `abans-reorganitzacio`, sense push. |
| 22/10/2026 | D23 (NASA com a font externa, §6.3.1) i D24. Tasca 1.0 reformulada: vèrtex de la geometria dibuixada i tolerància calculada. Nova pendent P12 (`CLAUDE.md` nou de l'equip). 0.1 continua `FET`, no `VALIDAT`. |
| 22/10/2026 | D25: `CLAUDE.md` substituït per la versió nova; `CLAUDE_ANTIC.md` sense canvis. P12 resolta. Retirades les instruccions transitòries que deien que `CLAUDE.md` estava desactualitzat. Definició de `FET`/`VALIDAT`, regla d'autoritzacions i criteri de comparació d'imatges alineats amb `CLAUDE.md`. Títol de §2 corregit (fotografia de l'etiqueta vs. canvis posteriors). 0.1 continua `FET`, pendent de la validació de l'equip. |
| 22/10/2026 | 0.1 `VALIDAT` per l'equip. Tasca 1.0 `FET`: `scripts/exercici_fotograma.py` i `docs/exercici_1_0_vertex_a_pixel.md`. Sense commit. |
| 22/10/2026 | 1.0 `VALIDAT`. Corregida la descripció de w (profunditat segons l'eix de visió, no distància euclidiana) a la documentació i al script. D26–D29. `CLAUDE.md` versionat (D27). Commit `6bca321` i push de la branca i l'etiqueta (D28); `main` sense canvis. |
| 22/10/2026 | 5.1 `FET`: primera versió local de la web a `docs/`. D30 i pendent P13 (O3 no és a l'acta 3 final). |
| 22/10/2026 | D31: O3 retirat i repartit (O1.1, O1.12, O2.6). Commit i push de la web i del pla. |
| 22/10/2026 | F2 `FET` (tasques 2.1–2.7): reorganització en commits locals separats, sense push. Estructura actual a §4. |
