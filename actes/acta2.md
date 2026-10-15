# ACTA DE SEGUIMENT DEL PROJECTE
**EGRA · Simulació d'un eclipsi sobre terreny real**

## INFORMACIÓ DE L'ACTA

| | | | |
|---|---|---|---|
| Estudiant 1 | Alícia Martí | NIU | 1702761 |
| Estudiant 2 | Oriol Mota | NIU | 1706459 |
| Estudiant 3 | Elena Gutiérrez | NIU | 1703828 |
| Número d'acta | 02 · Segona acta | Data | [PENDENT] |

## REVISIÓ DELS OBJECTIUS DE L'ACTA ANTERIOR

### Dataset

Mantenim el MDT de l'IGN/CNIG, però ara el descarreguem amb el **servei WCS de l'IGN** en lloc de fer-ho fulla a fulla. El MDT es distribueix en milers de fulles MTN50, cadascuna en el seu fus UTM (29, 30 o 31). El WCS, en canvi, retorna qualsevol zona en un sol GeoTIFF, a la resolució que demanem (5, 25 o 200 m) i en un únic sistema de referència per a tota la península (**EPSG:25830**, ETRS89 / UTM 30N). Un script nostre fa la descàrrega per rajoles i les uneix.

### Zona d'estudi

A l'acta 1 havíem proposat una zona de la província de Barcelona. Segons les dades oficials de l'eclipsi, Barcelona queda **fora de la totalitat**: hi té un enfosquiment màxim del 99,8 %, amb el Sol a 3,9° d'elevació (20:29 CEST). Per això treballem amb tres escales:

- **Península** (200 m): vista general de la trajectòria de l'eclipsi.
- **Astúries** (25 m): tota la comunitat queda dins la franja de totalitat (72–110 s).
- **Picos de Europa** (5 m, 20 × 20 km): és dins la totalitat (~100 s), no té mar i té un desnivell d'uns 2.200 m (cotes de 83 a 2.647 m). En el màxim, a les **20:28 CEST**, el Sol hi és a **9,6°** d'elevació (azimut 281,4°). Amb el Sol tan baix, el relleu pot tapar l'eclipsi, i aquest és l'efecte que volem estudiar. També conservem la zona de Luarca (5 m) de les primeres proves.

### Dades de l'eclipsi

Fem servir el conjunt de dades oficial del CNIG: efemèrides (GeoTIFF de 10 bandes, ~1,2 km), ombres del relleu en el màxim (GeoTIFF de ~300 m, 4 classes) i corbes de nivell (GeoPackage). Hem confirmat el significat de bandes i classes amb la documentació del CNIG. Hi hem trobat una incidència: a la capa de durada de la totalitat, el polígon «0–10 s» inclou també tota la zona sense totalitat i, per tant, no dona la vora de la franja. Per resoldre-ho, calculem la franja i les corbes de durada a partir de les bandes d'inici i final de la totalitat i de l'hora de posta, que són les dades amb què es va fer la capa.

### Vista exterior

És la part desenvolupada en aquest període. Les dues decisions tècniques principals són:

- **Heightmap com a textura.** La geometria és una graella plana fixa (com a màxim 1024 × 1024 vèrtexs) i el vertex shader llegeix l'altura d'una textura. Així el cost no depèn de la mida del fitxer (de 16 a 34 milions de mostres) i l'exageració vertical és un *uniform* que es canvia sense reconstruir res.
- **Normals amb el gradient a resolució completa.** La graella té un vèrtex cada ~20 m a Picos, però el pendent es calcula a 5 m i es guarda en una altra textura. El fragment shader en fa la normal per a cada píxel, de manera que l'ombrejat conserva el detall de 5 m i és exacte per a qualsevol exageració.

A més, hi ha:
- **Aspecte visual**: rampa de colors absoluta en metres, mar amb costa suau, faldilles a les vores i boira.
- **Interacció**: càmera amb ratolí enganxada al terreny, zoom cap al cursor, near/far adaptatius i *picking* amb el depth buffer (coordenades UTM i geogràfiques).
- **Escales**: selector península / Astúries / Picos / Luarca, amb memòria cau (Astúries passa de 7,5 s a 0,6 s de càrrega).
- **Curvatura de la Terra** opcional (d²/2R, sense exageració): 39 km a les cantonades de la península, 16 m a les de Picos.
- **Dades de l'eclipsi**: capes d'enfosquiment, durada i ombres del CNIG, i un punt d'observació amb les efemèrides (hores en CEST) que permet posar la llum al Sol del màxim.

Taula 1. Rendiment, mesurat fora de pantalla en un Apple M1, a 1200 × 900 i sense capa de l'eclipsi. A la finestra, el programa queda limitat a uns 120 FPS per la pantalla.

| Terreny | Resolució | Triangles | FPS | Càrrega (amb memòria cau) |
|---|---|---|---|---|
| Península | 200 m | 1,71 M | 360 | 0,4 s |
| Astúries | 25 m | 0,91 M | 644 | 0,6 s |
| Picos de Europa | 5 m | 2,10 M | 312 | 0,2 s |
| Luarca | 5 m | 2,10 M | 321 | 0,2 s |

### Vista d'observador, barra temporal i condicions meteorològiques

Encara **no s'han fet**. Ara la posició del Sol es fixa a mà o amb els valors del CNIG al màxim, sense evolució temporal. La boira actual es podrà reaprofitar per a l'opció meteorològica «boira».

### Organització del codi

Mantenim l'estructura dels reptes: una subclasse del `GraphicsEngineBase` (sense modificar-lo), objectes amb VBO, VAO, *shader* i *uniforms* de model, vista i projecció, i la interfície amb Slimgui. Treballem amb un entorn conda comú (`egra`, Python 3.11). La reorganització del codi en mòduls és el primer pendent.

## OBJECTIUS PER A LA SEGÜENT ACTA

1. **Sol i Lluna com a objectes de l'escena**, amb la posició calculada al llarg del temps per a qualsevol punt del terreny. Per validar-la, la compararem amb les efemèrides del CNIG a Picos, Luarca i Barcelona: azimut i elevació del Sol al màxim, i hores de contacte. [REVISAR: decidir el mètode de càlcul i les toleràncies acceptables, p. ex. < 0,1° i < 5 s]
2. **Model d'il·luminació.**
   - Llum direccional del Sol amb una intensitat proporcional a la fracció de disc solar visible en cada instant.
   - Ombres del relleu amb *shadow mapping*. Les validarem amb la capa d'ombres del CNIG a Picos, mesurant el percentatge de coincidència de classes.
3. **Barra temporal amb Slimgui**: play/pausa, avançar, retrocedir i hora en format hh:mm (CEST), almenys entre l'inici i el final de la parcialitat (19:31–21:21 a Picos).
4. **Terreny.**
   - Reorganitzar el codi en mòduls: càmera, terreny, lectura de dades, dades de l'eclipsi i *shaders* en fitxers separats.
   - Estudiar el nivell de detall (LOD) per rajoles.
   - Estudiar un retall de terreny a resolució completa al voltant de l'observador.
5. **Prototip de la vista d'observador.** Càmera a l'altura d'una persona (~1,7 m) sobre el punt d'observació, orientada cap a l'azimut del Sol, per comprovar si el relleu el tapa. Ho compararem amb la classe d'ombres del CNIG en aquell punt.
6. **Repartiment de tasques**: [PENDENT].

## NOVES CONSIDERACIONS

**Escala del Sol i la Lluna.** Tots dos tenen un diàmetre aparent d'uns 0,5° (per això la Lluna pot tapar el Sol), però a escala real no es poden posar a la seva distància dins l'escena. Cal distingir:
- **Vista exterior**: representació simbòlica, a una mida que es vegi i en la direcció correcta.
- **Vista d'observador**: mida angular real. Amb el camp de visió actual (50°), el disc solar ocuparia unes 9–10 línies d'una finestra de 900 píxels; es poden dibuixar a una distància fixa, escalats al diàmetre angular correcte.

**Limitacions conegudes.**
- El WCS només té dades d'Espanya: Portugal i França valen 0 i es mostren com a mar. Es podrien completar amb el Copernicus DEM.
- Les ombres del CNIG tenen píxels de ~300 m; sobre el terreny de 5 m són només una referència.
- La geometria és una mitjana (un vèrtex cada ~20 m a Picos): la vista d'observador necessitarà resolució completa a prop de l'observador.
- El MDT de 25 m del WCS ve en metres enters.

## ANNEXOS

**Fonts de dades**

- **MDT**: servei WCS de models digitals del terreny de l'IGN, `https://servicios.idee.es/wcs-inspire/mdt` (cobertures `Elevacion25830_5`, `_25` i `_200`). Proves inicials amb la fulla 0011 del MDT05 – 1a cobertura (Centre de Descàrregues del CNIG). Llicència CC BY 4.0: «MDT © Instituto Geográfico Nacional».
- **Eclipsi del 12/08/2026**: paquet de dades del CNIG (efemèrides, ombres del relleu i corbes de nivell) [REVISAR: nom exacte del producte i enllaç de descàrrega]. Visor: `https://visualizadores.ign.es/eclipses`; mètode de càlcul: `https://eclipses.ign.es/condiciones-de-observacion.html`. Atribució obligatòria (CC BY 4.0): *"Official astronomical information provided by the National Geographic Institute based on calculations made by the National Astronomical Observatory"* (traducció nostra: «Informació astronòmica oficial proporcionada per l'Institut Geogràfic Nacional a partir de càlculs de l'Observatori Astronòmic Nacional»).

**Llibreries** (entorn conda `egra`, Python 3.11)

- ModernGL (OpenGL 3.3) i glfw: estructura dels reptes de classe.
- Slimgui: panell d'opcions.
- NumPy i PyGLM: càlcul numèric i matrius.
- rasterio: lectura i reprojecció de GeoTIFF.
- pyproj: conversió de coordenades.
- SciPy: màscara de mar, distància a la costa i suavitzats.
- fiona i geopandas: lectura del GeoPackage.
- requests: descàrrega del WCS.
- tifffile i Pillow: escriptura de GeoTIFF i captures.

**Figures proposades** (a `captures/`)

- **Figura 1** (`picos.png`). Picos de Europa (MDT a 5 m) il·luminat amb la posició del Sol en el màxim de l'eclipsi (azimut 281,4°, elevació 9,6°), segons les efemèrides del CNIG.
- **Figura 2** (`peninsula_enfosquiment.png`). Enfosquiment màxim sobre la península (rampa del 90 al 100 %). En magenta, la franja de totalitat, amb els límits en blanc.
- **Figura 3** (`asturies_durada.png`). Durada de la totalitat a Astúries (72–110 s), amb corbes cada 10 s.
- **Figura 4** (`picos_ombres_cnig.png`). Classes de visibilitat del Sol en el màxim segons el CNIG (píxels de ~300 m) sobre el relleu de Picos, amb la llum de l'escena situada al Sol del màxim.
- Alternativa a alguna de les anteriors: `peninsula_sense_curvatura.png` i `peninsula_amb_curvatura.png`, vista de perfil de la península sense i amb curvatura de la Terra.

**Ús d'eines d'IA**

Proposta de frase: «Per al desenvolupament del codi d'aquest període (descàrrega i preparació de dades, *shaders* i interfície) hem utilitzat l'assistent de programació Claude Code (Anthropic). Nosaltres hem definit els objectius, hem revisat i provat cada pas, i hem pres les decisions sobre les dades i la zona d'estudi.» [REVISAR: ajustar-la a com hàgiu treballat realment]
