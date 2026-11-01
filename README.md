# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez).

Visualitzem en 3D l'**eclipsi total de Sol del 12 d'agost de 2026** sobre el relleu real d'Espanya.
L'escena és un model geomètric coherent: la Terra (el·lipsoide WGS84 amb textura de la NASA), el
relleu de la península (MDT de 200 m de l'IGN), una zona de detall de 5 m al voltant del punt
d'observació (zones fetes a mà a Vic, el Vallès, l'Escala i Picos, o un lloc de 6 × 6 km que es baixa sol a
qualsevol altre punt) i el Sol i la Lluna a les seves posicions i mides reals (efemèrides de JPL Horizons). L'ombra de la Lluna es
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

S'obre una finestra amb la vista des del terra (la UAB, plaça Cívica, on es fa la presentació), el
panell i la barra de temps. La primera vegada es calculen uns fitxers auxiliars del terreny (uns
segons); a partir de llavors es carrega en un o dos segons. Es poden calcular d'entrada amb:

```bash
python scripts/preparar_dades.py
```

---

## 2. Què es pot fer al programa

### Controls

Hi ha tres vistes. **Observar des del terra** posa la càmera als ulls d'una persona al punt
d'observació, 1,7 m sobre el terra: els ulls no es mouen i la mirada es queda on la deixes (el Sol no
se segueix sol). **Explorar** és una càmera lliure que es pot moure del terreny fins a l'espai; la
velocitat s'adapta a l'altura; dins d'Explorar, el panell deixa triar **Vol lliure** o **Caminar** (veure a
sota). **Allunyar-se fins a l'espai (guiat)** surt del punt d'observació per
una trajectòria fixa fins a veure la Terra, el sistema Terra–Lluna i el Sol, sense perdre's (veure a sota).

| Acció | Explorar | Observar des del terra | Allunyar-se (guiat) |
|---|---|---|---|
| Girar la mirada | ratolí capturat (veure a sota) o fletxes; caminant, també arrossegar | ratolí capturat, arrossegar o fletxes (els ulls no es mouen) | ratolí capturat, arrossegar o fletxes |
| Ratolí a la vista aèria (vol lliure, com Google Earth) | arrossegar: moure el terra (amb inèrcia); `Shift` + arrossegar o botó del mig: girar al voltant del centre i inclinar; arrossegar el cel: mirar | — | — |
| Moure's | Vol lliure: `W` `A` `S` `D` (endavant, enrere, costats), `E` / `Q` (pujar, baixar), `Ctrl`: més ràpid. Caminar: `W` `A` `S` `D` a 1,5 m/s, `Shift`: córrer | — | `W` / `S`: apropar-se / allunyar-se per la trajectòria |
| Roda o dos dits amunt/avall al trackpad | Vol lliure: apropar-se o allunyar-se del punt sota el cursor, amb una animació suau (cada pas, la distància ×0,74 o ×1,35; sobre el cel o amb el ratolí capturat, en la direcció de la mirada). Caminar: res | zoom òptic (com uns prismàtics: només canvia el camp de visió) | apropar-se / allunyar-se per la trajectòria (40 passos en total) |
| Triar el punt d'observació | doble clic al terreny: s'hi va i es passa a observar des del terra, mirant cap on mirava la càmera (`V` torna a l'aire on era); o la llista del panell | la llista del panell | la llista del panell |
| Capturar / alliberar el ratolí | `Tab` o clic dret a l'escena / `Tab` o `Esc` | ídem | ídem |
| Canviar de vista | `V` (explorar ↔ observar), `G` (guiat) | `V`, `G` | `V` torna a observar, `G` també |
| Mirar el Sol (una sola vegada) | botó *Mirar l'eclipsi* | ídem | ídem |
| Reproduir / pausar el temps | `P` | `P` | `P` |

**Mirar amb el ratolí (com en un joc en primera persona).** `Tab` (o un clic dret a l'escena, fora del
panell) captura el ratolí a l'instant: el cursor s'amaga i moure el ratolí gira la mirada sense haver de
prémer cap botó ni topar amb la vora de la pantalla. `Tab` o `Esc` l'alliberen per tornar a fer servir el
panell; amb el ratolí lliure, `Esc` tanca el programa, com abans. Canviar a una altra finestra també
l'allibera. El clic esquerre no captura: arrossegar (girar la mirada o, a la vista aèria, moure el terra) i el
doble clic funcionen sense esperes. La sensibilitat és una sola constant (`SENSIBILITAT` a
`basecode/control_ratoli.py`, 0,15° per punt de pantalla), igual capturat i arrossegant, proporcional al
camp de visió (amb zoom gira menys) i independent dels FPS. La mirada vertical es limita a ±89° i no hi
ha inèrcia. En capturar apareix uns segons un avís a dalt de la pantalla.

**Caminar (dins d'Explorar).** Es tria al panell ("Vol lliure" / "Caminar"). `W` `A` `S` `D` mouen en
horitzontal respecte de cap on mira la càmera (A/D de costat, sense girar), a 1,5 m/s (`Shift`: ×3); mirar amunt
o avall no fa volar, i en diagonal no es va més de pressa. Els ulls es mantenen a 1,7 m sobre el relleu
**dibuixat**, en pujada i en baixada; el moviment es fa en passos de 0,5 m com a molt, de manera que un fotograma
lent no es salta una carena. Al mar o on no hi ha relleu, la càmera s'atura a la vora. `E` / `Q` i la roda no hi
fan res. Per passar a caminar cal ser a menys de 5 km sobre el relleu (es baixa en vertical, sense moure's en
horitzontal); des de més amunt o sobre el mar, el panell ho diu i ofereix *Caminar des del punt d'observació*.
Sense salt ni gravetat; els edificis que es mostren són obstacles (veure *Edificis*). Constants: `VELOCITAT_CAMINAR_M_S` i
`FACTOR_CORRER` a `basecode/camera_exploracio.py`; comprovació: `python scripts/prova_caminar.py`.

**Allunyar-se fins a l'espai (guiat).** La posició de la càmera depèn només d'un *progrés* (de 0 a 1) que
canvien la roda i `W` / `S`; la mirada (ratolí, fletxes) és independent i la roda no la toca. Tram a tram:
a 300 m del punt, d'esquena al Sol, sobre una recta que surt del punt amb 70° d'elevació (sortida segura:
no es retrocedeix en la direcció de la mirada, que mirant el cel faria entrar sota terra); 100 km; la Terra
a 30.000 km d'altura, entre la vertical del punt i el Sol (cara de dia); el sistema Terra–Lluna de costat;
i, a 1,2 milions de km, una vista on caben la Terra, la Lluna i el Sol. Els mateixos passos enrere tornen
exactament al mateix lloc. En entrar-hi es mira el punt; després la mirada és de l'usuari, i el botó
*Recentrar* la torna a la de referència. La trajectòria es calcula amb el Sol i la Lluna de l'hora
d'entrada: si l'hora canvia, la càmera no es mou (el panell ho avisa) i *Recentrar* l'actualitza; canviar
d'ubicació des del panell la recalcula per al punt nou amb el mateix progrés. **Limitació (escala real):**
lluny, la Terra i la Lluna es veuen petites (a la vista Terra–Lluna, ~1° i ~0,3°), i amb el Sol al camp la
Terra és un creixent i la Lluna mostra la cara fosca: no hi ha cap lloc des d'on es vegin alhora el Sol i
la cara de dia de la Terra. La vista de l'espai és de context; no reprodueix l'eclipsi que es veu des del
terra. Geometria: `dades/trajectoria.py`; comprovació: `python scripts/prova_trajectoria.py`.

**Trackpad del Mac:** lliscar amb dos dits amunt o avall fa el mateix que la roda. El gest de pessigar no
funciona: GLFW, la llibreria de finestres, no el rep a macOS (veure el pla, tasca 12.4).

**Espai de navegació.** La càmera d'exploració no pot sortir d'un cub fix que conté la Terra, la Lluna i
el Sol durant tot l'interval de la barra de temps. A prop d'una cara se'n veu la paret (translúcida, amb
ratlles blaves); a la paret només s'atura el moviment cap a fora. Dimensions (sistema ECEF, km):

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
al punt inicial, la UAB (plaça Cívica, `dades/observador.UBICACIO_INICIAL`): a les 18:34:55 (hora d'estiu; C1
19:34:55, màxim 20:29:09, posta 20:55:22). Picos, el cas de totalitat, és a la llista. Canviar d'ubicació no canvia
l'hora.

**P** no canvia res de la càmera: congela el temps on és i el torna a posar en marxa des del mateix
instant. Per exemple: s'observa l'eclipsi des del terra, es prem P, es passa a explorar i s'allunya
fins a veure la Terra, i es prem P: l'eclipsi continua amb la càmera a l'espai.

Mentre es reprodueix, el punt d'observació queda bloquejat (el panell, el cel i el model són sempre
del mateix lloc). Quan es tria una ubicació de la llista, la càmera d'exploració es posa a sobre del lloc
nou, perquè en passar a explorar (V) es parteixi d'allà.

Ubicacions de la llista (coordenades verificades el 26/10/2026, font a `PLA_DE_TREBALL.md` §10.3): plaça Major de
Vic, ajuntament de Montmeló, ajuntament de Cerdanyola i plaça Cívica de la UAB (on arrenca). Picos de Europa (el cas
de totalitat) i l'Escala ja no hi són (equip, 01/11/2026), però les seves dades es conserven i els scripts de prova hi
continuen passant (`dades/observador.UBICACIONS_PROVES`); qualsevol altre punt es pot triar amb doble clic.

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

Al voltant del **punt de detall** el relleu té més detall que lluny: la península sencera (un vèrtex cada
~1 km), la península a 200 m en ~100 km al voltant del punt, la zona de 5 m que conté el punt (un vèrtex cada
10–20 m) i, en ~2,5 km al voltant del punt, un vèrtex per cada píxel de 5 m. A la vora de cada nivell, l'altura
passa suaument a la del nivell de sota. Els ulls de l'observador queden a 1,7 m dels triangles que es dibuixen
(l'altura de cada vèrtex la calcula la CPU).

El punt de detall és **el que es mira**: explorant, el punt del terra al centre de la pantalla (o el de sota la
càmera, a prop del terra o caminant); a les altres vistes, el punt d'observació. No cal cap doble clic.

### Detall segons la vista (qualsevol lloc d'Espanya)

Quan la càmera baixa a menys de 15 km d'un lloc d'Espanya, el programa hi prepara **en segon pla** el detall que
falta (`basecode/detall.py`), sense aturar la navegació:
1. **Relleu de 5 m** (IGN, 6 × 6 km): si no hi ha cap zona de detall, el del lloc de la quadrícula de 3 km.
   Uns 10–20 s la primera vegada. Les zones fetes a mà (Picos, Vic, l'Escala, el Vallès) es continuen fent servir.
2. **Edificis** (Catastro, la cel·la de 3 × 3 km), si es veuen a la vista actual: primer amb altures
   **estimades** (plantes × 3 m) i, quan arriben les dades, amb altures **mesurades** amb LiDAR (secció
   *Edificis*).
3. **Mapa de visibilitat de detall**, si el mapa es mostra (secció *Mapa de visibilitat*).
La fotografia aèria ja arribava a tot arreu i no canvia (secció *Fotografia aèria*).

Les dades es desen al disc i es reutilitzen (tornar a un lloc és immediat). Llegir-les i preparar-les es fa en
fils; el fil principal només crea els objectes OpenGL (un lloc: ~60 ms; Vic, ~0,2 s; el Vallès, ~0,5 s). Es
mantenen carregades fins a 3 zones (la del punt d'observació sempre). Una preparació que acaba quan la càmera ja és
en un altre lloc queda al disc però no canvia el que es veu. El punt d'observació no es mou en navegar.

El panell, a **Detall del lloc**, diu per separat què hi ha al punt: *Terreny* (5 m o 200 m, i què es prepara),
*Foto* (font, nivell i metres per píxel), *Edificis* (estimades, mesurades —amb la font— o no disponibles) i
*Mapa* (relleu i detall). Comprovació: `python scripts/prova_detall.py` (Vic, la UAB i València, on s'arriba
navegant).

### Edificis

A les zones de detall amb dades (el Vallès —UAB, Cerdanyola i Montmeló—, Vic i l'Escala; a Picos no n'hi ha
cap a menys de 2 km), els edificis del Catastro es dibuixen com a volums amb coberta plana i façanes,
assentats sobre el relleu. Són opacs i escriuen la profunditat com la resta de l'escena, de manera que tapen
el Sol (i el halo). Per defecte es dibuixen **en primera persona** (observar des del terra i caminar), per veure
l'horitzó que deixen, i no a la vista aèria, on taparien la fotografia. Les opcions del panell **Edificis des
del terra** i **Edificis també a la vista aèria** ho canvien sense moure la càmera ni l'hora, i el panell diu quina part del Sol tapen des dels ulls
(càlcul geomètric amb el disc sencer, separat de la part que tapa la Lluna). Les **altures són estimades**:
plantes del Catastro × 3 m (incertesa ~±20–30 %), o mesurades amb LiDAR (veure a sota). Els edificis fan ombra
al terra i als altres edificis (veure *Ombres del relleu i dels edificis*).

**Edificis com a obstacles.** Els punts d'observació no poden quedar dins d'un edifici: si el lloc triat (de la
llista o amb un doble clic, també sobre un terrat) cau dins d'un contorn del Catastro, els ulls es posen al punt
exterior més proper a 3 m o més de les façanes, dins de l'espai obert que continua cap als carrers (no en un
pati tancat ni al terrat). El panell ho indica ("Lloc dins d'un edifici: ulls a N m"). Passa a l'ajuntament de
l'Escala (13,7 m), de Cerdanyola (10,6 m), de Montmeló (8,9 m) i a la plaça Cívica de la UAB (20,7 m); la plaça
Major de Vic és a l'exterior. Caminant, el cos (un cercle de 0,3 m) no pot travessar les façanes i hi llisca; en
vol lliure la càmera no hi entra per sota de la coberta però hi pot passar per sobre. Si mai queda dins d'un
edifici, surt al punt exterior més proper. Amb *Mostrar edificis* desactivat no fan d'obstacle (com es veu).
Geometria: `dades/obstacles.py`; comprovació: `python scripts/prova_obstacles.py`.

**Llum de les façanes.** Una paret vertical veu mig cel i mig terra, i el terra en reflecteix part de la llum:
les façanes a l'ombra no queden negres (la meitat de la il·luminada, aproximadament). Aproximació il·lustrativa.

**Edificis a qualsevol lloc.** On es miren (o on es tria un punt) i no n'hi ha de preparats, el programa baixa
en segon pla els del Catastro de la cel·la de 3 × 3 km (secció *Detall segons la vista*). Només a Espanya: Navarra
i el País Basc tenen cadastres propis i no hi són (el panell ho diu). Cada lloc ocupa entre 20 i 110 MB; se'n
guarden com a molt 6 (`MAX_LLOCS` a `dades/llocs.py`) i els que fa més temps que no es fan servir s'esborren sols.
Comprovació: `python scripts/prova_llocs.py`.

**Altures mesurades.** Quan els edificis es veuen, les seves altures es mesuren amb un model d'alçàries LiDAR
(altura sobre el terra, `dades/alcaries.py`), per cel·les de 3 × 3 km al voltant del punt que es mira: a Catalunya
el de l'ICGC (1 m, vols 2021–2023, llegit per finestres del fitxer de tot Catalunya) i a la resta d'Espanya el MDS
normalitzat de l'IGN (2,5 m, vols 2008–2015). L'altura d'una part és el percentil 90 de l'alçària dins del seu
contorn; les parts que no s'hi poden mesurar (pati, edifici fet després del vol) conserven l'estimació. Els
edificis canvien sols quan arriben les mesures (~40–60 s per cel·la). El panell diu quantes parts són mesurades i
quantes estimades. A la UAB, l'estimació per plantes queda 2–3 m per sota de les dues mesures
(`python scripts/validar_alcaries.py`).

### Fotografia aèria (a tot arreu, com Google Earth)

El color del terra i de la Terra és la fotografia aèria: el PNOA de l'IGN a Espanya (fins a ~0,22 m per píxel) i
Sentinel-2 cloudless (EOX, 10 m per píxel) a la resta del món i des de lluny. Es baixa en segon pla a mesura que
cal, en teselles de 256 px, i es desa a `data/cache/teselles/`: en arribar a un lloc nou es veu de seguida una
imatge borrosa que s'afina en uns segons (la primera vegada; després es llegeix del disc). Sense connexió, el
terra té el color segons l'altitud, com abans. Cada píxel fa servir el nivell de detall que li correspon (més a
prop, més detall) i, si aquell encara no ha arribat, el de menys detall: no hi ha forats. Hi apliquem la nostra
llum (Sol, ombra de la Lluna, ombres del relleu i dels edificis); les fotos conserven les seves pròpies ombres
del dia del vol. La casella **Fotografia aèria** del panell la desactiva. El relleu fora de les zones de detall
continua sent el de 200 m. Funcionament: `basecode/mosaic.py`; comprovació: `python scripts/prova_mosaic.py`.

Des de l'espai, la Terra té una resplendor blava a la vora (la closca d'atmosfera, `shaders/atmosfera_terra.*`):
més forta on la mirada travessa més aire. És il·lustrativa: molt més gruixuda que l'aire real, perquè es vegi de
lluny.

**Colors dels edificis** (a tot arreu igual):
- **Altura mesurada (LiDAR):** la coberta té el color real, el de la fotografia aèria del PNOA al seu lloc (la mitjana
  dels píxels de les teselles de z = 17, ~0,9 m, dins del contorn sense 1 m de vora; `dades/edificis.colors_cobertes`).
  Es calcula en un procés la primera vegada que es veu cada zona (Vic: 17.000 parts, ~240 teselles, uns segons si ja
  són al disc) i es desa a `data/cache/cobertes_<zona>.npz`. Les façanes tenen colors variats (estètic).
- **Altura estimada (plantes × 3 m):** tot l'edifici és **blau**, un color que no és d'edifici: es veu que l'altura
  no és una mesura. El panell *Càmera* ho recorda sota la casella *Edificis*.
La foto no és ortofoto vertadera: la teulada dels edificis alts hi queda desplaçada uns metres, i la mitjana de tota
la coberta en redueix l'efecte.

L'ortofoto de Vic descarregada a la F18 (`python scripts/descarregar_ortofoto.py vic`) **ja no es fa servir** (equip,
01/11/2026): Vic es tracta com qualsevol altre lloc. **Comparació** (per què no calia): és la
mateixa font (PNOA) a 0,5 m; la fotografia per teselles arriba a z = 19 (~0,22 m per píxel a Catalunya i València),
que ja és la resolució del vol (0,25 m a tots els llocs consultats). Per tant, la fotografia per teselles ja dona el
detall màxim de la font a tot Espanya; el WMTS té z = 20, però seria la mateixa imatge ampliada.

### El Sol i la Lluna de prop

**La Lluna** fa servir les dades de la NASA (CGI Moon Kit): el color de la LRO a 8192 × 4096 (~1,3 km per píxel)
i el relleu del LOLA, que fa que els cràters facin ombra prop del terminador. Es baixen un sol cop (84 MB, no van
al Git) amb `python scripts/descarregar_textures.py --alta`; sense, el programa fa servir la textura d'1k.
De molt a prop (menys de ~0,5 km per píxel de pantalla) s'hi afegeixen cràters petits i variacions de color
**il·lustratius** (no són dades). **El Sol**, des del terra, és un disc blanc que enlluerna; en pujar fins a l'espai pren
un aspecte de foc (flames animades, vora fosca i vermella), il·lustratiu, com les fotos fetes amb filtre.

### Ombres del relleu i dels edificis

Dins de la zona de 5 m de l'observador (16 km al voltant del punt), les muntanyes fan ombra amb la
tècnica del *shadow mapping* (`basecode/ombres_relleu.py`): primer es dibuixa el relleu vist des del Sol
en una textura de profunditat i, després, cada punt del terreny mira si és més lluny del Sol que el que hi
ha guardat. L'ombra del relleu només treu la llum directa del Sol; la del cel continua. És diferent de
l'ombra de la Lluna (la part del Sol que tapa la Lluna, a tota una regió). Es pot apagar al panell *Càmera*.
Fora de la zona de 5 m no hi ha ombres del relleu.

**Edificis (F36).** Hi ha un segon mapa, **fi**: 3 × 3 km al voltant del punt de detall, amb píxels de 0,7–0,9 m
(el gran, de 32 km, en té de ~8 m). Amb aquest, tots els edificis fan ombra (al terra i als altres edificis) i les
façanes i les cobertes **en reben**. La funció és compartida pel terreny i els edificis (`shaders/ombres.glsl`).
Amb el Sol rasant (a la posta del 2026), el terra rep molt poca llum directa (un 5 % amb el Sol a 3°) i l'ombra hi
es nota poc; es veu a les façanes de cara al Sol i, a hores amb el Sol més alt, als carrers i les places. Per evitar
que una superfície es faci ombra a si mateixa, el marge creix amb la inclinació de la llum: amb el Sol rasant, els
primers metres de l'ombra arran de l'edifici es perden. Els mapes es refan quan l'hora canvia en 1 s o més (temps de
l'eclipsi): mentre es reprodueix a x60, cada fotograma passa de ~13 a ~22 ms.

### Panell i barra de temps

- **Dos panells** (només controls):
  - **Eclipsi** (a l'esquerra): l'eclipsi (12/08/2026 total, 02/08/2027 total, 26/01/2028 anular); hora, fase, part
    del Sol tapada i velocitat (*Auto* o x1 a x1000); el punt d'observació (llista, coordenades, **nucli i
    municipi**, tornar-hi, anar al màxim); el mapa de visibilitat; les línies de l'ombra de la Lluna i, només el
    2026, les capes del CNIG.
  - **Càmera** (a la dreta): la vista (explorar, des del terra, espai; vol lliure o caminar; mirar el Sol; l'ombra
    de la Lluna des de l'espai); **on és la càmera**: altura sobre el terra que es dibuixa a sota, altitud sobre el
    nivell del mar (sobre l'el·lipsoide WGS84) i coordenades; què es dibuixa (fotografia aèria, edificis, ombres del
    relleu, noms de lloc); el **detall del lloc** (terreny, foto, edificis i mapa). *Tecles* i *Avançat* (FPS, exageració,
    filferros, origen de les altures, dades del CNIG) són desplegables tancats.
- **Noms de lloc sobre el mapa** (`ui.noms_al_mapa`, `data/noms_mapa.json`), com a Google Maps, a les vistes aèries:
  segons l'altura de la càmera sobre el terra, les capitals de comunitat (de 25 a 4.000 km), les de província (de 12 a
  1.500 km) i les de comarca de Catalunya (de 3 a 200 km). Més a prop desapareixen. No s'escriuen els que queden
  darrere de l'horitzó ni els que en taparien un de més important. La casella *Noms de lloc* del panell *Càmera* els
  amaga.
- **Rendiment:** el programa fa servir la sincronia vertical (`glfw.swap_interval(1)`): no dibuixa més fotogrames dels
  que la pantalla mostra (~60 per segon). La imatge és la mateixa. Si durant mig segon no canvia res (mateixa càmera i
  hora, en pausa) i no hi ha res en segon pla (descàrregues, càlculs de mapes, detall, nom del lloc), queda **en
  repòs**: només redibuixa 4 vegades per segon fins que es toca el teclat o el ratolí, que el desperten a l'instant.
  *Avançat* ho indica al costat de l'FPS.
- **Nom del lloc** (`dades/noms.py`): en triar un punt, el **nucli de població més proper** (Nomenclàtor Geogràfic
  Bàsic de l'IGN; si l'adreça més propera pertany a un nucli, "dins de" aquell) i el **municipi** administratiu
  (CartoCiudad). Són dades diferents: entre Vic i Tona, un punt pot ser del municipi de Malla o de Tona i tenir com a
  nucli més proper el Gurri. Els noms es mostren sense accents (limitació de la font del panell).
- **Barra de temps** (a baix): reproduir/pausar, ±5 min i l'hora, que es pot arrossegar. Marques al punt triat:
  inici i final (groc), fase central (lila), màxim (blanc) i posta (taronja); a sota, les hores.

### Mapa de visibilitat de l'eclipsi (on anar a veure'l)

Per a cada punt del relleu, si el relleu tapa el Sol durant l'eclipsi: el centre del Sol es veu si queda per
sobre de l'horitzó en la seva direcció (des dels ulls, a 1,7 m; amb la curvatura de la Terra i el relleu llunyà
fins a 200 km). No depèn de la llum. Tres opcions al panell:
- **Al màxim**: tapat, menys de mig Sol, més de mig Sol o sencer (les classes de la capa del CNIG).
- **Totalitat visible**: segons de totalitat (o anularitat) que es veuen sense que el relleu tapi el Sol.
- **Instant actual**: segueix la barra de temps: on el relleu tapa el Sol, la part que en tapa la Lluna i la
  fase central.

Es calcula la primera vegada que es demana per a cada terreny i eclipsi (en segon pla; la península, ~20 min; una
zona de 5 m feta a mà, 15–30 min; un lloc de 6 × 6 km, ~1 min) i es desa a `data/cache/visibilitat_*.npz`. Per
tenir-los preparats: `python scripts/preparar_visibilitat.py [2026 2027 2028]`. Comprovació:
`python scripts/validar_visibilitat.py <MDT> [--cnig]`. Aquest mapa només té el relleu del MDT.

**Mapa de detall (edificis i vegetació).** Mentre el mapa es mostra, a la cel·la de 3 × 3 km del punt de detall es
calcula el mateix amb els obstacles mesurats: terra + alçària LiDAR (ICGC a 2 m a Catalunya, IGN a 2,5 m a la resta;
els arbres compten si la font els té) i els ulls sobre els terrats a les cel·les d'edifici. Mentrestant es veu el
mapa del relleu, i el panell diu què s'està calculant. La UAB es tracta igual que la resta (model d'alçàries de
l'ICGC); el núvol de punts de la UAB (`scripts/visibilitat_lidar.py`, 1 m) només serveix per validar-lo. Les altures estimades per plantes **no** hi entren. Limitacions: fora d'Espanya el
MDT val 0; les dates de les fonts (IGN, fins a 15 anys); sense refracció terrestre.

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
- **Cel i atmosfera** (`dades/atmosfera.py`, `basecode/cel.py`, `shaders/cel.frag`): dispersió de Rayleigh,
  Mie i absorció de l'ozó, amb la densitat de l'aire decreixent amb l'altura i el raig des de l'altitud de la
  càmera; a cada punt del raig, la part del Sol que hi tapa la Lluna (a la totalitat, l'horitzó encara brilla).
  El mateix model dona el color de la llum del Sol al terreny, als edificis i a la Terra i el color de la boira.
  La boira del terreny i de la Terra s'enfosqueix exponencialment amb la distància, amb la densitat mitjana de
  l'aire entre la càmera i el punt: des de dalt, el paisatge llunyà es veu velat com des del terra.
  Es calcula a baixa resolució (com a molt 400 px d'amplada) i es dibuixa només on no hi ha res: no tapa el Sol
  ni la Lluna. Comprovació: `python scripts/prova_cel.py`.
- **Il·lustratiu (no validat)**: l'exposició i l'adaptació de l'ull a la foscor de l'eclipsi, la llum mínima
  dins de l'ombra (en lloc de dispersió múltiple), el color del cel ambient, el halo i la corona, el contorn
  blau de l'atmosfera de la Terra, la granulació animada del Sol, i les finestres i els colors de façana dels
  edificis. L'orientació de la Lluna és aproximada (sense libració).

---

## 3. Què hi ha a cada carpeta

```
main.py                  Programa principal: coordina l'escena (temps, astres, cel i teclat)
ui.py                    Interfície: els panells Eclipsi i Càmera i la barra de temps (slimgui)
basecode/                Codi base de l'assignatura (el del repte 4, sense canvis) i els nostres objectes:
  engine.py, window.py, ui_panel.py, objects.py, camera.py, light.py, axis.py,
  meshloader.py, shaders.py       fitxers originals del professor (no es modifiquen)
  terra.py               La Terra (el·lipsoide amb textura, dia i nit, ombra de la Lluna)
  mosaic.py              Fotografia aèria per teselles (nivells de zoom a la GPU, carregats en segon pla)
  terrain.py             Relleu d'un MDT: mode globus (posat sobre la Terra) i mode pla (scripts)
  astres.py              El Sol (amb limbe i granulació), el seu halo i la Lluna (amb textura)
  ombres_relleu.py       Ombres del relleu (shadow mapping) a la zona de 5 m
  paret_cub.py           Les parets translúcides del cub de navegació
  edificis.py            Els edificis (volums opacs) de la zona de detall
  control_ratoli.py      Ratolí capturat per mirar (Tab), sensibilitat, roda i trackpad
  camera_guiada.py       Càmera de la vista guiada (roda = progrés de la trajectòria)
  sol.py                 La llum de l'escena (Light del basecode)
  camera_exploracio.py   Càmera lliure, del terreny fins a l'espai
  camera_observador.py   Càmera als ulls de l'observador (1,7 m sobre el terra)
  camera_orbital.py      Càmera orbital del mode pla (només per als scripts)
  programes.py           Carrega shaders amb opcions (#define) i fitxers compartits (#include)
  shaders/               gouraud i phong (originals); terrain, terra, esfera, ombra, paret, cel, edifici i
                         mosaic.glsl (nostres)
dades/                   Lectura i càlcul de dades, sense OpenGL:
  efemerides.py          Posicions del Sol i la Lluna en coordenades terrestres
  geodesia.py            Latitud, longitud i altitud <-> coordenades terrestres (WGS84)
  model_eclipsi.py       Part del Sol tapada, contactes i centre de l'ombra
  observador.py          La ubicació de l'observador i la llista d'ubicacions
  navegacio.py           El cub de navegació (límits de la càmera d'exploració)
  trajectoria.py         La trajectòria de la vista guiada (del punt a l'espai)
  edificis.py            Edificis: altures estimades, cotes, malla i ocultació del Sol (sense OpenGL)
  data_io.py             Lectura dels MDT, neteja de les dades i fitxers auxiliars (data/cache/)
  mdt_wcs.py             Peticions al servei WCS del MDT de l'IGN
  catastro.py            Edificis del Catastro: canals ATOM, ZIP per municipi i lectura
  llocs.py               Llocs nous amb detall (doble clic): relleu i edificis en segon pla
  eclipsis.py            Els tres eclipsis (data, tipus, efemèrides, hora local)
  visibilitat.py         Mapa de visibilitat: circumstàncies en graella i horitzó cap al Sol per a cada píxel
  teselles.py            Fotografia aèria: coordenades Web Mercator, descàrrega en fils i memòria cau
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
    llocs/                (no es puja al git) llocs nous del doble clic, 6 x 6 km a 5 m (com a molt 3)
  mdt05/
    PNOA_MDT05_ETRS89_HU30_0011_LID.tif   Fulla 0011 (Luarca) del MDT05, 5 m (exemple de fulla original)
  eclipsi2026/          Dades oficials de l'eclipsi del 12/08/2026 (CNIG)
    10bandas2026_3857_COG.tiff      Efemèrides: posició del Sol, enfosquiment i hores de cada fase
    terrain_shadows_2026_..._.tif   Visibilitat del Sol al màxim segons el relleu (4 classes)
    Eclipses_2026.gpkg              Corbes de nivell (durada, enfosquiment, avanç de l'ombra)
    LLEGENDA.md                     Què conté cada banda, classe i capa
    doc/                            Documentació original del CNIG
  lidar/                (no es puja al git) rasters d'1 m del LiDAR de l'ICGC (UAB: superfície, terra, edificis)
  edificis/             (no es puja al git) edificis del Catastro de les zones de detall
    catastro/             ZIP originals per municipi (~45 MB)
    valles.gpkg, vic.gpkg, escala.gpkg, picos.gpkg   parts d'edifici a 2 km dels punts (EPSG:25830)
    lloc_<x>_<y>.gpkg     parts d'edifici dels llocs nous (2 x 2 km)
  nasa/
    circumstancies_nasa.csv          Resultats del calculador de la NASA (comprovació externa)
  textures/             Terra (Blue Marble, 2048 px) i Lluna (1024 px), al git; la Lluna a 8k i el seu
                        relleu (lluna_8k.jpg, lluna_altitud.npy, originals/) no es pugen al git
  cache/                (no es puja al git) fitxers que genera el programa (també la malla dels edificis)
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
| `descarregar_efemerides.py` | Descarrega les posicions del Sol i la Lluna de JPL Horizons (`data/efemerides/`) per a un eclipsi (`2026`, `2027` o `2028`) |
| `descarregar_textures.py` | Descarrega les textures de la Terra i la Lluna (NASA, `data/textures/`); amb `--alta`, la Lluna a 8k i el seu relleu (84 MB) |
| `validar_model.py` | Compara les hores de l'eclipsi del nostre model amb les del CNIG a 9 punts |
| `validar_ombra.py` | Comprova que l'ombra de la Lluna cau dins de la umbra publicada pel CNIG |
| `prova_vistes.py` | Prova el programa a les sis ubicacions (ulls, mirar avall, pausa, allunyar-se comprovant la superfície, P a l'espai, botons, ombra) i la seqüència sencera amb el bucle real i el teclat i el ratolí simulats; captures a `captures/proves/`. Amb `--visible`, es veu a la finestra |
| `descarregar_edificis.py` | Baixa els edificis del Catastro de les zones de detall i en prepara les dades i la malla (`data/edificis/`, `data/cache/`) |
| `validar_edificis.py` | Edificis: contorns contra OpenStreetMap, plantes contra la font, cobertes a la cota calculada, Sol visible/parcial/total a la imatge contra el càlcul geomètric, halo, interruptor, rendiment |
| `prova_noms.py` | Noms de lloc sobre el mapa: el fitxer té els tres nivells; quins s'escriuen sobre Manresa a 1.200, 300, 60, 8 i 1,5 km (de prop, cap); cap des del terra ni amb la casella desactivada; captures a `captures/proves/noms_*.png` |
| `prova_eclipsis.py` | Els tres eclipsis amb el bucle real i el panell dibuixat: canviar-hi sense errors d'OpenGL, contactes, *Anar al màxim*, Sol i Lluna de l'escena iguals al model, capes del CNIG només el 2026, el mapa de visibilitat comença; captures a `captures/proves/eclipsi_*.png` |
| `prova_controls.py` | Arrencada, cub de navegació (sis cares, teclat, roda, botons), enquadrar el Sol, ratolí capturat (Tab, clic dret, focus, FPS, zoom, límits), panell, P, roda i vista guiada (anada i tornada, temps, ubicació, Mirar l'eclipsi); captures a `captures/proves/guiat_*.png` |
| `prova_cel.py` | Cel i llum: shader contra el model de la CPU, el cel no tapa cap objecte, continuïtat minut a minut, saturació, totalitat contra posta, orientació dels triangles dels edificis i colors de coberta, temps per fotograma (1280 × 860 i 2560 × 1720) |
| `prova_obstacles.py` | Edificis com a obstacles: geometries de prova (paret, diagonal, cantonades, escletxes, patis), 3.000 moviments a l'atzar sobre el Catastro del Vallès i el programa real (punts exteriors amb cel, caminar i volar contra l'ajuntament de Cerdanyola, cobertes, recuperació) |
| `prova_ortofoto.py` | (Obsolet des de la F38: el programa ja no carrega l'ortofoto.) Ortofoto d'una zona: alineació amb el Catastro, mida, memòria, temps per fotograma i captures |
| `descarregar_ortofoto.py` | Descarrega l'ortofoto del PNOA d'una zona (tota la zona a 5 m i 4 × 4 km a 0,5 m al voltant de cada punt) |
| `prova_mosaic.py` | Fotografia aèria i controls aeris: coordenades de les teselles, precisió, sense xarxa, alineació entre la Terra i el terreny, temps, arrossegar, roda, orbitar, inèrcia, doble clic i edificis segons la vista; captures a `captures/proves/mosaic_*.png` |
| `prova_caminar.py` | Mode Caminar amb el programa real: direcció amb W/S/A/D a diferents rumbs, diagonal, inclinació, FPS, pendents (ulls a 1,7 m), pas llarg subdividit, vora de zona i mar, entrar/sortir, focus, panell |
| `validar_visibilitat.py` | Mapa de visibilitat d'un MDT: circumstàncies de la graella contra el model punt a punt, marge al màxim i hores contra un raig exacte; amb `--cnig`, classes contra la capa del CNIG |
| `descarregar_lidar.py` | Baixa el LiDAR de l'ICGC al voltant d'un punt (`uab`: 3 × 3 km) i en fa rasters d'1 m (superfície, terra, edificis); els LAZ s'esborren (`data/lidar/`) |
| `comparar_altures.py` | Altures dels edificis estimades amb el Catastro contra les del LiDAR, i terra del LiDAR contra el MDT de l'IGN |
| `preparar_visibilitat.py` | Precalcula els mapes de visibilitat de la península i les zones de detall (per eclipsi) |
| `prova_llocs.py` | Llocs nous amb doble clic: claus, cobertura i esborrat dels antics; UAB i mar sense lloc nou; Manresa (o, amb `--xarxa`, Igualada preparada de nou) en segon pla, observador sobre el relleu de 5 m, espera a la pausa |
| `prova_trajectoria.py` | Sense finestra: la trajectòria guiada no travessa la Terra, la Lluna ni el Sol, és contínua, enquadra cada tram i és reversible, a les sis ubicacions i 16 hores; límits de la mirada |
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
- **Edificis**: Catastro INSPIRE (Dirección General del Catastro), descarregats el 26/10/2026; detall a
  `data/FONTS.md`.
- **Coordenades de les ubicacions**: geocodificador de l'ICGC i OpenStreetMap (© col·laboradors
  d'OpenStreetMap, ODbL).
- **Textures**: NASA Visible Earth ("Blue Marble", la Terra) i NASA SVS ("CGI Moon Kit", la Lluna: color de la
  LRO i relleu del LOLA), domini públic.
- **Fotografia aèria**: PNOA cedit per © Instituto Geográfico Nacional (CC BY 4.0); Sentinel-2 cloudless 2020
  (https://s2maps.eu, EOX IT Services GmbH, dades modificades de Copernicus Sentinel 2020; CC BY-NC-SA 4.0, ús no
  comercial).

El detall de cada fitxer (zona, resolució, CRS, llicència i com es torna a descarregar) és a
`data/FONTS.md`.
