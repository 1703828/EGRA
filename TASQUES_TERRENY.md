# TASQUES DEL TERRENY — Projecte EGRA (eclipsi sobre terreny real)

Aquest fitxer descriu la feina pendent sobre el **terreny**. Fes les tasques **una a una i en ordre**.
Després de cada tasca: el programa s'ha d'executar, cal explicar què s'ha canviat i cal esperar
que l'usuari ho provi abans de passar a la següent.

## Regles generals

- Mantenir l'organització de codi dels reptes de classe: `GraphicsEngineBase` (a `basecode/`) amb
  `on_init`, `render`, `drawables` i `build_ui`; objectes amb VBO + VAO + shader i uniforms
  `m_proj`, `m_view` i `m_model`. **No modificar `basecode/`**: tot el que sigui nou va fora.
- Entorn: conda **`egra`** (Python 3.11), no l'anaconda base. Executar amb `conda activate egra`
  i `python ...` (o `~/anaconda3/envs/egra/bin/python ...`).
- Llibreries (ja instal·lades a `egra`): ModernGL (GL 3.3 core), slimgui, numpy, PyGLM, rasterio,
  pyproj, scipy, fiona, tifffile, Pillow. Si cal alguna cosa més, preguntar abans d'instal·lar-la
  (`conda install -n egra -c conda-forge --solver=libmamba ...`) i afegir-la a `requirements.txt`.
- Comentaris i textos de la interfície en català (sense accents a la UI si la font no els mostra).
- Unitats: el món 3D en **km**, X = est, Y = altitud, Z = sud (com ara). Les altituds als
  fitxers estan en metres.
- Res de peticions de xarxa dins del bucle de render. Les dades es preprocessen offline.
- Els fitxers generats van a `data/cache/` (afegir-la al `.gitignore`).

## Dades

```
data/
  mdt05/          fulla MDT05 que fem servir: PNOA_MDT05_ETRS89_HU30_0011_LID.tif (Luarca, EPSG:25830)
  mdt05/altres/   fulles que no fem servir (0011 en HU29 i 0296 en HU31)
  eclipsi2026/    dataset del CNIG de l'eclipsi del 12/08/2026 (ja descarregat per l'usuari)
  cache/          generat pels scripts (no versionar): MDT descarregats per WCS
```

Abans de tocar res, inspecciona els fitxers que hi hagi (CRS, mida, nodata, rang d'altituds) i
fes-ne un resum a l'usuari.

## T0 — Script de descàrrega del MDT pel servei WCS de l'IGN

El Centro de Descargas distribueix el MDT en milers de fulles petites. Per evitar-ho, farem servir el
**servei WCS 2.0.1 de l'IGN**, que retorna un sol GeoTIFF de la zona i la resolució que li demanem:

- GetCapabilities: `https://servicios.idee.es/wcs-inspire/mdt?version=2.0.1&request=GetCapabilities&service=WCS`
- Resolucions: 1000, 500, 200, 25 i 5 m. CRS: ETRS89-UTM30 (EPSG:25830), és a dir, tota la
  península en un sol fus, de manera que no cal reprojectar.
- Els identificadors de cobertura tenen la forma `Elevacion25830_<resolucio>`
  (p. ex. `Elevacion25830_200`). **Confirma-ho amb GetCapabilities i DescribeCoverage**, i també
  els noms dels eixos per al `SUBSET` i els formats de sortida acceptats (GeoTIFF).

Crea `scripts/descarregar_mdt.py`:
- Arguments: resolució (5, 25, 200…), bbox en lat/lon (es converteix a EPSG:25830 amb pyproj) i nom
  del fitxer de sortida a `data/cache/`.
- El servidor segurament limita la mida de cada petició: dividir la zona en rajoles (p. ex. de 2000×2000
  píxels com a màxim), descarregar-les amb `requests` (amb reintents) i unir-les amb rasterio en un sol
  GeoTIFF comprimit. Si una rajola ja existeix, no tornar-la a baixar.
- Mostrar el progrés al terminal.
- Configuracions predefinides:
  - `peninsula`: 200 m, lat 35.9–43.9, lon -9.5–3.4 → `data/cache/peninsula_200m.tif`
  - `asturias`: 25 m, la comunitat d'Astúries → `data/cache/asturias_25m.tif`
  - `detall`: 5 m, uns 20×20 km centrats en un punt donat → `data/cache/detall_5m.tif`
- Les descàrregues les executa l'usuari al seu ordinador (és qui té xarxa). Prova primer una
  petició petita i ensenya a l'usuari la comanda exacta.
- Reconeixement obligatori (llicència compatible CC BY 4.0): "MDT © Instituto Geográfico
  Nacional". Afegir-lo al README.

---

## Estat actual (`terreny.py`) i problemes detectats

1. `tifffile` llegeix només els píxels: **es perd la georeferència** (origen UTM, mida de píxel,
   CRS). Sense això no podem fer mosaics, ni convertir a lat/lon per al Sol, ni casar les dades
   de l'eclipsi.
2. El submostreig `[::step, ::step]` agafa 1 de cada 8 mostres i provoca *aliasing*. Cal fer la
   mitjana per blocs.
3. Les normals es calculen a partir de la malla submostrejada, i això fa perdre el detall del 5 m.
4. Totes les dades de la malla es calculen a la CPU i van al VBO, de manera que no escala a zones grans.
5. El mar es detecta amb `altitud <= 0`. Els valors `-32767` (sense dades) i els zeros es tracten
   igual, i dins de terra hi ha forats que surten pintats de blau (es veuen al riu de la captura).
6. Els colors hipsomètrics són relatius a `max_height` de la fulla, així que dues zones diferents no tindrien
   els mateixos colors per a la mateixa altitud.
7. La relació d'aspecte és fixa (no hi ha resize), no hi ha comptador de FPS i la càmera només es
   pot moure amb sliders.
8. Les vores del terreny queden "a l'aire" (no hi ha faldilles) i el mar és un pla pla sense res.

---

## T1 — Lectura georeferenciada i neteja de dades

- Crear `data_io.py` amb una funció que llegeixi un GeoTIFF amb `rasterio` i retorni:
  l'array d'altituds (float32, metres), la `transform`, el CRS i una **màscara de mar/sense dades**.
- Distingir:
  - **Mar**: zones sense dades o amb altitud 0 **connectades a la vora** del fitxer (fer servir
    `scipy.ndimage.label` o un flood-fill des de les vores). Si `scipy` no hi és, afegir-lo.
  - **Forats interiors** (sense dades rodejades de terra): omplir-los interpolant els veïns
    (p. ex. repetint mitjanes de veïns vàlids fins que no quedin forats). No han de sortir blaus.
- Funció de **submostreig per mitjana de blocs** (`factor` enter), que ignori les cel·les de mar en
  fer la mitjana i que submostregi també la màscara.
- `terreny.py` passa a fer servir `data_io.py`. Al terminal ha de mostrar el CRS, l'origen UTM, la mida
  i el rang d'altituds.

**Acceptació:** es veu igual que ara però sense taques blaves dins de terra, i el terminal mostra
la georeferència correcta (EPSG:25830 per a la fulla 0011 en HU30 de `data/mdt05/`).

## T2 — Heightmap com a textura i desplaçament al vertex shader

- Pujar les altituds a una textura `R32F` (filtre LINEAR, clamp to edge) i la màscara de mar a una
  textura `R8`.
- Fer servir una **graella plana fixa** (p. ex. 1024×1024 vèrtexs com a màxim, independent de la
  mida del fitxer) amb només coordenades UV. El vertex shader llegeix l'altura amb `texture()` i
  calcula la posició.
- **Exageració vertical** com a uniform aplicat al shader. En canviar-la, no s'ha de reconstruir res.
- **Detall a resolució completa**: calcular el gradient (dh/dx, dh/dz) a la resolució original del
  fitxer (5 m) i guardar-lo en una textura `RG32F` (o `RG16F`). El fragment shader construeix la normal
  com `normalize(vec3(-k*dhdx, 1, -k*dhdz))`, on k és l'exageració. Així la normal és exacta per a
  qualsevol k i l'ombrejat té el detall de 5 m encara que la geometria sigui grollera.
  Si la textura a resolució completa no hi cap (`ctx.info['GL_MAX_TEXTURE_SIZE']`), fer-la a
  2× o 4× de submostreig i avisar.
- Mantenir l'opció de filferros.

**Acceptació:** el moviment de l'slider d'exageració és instantani, el relleu es veu clarament més detallat
que ara i els FPS (veure T3) són iguals o millors.

## T3 — Qualitat visual i usabilitat bàsica

- **Rampa de colors absoluta** en metres (p. ex. 0, 200, 600, 1200, 2000, 3000+ m), i no relativa al
  màxim de la fulla.
- **Mar**: color d'aigua amb una mica de variació (més fosc lluny de la costa, usant la distància
  a la costa precalculada o simplement l'atenuació per distància de càmera).
- **Faldilles**: parets verticals a les 4 vores del terreny fins a una cota base, perquè no
  sembli un llençol.
- **Boira atmosfèrica** segons la distància a la càmera (color del cel, densitat com a uniform i
  slider). Més endavant es reaprofitarà per a l'opció meteorològica "boira".
- **Resize de finestra**: actualitzar l'aspect ratio i el viewport (callback de glfw al
  `GraphicsEngine` del projecte, sense tocar `basecode/`).
- **FPS** i nombre de triangles al panell.

## T4 — Càmera amb ratolí (`camera.py`)

- Moure la classe `Camera` a `camera.py`.
- Càmera orbital al voltant d'un **punt objectiu** (no sempre l'origen):
  - arrossegar amb el botó esquerre: gir i inclinació
  - arrossegar amb el botó dret (o Maj + esquerre): desplaçar l'objectiu sobre el terreny
  - roda: distància (zoom exponencial)
- Que no reaccioni al ratolí quan el cursor és sobre el panell slimgui
  (`imgui.get_io().want_capture_mouse`).
- Mantenir els sliders com a alternativa.
- Ajustar `near`/`far` a la distància (near ≈ distància/1000) per evitar z-fighting quan ens
  apropem molt (ho necessitarà la vista d'observador).

## T5 — Mosaic i dues escales: península (200 m) + zona de detall (5 m)

- Fer servir els fitxers de T0 (`peninsula_200m.tif`, `asturias_25m.tif`, `detall_5m.tif`), que ja
  estan tots en EPSG:25830, igual que la fulla 0011 en HU30 de `data/mdt05/` (no cal reprojectar res).
- Si alguna textura supera `GL_MAX_TEXTURE_SIZE`, submostrejar-la per mitjana de blocs (T1).
- Al programa, un selector al panell (botons de ràdio) entre les vistes **Península** (200 m),
  **Astúries** (25 m) i **Zona de detall** (5 m).
  - A la vista Península, opcionalment dibuixar un rectangle on hi ha la zona de detall.
- Totes dues fan servir la mateixa classe de terreny de T2 (només canvien les textures i la mida en km).
- **Curvatura de la Terra** al vertex shader, com a opció activable:
  `y -= d² / (2·R)`, amb d = distància horitzontal al punt objectiu de la càmera i R = 6371 km.
  A la vista Península s'ha de poder veure l'efecte.

**Acceptació:** es veu tota la península sencera fluida (>30 FPS) i la zona de detall al màxim de detall.

## T6 — Primeres dades de l'eclipsi sobre el terreny (només visualització)

Dataset del CNIG del 12/08/2026, a `data/eclipsi2026/` (3 fitxers):
- **Efemèrides** (GeoTIFF, multibanda, ~800 m): azimut i elevació del Sol al màxim, enfosquiment
  màxim i hores (TU) de sortida i posta del Sol, de la parcialitat i de la totalitat. Identificar
  quina banda és cada una (descripcions de les bandes o metadades).
- **Corbes de nivell** (GeoPackage): contorns d'enfosquiment, de durada de la totalitat i d'avanç de
  la taca. Llegir-lo amb `fiona`, `geopandas` o `sqlite3`, i llistar-ne les capes.
- **Ombres del terreny** (GeoTIFF): condicions de visibilitat del màxim considerant el relleu.

- Inspeccionar els fitxers i documentar al terminal quines bandes/capes hi ha i en quin CRS estan.
- Reprojectar l'enfosquiment màxim al CRS del terreny i pujar-lo com a textura **superposada**
  (overlay activable al panell, amb opacitat): així es veu la franja de totalitat sobre el relleu.
- Afegir un **punt d'observació** escollible (clic sobre el terreny o coordenades) que mostri al
  panell el valor de les efemèrides en aquell punt (azimut i elevació del Sol al màxim, hora del màxim
  en hora local, durada de la totalitat).
- Botó "Sol al màxim de l'eclipsi": posar els sliders d'azimut i elevació del Sol amb els valors
  del dataset en aquell punt.
- El GeoTIFF d'**ombres del terreny** es guarda com a **referència per validar** més endavant el
  nostre càlcul d'ombres i visibilitat. Ara només cal carregar-lo i poder mostrar-lo com a overlay.
- Les corbes del GeoPackage es poden dibuixar com a línies sobre el terreny (opcional).

(El càlcul propi de la posició del Sol i la Lluna al llarg del temps i les ombres NO formen part
d'aquest fitxer de tasques.)

## T7 — Organització final del codi

```
main.py          GraphicsEngine (subclasse de GraphicsEngineBase), build_ui
camera.py        Camera
terrain.py       Terrain (textures, graella, shaders)
data_io.py       lectura GeoTIFF, màscares, submostreig
eclipse_data.py  lectura del dataset del CNIG
shaders/         terrain.vert, terrain.frag (fitxers separats)
scripts/preparar_dades.py
```

Al final, `terreny.py` es pot eliminar o deixar com a exemple mínim.

**Fet:** `terreny.py` s'ha eliminat i el programa és `python main.py`. Seguint l'estructura del repte 4,
els shaders es carreguen de fitxers amb `basecode.shaders.load_program` (el `basecode/` s'ha
actualitzat a la versió del repte 4). La llista de terrenys és a `data_io.TERRENYS`. Comprovat: la
versió reorganitzada dibuixa exactament el mateix que l'anterior (comparació píxel a píxel).

## T8 (opcional, només si sobra temps) — LOD per rajoles

Piràmide de rajoles (p. ex. 256×256 mostres) a diversos nivells generades per l'script.
Quadtree que carrega les rajoles de 5 m només a prop de la càmera i les de 200 m a la resta, amb
faldilles per amagar les escletxes entre nivells. Només s'ha de fer si T1–T7 funcionen bé.

---

## Limitacions conegudes i millores futures

- **Portugal i França valen 0 al WCS de l'IGN.** El servei només té dades d'Espanya i fora de la
  frontera retorna 0 m, de manera que la T1 marca Portugal, França (i el nord d'Àfrica) com a mar.
  Per ara ho acceptem. Millora futura: omplir aquestes zones amb un MDT global, p. ex. el
  **Copernicus DEM GLO-30/GLO-90** (reprojectat a EPSG:25830 i fusionat on el MDT de l'IGN val 0
  fora de la costa espanyola).
- **El MDT de 25 m del WCS ve en metres enters** (sense decimals, a diferència del de 5 m i el de
  200 m). En calcular normals a 25 m pot aparèixer un lleuger efecte d'esglaons en zones planes.
- **Les dades de 5 m del WCS no coincideixen exactament amb la fulla MDT05** (diferència mediana
  ~0,8 m i un possible desplaçament de mig píxel). Per a la visualització és irrellevant.
- **Vista d'observador i resolució de la geometria:** a la vista d'observador caldrà un retall de
  terreny a resolució completa al voltant de l'observador, perquè la geometria actual és la mitjana
  (un vèrtex cada ~20 m a Picos). L'ombrejat sí que té el detall de 5 m (normals per fragment).
- **Corbes del GeoPackage (T6):** el polígon 0–10 s de la capa `durtot` inclou tota la zona sense
  totalitat, així que no s'ha fet servir per a la vora de la franja. La franja (amb la posta) i les
  corbes de durada cada 10 s es dibuixen a partir de les bandes 9, 10 i 5 del GeoTIFF. Les capes
  d'enfosquiment i d'avanç de la taca no es dibuixen.
- **Ombres del CNIG:** píxels de ~300 m (calculats amb un MDT de ~200 m). Sobre el terreny de 5 m es
  veuen com a blocs; serveixen de referència per validar el nostre càlcul, no com a resultat final.
