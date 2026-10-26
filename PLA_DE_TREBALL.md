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

Darrera actualització: 2026-10-26 (F14: edificis a les zones de detall).

---

## 0. Regles de treball

1. **Treball autònom en passos petits** (D32). Claude implementa, executa les comprovacions,
   inspecciona captures i corregeix; quan les comprovacions disponibles passen, continua amb la
   tasca següent. La prova de l'equip no és una condició rutinària per avançar. A cada tasca es
   diu com s'ha comprovat: **comprovat automàticament**, **inspeccionat visualment** o **provat per
   l'equip**. Commits locals petits i recuperables.
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
| D32 | **Treball autònom** (substitueix l'aturada després de cada tasca): implementar, comprovar, inspeccionar captures, corregir i continuar. Distingir comprovat automàticament / inspeccionat visualment / provat per l'equip. | 22/10 |
| D33 | **Cap marcador permanent** (fora l'esfera taronja). La selecció d'un punt s'indica de manera discreta i temporal. | 22/10 |
| D34 | **Observació:** ulls fixos, la mirada conserva l'orientació, ratolí i fletxes giren el cap, **sense seguir el Sol**. **Exploració:** càmera lliure (WASD desplacen, ratolí i fletxes giren, allunyar-se mou la càmera de debò) amb velocitat adaptada a l'escala, del terreny a l'espai. | 22/10 |
| D35 | **P = només reproduir/pausar.** El temps de simulació és independent de la càmera; el punt d'observació i la càmera són dades independents. Substitueix el comportament anterior de P (canviar de vista, mirar el Sol i reiniciar). | 22/10 |
| D36 | **Escena espacial coherent com a objectiu principal:** Terra, Sol i Lluna en un sol sistema de coordenades amb posicions reals (efemèrides), terreny de la península (Picos com a detall) posat sobre la Terra, ombra de la Lluna calculada per a cada punt de la superfície. Substitueix la Lluna a distància artificial (D22 queda superada per a la vista espacial). | 22/10 |
| D37 | **Interfície senzilla:** reproduir/pausar, hora i velocitat; explorar / observar; escollir ubicació; tornar al punt; ajuda curta. Capes tècniques i depuració en un apartat avançat tancat. | 22/10 |
| D38 | Autoritzades descàrregues de dades i textures de fonts fiables amb llicència compatible (documentant-ne la procedència i sense pujar fitxers grans al Git). | 22/10 |
| D39 | (F10) Al mode globus, l'altura dels vèrtexs la calcula la CPU; nivells de detall amb pegats al voltant de l'observador i zones de 5 m de les ubicacions (una de carregada cada vegada); el pegat de 200 m de la península fa, de moment, el paper de l'anell de 25 m de la 4.3. | 22/10 |
| D40 | (F11) Ubicacions concretes: plaça Major de Vic, ajuntaments de l'Escala, Cerdanyola i Montmeló, plaça Cívica de la UAB. Font: geocodificador de l'ICGC per als ajuntaments i centre del polígon d'OpenStreetMap per a les places. Picos es manté com a centre de la zona de 5 m. | 26/10 |
| D41 | (F11) La comparació amb la NASA executa el codi del calculador (`SEcirc.js`) amb les nostres coordenades en lloc de fer-hi clic (mateix càlcul, sense arrodonir); el resultat es desa en un CSV versionat. El model no s'ajusta a la NASA. | 26/10 |
| D42 | (F11) Ombres del relleu amb shadow mapping, primer només a la zona de 5 m de l'observador; llum del Sol aparent (amb refracció); interruptor a l'apartat Avançat, actiu per defecte (és un efecte físic, no una capa tècnica). | 26/10 |
| D43 | (F11) Triar una ubicació de la llista posa també la càmera d'exploració a sobre del punt nou; el doble clic no mou cap càmera. | 26/10 |
| D44 | (F12, equip) Arrencada pausada a C1 − 60 min del model al punt inicial; canviar d'ubicació no toca el temps. | 26/10 |
| D45 | (F12, equip) Espai de navegació: cub fix amb la Terra, la Lluna i el Sol a tot l'interval, en el mateix sistema que l'escena (ECEF); marge mínim d'un radi solar, ampliat fins que el Sol hi capiga sencer des de la paret. Parets translúcides visibles a prop. | 26/10 |
| D46 | (F12, equip) Mirada amb el ratolí capturat: un clic a l'escena captura, Esc o perdre el focus alliberen; el doble clic amb el ratolí lliure continua triant el punt. Esc amb el ratolí lliure continua tancant el programa (comportament anterior conservat). | 26/10 |
| D52 | (F14, equip) Edificis a les zones de detall per veure si tapen el Sol. Font: Catastro INSPIRE (parts d'edifici amb plantes); altures estimades amb plantes × 3 m, identificades com a estimació. Àrea: 2 km al voltant dels punts d'observació. Les dades i la memòria cau, fora del Git. | 26/10 |
| D53 | (F14) Els punts d'observació que cauen dins d'un edifici no es mouen: es documenten i es proposa un punt exterior proper, pendent de la decisió de l'equip. | 26/10 |
| D47 | (F12) El gest de pessigar del trackpad no és disponible amb GLFW a macOS; l'alternativa és lliscar amb dos dits (el mateix esdeveniment que la roda). El gest natiu necessitaria una dependència nova (PyObjC), pendent d'autorització. | 26/10 |

### 1.2 Pendents

Cap pregunta oberta en aquest moment. (Historial: P1–P13 resoltes a D15–D25 i D31.)

---

## 2. Funcionalitats existents (codi actual, després de la F14)

El **comportament** és el mateix que el de la fotografia guardada a l'etiqueta
`abans-reorganitzacio`: la fase F2 només ha mogut fitxers i codi (veure F2 a §11). Les rutes
d'aquesta taula són les **actuals**; a l'etiqueta els fitxers eren a l'arrel del projecte.

Res d'aquesta llista no està validat formalment per l'equip.

| Funcionalitat | On és | Estat / observacions |
|---|---|---|
| La Terra (el·lipsoide WGS84) amb textura, dia i nit i ombra de la Lluna per a cada punt | `basecode/terra.py`, `shaders/terra.*` | F9 (`FET`) |
| Relleu de la península (200 m) i Picos (5 m) posats sobre la Terra | `basecode/terrain.py` (mode globus), `shaders/terrain.*` | F9 (`FET`); només Espanya |
| Sol i Lluna a la seva posició i mida reals; Sol amb limbe i granulació; Lluna amb textura | `dades/efemerides.py`, `basecode/astres.py`, `shaders/esfera.*` | F9 (`FET`); granulació il·lustrativa |
| Model de l'eclipsi per a qualsevol punt (part tapada, contactes, posta, centre de l'ombra) | `dades/model_eclipsi.py`, `dades/geodesia.py` | F9 (`FET`); comprovat contra el CNIG i (F11) la NASA |
| Càmera d'exploració lliure (del terreny a l'espai) | `basecode/camera_exploracio.py` | F9 (`FET`) |
| Observació als ulls (1,7 m), mirada fixa, sense seguir el Sol | `basecode/camera_observador.py` | F9 (`FET`) |
| Punt d'observació com a dada; llista d'ubicacions; doble clic; bloquejat en reproduir | `dades/observador.py`, `main.py` (`triar_punt`) | `FET` |
| P només reproduir/pausar; temps independent de la càmera | `main.py`, `ui.py` | F9 (`FET`) |
| Panell senzill i apartat Avançat (capes del CNIG, ombres del relleu, depuració) | `ui.py` | F9 (`FET`) |
| Zones de 5 m de Vic, l'Escala i el Vallès (fitxers ignorats pel Git) i pegats de detall | `dades/data_io.py`, `basecode/terrain.py` | F10 (`FET`) |
| Ombres del relleu (shadow mapping) a la zona de 5 m | `basecode/ombres_relleu.py`, `shaders/ombra.*`, `terrain.frag` | F11 (`FET`) |
| Arrencada a C1 − 1 h; cub de navegació amb parets; mirada amb el ratolí capturat; roda i trackpad | `main.py`, `dades/navegacio.py`, `basecode/paret_cub.py`, `basecode/control_ratoli.py` | F12 (`FET`) |
| Edificis del Catastro a les zones de detall (opacs, tapen el Sol, fan ombra), "Mostrar edificis" | `dades/edificis.py`, `basecode/edificis.py`, `shaders/edifici.*` | F14 (`FET`) |
| Mode pla del terreny i càmera orbital, per als scripts | `basecode/terrain.py`, `basecode/camera_orbital.py` | Funciona |
| Scripts: descàrregues, caches, captura, exercici 1.0, validacions | `scripts/` | Funcionen |

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
| Ombres del relleu (shadow mapping) i menú de meteorologia (acta 3) | N | Mínim (segons l'acta 3) | F6 (ombres fetes a la F11) |
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

Estructura **actual** (després de la F14):

```
main.py                         GraphicsEngine: escena, temps, astres, cel i teclat
ui.py                           build_ui(app): panell i barra de temps
basecode/                       ORIGINALS sense canvis, més els nostres objectes:
  terra.py                        Terra (el·lipsoide amb textura)
  terrain.py                      Terrain (mode globus i mode pla)
  astres.py                       Esfera (Sol, halo) i Lluna
  ombres_relleu.py                OmbresRelleu (shadow mapping de la zona de 5 m)
  edificis.py                     Edificis (volums del Catastro de la zona de detall)
  paret_cub.py                    ParetCub (parets translúcides del cub de navegació)
  control_ratoli.py               ControlRatoli (ratolí capturat, roda i trackpad)
  sol.py                          Sol (Light amb azimut i elevació)
  camera_exploracio.py            CameraExploracio (lliure, ECEF)
  camera_observador.py            CameraObservador (als ulls)
  camera_orbital.py               CameraOrbital (mode pla, scripts)
  programes.py                    carregar shaders amb #define
  shaders/                        gouraud, phong (originals) + terrain, terra, esfera, ombra, paret (nostres)
dades/                          sense OpenGL: efemerides.py, geodesia.py, model_eclipsi.py,
                                observador.py, navegacio.py, edificis.py, data_io.py, eclipse_data.py
scripts/                        descarregar_mdt/efemerides/textures, preparar_dades, captura,
                                exercici_fotograma, validar_model, validar_ombra, prova_vistes,
                                comparar_nasa, validar_horitzo, validar_ombres_relleu, prova_controls,
                                descarregar_edificis, validar_edificis
models/                         .obj, com al repte 4
data/                           MDT, CNIG, efemerides, textures, cache (veure data/FONTS.md)
docs/                           web de seguiment
```

(`scripts/validar_model.py`, la tasca 0.2, ja existeix.)

**Constants compartides:** les mides aparents del Sol i la Lluna (`RADI_*`, `DIST_*`) les fa servir
tant el model de l'eclipsi com el dibuix. Abans eren a `astres.py` i `model_eclipsi.py` les
importava d'allà, és a dir, les dades depenien d'un mòdul gràfic. Ara es defineixen una sola vegada
a `dades/model_eclipsi.py` i `basecode/astres.py` i `main.py` les importen d'allà. Les dependències
van en un sol sentit (gràfics → dades) i no hi ha cap import circular.

`basecode/personatge.py` es va retirar a la tasca 3.1 (canvi de comportament), després de la reorganització.

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
| Horitzó i ocultació pel relleu | **Nosaltres**: `scripts/validar_horitzo.py` (des de l'observador, al màxim) i les ombres del relleu del programa (shadow mapping, a qualsevol hora) | |

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
- (Resolt a la tasca 3.2.) Si es camina durant la reproducció, el model queda congelat al punt antic i el panell barreja
  coordenades noves amb dades velles (`main.py:262`). Es resol amb D5.
- La direcció de la Lluna també està girada γ graus (mateix marc geogràfic).
- `centre_curvatura` només l'actualitza la càmera orbital (`basecode/camera_exploracio.py`, `update()`). A la vista de primera
  persona, la curvatura es mesura des de l'últim objectiu de la càmera orbital, no des de
  l'observador.
- El renderitzat fa servir la curvatura **geomètrica** (d²/2R, sense refracció). El script
  d'horitzó feia servir el radi efectiu (k = 0,13). **Encara no són coherents** (§7).
- El MDT és de terreny nu: no hi ha edificis ni arbres.
- `eclipse_data.punt()` obre els fitxers i crea un `Transformer` a cada crida.

**Pendent** (estat a 26/10; §6.1–6.6 descriuen el model antic, abans de la F9):
- Provar el programa amb finestra (ho ha de fer l'equip).
- ~~Comprovació independent del model (tasca 3.8)~~: feta a la F11 (NASA).
- Costat per on passa la Lluna (nord/sud del Sol).
- Si les hores de contacte del CNIG inclouen refracció.
- ~~Coordenades exactes de les ubicacions (tasca 0.3)~~: fetes a la F11.

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
| Desplaçar la càmera i inspeccionar el terreny | **Sí** (càmera d'exploració) | Fet a la tasca 3.1 |
| Seleccionar un punt i observar a l'altura dels ulls | **Sí** (doble clic + vista d'observador) | Fet a les tasques 3.1 i 3.2 |
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

### 10.3 Ubicacions (coordenades verificades a la tasca 0.3, 26/10/2026)

Font de les coordenades (consultades el 26/10/2026): ajuntaments, geocodificador de l'ICGC
(`eines.icgc.cat/geocodificador`), que coincideix a menys de 20 m amb OpenStreetMap (Nominatim); places,
centre del polígon de la plaça a OpenStreetMap (l'ICGC hi retorna el primer portal, a la vora: 70 m a Vic,
~100 m a la UAB). ETRS89 i WGS84 coincideixen a aquesta precisió (4 decimals ≈ 10 m). Picos és el centre de
la zona de 5 m, sense lloc concret. Respecte de les coordenades provisionals, els punts s'han mogut de 14 a
70 m; les zones de 5 m de Vic i l'Escala (centrades a les coordenades antigues) els contenen igualment.

Columnes CNIG: efemèrides (píxel de ~920 m) i classe d'ombres (~230 m); no canvien amb les coordenades
noves. Horitzó: `scripts/validar_horitzo.py`, en l'azimut del Sol al màxim, des dels ulls (1,7 m), amb el
MDT complet (5 m dins la zona, 200 m fora) i curvatura geomètrica (k = 0, D18). Classe nostra: el mateix
criteri que el CNIG amb aquest horitzó i el Sol aparent.

| Lloc | Lat, lon | C1 | Màxim | Posta | C4 | Sol tapat (Lluna) | Elev. al màx. | Relleu (CNIG) | Horitzó (MDT) | Classe nostra |
|---|---|---|---|---|---|---|---|---|---|---|
| Picos | 43.2620, −4.9490 | 19:31:39 | 20:28:02 | 21:27:13 | 21:20:55 | 100 % (100,4 s) | 9,60° | 1 | 5,82° (a 0,9 km) | 3 |
| Vic, pl. Major | 41.9303, 2.2540 | 19:34:11 | 20:28:27 | 20:55:37 | després de la posta | 99,25 % | 4,15° | 3 | 3,81° (4,3 km) | 3 |
| L'Escala, ajuntament | 42.1248, 3.1322 | 19:33:48 | 20:27:52 | 20:52:30 | després de la posta | 98,67 % | 3,70° | 3 | 6,45° (0,1 km) | 0 |
| Cerdanyola, ajuntament | 41.4910, 2.1407 | 19:34:56 | 20:29:10 | 20:55:11 | després de la posta | 99,74 % | 3,99° | 3 | 1,85° (5,7 km) | 3 |
| Montmeló, ajuntament | 41.5517, 2.2479 | 19:34:49 | 20:29:02 | 20:54:53 | després de la posta | 99,64 % | 3,95° | 3 | 1,66° (0,3 km) | 3 |
| UAB, pl. Cívica | 41.5019, 2.1039 | 19:34:54 | 20:29:09 | 20:55:21 | després de la posta | 99,73 % | 4,02° | 3 | 3,76° (1,4 km) | 3 (vora de baix a 0,01°) |

Hores en CEST (TU + 2). A tots els punts catalans el Sol es pon abans del final de l'eclipsi.
A l'Escala, el terreny (MDT, sense edificis) puja a 100 m de l'ajuntament cap al WNW: des d'aquest punt
el relleu tapa el Sol al màxim. El CNIG, amb cel·les de ~230 m, no ho pot veure. A Picos, la carena que
limita l'horitzó és a 0,9 km i el GMTED de 200 m del CNIG la representa diferent.

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

**0.3 Verificar les coordenades de les ubicacions** — Tipus: dades. Estat: `FET` (26/10/2026, F11: §10.3 i D40)
- Aprenem: geocodificació, sistemes de coordenades (ETRS89/WGS84), d'on surt una coordenada "oficial".
- Canvia: la taula de §10.3, amb la font de cada coordenada (nom del servei o mapa, data de
  consulta), i els valors del CNIG recalculats per als punts concrets.
- Depèn: D17; permís per fer peticions de xarxa a un geocodificador (no és una descàrrega de dades).
- Comprovació: cada punt es pot obrir al mapa de la font i cau al lloc indicat (plaça, edifici).
- Documentem: §10.3 i la web (O1.2).

**0.2 Línia base de comportament** — Tipus: N (només scripts de prova). Estat: `FET` en part (22/10: `scripts/validar_model.py`, `scripts/validar_ombra.py` i `scripts/prova_vistes.py`, la prova del programa real a les sis ubicacions, són al repositori)
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
| 2.1 | `sol.py` → `basecode/sol.py` | `VALIDAT` |
| 2.2 | `data_io.py`, `eclipse_data.py`, `model_eclipsi.py` → `dades/`; constants del Sol i la Lluna a `dades/model_eclipsi.py` | `VALIDAT` |
| 2.3 | `astres.py` i `personatge.py` → `basecode/` | `VALIDAT` |
| 2.4 | `terrain.py` → `basecode/` (i els imports dels scripts) | `VALIDAT` |
| 2.5 | `camera.py` → `basecode/camera_exploracio.py` (`CameraExploracio`); `camera_primera_persona.py` → `basecode/camera_observador.py` (`CameraObservador`); el codi de dins no canvia | `VALIDAT` |
| 2.6 | `build_ui` i les funcions del panell de `main.py` → funcions de `ui.py` | `VALIDAT` |
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
  la GPU, que es va mesurar amb el **mateix codi** (sense cap canvi entre les dues execucions):

  | Cas (mateix codi) | Píxels diferents | Diferència màxima | Diferència mitjana | Grups (el més gran) | En vores del relleu |
  |---|---|---|---|---|---|
  | `captura.py`, repetició 1 | 503 (0,031 %) | 23/255 | 1,6 | 39 (83 px) | 69 % |
  | `captura.py`, repetició 2 | 299 (0,019 %) | 14/255 | 1,5 | 51 (36 px) | 72 % |
  | `exercici_fotograma.py` | 13 (0,001 %) | 5/255 | 1,8 | 8 (5 px) | 38 % |
  | Programa, 1r fotograma, una altra sessió | 39 (0,004 %) | 9/255 | 1,9 | 10 (16 px) | 64 % |

  "En vores del relleu" = píxels on la imatge canvia de cop (gradient de lluminositat > 8); a tota la
  imatge només ho són el 19 % (captura) o el 3 % (programa). Per tant, el soroll és **dispers, petit
  (gairebé sempre menys de 10/255) i concentrat a les vores**, on l'antialiasing i l'ordre de
  rasterització poden canviar un píxel. Una regressió real (un objecte desplaçat, un color diferent)
  faria una taca compacta o una diferència gran.
- **Limitació del criteri que es va fer servir:** durant la fase es va acceptar ≤ 1000 píxels
  diferents. Aquest límit, tot sol, no descarta una regressió petita (p. ex. un objecte de 30 × 30
  píxels desplaçat). El que la descarta és la combinació de: l'estat numèric idèntic, la diferència
  màxima i mitjana petites, la dispersió en grups petits a les vores i, sobretot, la **comparació
  final**, en què totes les imatges (programa, captures i exercici) van sortir **idèntiques, amb 0
  píxels diferents**. Per a les properes comparacions, el criteri inclourà la diferència màxima, la
  mida del grup més gran i la ubicació, no només el recompte.
- `diff -r basecode repte4/basecode`: els originals del professor, idèntics.
- El bucle real `run()` (90 fotogrames, amb el panell dibuixat) funciona sense errors.
- **Prova de l'equip (22/10/2026):** amb la finestra visible, els controls principals funcionen com
  abans. Amb això, 2.1–2.6 passen a `VALIDAT`. 2.7 (documentació) queda `FET`.
- **Limitacions de les proves:** l'script de prova no simula el teclat ni el ratolí (només crida les
  funcions que hi ha al darrere, com la de la tecla P); `descarregar_mdt.py` no s'ha tornat a
  executar (no s'ha fet cap descàrrega); l'equip ha provat els controls principals, no cada opció
  del panell.

### F3 — Canvis de comportament i correccions (C; mínim)

**Com es van comprovar 3.1 i 3.2 (Claude, 22/10/2026):** un script de prova (fora del repositori)
executa el programa real amb una finestra amagada, simula les tecles (W, D, fletxes) i el doble clic,
i comprova 28 condicions. Entre d'altres: no hi ha personatge; a l'inici, després d'un doble clic,
durant la reproducció i després d'aturar-la, les coordenades de l'observador, el model i les dades
del CNIG del panell són del mateix punt; W mou la càmera i no l'observador; la tecla P posa la càmera
als ulls (1,7 m sobre el terra, amb una diferència de 0,06 mm per la precisió de `glm`) mirant el Sol;
durant la reproducció `triar_punt`, el doble clic i el WASD no mouen l'observador, però les fletxes
giren la mirada i el zoom funciona; en aturar-la es pot tornar a triar un punt. Totes 28 correctes.
També: `captura.py`, `exercici_fotograma.py` i `preparar_dades.py` donen la mateixa sortida que a
la línia base (imatges: 0 píxels diferents, i 20 píxels dispersos amb un màxim de 5/255 a la captura
amb antialiasing); el bucle `run()` fa 90 fotogrames sense errors; els originals del `basecode/`,
sense canvis. **No provat:** la finestra visible amb el teclat i el ratolí reals (ho ha de fer l'equip).


| Tasca | Canvia | Comprovació | Estat |
|---|---|---|---|
| 3.1 Retirar el personatge | Fora `basecode/personatge.py`, salts i el WASD del ninot. Nou `dades/observador.py` (x, z, lat, lon, altitud; sense dibuix). `main.triar_punt()` crea alhora l'observador, el model i les dades del CNIG. Càmera d'exploració lliure (WASD i ratolí la desplacen); el doble clic tria el punt, marcat amb una esfera. Càmera d'observador als ulls | Prova automàtica (Claude) i llista de proves de l'equip: explorar, triar un punt, passar a la vista d'observador; les coordenades del panell = les del punt | `FET` |
| 3.2 Bloquejar l'observador durant la reproducció (D5) | `triar_punt()` no canvia res mentre es reprodueix; el doble clic i el WASD només mouen la càmera; el panell avisa que el punt està bloquejat | Prova automàtica (Claude) i de l'equip: amb la reproducció en marxa, canviar de punt no fa res; es pot girar i fer zoom; coordenades, CNIG i model del mateix punt | `FET` |
| 3.3 `durada = None` sense dades vàlides | `dades/model_eclipsi.py` | `validar_model.py`: el punt (55, 0) no dona error en accedir a `durada` | `FET` (Resolta a la 9.2: el model nou té `durada = None` quan no hi ha totalitat) |
| 3.4 Curvatura i horitzó coherents (D6, D18, §7) | Mode normal amb curvatura geomètrica activa (centrada a l'observador, k = 0) i exageració 1; controls de depuració etiquetats; ull a altitud del MDT complet + 1,7 m | Horitzó del script = horitzó del depth buffer (≤ 0,05°), tots dos amb k = 0 | `FET` (F11: `scripts/validar_horitzo.py`, ≤ 0,006° a les sis ubicacions. Els ulls són sobre la superfície dibuixada, que coincideix amb el MDT a ≤ 1 cm al punt) |
| 3.5 Convergència UTM | Sol i Lluna girats −γ | `validar_model.py`: el nord geogràfic té azimut de quadrícula −γ a l'escena | `FET` (Resolta a la 9.3: tot és en coordenades terrestres; no hi ha nord de quadrícula a l'escena) |
| 3.6 Refracció del Sol | Substituir la correcció constant per una fórmula de refracció documentada (§6.5), només si l'explicació és defensable | Error tipus 1: elev. al màxim ≤ 0,02° del CNIG als 9 punts. Error tipus 2 (mateixa font): posta ≤ 1 min de la banda 5 | `FET` (Resolta a la 9.2: refracció de Bennett per a l'elevació mostrada; elevació al màxim a ≤ 0,017° del CNIG) |
| 3.7 Contactes asimètrics | Primer: explicar la causa de l'asimetria. Després, només si aporta valor (§6.4.1), un model de la Lluna amb C1 i C4 correctes | Error tipus 1: C1–C4 ≤ 5 s als 9 punts | `FET` (Resolta a la 9.2: amb les efemèrides reals, C1–C4 a ≤ 1,2 s del CNIG) |
| 3.8 Comprovació independent (D20, D23) | Consulta manual del calculador de la NASA (§6.3.1) en uns quants punts (Picos, un punt de totalitat més, 2 punts catalans) i moments (C1, màxim, C4, posta). Taula amb les convencions de cada valor: hora (TU), coordenades i altitud, refracció inclosa o no, definició dels contactes | Error tipus 2 dins dels objectius de §6.4, o explicació de la diferència | `FET` (F11: `scripts/comparar_nasa.py`, 9 punts i tots els contactes; D41) |

Per a la F3:
- Aprenem: càmeres (orbital i de primera persona), geodèsia bàsica (convergència, curvatura,
  refracció), validació (ajust vs. predicció).
- Documentem: una taula d'errors abans i després a la web (O1.3) i aquí.

### F4 — Dades i ubicacions (N; mínim)

| Tasca | Canvia | Depèn | Comprovació | Estat |
|---|---|---|---|---|
| 4.1 `data/FONTS.md` i política del `.gitignore` (MDT nous a una carpeta ignorada; Picos versionat) | Documentació i `.gitignore` | D21 | Cada fitxer de `data/` hi surt amb la seva comanda | `FET` (MDT nous a `data/mdt/zones/`, ignorada) |
| 4.2 Retirar Luarca, Astúries i la fulla `mdt05` | `TERRENYS`, scripts, README; retirar del git; esborrar `altres/` | 4.1, permís | `preparar_dades.py`, `captura.py` i `main.py` funcionen | `PENDENT` |
| 4.3 Zona del Vallès | 5 m en ~25 km (Cerdanyola, UAB, Montmeló) + anell de 25 m fins a ~100 km (dos `Terrain`; el shader ja té les "zones" per amagar el llunyà on hi ha el proper) | 3.4, 0.3; l'equip fa la descàrrega | Horitzó del programa = script (≤ 0,05°); ombra del CNIG al màxim coherent | `EN CURS` (F10: zona de 5 m de 31,7 × 28,5 km i pegats de detall. F11: 3.4 i 0.3 fets; horitzó ≤ 0,006° i ombres comparades amb el CNIG. Falta l'anell de 25 m: ara hi fa el paper un pegat de la península a 200 m de ~100 km) |
| 4.4 Vic i l'Escala | Ídem | 4.3 | Ídem | `FET` (F10: zones de 5 m de 20 × 20 km; F11: horitzó i ombres comprovats. Sense anell de 25 m, com el Vallès) |

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
- 6.1 Ombres del relleu (shadow mapping) i comparació amb `terrain_shadows` del CNIG. `FET` a la zona de 5 m (F11, tasca 11.5). Pendent: estendre-ho fora de la zona (península).
- 6.2 Menú de meteorologia (clar, boira, núvols). `PENDENT` (fora d'aquest tram, per indicació de l'equip).

### F9 — Escena coherent i interacció nova (mínim; D32–D38)

Substitueix l'ordre anterior: es comença pels problemes visibles i després es construeix l'escena
espacial, integrant-hi les correccions astronòmiques i geogràfiques (3.4–3.8).

| Tasca | Canvia | Estat |
|---|---|---|
| 9.1 | P només reproduir/pausar; sense seguir el Sol; fora el marcador permanent; panell senzill | `FET` |
| 9.2 | Efemèrides reals del Sol i la Lluna (JPL Horizons) i geodèsia (WGS84) a `dades/` | `FET` |
| 9.3 | Món en coordenades terrestres (ECEF): Terra, península + Picos posats sobre el globus, profunditat logarítmica, coordenades relatives a la càmera | `FET` |
| 9.4 | Càmeres noves: exploració lliure del terreny a l'espai i observació amb la mirada fixa | `FET` |
| 9.5 | Ombra de la Lluna per a cada punt de la superfície; Sol treballat; Lluna amb textura | `FET` |
| 9.6 | Model de l'observador a partir de la geometria; comprovació contra el CNIG (fet) i la NASA (F11, fet) | `FET` |
| 9.7 | README, `data/FONTS.md`, `CLAUDE.md`, pla i web | `EN CURS` |

**Resultats de la F9 (22/10/2026).**

*Comprovat automàticament:*
- `scripts/validar_model.py` (independent: el model no s'ajusta al CNIG): als 9 punts, C1, C2, màxim, C3 i
  C4 a ≤ 1,2 s del CNIG; part tapada al màxim a ≤ 0,05 punts; elevació del Sol a ≤ 0,017°.
- `scripts/validar_ombra.py`: l'eix de l'ombra cau dins del polígon de la umbra del CNIG a tots els
  instants comparats que no estan retallats (de 18,338 a 18,518 h TU). La distància al centre del
  polígon creix quan el Sol baixa (de 3 a 132 km), perquè l'ombra s'allarga cap al terminador.
- Prova del programa real (finestra amagada, 13 condicions): els ulls i la mirada no canvien en
  reproduir (el Sol no se segueix); els ulls són a 1,7 m del terra dibuixat; P congela i continua des
  del mateix instant sense moure la càmera; la roda allunya la càmera de 3,5 km a ~27.000 km sense
  canviar el camp de visió; la velocitat amb W és ~2,6 km/s a 3,5 km d'altura i ~21.000 km/s a
  27.000 km; el punt no es pot canviar durant la reproducció; el picking cau a 0,3 m de la superfície;
  el terra s'enfosqueix a la totalitat.
- Mode pla (`captura.py`, exercici 1.0): igual que abans llevat d'arrodoniments a les siluetes
  (l'exercici continua `COINCIDEIX`). Els originals del `basecode/`, sense canvis.

*Inspeccionat visualment (captures):* eclipsi parcial amb el creixent del Sol; totalitat amb la corona;
transició del terreny a 50 km i 800 km amb Picos encaixat dins la península i el globus fora d'Espanya;
la Terra des de l'espai amb la cara de dia i l'ombra; la Lluna amb textura il·luminada pel costat del Sol.

*Provat per l'equip:* encara no.

*Aproximacions i limitacions:* el geoide no es corregeix (~50 m); la malla del globus queda fins a
~120 m per sota de l'el·lipsoide entre vèrtexs (el relleu la tapa); fora d'Espanya només hi ha la
textura del globus, sense relleu; la península té un vèrtex cada ~1 km; els ulls van sobre la
superfície dibuixada (mitjana de la malla); l'orientació de la Lluna és aproximada (sense libració);
el color del cel, el halo, la corona, el contorn d'atmosfera i la granulació del Sol són il·lustratius;
l'eclipsi a Espanya passa a prop de la posta, de manera que des de l'espai l'ombra cau a prop del
terminador i es distingeix poc del vespre.


### F10 — Correccions de les vistes des del terra (prova de l'equip, 22/10/2026)

L'equip va provar el programa i va trobar, a Vic, la UAB, Cerdanyola, Montmeló i l'Escala, el terra
tallat gairebé en horitzontal i, a sota, una superfície blava amb textura, i l'avís del controlador
`unit 0 GLD_TEXTURE_INDEX_2D is unloadable`. Abans de cap funcionalitat nova, es corregeixen les causes.

| Tasca | Canvia | Estat |
|---|---|---|
| 10.1 | Retall dels triangles amb la profunditat logarítmica; textura de la unitat 0 al shader de les esferes | `FET` |
| 10.2 | Altures calculades a la CPU (els ulls sobre els triangles dibuixats); zones de 5 m de Vic, l'Escala i el Vallès; pegats de detall al voltant de l'observador; transicions entre nivells; el mar de les zones de la costa | `FET` |
| 10.3 | "Anar al màxim del punt seleccionat", "Veure l'ombra des de l'espai" i ressaltat didàctic opcional | `FET` |
| 10.4 | `scripts/prova_vistes.py`: prova reproduïble a les sis ubicacions | `FET` |

**Causes demostrades.**
- *Tall blau.* Els vertex shaders escrivien la profunditat logarítmica a `gl_Position.z`. La GPU retalla
  (clipping) cada triangle interpolant z **linealment** entre els vèrtexs; amb una z logarítmica, un
  triangle gran que passa per darrere de la càmera es retallava fins a desenes de metres davant dels
  ulls. A la península hi ha un vèrtex cada ~1 km: a Vic desapareixia el terra proper i es veia
  l'interior del globus (Amèrica, mirant a l'oest). Un càlcul amb els triangles reals prediu el tall a
  la fila 127 de la imatge (12 m davant dels ulls) i la captura el mostra a la 146; la diferència ve
  de les altures aproximades del càlcul. Correcció: `gl_Position.z` és la de la projecció i la
  profunditat logarítmica només la posa `gl_FragDepth`.
- *Avís de textura.* El shader de les esferes declara el sampler de la textura de la Lluna per a tots
  els modes; el Sol, la primera passada del primer fotograma, es dibuixava sense cap textura a la
  unitat 0 (textura incompleta). Comprovat dibuixant cada passada per separat. Correcció: cada esfera
  hi lliga una textura (d'1 píxel per al Sol i el halo).
- *Ulls mal posats.* La prova de la F9 comparava l'altura dels ulls amb l'estimació de la CPU, no amb
  el que es dibuixa. Llegint el depth buffer mirant avall, els ulls eren a 1,33 m (Picos), 2,7 m (Vic),
  90 m (Cerdanyola) i 122 m (Montmeló) del terra dibuixat: la CPU (interpolació bilineal d'una mitjana
  per blocs) i la GPU (mipmap de nivell fraccionari i triangles d'~1 km) calculaven l'altura de maneres
  diferents. Correcció: al mode globus, l'altura de cada vèrtex la calcula la CPU (atribut `in_h`), que
  després interpola sobre els mateixos triangles.

**Nivells de detall (D39).** De lluny a prop: graella general de la península (~1 km entre vèrtexs);
pegat de la península al voltant de l'observador (un vèrtex per píxel de 200 m, ~100 km); zona de 5 m
que conté el punt (~20 m entre vèrtexs; Picos, Vic, l'Escala o el Vallès, carregada en triar el punt,
0,5–1,6 s); pegat de la zona al voltant de l'observador (un vèrtex per píxel de 5 m, ~2,5 km). Cada
nivell fa un forat al de sota; a la franja de la vora (12 %), l'altura passa suaument a la del nivell
de sota, i unes faldilles de 30 m tapen les escletxes que quedin. Al mar de les zones de la costa,
l'aigua passa al color del globus (mateixa textura i llum) cap a la vora. Només es manté carregada la
zona de l'observador (~200 MB de GPU cadascuna).

**Comprovat automàticament** (`python scripts/prova_vistes.py`, finestra amagada i també `--visible`):
a les sis ubicacions, els ulls a 1,698–1,700 m dels triangles dibuixats (llegit del depth buffer); la
superfície dibuixada coincideix amb el MDT original a ≤ 1 cm al punt; mirant a −30° i −60°, la meitat de
baix de la imatge és terreny a menys de 56 m (Picos) o 4 m (la resta), sense cel ni globus; reproduir i
pausar no mou els ulls ni la mirada; allunyar-se fins a més de 20.000 km sense canviar l'hora i tornar
al mateix punt i mirada; "Anar al màxim" deixa l'hora del màxim pausada i la càmera quieta; el terra és
més fosc al màxim que a l'inici; "Veure l'ombra des de l'espai" posa al centre de la imatge el punt més
fosc de l'ombra (a ≤ 7 km); el punt no es pot canviar reproduint; picking a 0,01 m; velocitats; cap avís
`UNSUPPORTED` del controlador. El mode pla (`captura.py`) dona la mateixa imatge que abans (0 píxels
diferents) i l'exercici 1.0 continua `COINCIDEIX`.

**Inspeccionat visualment** (captures a `captures/proves/`, una làmina per ubicació): les quatre
direccions i cap als peus des del terra; 50 km, 800 km i 20.000 km; l'inici, el màxim i el final; l'ombra
des de l'espai amb i sense línies; les unions entre nivells des de 0,4, 4, 30 i 250 km (també amb
filferros) a Vic, l'Escala i Cerdanyola.

**Provat per l'equip:** encara no. La prova `--visible` obre la finestra i hi mostra cada fotograma,
però no fa servir el ratolí ni el teclat de debò.

**Limitacions.** Des de l'espai, l'ombra real es distingeix poc: a Espanya l'eclipsi passa a prop de la
posta, l'ombra cau a prop del terminador i sovint sobre el mar fosc; la umbra fa ~290 km i la penombra
enfosqueix de manera gradual. Per això hi ha les línies didàctiques, opcionals i identificades. Entre
10 i 50 km de l'observador el relleu ve del MDT de 200 m (l'anell de 25 m de la 4.3 és pendent). Amb
el Sol baix, el terra es veu fosc: és el model d'il·luminació actual, no s'ha tocat. La textura del
globus té píxels de ~20 km. En explorar una zona de 5 m que no és la de l'observador, només hi ha el
relleu de 200 m.


### F11 — Estabilitat de la seqüència, validació geogràfica i astronòmica, ombres del relleu (26/10/2026)

Objectiu del tram: deixar estable i comprovada la seqüència triar una ubicació → observar a 1,7 m →
mirar a mà → P → explorar fins a l'espai → reprendre el temps sense moure la càmera → tornar al punt.
Després, tancar les validacions pendents (0.3, 3.4, 3.8) i començar les ombres del relleu (6.1).

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 11.1 | N (prova) | `scripts/prova_vistes.py`: superfície coherent pujant, P a l'espai, canvi d'ubicació explorant, seqüència sencera amb el bucle real | `FET` |
| 11.2 | C | Triar una ubicació de la llista posa la càmera d'exploració a sobre del punt nou (D43) | `VALIDAT` (26/10: l'exploració comença a Vic) |
| 11.3 | dades | Coordenades verificades (tasca 0.3, D40) | `FET` |
| 11.4 | N (prova) | `scripts/comparar_nasa.py` i `data/nasa/circumstancies_nasa.csv` (tasca 3.8, D41); `scripts/validar_horitzo.py` (tasca 3.4) | `FET` |
| 11.5 | N | Ombres del relleu (shadow mapping) a la zona de 5 m i `scripts/validar_ombres_relleu.py` (tasca 6.1, D42) | `FET` |
| 11.6 | doc | Pla, README, `data/FONTS.md` i web | `FET` |
| 11.7 | C | L'interruptor de les ombres del relleu no les tornava a encendre en pausa (error trobat per l'equip) | `VALIDAT` (26/10: l'equip l'ha tornat a provar i funciona) |

**11.1 — Estabilitat (comprovat automàticament, `python scripts/prova_vistes.py`, ~25 s).** Abans de
canviar res, totes les proves existents passaven (`validar_model.py`, `validar_ombra.py`,
`prova_vistes.py`). S'hi han afegit les comprovacions que faltaven:
- *Superfície coherent pujant:* a cada fotograma de l'ascens fins a 20.000 km (sis ubicacions, ~7.000
  píxels per ubicació), cada píxel es desprojecta i ha de caure sobre una de les dues superfícies que hi
  poden ser: el relleu dibuixat (±35 m per les faldilles, més 2·10⁻⁶ de la distància per la precisió del
  depth buffer logarítmic de 24 bits) o el globus, només on la península no dibuixa (mar i fora d'Espanya):
  fins a 120 m sota l'el·lipsoide (cares planes de la malla) més 2·10⁻⁵ de la distància (`terra.frag`
  empeny la seva profunditat perquè el relleu li guanyi). A més, cap píxel es pot veure per sota (raig que
  arriba pujant: seria l'interior del globus). Resultat: 0 píxels fora i 0 per sota; pitjor diferència
  amb el relleu, 30 m a 9.000 km d'altura (dins de la precisió). *Primera execució:* 2 % de píxels "fora":
  eren el biaix del globus i el mar, no forats (diagnosticat classificant-los per la distància a la costa);
  i un píxel que era el Sol.
- *P a l'espai:* a 20.000 km, reprendre el temps fa avançar l'hora i no canvia ni la posició ni
  l'orientació de la càmera d'exploració.
- *Canvi d'ubicació explorant* (doble clic): la càmera d'exploració no es mou; els ulls van al punt nou.
- *Seqüència sencera amb el bucle real* (`GraphicsEngineBase.run`, el panell dibuixat a cada fotograma):
  les tecles P i V i el ratolí entren com a esdeveniments d'imgui; les fletxes, substituint
  `glfw.get_key`; la ubicació, amb `triar_ubicacio` (el que crida el desplegable). Comprova els set passos
  de la seqüència.
- *Avís `texture unloadable`:* no s'ha reproduït en aquest ordinador ni amb el bucle real i el panell, ni
  activant les capes del CNIG, els filferros i el canvi de zona; la prova busca `UNSUPPORTED` i
  `unloadable` a la sortida d'errors del controlador. **No es pot donar per resolt a la màquina on el va
  veure l'equip** fins que l'equip ho comprovi allà.

Observació d'ús (no corregida): amb la mirada inclinada −25°, cada pas de la roda guanya ~10 % d'altura:
calen ~90 passos per arribar a 20.000 km.

**11.2 — Correcció (comprovada automàticament).** Abans, si es triava una ubicació de la llista i després
es premia V, la càmera d'exploració continuava sobre l'ubicació anterior (Picos, on comença). Ara
`triar_ubicacio()` (main.py) també la posa a sobre del punt nou; el doble clic continua sense moure-la.
Comprovació: a la seqüència, després de triar Cerdanyola i prémer V, la càmera és a 6,7 km dels ulls.

**11.3 — Coordenades:** §10.3 i D40. Els resultats de `validar_model.py` no canvien de manera apreciable
(diferències màximes amb el CNIG: 0,7 / 1,2 / 0,7 / 0,5 / 1,2 s a C1, C2, màxim, C3 i C4).

**11.4 — NASA i horitzó (comprovat automàticament).**
- `python scripts/comparar_nasa.py` (el pas `--calcular` necessita macOS i xarxa; la resta funciona amb el
  CSV). Convencions alineades: observador a 0 m, elevació geomètrica (sense refracció), hores en TU.
  Resultat, model − NASA als 9 punts: C1 +3,1 s, C2 +1,1…+1,9 s, màxim +2,5 s, C3 +3,1…+3,9 s, C4 +2,0 s;
  part tapada ≤ 0,02 punts; elevació i azimut al màxim ≤ 0,005°. CNIG − NASA: +2,2…+3,8 s. Explicació:
  (1) la NASA fa servir dos radis de la Lluna (k = 0,2725076 per a C1 i C4, k = 0,272281 per a C2 i C3) i
  nosaltres 1737,4 km per a tots; amb els seus radis, tots els contactes queden a +2,49 s (de +2,27 a
  +2,71); (2) aquesta diferència constant és la que donaria un ΔT de 68,9 s a les efemèrides de JPL,
  contra els 71,4 s de la NASA. Compatible amb el ΔT actual (~69 s), **no verificat**: l'API de Horizons
  retornava un error intern quan es va consultar. Tot és sota l'objectiu de 5 s (§6.4); no s'ha ajustat res.
- `python scripts/validar_horitzo.py` (~13 s). Horitzó en l'azimut del Sol al màxim: MDT complet,
  superfície dibuixada i depth buffer (zoom de 2°, 0,003° per píxel). Imatge − superfície dibuixada:
  ≤ 0,006° a les sis ubicacions (objectiu 0,05°). MDT − dibuixada: fins a 0,07° (UAB, carena a 1,4 km,
  fora del pegat de 5 m). Ocultació del Sol al màxim: §10.3. Limitacions: fora d'Espanya el MDT val 0; sense
  edificis ni arbres; sense refracció terrestre.

**11.5 — Ombres del relleu (comprovat automàticament i inspeccionat visualment).**
- Implementació: `basecode/ombres_relleu.py` (passada des del Sol en una textura de profunditat de 4096²,
  projecció ortogràfica ajustada a 16 km al voltant de l'observador, àncora al punt d'observació),
  `shaders/ombra.*` i `llum_relleu()` a `terrain.frag` (comparació per maquinari, `sampler2DShadow`, 3 × 3
  lectures). Només la zona de 5 m projecta i rep ombres. La llum és la del Sol aparent. El mapa es recalcula
  només si canvien l'hora, el punt o l'exageració. Cost mesurat: el mateix temps per fotograma (~9 ms,
  finestra amagada de 1280 × 860) amb ombres i sense, reproduint i en pausa.
- *Acne:* desplaçament d'1 texel (~8 m) en la direcció de la normal i 3 m de marge cap al Sol. Provat
  0,5 texels: apareix acne (menys píxels clarament al sol o a l'ombra: 916 contra 1.113). Conseqüència:
  obstacles de menys de ~12 m per sobre del raig no fan ombra.
- `python scripts/validar_ombres_relleu.py --totes` (~25 s): (1) GPU contra un raig independent de la CPU
  sobre la superfície dibuixada, ~1.150 píxels per ubicació (mode de depuració que pinta el factor
  d'ombra): 0 desacords fora del biaix calculat (11,6–12,7 m); els casos dins del biaix són del 4 % (Picos)
  al 17 % (UAB, Sol a 4°). Primera execució amb un llindar fix de 5 m: 96–99 %, sempre "GPU sol" amb
  l'obstacle a 5–8 m: era el biaix, no un error. (2) Contra la capa `terrain_shadows` del CNIG (si el
  centre del Sol arriba al terra al màxim; cel·les de ~230 m en 6 km al voltant del punt): amb el nostre MDT
  de 200 m coincideixen el 74,4 % (Picos), 82,9 % (Vic), 95,1 % (l'Escala), 78,5 % (Cerdanyola), 81,2 %
  (Montmeló) i 80,1 % (UAB) de les cel·les; sense refracció, ±1 punt (no és la causa); amb el MDT de 5 m,
  65,7–91,7 %, i trobem el doble de cel·les tapades (ombres petites que el CNIG no resol). Les
  diferències a 200 m vénen dels dos MDT (GMTED2010 contra IGN) i de la posició i mida de les cel·les; el
  CNIG no documenta com tracta la vora del Sol.
- Inspecció visual: Picos 30 min abans del màxim des de l'aire (ombres a la cara oculta de les carenes,
  sense acne visible) i des del terra (diferència petita; ratlles d'1–2/255 al pendent proper).
- El mode pla (`captura.py`) dona la mateixa imatge que abans (0 píxels diferents); l'exercici 1.0
  continua `COINCIDEIX`; els originals del `basecode/`, sense canvis.

**Provat per l'equip (26/10/2026, Mac de l'equip, entorn `egra`).** Només el que l'equip va fer i
informar:
- *Arrencada:* la finestra i el terreny s'obren bé. La sortida de la consola que l'equip va enganxar
  (de l'arrencada fins a carregar la zona de Picos) **no conté l'avís `texture unloadable`**. No tenim la
  sortida de la resta de la sessió, així que només queda comprovat per a l'arrencada.
- *Vic:* terreny correcte mirant al voltant i cap avall; la mirada es queda fixa durant la reproducció;
  l'exploració comença a Vic (11.2).
- *Terra → espai → terra:* en pausa, l'hora no canvia mentre es mou la càmera; P reprèn el temps sense
  moure la càmera; "Tornar al punt d'observació" torna al lloc correcte.
- *Roda:* s'allunya bé, però **a l'espai es perd l'orientació i costa tornar a trobar els astres**
  (observació d'ús, pendent de decidir com resoldre-ho; no s'ha canviat res).
- *Picos:* terreny, controls i seqüència completa correctes; la fluïdesa, "crec que bé" (no mesurada).
- *Ombres del relleu:* **no funcionava l'interruptor**. La primera vegada que es van desactivar sí que es
  va notar el canvi; en tornar-les a activar i desactivar, cap canvi. Causa: en apagar-les es conservava
  la clau del mapa i, en pausa, en tornar-les a encendre no es recalculava (`valid` es quedava a fals).
  Corregit a la 11.7 i comprovat automàticament (apagar, encendre, apagar, encendre en pausa a les sis
  ubicacions). *Segona prova de l'equip (26/10):* l'interruptor ara funciona. Només s'ha registrat
  aquesta comprovació de l'interruptor.
- *L'Escala:* al màxim, el Sol queda tapat pel relleu, com deia `validar_horitzo.py` (horitzó de 6,45°
  contra 3,71° del Sol). El càlcul situa l'obstacle a 100 m de l'ajuntament; l'equip el descriu com "les
  muntanyes" (no s'ha comprovat a quina distància el va veure). En pujar amb la càmera, la Terra es veu
  fosca i el Sol no es veu.
- *Cerdanyola, Montmeló i la UAB:* "tot bé" (sense detall de quines comprovacions).

Proves que encara falten de l'equip: les ombres del relleu després de la 11.7 (Picos cap a les 19:58,
Avançat → apagar i encendre diverses vegades, en pausa i reproduint); l'avís de textura al llarg d'una
sessió completa (amb capes del CNIG i canvis d'ubicació).

**Següent pendent:** que l'equip torni a provar l'interruptor de les ombres; decidir com ajudar a
orientar-se a l'espai (p. ex. un botó per mirar cap al Sol o cap a la Terra; seria un canvi de la
interfície, a acordar); estendre les ombres del relleu fora de la zona de 5 m (casters de la península, per a
les serres llunyanes amb el Sol baix); l'anell de 25 m (4.3); la prova de l'equip; després, 6.2
(meteorologia) quan l'equip ho decideixi.

### F12 — Arrencada, espai de navegació, mirada amb el ratolí i roda (26/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 12.0 | C | El halo del Sol escrivia profunditat (`ctx.depth_mask` no existeix a ModernGL 5) | `FET` |
| 12.1 | C | Arrencada pausada a C1 − 60 min (D44) | `FET` |
| 12.2 | N | Cub de navegació i parets (`dades/navegacio.py`, `basecode/paret_cub.py`, `shaders/paret.*`) (D45) | `FET` |
| 12.3 | N | Mirada amb el ratolí capturat (`basecode/control_ratoli.py`, `run()` a `main.py`) (D46) | `FET` |
| 12.4 | C | Roda i trackpad adaptats a l'escala (D47) | `FET` |
| 12.5 | doc | README, pla i web | `FET` |

**12.0 — Halo (trobat en provar l'enquadrament del Sol).** A ModernGL 5.12 la màscara de profunditat és
de cada framebuffer (`Framebuffer.depth_mask`); `ctx.depth_mask = False` només creava un atribut de Python.
El halo (esfera de 4 radis solars, translúcida) escrivia profunditat: mirant el Sol amb zoom des de Picos,
39.510 píxels amb profunditat contra 2.474 després de la correcció (el disc del Sol, ~2.548 esperats). Un
doble clic al cel a prop del Sol podia retornar un punt del halo. Ara es fa servir `ctx.fbo.depth_mask`.

**12.1 — Arrencada.** `hora = C1 del model − 1 h` (TU, `HORA_ABANS_C1` a `main.py`), pausat. A Picos,
C1 19:31:39 CEST → arrencada a les **18:31:39 CEST**, dins de la barra de temps (16:00–23:30). Comprovat
automàticament (`prova_vistes.py`): l'hora inicial és exactament aquesta i, en triar tres ubicacions de la
llista, l'hora no canvia ni es posa en marxa.

**12.2 — Espai de navegació.**
- *Càlcul* (`cub_navegacio`, un sol cop en arrencar): extrems en X, Y i Z de la Terra (el·lipsoide WGS84,
  6.378,137 km a X i Y, 6.356,752 km a Z), la Lluna (+1.737,4 km) i el Sol (+696.000 km), cada minut de 14:00
  a 21:30 TU, en ECEF (el sistema de tota l'escena: X cap a la longitud 0, Y cap a 90° E, Z cap al pol nord;
  km). Marge a cada costat; després les dimensions curtes s'amplien simètricament fins a la més llarga.
- *Marge final:* amb un radi solar, des de la paret de darrere del Sol (a 2 radis del centre), el disc faria
  60° i no cabria en el camp vertical de 50° de la càmera d'exploració. Es demana que ocupi com a molt el
  90 % del camp: distància = R / sin(22,5°) = 2,613 R, és a dir, **marge = 1,613 radis solars = 1.122.736 km**.
- *Resultat:* **costat 246.438.601 km = 1,6473 UA**; X de −116.133.088 a 130.305.513 km; Y de
  −196.844.044 a 49.594.556 km; Z de −103.452.898 a 142.985.702 km (extrems dels astres: X −115.010.352 …
  129.182.777; Y −147.255.866 … 6.378; Z −6.357 … 39.539.160).
- *Per què més d'1 UA:* en ECEF la Terra no gira i el Sol hi fa ~112° de volta en les 7,5 h de l'interval;
  el cub ha de contenir tot l'arc, per això la dimensió més llarga és X (1,63 UA d'arc més els marges). Un cub
  fix respecte de les estrelles seria d'~1 UA, però giraria respecte de l'escena mentre es reprodueix: no
  compleix que "no es desplaci" en el sistema en què es dibuixa i es navega.
- *Límit:* `CameraExploracio.posicio` és una propietat i tota posició nova passa per `Cub.limitar`, que
  retalla cada coordenada per separat. A la paret s'atura només el moviment cap a fora i el paral·lel
  continua; no hi ha rebots perquè no s'inverteix cap velocitat. La càmera s'atura a 1.000 km de la paret
  (4·10⁻⁶ del costat): si el pla d'una cara passés pels ulls es veuria de cantell i la rasterització seria
  degenerada (vist a la primera prova d'enquadrament).
- *Parets:* sis cares translúcides; l'opacitat de cada una passa de 0 a 1 entre el 3 % del costat (~7,4
  milions de km) i la paret. Ratlles diagonals d'amplada proporcional a la distància (~1/20), barrejant dues
  escales perquè no canviïn de cop. El punt de la paret es reconstrueix al fragment shader com la
  intersecció del raig amb el pla (la posició interpolada en float32 no té prou precisió en cares de
  2,5·10⁸ km). Les ratlles són relatives a la càmera: no es desplacen quan la càmera es mou en paral·lel a
  la paret (simplificació).
- *Comprovat automàticament* (`python scripts/prova_controls.py`): el cub conté els tres astres a tot
  l'interval; a les sis cares, el teclat (W i E premudes 40 fotogrames), la roda i una posició posada
  directament s'aturen al límit, la coordenada de la cara es queda exactament igual cada fotograma i el
  moviment paral·lel continua; els botons "Veure l'ombra des de l'espai" i triar una ubicació deixen la
  càmera dins. *Enquadrar el Sol:* per a cada cara, amb el Sol a l'instant en què hi és més a prop, des de
  la paret de darrere: a les cares X (el cas límit) el Sol és a 2,61 radis i fa 45,0° dels 50°; el disc
  sencer és dins de la imatge (41 % dels píxels, cap a la vora). *Inspeccionat visualment:* la paret a
  1.000 km i a 3 milions de km, i el Sol sencer des de la paret X−.

**12.3 — Mirada amb el ratolí.** GLFW `CURSOR_DISABLED`: el cursor s'amaga i queda lligat a la finestra, i
`get_cursor_pos` dona una posició virtual sense límits; la diferència entre fotogrames és el moviment
relatiu. El moviment "raw" (`RAW_MOUSE_MOTION`) no és disponible a macOS (`raw_mouse_motion_supported()` =
False); s'activa només si el sistema el té. Sensibilitat: 0,12° per punt de pantalla (menys amb zoom), sense
inèrcia; inclinació limitada a ±89° (observació) i ±89,9° (exploració). Un clic (sense arrossegar) a
l'escena captura passat el temps del doble clic (0,3 s); un doble clic no captura i, a l'exploració, tria el
punt. Mentre és capturat, imgui no rep el ratolí (`ConfigFlags.NO_MOUSE`). Esc: el bucle del basecode
tancava el programa; `GraphicsEngine.run()` és el mateix bucle amb un canvi (si el ratolí és capturat, Esc
l'allibera i cal deixar anar la tecla abans que un altre Esc tanqui). Perdre el focus allibera (callback de
GLFW, encadenat amb el d'imgui). En capturar, el primer moviment es compta des d'on és el cursor: sense salts.
*Comprovat automàticament* (`prova_controls.py`, `prova_vistes.py`): 50 i 20 punts giren 6,0° i 2,4° i els
ulls no es mouen; 60 fotogrames sense moviment, la mirada no canvia; amb −5000 punts la inclinació es queda a
89°; alliberat, moure el cursor no gira; tornar a capturar en un altre lloc no fa saltar; perdre el focus
allibera; un clic a l'escena captura sense girar; un clic al panell no; el doble clic tria el punt i no
captura; arrossegar i fer rodar sobre el panell no mou la càmera; P (explorant i observant) només canvia
reproduir/pausar; amb el bucle real, Esc allibera i el programa continua. *Limitació de la prova:* la
finestra amagada no té el focus i macOS no hi aplica el cursor desactivat; el moviment se simula substituint
`glfw.get_cursor_pos` (com les fletxes amb `glfw.get_key`). Per tant, **la captura real del cursor no està
comprovada automàticament**.

**12.4 — Roda i trackpad.** El trackpad del Mac: s'ha comprovat què implementa la biblioteca GLFW que fa
servir l'entorn (`/opt/homebrew/Cellar/glfw/3.5.1/lib/libglfw.3.5.dylib`): conté `scrollWheel:` i
`hasPreciseScrollingDeltas` (lliscar amb dos dits, amb valors fraccionaris) però no `magnifyWithEvent:`, el
mètode de macOS que rep el pessic. Per tant **el gest de pessigar no arriba al programa** (deduït del binari;
no provat amb un trackpad). Alternativa: lliscar amb dos dits amunt/avall, que arriba com la roda. Els valors
es sumen fins al fotograma següent (callback de GLFW). Exploració: n passos multipliquen l'altura per
1,35⁻ⁿ (endavant s'acosta al terra cada cop més a poc a poc i no el travessa), el desplaçament es divideix pel
sinus de la inclinació (mínim 0,3) i es limita a 3 passos per fotograma. Observació: el camp de visió es
multiplica per 0,85ⁿ, sense moure els ulls. *Comprovat automàticament:* del terra (2,9 km) a 20.000 km amb
28 passos (mirant a −25°; abans ~90) i 30 (a −60°); 25 passos en un fotograma es limiten a 3; un pas a
l'observació canvia el camp de 60° a 51° i els ulls no es mouen.

**Proves de la seqüència i de les ombres** (automàtiques, després dels canvis): `prova_vistes.py` (sis
ubicacions i seqüència amb el bucle real) i `validar_ombres_relleu.py` (interruptor en pausa) donen tot
correcte; l'horitzó (`validar_horitzo.py`), el mode pla (0 píxels diferents) i l'exercici 1.0, igual.
`prova_vistes.py` ha calgut ajustar-lo: amb la roda nova l'ascens passa per altres posicions i hi ha aparegut
la frontera amb França a la Cerdanya, on, vist de lluny, el mipmap de la textura de costa desplaça la vora
on la península deixa de dibuixar-se (es veu el globus); la franja de la prova s'ha fet proporcional a la
distància.

**Provat per l'equip:** encara no. Proves amb el ratolí i el trackpad físics del Mac:
1. Clic a l'escena: el cursor desapareix i moure el ratolí gira la mirada sense prémer, sense topar amb la
   vora; Esc l'allibera i es pot fer servir el panell; Esc un altre cop tanca.
2. Canviar a una altra aplicació (Cmd+Tab) amb el ratolí capturat: queda alliberat; en tornar i fer clic,
   la mirada no salta.
3. Doble clic al terreny explorant (ratolí lliure): tria el punt i no captura.
4. Clic i arrossegar sobre el panell: la càmera no es mou.
5. Roda del ratolí i lliscar amb dos dits: acostar-se al terra amb precisió i sortir a l'espai amb ~30
   passos; pessigar no fa res (esperat).
6. Explorar fins a una paret del cub: s'hi veuen les ratlles, la càmera s'hi atura sense tremolar i es pot
   lliscar al llarg de la paret.
7. Arrencar: el rellotge marca 18:31:39 en pausa.

**Següent pendent:** les proves de l'equip; si es vol el pessic natiu, autoritzar PyObjC (D47); ancorar les
ratlles de la paret al món (ara es mouen amb la càmera).

### F14 — Edificis a les zones de detall (26/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 14.1 | N | Descàrrega i preparació (`scripts/descarregar_edificis.py`, `dades/edificis.py`) | `FET` |
| 14.2 | N | Dibuix, opció "Mostrar edificis", fracció del Sol tapada (`basecode/edificis.py`, `shaders/edifici.*`, `ui.py`) | `FET` |
| 14.3 | N | Els edificis projecten ombra al mapa d'ombres de la zona | `FET` (inspeccionat; no validat numèricament) |
| 14.4 | N (prova) | `scripts/validar_edificis.py` | `FET` |
| 14.5 | doc | README, `data/FONTS.md`, pla i web | `FET` |

**Fonts investigades.** MDT (el sòl), MDS (superfícies superiors: edificis *i* vegetació) i geometria
d'edificis (contorns separats del terreny) són coses diferents: no s'ha substituït el terreny per un MDS.
- *Catastro INSPIRE, Buildings* (ATOM per municipi): contorns de les parts d'edifici (precisió declarada
  0,1 m) i plantes sobre rasant. **Accessible i fet servir.** El servidor té un certificat de la FNMT que curl
  no reconeix; Python (`requests`, amb `certifi`) sí.
- *CNIG, MDS normalitzat d'edificació (2,5 m, LiDAR PNOA)*: altures d'edificis sobre el terra, la millor
  font per a les altures. **No accessible:** el Centre de Descàrregues accepta la connexió però no respon;
  el servei WCS d'elevacions de l'IGN només té MDT.
- *ICGC (MDS costaner 0,5 m, LiDAR territorial 2021-2023)*: lliurament per enllaç per correu; no
  automatitzable aquí.
Per tant, les altures són **estimades** (plantes × 3 m), no mesurades.

**Preparació** (`python scripts/descarregar_edificis.py`, ~2 min la primera vegada): municipis que toquen
un cercle de 2 km al voltant de cada punt d'observació (amb el Sol entre 0 i 4 graus, un edifici de 30 m
pot tapar-lo fins a ~1,7 km a 1 grau); parts amb almenys una planta; EPSG:25831 → EPSG:25830; una sola
vegada cada part (identificador del Catastro). Resultat: Vallès 49.797 parts (compartides per la UAB,
Cerdanyola i Montmeló), Vic 16.987, l'Escala 15.091, **Picos 0** (cap edifici a menys de 2 km: zona sense
cobertura d'edificis). Plantes de 1 a 17 (Vallès), 13 (Vic, l'Escala).

**Col·locació sobre el relleu** (`dades/edificis.py`). Altura sobre el sòl = plantes × 3,0 m. Cota del sòl
de referència = mediana del MDT de 5 m als vèrtexs i al centre del contorn; cota de la coberta = referència
+ altura (absoluta, m). Les façanes baixen fins a 1 m per sota del punt més baix del terra sota l'edifici
(del MDT o de la malla del terreny, la més baixa): no floten ni deixen escletxes en pendent. Desnivell del
terra sota les parts: mediana 0,4 m, percentil 95 2,3 m (una incertesa més de la coberta). Coberta plana
triangulada amb triangulació restringida (respecta els patis): a totes les parts del Vallès, l'àrea dels
triangles és la del contorn. Malla en ECEF relativa a un origen (doble precisió a la CPU; float32 relatiu a
la càmera a la GPU), profunditat logarítmica. Una zona carregada cada vegada: sense duplicats entre zones.

**Ocultació del Sol.** Els edificis són opacs i escriuen la profunditat: tapen el disc del Sol i el halo
(que es dibuixa després i no escriu profunditat) des de qualsevol càmera. El panell mostra quina part del
Sol tapen des dels ulls amb un càlcul geomètric independent de la imatge: el perfil d'horitzó dels edificis
(per a cada 0,01 graus d'azimut, l'angle més alt de les vores de les cobertes, mostrejades amb un pas
angular més fi que l'interval, amb la curvatura i la convergència de meridians) i el disc del Sol mostrejat
sencer, separant-ne la part que tapa la Lluna. Es distingeix de l'ombra que un edifici projecta al terra
(14.3).
- Dos errors trobats en fer-ho: el mostreig de les vores era cada 0,25 m com a mínim, i una façana a 3 m dels
  ulls quedava plena de forats (patró d'ocultacions intermitents del 2–3 %); i el gir de la convergència
  (azimut geogràfic = de quadrícula + convergència) tenia el signe al revés. Ara el càlcul aproximat
  coincideix amb l'exacte en ECEF a ≤ 0,004° (Vic, l'Escala); al Vallès, 2 de 36.000 intervals difereixen a la
  cantonada d'una façana a 3 m, on l'elevació salta.

**Punts d'observació dins d'edificis (D53).** El geocodificador va donar la posició *de l'edifici* de
l'ajuntament, i la plaça Cívica coincideix amb una part del Catastro de 2 plantes. No s'han mogut. Propostes
(punt exterior més proper a més de 3 m de qualsevol façana): l'Escala 42,12479, 3,13237 (14 m); Cerdanyola
41,49092, 2,14077 (11 m); Montmeló 41,55163, 2,24796 (9 m); UAB 41,50180, 2,10411 (21 m). Atenció: des
d'aquests punts, tan a prop de les façanes, el Sol queda tapat per edificis gairebé tota la tarda; per veure'l,
cal un punt en un espai més obert (p. ex., a la UAB, el punt de prova 41,50220, 2,10416, a 40 m de la plaça:
Sol visible fins a les 20:24:55 i tapat per edificis al màxim). Vic (plaça Major) és fora dels edificis.

**Comprovat automàticament** (`python scripts/validar_edificis.py`, ~1 min):
- *Precisió geogràfica:* 72 edificis d'OpenStreetMap coincidents a 400 m de la UAB: solapament (IoU)
  mediana 0,76, distància entre centres mediana 2,1 m, desplaçament mitjà (+1,15, −0,92) m (dins de la precisió
  d'OSM, de pocs metres).
- *Altures:* 10 parts a l'atzar tenen les plantes del GML original; 5 cobertes dibuixades són a la cota
  calculada (≤ 0,1 mm, llegit del depth buffer). Referència independent: 10 edificis d'OSM amb
  `building:levels`, 8 amb les mateixes plantes i 2 amb 1 de diferència. Les altures en metres **no** s'han
  pogut contrastar amb una mesura (cap LiDAR accessible).
- *Renderitzador:* fracció visible del disc del Sol a la imatge (píxels classificats per profunditat) contra
  el càlcul geomètric, des dels ulls i des de la càmera d'exploració: UAB (punt de prova) visible 84,5/84,6 %,
  parcial 6,8/6,8 % (Lluna 93,2 %, edificis 17,1 %), total 0,0/0,0 %; Vic visible 41,5/41,4 %, parcial
  21,1/21,1 % (edificis 45,8 %), total 0/0 %; l'Escala, Cerdanyola i Montmeló (punts exteriors) totals 0/0 %.
  El halo no canvia cap píxel de les façanes. Mostrar/amagar 4 vegades en pausa: imatges idèntiques, càmera
  i hora iguals.
- *Regressions:* `prova_vistes.py`, `prova_controls.py`, `validar_horitzo.py` i `validar_ombres_relleu.py`
  correctes (les tres últimes comproven el relleu i hi amaguen els edificis); mode pla 0 píxels diferents;
  exercici 1.0 `COINCIDEIX`; cap avís de textures.

**Rendiment** (Vallès, el cas més gran; finestra amagada 640 × 640): 1.020.077 triangles, 37 MB de GPU;
càrrega des de la memòria cau 0,02 s (la primera preparació, ~10 s, la fa l'script); perfil des dels ulls
0,3–1,0 s un cop per punt; temps per fotograma 7,3 ms sense edificis i 8,8 ms amb. Vic: 314.741 triangles,
l'Escala 305.648. No calen nivells de detall amb aquesta mida.

**Inspeccionat visualment:** vista aèria de Cerdanyola i de Vic amb edificis i sense (assentats, sense flotar);
Vic, Sol visible, parcial i total amb edificis i sense; ombres d'edificis a Vic.

**Limitacions:** altures estimades (±20–30 %; cobertes planes, sense ampits ni teulades inclinades);
sense arbres (el MDT és terra nu i no s'ha fet servir cap MDS); el Sol es dibuixa a la posició geomètrica
(sense refracció), de manera que a prop de l'horitzó l'ocultació real per edificis pot començar uns minuts
més tard; només 2 km al voltant dels punts; els edificis no reben ombres; al mapa d'ombres, els de menys de
~12 m no en fan (a la UAB, el 0,2 % del terra d'una vista aèria; a Vic, el 34,6 %).

**Provat per l'equip:** encara no. Proves manuals: (1) a Vic, cap a les 20:15–20:20, mirar el Sol des de la
plaça Major amb zoom i veure com hi entra l'edifici; (2) "Mostrar edificis" en pausa, diverses vegades;
(3) explorar Cerdanyola i Vic des de l'aire; (4) decidir els punts exteriors de l'Escala, Cerdanyola,
Montmeló i la UAB.

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
| 22/10/2026 | 2.1–2.6 `VALIDAT` per l'equip (finestra i controls principals). Documentades la magnitud i la ubicació de les diferències d'imatge. |
| 22/10/2026 | Web reescrita (un desplegable per subobjectiu, text seguit). Tasques 3.1 i 3.2 `FET`: personatge retirat, observador com a dada, bloqueig durant la reproducció. Commits locals, sense push. |
| 22/10/2026 | Treball autònom (D32–D38). F9: P només reproduir/pausar, efemèrides de JPL i geodèsia WGS84, escena en coordenades terrestres amb la Terra, la península i Picos, Sol i Lluna reals, ombra de la Lluna per punt, càmeres noves i panell senzill. Comprovacions a la F9. 3.3–3.7 resoltes. `data/FONTS.md` creat (tasca 4.1, part de documentació). |
| 22/10/2026 | F10 (prova de l'equip): correcció del tall blau (retall amb z logarítmica), de l'avís de textura i de l'altura dels ulls; zones de 5 m de Vic, l'Escala i el Vallès (D39); botons del màxim i de l'ombra des de l'espai; `scripts/prova_vistes.py`. 4.1 `FET`; 4.3 i 4.4 `EN CURS`. Commits locals, sense push. |
| 26/10/2026 | F11: proves de la seqüència sencera (11.1), càmera d'exploració sobre la ubicació triada (11.2), coordenades verificades (0.3), comparació amb la NASA (3.8), horitzó (3.4) i ombres del relleu (6.1, zona de 5 m). D40–D43. 0.3, 3.4, 3.8, 4.4 i 9.6 `FET`; 4.3 continua `EN CURS` (anell de 25 m). Commits locals, sense push. |
| 26/10/2026 | Prova de l'equip de la F11 registrada (només el que es va provar). 11.2 `VALIDAT`. Error de l'interruptor de les ombres trobat per l'equip i corregit (11.7, `FET`, pendent de tornar-lo a provar). |
| 26/10/2026 | Segona prova de l'equip: l'interruptor de les ombres del relleu funciona (11.7 `VALIDAT`). |
| 26/10/2026 | F12 (petició de l'equip): arrencada a C1 − 1 h, cub de navegació (1,647 UA), mirada amb el ratolí capturat, roda i trackpad, correcció del halo (12.0). D44–D47. Commits locals, sense push. |
| 26/10/2026 | La F13 (mirada fixa al món, E/Q segons la mirada, Mirar/Apropar-s'hi, velocitat segons l'astre més proper, parets amagades) **revertida a petició de l'equip**: els controls nous no eren intuïtius i preferia els d'abans, amb les tecles. Es torna a l'estat de la F12 (commits de revert, sense reescriure l'historial). |
| 26/10/2026 | F14 (petició de l'equip): edificis del Catastro INSPIRE a les zones de detall (Vallès, Vic, l'Escala; Picos sense edificis a 2 km), dibuixats i opacs, "Mostrar edificis", part del Sol tapada, ombres dels edificis al mapa, `validar_edificis.py`. D52–D53. Quatre punts d'observació dins d'edificis: propostes pendents de l'equip. Commits locals, sense push. |
