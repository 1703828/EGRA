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

Darrera actualització: 2026-10-31 (F31: detall segons la vista a tot Espanya, altures mesurades dels edificis, mapa de detall i nom del lloc).

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
| D53 | (F14; substituïda per D60) Els punts d'observació que cauen dins d'un edifici no es mouen: es documenten i es proposa un punt exterior proper, pendent de la decisió de l'equip. | 26/10 |
| D54 | (F15, equip) Mirada amb el ratolí: Tab (o clic dret a l'escena) captura a l'instant i Tab o Esc alliberen; el clic esquerre ja no captura (arrossegar i doble clic com abans, sense l'espera de 0,3 s). Sensibilitat única (`SENSIBILITAT`), proporcional al camp de visió. | 27/10 |
| D55 | (F15, equip) Tercera vista, "Allunyar-se fins a l'espai (guiat)" (tecla G): la posició depèn només d'un progrés (roda, W/S) sobre una trajectòria fixa; la mirada és de l'usuari. Les altres vistes i el significat de les tecles existents no canvien. | 27/10 |
| D56 | (F15) La trajectòria guiada es calcula amb el Sol i la Lluna de l'hora d'entrada (ancora): canviar l'hora no mou la càmera; Recentrar l'actualitza; canviar d'ubicació des del panell la recalcula amb el mateix progrés. | 27/10 |
| D57 | (F15) Mides i distàncies reals també a la vista guiada: no es fan cabre els astres. La vista de l'espai és de context i no reprodueix l'eclipsi vist des del terra. | 27/10 |
| D58 | (F16, equip) Mode "Caminar" dins d'Explorar, al costat de "Vol lliure" (selector del panell): W A S D a 1,5 m/s (Shift: córrer ×3), ulls a 1,7 m sobre el relleu dibuixat en pujada i en baixada; E/Q i la roda no hi fan res; sense salt, gravetat ni col·lisions amb edificis. | 27/10 |
| D59 | (F16) Caminant, el mar i les zones sense relleu no es trepitgen: la càmera s'atura a la vora. Per entrar-hi cal ser a menys de 5 km sobre el relleu (es baixa en vertical); si no, el panell ho diu i ofereix "Caminar des del punt d'observació". | 27/10 |
| D60 | (F17, equip) Els ulls de l'observador mai dins d'un edifici: si el lloc triat (llista o doble clic) hi cau, es posen al punt exterior més proper a 3 m de les façanes, a l'espai obert connectat amb els carrers (no a un pati tancat ni al terrat). La referència es conserva i es distingeix de la posició efectiva. Substitueix D53. | 27/10 |
| D61 | (F17, equip) Els edificis que es mostren són obstacles: caminant (cos de 0,3 m, lliscant) i en vol lliure per sota de la coberta (es pot passar per sobre). Amagats, no fan d'obstacle. | 27/10 |
| D62 | (F18, equip) Terra de les zones de detall: ortofoto del PNOA (IGN, CC BY 4.0) com a color base, primer només a Vic (zona a 5 m i 4 × 4 km a 0,5 m). L'ICGC queda descartada fins a confirmar-ne la llicència. Les ombres de la foto s'accepten provisionalment. | 27/10 |
| D63 | (F18, equip) Després de validar el terra: façanes procedimentals (plantes reals) i cobertes amb el color de l'ortofoto. | 27/10 |
| D64 | (F19, equip) Cel per dispersió (Rayleigh, Mie, ozó) amb la densitat decreixent amb l'altura i l'ombra de la Lluna a cada punt del raig; la mateixa atmosfera dona el color de la llum i de la boira. Dibuixat només on no hi ha res (no altera els discs ni la geometria). | 27/10 |
| D65 | (F20, equip) Textures dels edificis abans de la validació del terra (petició explícita): façanes procedimentals amb les plantes reals i cobertes amb el color de l'ortofoto (D63). | 27/10 |
| D66 | (F21, equip) Fotografia aèria a tot el territori i a la Terra, "com a Google Earth", carregada a mesura que cal (petició explícita: avança la descàrrega progressiva que CLAUDE.md deixava per a més endavant). Fonts: PNOA de l'IGN (WMTS, CC BY 4.0) i Sentinel-2 cloudless 2020 d'EOX (WMTS, CC BY-NC-SA 4.0, ús no comercial) on el PNOA no en té i als zooms de país i de la Terra. Les imatges de Google no es poden fer servir (condicions d'ús). Memòria cau al disc (`data/cache/teselles`, ignorada). | 28/10 |
| D67 | (F21, equip) Vista aèria (vol lliure) amb controls de ratolí com Google Earth: arrossegar desplaça el terra, Shift + arrossegar (o botó del mig) orbita al voltant del centre de la pantalla, la roda s'acosta al punt del cursor amb una animació suau; inèrcia en deixar anar. Les tecles no canvien. Caminant i observant, el ratolí fa el mateix que abans. | 28/10 |
| D68 | (F21, equip) Doble clic explorant: l'observador va al punt i la vista passa directament a primera persona (observar des del terra), mirant cap on mirava la càmera, en horitzontal. La càmera d'exploració no es mou (V hi torna). Substitueix la part de D43 i D46 sobre el doble clic. | 28/10 |
| D69 | (F21, equip) Edificis: per defecte només en primera persona (observació i caminar), per veure l'horitzó que deixen; a la vista aèria (vol lliure i guiada) no, perquè no tapin la fotografia. Totes dues opcions es poden canviar al panell. | 28/10 |
| D70 | (F21) Boira del terreny i de la Terra amb extinció exponencial (Beer-Lambert) i la densitat mitjana de l'aire en el camí de la càmera al punt (atmosfera exponencial, escala 8 km); 1/e cada 120 km a nivell del mar. La Terra (mar, països veïns) té la mateixa boira que el terreny. | 28/10 |
| D71 | (F22) La coordenada Mercator dels vèrtexs del terreny es passa relativa a l'origen de cada terreny (un nombre petit, precís en float32), no partida en alta + baixa: el compilador de la GPU pot reordenar les sumes i la foto es movia ~1 m per vèrtex. | 28/10 |
| D72 | (F22, equip) Lluna amb les dades d'alta resolució de la NASA (CGI Moon Kit): color de la LRO a 8192 × 4096 i relleu del LOLA (16 px/grau), baixats amb autorització explícita de l'equip (84 MB, fora del Git). De molt a prop (menys de ~0,5 km per píxel), cràters petits procedimentals, **il·lustratius**. | 28/10 |
| D73 | (F22, equip) Sol amb aspecte de foc (taronja i vermell, flames animades) **només des de l'espai**: **il·lustratiu**, com les fotos fetes amb filtre. Des del terra, disc blanc que enlluerna; transició gradual en pujar fins a 60 km. | 28/10 |
| D74 | (F22) La corona només apareix amb menys del 0,05 % del disc del Sol visible (els últims segons abans de la totalitat). Abans començava al 0,4 % i a Cerdanyola (99,74 %, parcial) se'n veia una part. | 28/10 |
| D75 | (F23, equip) No es fan servir imatges ni models 3D de Google (Photorealistic 3D Tiles): cal clau i facturació, no es poden desar al disc, i arran de terra la malla es veu desfeta. Es milloren les nostres dades (llum de les façanes, edificis a qualsevol lloc). | 30/10 |
| D76 | (F23) Llum de les façanes: una paret vertical veu mig cel i mig terra (que reflecteix el ~25 % de la llum que rep), i el contrast entre cares es codifica amb gamma 2,2 respecte d'una cara de cara al Sol. A l'ombra, la paret passa de ~1/4 a ~1/2 de la il·luminada. Les cobertes, com el terra (0,25 cel + 0,75 Sol). **Aproximació il·lustrativa.** | 30/10 |
| D77 | (F23, equip) Llocs nous amb detall: el doble clic on no hi ha edificis a menys de 500 m prepara en segon pla el relleu de 5 m (6 × 6 km, WCS de l'IGN) i els edificis del Catastro (2 × 2 km, ZIP per municipi; el WFS per rectangle és massa lent). Com a molt 3 llocs al disc (~40–110 MB cadascun); s'esborren els més antics. Malles d'edificis comprimides. | 30/10 |
| D78 | (equip) Les vistes en primera persona i aèria es donen per bones de moment. La transició cap a l'espai (fins a la Lluna i el Sol) no agrada, però queda aparcada: s'hi tornarà més endavant. | 30/10 |
| D79 | (equip) Objectiu nou **O3 · On es veurà l'eclipsi** (aplicació de dades): mapa de visibilitat segons el que tapa el Sol (relleu i edificis), estàtic al màxim i dinàmic al llarg de l'eclipsi, per als eclipsis del 2026, 2027 i 2028. El número O3 es reutilitza (l'antic es va retirar a D31). Proposta a §11, O3; pendent de P14–P17. | 30/10 |
| D80 | (equip, P14–P17) L'afluència (F30) es descarta. L'aplicació és part del programa (capa sobre el terreny i opció del menú), no una web a part. Els mapes, a la resolució del MDT (5 m a les zones; no es redueix). L'índex: classes al màxim i segons de fase central visibles (proposta de F29). | 30/10 |
| D81 | (equip) Als mapes de visibilitat, els edificis només hi entraran amb **altures mesurades**, no estimades (plantes × 3 m). Candidates: MDS normalitzat d'edificació del CNIG (LiDAR PNOA, 2,5 m, primera cobertura) i el LiDAR territorial de l'ICGC (3a cobertura, CC BY 4.0, fulls d'1 × 1 km). Pendent d'autorització de la descàrrega (F27). | 30/10 |
| D82 | (equip) Menú d'imgui net: només controls (eclipsi, temps, vista, punt, mapa de visibilitat, capes); sense textos d'explicació; les tecles i la depuració en desplegables tancats. Substitueix la part de CLAUDE.md sobre l'"ajuda curta" visible. | 30/10 |
| D83 | (equip, P18) LiDAR territorial de l'ICGC (3a cobertura, CC BY 4.0) a la UAB: 3 × 3 km (9 fulls) centrats a la plaça Cívica. Instal·lades `laspy` i `lazrs` (lectura de LAZ). Cada full es converteix en rasters d'1 m i el LAZ s'esborra. | 30/10 |
| D84 | (F31, equip) El detall es prepara segons el que es mira, a qualsevol lloc d'Espanya amb dades, sense doble clic ni punt d'observació: relleu de 5 m, edificis (si es veuen), altures mesurades i mapa de detall (si es mostra), en segon pla i reutilitzats. Llocs en una quadrícula fixa de 3 km (relleu 6 × 6 km, edificis 3 × 3 km); com a molt 6 llocs al disc i 3 zones carregades (la del punt d'observació, fixada). Una preparació antiga no canvia el que es veu. Substitueix el doble clic de D77 com a única manera de preparar llocs. | 31/10 |
| D85 | (F31, equip) Altures dels edificis: provisionalment estimades (plantes × 3 m) mentre arriben les mesurades. Fonts mesurades: a Catalunya el model d'alçàries de l'ICGC (LiDAR 2021–2023, 1 m, llegit per finestres del COG de tot Catalunya, sense descarregar-lo); a la resta d'Espanya el MDS normalitzat de l'IGN (PNOA-LiDAR 2008–2015, 2,5 m, WCS, edificació i vegetació). Es mesuren per cel·les de 3 × 3 km on es mira. El panell distingeix mesurades, estimades i no disponibles. | 31/10 |
| D86 | (F31) Fotografia: la de teselles (PNOA fins a z = 19, ~0,22 m/px) ja dona la resolució del vol (0,25 m a tots els llocs consultats) a tot Espanya; l'ortofoto de Vic (0,5 m) no s'estén. z = 20 existeix al WMTS però seria la mateixa imatge ampliada. | 31/10 |
| D87 | (F31, equip) Mapa de visibilitat amb detall local a qualsevol lloc: superfície = terra + alçària mesurada (edificis i, si la font la té, vegetació), a 2 m (ICGC) o 2,5 m (IGN), per cel·les; mentrestant, el mapa del relleu. Les altures estimades no hi entren (D81). | 31/10 |
| D88 | (F31, equip) Nom del punt triat: el nucli de població més proper (NGBE de l'IGN) i, separat, el municipi administratiu (CartoCiudad). | 31/10 |
| D89 | (F31) Les feines que passen molta estona dins de GDAL o en bucles de Python (Catastro, malla, altures, superfície) es fan en un **procés** separat: en un fil, el bloqueig global de Python (GIL) aturava el dibuix (5 min sense fotogrames llegint el Catastro de València). | 31/10 |
| D47 | (F12) El gest de pessigar del trackpad no és disponible amb GLFW a macOS; l'alternativa és lliscar amb dos dits (el mateix esdeveniment que la roda). El gest natiu necessitaria una dependència nova (PyObjC), pendent d'autorització. | 26/10 |

### 1.2 Pendents

(Historial: P1–P13 resoltes a D15–D25 i D31.) Obertes (O3, 30/10):

- P14–P17 resoltes a D80.
- P18 resolta a D83.
- Aparcat (D78): la transició cap a l'espai.

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
| Mirada amb el ratolí (Tab), límits de la mirada, "Mirar l'eclipsi" i vista guiada fins a l'espai | `basecode/control_ratoli.py`, `basecode/camera_guiada.py`, `dades/trajectoria.py`, `main.py`, `ui.py` | F15 (`FET`; Mouse Look `VALIDAT`) |
| Caminar sobre el relleu dins d'Explorar (ulls a 1,7 m, W A S D, Shift) | `basecode/camera_exploracio.py`, `basecode/terrain.py` (`es_terra`), `main.py` (`altitud_caminable_km`), `ui.py` | F16 (`FET`) |
| Punts d'observació a l'exterior dels edificis; edificis com a obstacles | `dades/obstacles.py`, `basecode/camera_exploracio.py`, `main.py` (`triar_punt`), `dades/observador.py` | F17 (`FET`) |
| Ortofoto del PNOA com a color del terra (prova a Vic) | `scripts/descarregar_ortofoto.py`, `basecode/terrain.py`, `shaders/terrain.frag` | F18 (`FET`, pendent de valoració) |
| Cel per dispersió, llum i boira de l'atmosfera | `dades/atmosfera.py`, `basecode/cel.py`, `shaders/cel.*`, `terrain.*`, `terra.*`, `esfera.frag` | F19 (`FET`) |
| Façanes amb finestres per planta i cobertes de l'ortofoto | `dades/edificis.py`, `basecode/edificis.py`, `shaders/edifici.*` | F20 (`FET`) |
| Fotografia aèria a tot arreu (PNOA + Sentinel-2), carregada en segon pla; controls aeris; doble clic a primera persona; edificis segons la vista | `dades/teselles.py`, `basecode/mosaic.py`, `shaders/mosaic.glsl`, `terrain.*`, `terra.*`, `camera_exploracio.py`, `main.py`, `ui.py` | F21 (`FET`) |
| Llocs nous amb detall amb doble clic (relleu de 5 m i edificis a qualsevol lloc d'Espanya, en segon pla) | `dades/llocs.py`, `dades/catastro.py`, `dades/mdt_wcs.py`, `main.py`, `ui.py` | F23 (`FET`) |
| Detall segons la vista a tot Espanya (relleu, edificis amb altures mesurades, mapa de detall); nom del lloc | `basecode/detall.py`, `dades/alcaries.py`, `dades/llocs.py`, `dades/noms.py`, `dades/feines.py`, `basecode/terrain.py`, `basecode/edificis.py`, `main.py`, `ui.py` | F31 (`FET`) |
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
| O3 · Mapa de visibilitat de l'eclipsi (estàtic i dinàmic, relleu i edificis, 2026–2028) | N | Proposta (D79) | F24–F30 |

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
  mosaic.py                       Mosaic (fotografia aèria per teselles, carregada a mesura que cal)
  detall.py                       Detall (detall segons la vista: quina zona, edificis i mapa, i la seva càrrega)
  terrain.py                      Terrain (mode globus i mode pla)
  astres.py                       Esfera (Sol, halo) i Lluna
  ombres_relleu.py                OmbresRelleu (shadow mapping de la zona de 5 m)
  edificis.py                     Edificis (volums del Catastro de la zona de detall)
  paret_cub.py                    ParetCub (parets translúcides del cub de navegació)
  control_ratoli.py               ControlRatoli (ratolí capturat, roda i trackpad)
  sol.py                          Sol (Light amb azimut i elevació)
  camera_exploracio.py            CameraExploracio (lliure, ECEF)
  camera_observador.py            CameraObservador (als ulls)
  camera_guiada.py                CameraGuiada (vista guiada: progrés sobre una trajectòria)
  camera_orbital.py               CameraOrbital (mode pla, scripts)
  programes.py                    carregar shaders amb #define i #include
  shaders/                        gouraud, phong (originals) + terrain, terra, esfera, ombra, paret, cel, edifici,
                                  mosaic.glsl (nostres)
dades/                          sense OpenGL: efemerides.py, geodesia.py, model_eclipsi.py,
                                observador.py, navegacio.py, trajectoria.py, edificis.py, data_io.py,
                                eclipse_data.py, obstacles.py, atmosfera.py, teselles.py, mdt_wcs.py,
                                catastro.py, llocs.py, eclipsis.py, visibilitat.py, alcaries.py, noms.py, feines.py
scripts/                        descarregar_mdt/efemerides/textures, preparar_dades, captura,
                                exercici_fotograma, validar_model, validar_ombra, prova_vistes,
                                comparar_nasa, validar_horitzo, validar_ombres_relleu, prova_controls,
                                descarregar_edificis, validar_edificis, prova_trajectoria,
                                prova_caminar, prova_obstacles, descarregar_ortofoto, prova_ortofoto,
                                prova_cel, prova_mosaic, prova_llocs
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
  - **O3** On es veurà l'eclipsi (D79, proposta): O3.1 circumstàncies de cada eclipsi, O3.2 mapa estàtic del
    relleu, O3.3 edificis i terrats, O3.4 mapa dinàmic, O3.5 aplicació de planificació, O3.6 afluència (opcional).
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

### F15 — Ratolí i navegació de la càmera (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 15.1 | C | La captura del ratolí es desfeia a cada fotograma (slimgui); Tab captura/allibera; el clic esquerre ja no captura; sensibilitat única | `VALIDAT` (27/10: l'equip ha provat el Mouse Look amb el ratolí real i "funciona bé") |
| 15.2 | C | Límits de la mirada comuns (rumb normalitzat, inclinació ±89°, valors no finits rebutjats) a tots els camins, també els botons | `FET` |
| 15.3 | N | "Mirar l'eclipsi": orienta la càmera activa cap al Sol una sola vegada | `FET` |
| 15.4 | N | Vista guiada fins a l'espai (`dades/trajectoria.py`, `basecode/camera_guiada.py`, tecla G) | `FET` |
| 15.5 | N (prova) | `scripts/prova_trajectoria.py`; `scripts/prova_controls.py` ampliat | `FET` |
| 15.6 | doc | README, pla i web | `FET` |

**Problemes trobats (diagnòstic abans de canviar res).**
- *La captura no durava.* `GlfwRenderer.new_frame()` de slimgui crida `_update_mouse_cursor()`, que fa
  `glfw.set_input_mode(CURSOR, CURSOR_NORMAL)` a cada fotograma sense mirar si el cursor està desactivat (el
  backend en C++ d'imgui sí que ho comprova). Reproduït: just després de capturar, `DISABLED`; després de
  `new_frame()`, `NORMAL`. Per tant el cursor tornava a ser visible i topava amb les vores. La prova de la F12
  no ho podia veure perquè substituïa `glfw.get_cursor_pos`. Correcció: `ControlRatoli` embolcalla aquest pas
  del renderer i el salta mentre és capturat (no es toca la biblioteca).
- *Tab bloquejava el teclat.* imgui fa servir Tab per passar d'un control al següent; després del primer Tab,
  `want_capture_keyboard` era cert i el programa deixava de rebre P, V, W... Correcció: els controls del panell
  i de la barra de temps es marquen `NO_TAB_STOP`.
- *Clic per capturar.* El clic esperava 0,3 s (temps del doble clic) i, si es canviava de finestra en aquell
  interval, la captura pendent no es cancel·lava. Ara el clic esquerre no captura.
- *Sensibilitat dispersa:* 0,12 (capturat), 0,2 (arrossegar a l'exploració), 0,15 (arrossegar a l'observació).
  Ara una sola constant de 0,15°/punt, proporcional al camp de visió.
- *Mirada sense límits als botons:* `veure_ombra_des_de_lespai` i `CameraObservador.mirar` assignaven la
  inclinació sense limitar-la; l'exploració permetia ±89,9°.
- *Prova del panell (ja fallava abans de la F15):* el fitxer local `imgui.ini` deixa el panell plegat
  (`Collapsed=1`); la prova ara el força obert. A la finestra real, si el panell surt plegat, s'obre amb la
  fletxa del títol.
- La càmera orbital (`camera_orbital.py`) només la fan servir `scripts/captura.py` i l'exercici 1.0: no s'ha tocat.

**Ordre del bucle (sense canvis):** `poll_events` → Esc → `new_frame` d'slimgui (ara sense tocar el cursor
capturat) → `imgui.new_frame` → `render()`: teclat (Tab, V, G, P, fletxes amb `dt`) → temps → astres →
`ControlRatoli.fotograma()` (un sol delta per fotograma, sense `dt`; la roda va al panell o a la càmera, mai
a tots dos) → càmera → dibuix → panell.

**Vista guiada.** Punts clau del progrés s: 0 (a 300 m del punt, recta de 70° d'elevació d'esquena al Sol),
S1 = 0,3 (100 km per la mateixa recta: per sobre del pla tangent al punt, fora de la Terra), S2 = 0,55 (la Terra
a 30.000 km, entre la vertical del punt i el Sol), S3 = 0,8 (de costat respecte de la recta Terra–Lluna, a 1,6
vegades la seva distància del punt mig) i 1 (a 1,2·10⁶ km, a 40° de la direcció oposada al Sol: hi caben la
Terra, la Lluna i el Sol). De S1 a 1, altura en escala logarítmica i direcció (des del centre de la Terra) girant
en proporció a l'altura guanyada. La primera versió interpolava el radi i girava la direcció linealment: a
~100 km d'altura la càmera escombrava milers de km de costat (12,9 % de la distància per mostra, gir de 5°); la
prova de continuïtat ho va detectar. Mirada de referència: cap al punt fins a S2, cap al punt mig Terra–Lluna a
S3 i a mig camí entre la Terra i el Sol al final; "amunt" transportat amb el gir mínim. La mirada de l'usuari és
(gir, inclinació) respecte d'aquesta referència i la base es construeix perpendicular (cap singularitat de
`lookAt`). Salvaguardes, que no acumulen res: 20 m sobre el terreny dibuixat i fora de 1,5 radis lunars.

**Comprovat automàticament.**
- `python scripts/prova_trajectoria.py` (~17 s, sense finestra; 6 ubicacions × 16 hores d'ancora × 4.001 valors
  del progrés): fins a S1, ≥ 282 m per sobre del pla tangent; des de S1, ≥ 6.463 km del centre de la Terra;
  ≥ 129 radis lunars de la Lluna i ≥ 217 radis solars del Sol; ≥ 48 milions de km de les parets del cub (no fa
  servir el límit); continuïtat ≤ 0,8 % de la distància per mostra, gir de la mirada ≤ 0,31°, "amunt" sense
  inversions; el punt visible fins a S2; enquadraments a S2 (Terra sencera, 19,3° de 25°), S3 (17,4°) i final
  (19,9°); anada i tornada amb 200 passos fraccionaris exacta; `orientacio`/`angles_cap_a` inversos; ±89°
  finits i perpendiculars; `limitar_orientacio`.
- `python scripts/prova_controls.py`: tot correcte (vegeu la llista de la secció 3 i la secció 7 de l'script).
- Regressions: `prova_vistes.py`, `validar_horitzo.py`, `validar_ombres_relleu.py --totes` i
  `validar_edificis.py`, tot correcte.

**Inspeccionat visualment** (`captures/proves/guiat_*.png`, Vic al màxim): a prop (edificis i carrers, foscos
pel màxim de l'eclipsi i el Sol baix); la Terra a S2 (cara de dia a dalt; el punt, a la part fosca, prop del
terminador); a S3 la Terra (~15 px) i la Lluna (~4 px); al final el Sol (~16 px) i la Terra com un creixent
(~6 px); la Lluna, amb la cara fosca, no es distingeix. El panell dibuixat amb la vista guiada i l'avís de
captura.

**Provat per l'equip:** encara no. Proves manuals (finestra real, ratolí i trackpad físics):
1. Tab: el cursor desapareix i moure el ratolí gira la mirada sense topar amb la vora, durant estona; Tab o Esc
   l'alliberen; Esc un altre cop tanca. Clic dret a l'escena també captura.
2. Cmd+Tab amb el ratolí capturat i tornar: queda alliberat i la mirada no salta.
3. Amb el cursor lliure: el panell funciona, arrossegar gira, el doble clic (explorar) tria el punt.
4. G: vista guiada mirant el punt; roda i dos dits fins a la vista ampla i tornada; Recentrar; P durant la
   vista guiada (la càmera no es mou); canviar d'ubicació des de la llista.
5. "Mirar l'eclipsi" a les tres vistes.
6. Si la sensibilitat de 0,15°/punt és còmoda (es canvia a `basecode/control_ratoli.py`).

**Limitacions.** A escala real, des de l'espai els astres són petits i amb el Sol al camp la Terra és un
creixent (D57). La trajectòria no segueix els astres si l'hora canvia (D56). La captura real del cursor
continua sense poder-se provar amb la finestra amagada (macOS no hi aplica el cursor desactivat sense focus):
la prova comprova el mode que GLFW té guardat, no el comportament del sistema. El moviment "raw" no és
disponible a macOS. L'exploració lliure manté la seva roda (avançar en la direcció de la mirada).

### F16 — Caminar sobre el relleu (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 16.1 | C | Vol lliure: la combinació de tecles es normalitza (W+D anava √2 més ràpid) | `FET` |
| 16.2 | N | Mode Caminar: moviment relatiu a la càmera, seguiment del relleu, subdivisió, vores, entrada | `FET` |
| 16.3 | C | Teclat: sense focus o amb un control del panell actiu, W A S D no mouen la càmera | `FET` |
| 16.4 | N (prova) | `scripts/prova_caminar.py`; comparacions de posició més estrictes a les proves | `FET` |
| 16.5 | doc | README, pla i web | `FET` |

**Què ja funcionava.** `CameraExploracio.moure()` ja calculava el desplaçament horitzontal amb la base local
(est, nord, amunt) del punt i el rumb, sense fer servir la inclinació: mirar amunt o avall no feia volar.
El Mouse Look (F15) no s'ha tocat.

**Què faltava.** (1) La diagonal no es normalitzava: W+D anava a √2 de la velocitat. (2) La velocitat
creix amb l'altura (`max(20 m/s, 0,8 × altura)`): a terra, 20 m/s. (3) Només hi havia `no_sota_terra`: en
pujada la càmera s'enfilava, però en baixada quedava flotant (mesurat: 20 m de baixada en vol lliure, 15 m
per sobre del terra). (4) `altitud_terra_km` retorna 0 al mar i fora d'Espanya, i no distingeix on no hi ha
relleu. (5) Sense focus o amb un control del panell actiu, el teclat continuava movent la càmera.

**Implementació** (`basecode/camera_exploracio.py`):
- `caminar_pas(endavant, dreta, dt, correr)`: entrada normalitzada; distància = 1,5 m/s (× 3 amb Shift) ×
  dt; es fa en passos de 0,5 m com a molt (el MDT és de 5 m). A cada pas, la posició horitzontal nova (base
  local del punt on es és, ECEF en float64) es posa a 1,7 m sobre el relleu **dibuixat** en aquell punt
  (`app.altitud_caminable_km`: els mateixos triangles que la GPU, amb l'exageració i les transicions entre
  nivells, igual que els ulls de l'observador). Sense suavitzat: l'altura és la de la superfície (contínua),
  i per tant no pot penetrar-la.
- On no hi ha relleu de terra (mar o sense dades, amb la mateixa màscara que el shader, `Terrain.es_terra`),
  el pas no es fa: la càmera s'atura a l'últim punt bo i el panell ho indica.
- `seguir_terra()` a cada fotograma caminant: si el relleu canvia (exageració, zona de detall que es carrega o
  es descarrega), els ulls el segueixen.
- `entrar_caminar()`: baixa o puja en vertical (sense moure's en horitzontal) si la càmera és a menys de 5 km
  sobre el relleu; si no, no fa res i el panell ofereix l'acció explícita "Caminar des del punt d'observació".
- Caminant, E/Q i la roda no fan res. Els botons que mouen la càmera d'exploració: triar una ubicació de la
  llista la posa als ulls del punt nou (continua caminant); "Veure l'ombra des de l'espai" passa a vol lliure.
- Teclat (`main.py`): sense focus (`ControlRatoli.focus`) o amb `imgui.is_any_item_active()`, W A S D no es
  processen; `want_capture_keyboard` ja ho impedia mentre s'escriu. El `dt` del programa ja es limita a 0,1 s.

**Comprovat automàticament** (`python scripts/prova_caminar.py`, ~30 s, programa real amb finestra amagada):
- 6 rumbs × W/S/A/D: direcció exacta (error 0,000°), 1,5 m per segon, la mirada no canvia; mirant a −80°, 0° i
  +80°, el mateix desplaçament; W+D = 1,500 m/s a 45°; Shift 4,5 m/s.
- 2 s a 30, 60 i 144 FPS: 3,0000 m en tots tres casos; un fotograma de 5 s avança 15 cm (dt limitat).
- Pujant (+91 m) i baixant pel pendent més fort a prop de Picos, 1.500 fotogrames: ulls a 1,700000 m.
- Un pas de 30 s corrent en una sola crida (135 m): 270 passos, el camí queda ≥ 1,64 m sobre el relleu; la
  recta directa hi quedaria 13 m per sota.
- Sortint de la zona de 5 m cap al relleu de 200 m: just a la frontera, 0,5 cm de diferència en 1 cm (el
  pendent, cap esglaó); l'Escala cap a l'est: s'atura a la costa (354 m) sense entrar al mar.
- Entrar des de 2,9 km: baixa en vertical (0 mm en horitzontal); des de l'espai, no fa res i ho diu.
- Sense moviment residual en deixar W, canviar de mode o d'ubicació; sense focus W no mou; E/Q i la roda no
  mouen caminant; l'exageració ×3 i tornar a 1, els ulls la segueixen; amb un control del panell actiu, W no mou.
- Les proves anteriors feien servir `np.allclose`, que té una tolerància relativa (1e-5 × 6.400 km ≈ 64 m en
  ECEF): podia donar per iguals posicions separades desenes de metres. S'ha canviat per una distància
  explícita (1 µm) a `prova_caminar.py`, `prova_controls.py` i `prova_vistes.py`.

**Provat per l'equip:** encara no. Proves manuals: (1) Explorar → Caminar a Picos i Vic: W A S D, Shift, mirar
amb el ratolí capturat mentre es camina; (2) baixar i pujar un pendent fort (cap salt ni tremolor); (3) a
l'Escala, caminar cap al mar; (4) Cmd+Tab amb W premuda; (5) des de l'espai, "Caminar" (missatge) i "Caminar des
del punt d'observació"; (6) si 1,5 m/s i ×3 són còmodes (`VELOCITAT_CAMINAR_M_S`, `FACTOR_CORRER`).

**Limitacions.** Els edificis es travessaven (resolt a la F17). Sense salt ni gravetat. Els
pendents no limiten el pas (es pot pujar un cingle). Lluny del punt d'observació el relleu és el de la graella de
la zona (~20 m) o el de 200 m: es camina sobre la superfície que es dibuixa, no sobre el MDT de 5 m. El rumb es
manté respecte del nord local (en distàncies llargues, una loxodròmica).

### F17 — Edificis com a obstacles i punts d'observació exteriors (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 17.1 | C | Punts d'observació fora dels edificis (referència i posició efectiva) | `FET` |
| 17.2 | N | Col·lisions caminant i en vol lliure; recuperació (`dades/obstacles.py`) | `FET` |
| 17.3 | N (prova) | `scripts/prova_obstacles.py`; ajustos de proves de relleu (amaguen els edificis) | `FET` |

**Causa (comprovada).** Les coordenades de l'ajuntament de Cerdanyola (geocodificador de l'ICGC: dona la posició
de l'edifici) cauen dins d'una part del Catastro de 4 plantes, a 7 m de la façana. Els ulls quedaven dins del
prisma: al voltant, les façanes per dins; a dalt, la coberta. Mesurat mirant amunt des d'aquell punt: 0 % de cel.
El mateix passava a l'ajuntament de l'Escala, al de Montmeló i a la plaça Cívica de la UAB (ja ho deia D53); Vic
i Picos no.

**Punts d'observació (D60).** `Obstacles.punt_exterior`: dins d'un quadrat de 300 m, l'espai lliure és el quadrat
menys els contorns eixamplats 3 m (si no n'hi ha, 1,5 i 0,5 m); se'n queden els trossos que toquen la vora del
quadrat (carrers i places connectats; un pati tancat no) i s'agafa el punt més proper. Resultats (efectiu, a 3 m de
les façanes): l'Escala a 13,7 m, Cerdanyola a 10,6 m, Montmeló a 8,9 m, UAB a 20,7 m (coincideixen amb les
propostes de la F14 a ≤ 0,5 m); Vic i Picos sense canvis. `Observador` guarda `lat_ref`, `lon_ref` i
`desplacament_m`; el model, el CNIG i la càmera fan servir la posició efectiva. Es fa amb els contorns encara que
els edificis estiguin amagats (el punt no canvia en mostrar-los).

**Col·lisions (D61).** Els contorns són prismes verticals, per tant tot es fa al pla horitzontal (EPSG:25830, m).
`Obstacles.moure`: si cap contorn no és a prop del camí, el pas es fa sencer; si no, en passos de mig radi com a molt
i, a cada pas, el cercle s'empeny fora de les vores que toca (punt més proper de cada contorn, `shapely`), fins a 6
iteracions per resoldre les cantonades còncaves. Com que cap pas supera el radi, el centre no pot passar a l'altre
costat d'una paret; si el resultat no és vàlid, el pas no es fa. Caminant, radi 0,3 m (`RADI_COS_M`), dins dels
passos de 0,5 m de la F16. En vol lliure (`desplacar`), a l'altura dels edificis, en passos de 0,5 m: radi 0,5 m
contra les parts de coberta més alta que la càmera menys 0,5 m; si un pas baixa sobre una coberta venint de dalt,
es queda a 0,5 m del terrat (amb 1 cm de tolerància perquè els arrodoniments no la facin obstacle). La roda també hi
passa. Recuperació (`sortir_dels_edificis`), a cada fotograma d'exploració: si la càmera és dins o enganxada a una
façana, va al punt exterior més proper. Passar a caminar damunt d'un edifici baixa al carrer més proper i ho diu.
Contorns a la memòria cau dels edificis (WKB, `VERSIO_MALLA` = 3); construir l'índex del Vallès (49.797 parts): 0,05 s.

**Comprovat automàticament** (`python scripts/prova_obstacles.py`, ~55 s):
- Geometries de prova: s'atura a 0,300 m de la paret; en diagonal hi llisca; un pas de 100 m no la travessa;
  passa la cantonada convexa; a la còncava, 66 fotogrames empenyent-hi, quiet (cap vibració); no passa per una
  escletxa de 0,2 m ni entre dos edificis que es toquen per una cantonada; el punt exterior d'un edifici amb pati
  és al carrer.
- Contorns reals del Vallès: 3.000 moviments a l'atzar de fins a 50 m d'un cop (1.052 contra edificis): cap acaba
  dins ni a menys de 0,3 m. Temps: mediana 0,02 ms; percentil 95, 22 ms (moviments de desenes de metres;
  caminant, un fotograma avança com a molt 0,45 m).
- Programa real: a les sis ubicacions, els ulls a l'exterior i mirant amunt 72–100 % de cel (des de la referència
  dins de l'edifici: 0 %); caminant cap a l'ajuntament de Cerdanyola de cara i a 40°, 30 s corrent: topa i queda a
  0,300 m; un pas de 135 m: cap punt a menys de 0,3 m; en vol lliure no s'entra per la façana, baixant amb Q
  s'atura a 0,50 m de la coberta i s'hi pot passar per sobre; recuperació; passar a caminar damunt de l'edifici;
  doble clic dins d'un edifici; edificis amagats i tornats a mostrar.
- Regressions: dues proves de relleu fallaven per l'aparició dels edificis (la UAB, des del punt nou, veu un edifici
  alt pujant; a l'Escala, caminant cap al mar es topa amb un edifici abans): ara aquelles comprovacions de relleu
  amaguen els edificis, com ja feien `validar_horitzo.py` i `validar_ombres_relleu.py`.

**Provat per l'equip:** encara no. Proves manuals: (1) triar les sis ubicacions: es veu el cel i el panell diu on són
els ulls; (2) caminar contra façanes, en diagonal i corrent, i resseguir-les; cantonades i carrers estrets; (3) vol
lliure baixant sobre un terrat i passant-hi per sobre; (4) doble clic sobre un terrat; (5) dir si 3 m de marge
per als punts és adequat.

**Limitacions.** Només les parts del Catastro (2 km al voltant dels punts) fan d'obstacle; voladissos, porxos i
passatges sota edificis no existeixen al model (prismes). Els edificis amagats no són obstacles. Un pas sobre el relleu
pot pujar un desnivell gran (no hi ha límit de pendent).

### F18 — Prova d'ortofoto a Vic (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 18.1 | dades | Fonts verificades; `scripts/descarregar_ortofoto.py`; `data/ortofoto/` (ignorada pel Git) | `FET` |
| 18.2 | N | Ortofoto com a color base del terra de la zona (`terrain.py`, `terrain.frag`), interruptor a Avançat | `FET` |
| 18.3 | N (prova) | `scripts/prova_ortofoto.py`: alineació, memòria, temps per fotograma, captures | `FET` |

**Fonts verificades (27/10/2026).** PNOA màxima actualitat (IGN), WMS: el GetCapabilities diu `AccessConstraints`
"CC BY 4.0 scne.es" i `Fees` "No se aplican condiciones"; EPSG:25830 disponible; màxim 4096 px per petició. A Vic:
vol de juliol de 2024, 0,25 m, "Ortoimagen verdadera: NO". ICGC (25 cm, 2009–2025): disponible, però el
GetCapabilities diu "copyright" i la pàgina de condicions no especifica la llicència d'aquesta capa: no es fa servir.

**Dades.** `vic_5m.tif`: tota la zona amb la graella del MDT (4000 × 4000 px, 5,3 MB); `vic_vic_0p5m.tif`: 4 × 4 km
a 0,5 m (8000 × 8000 px, 19,8 MB). Descàrrega: 20,1 MB en 123 s.

**Dibuix.** Al shader del terreny, la foto substitueix la rampa per altitud com a color base; la llum és la mateixa
(Sol aparent, ombra de la Lluna, ombres del relleu i dels edificis). La de detall es barreja amb la de la zona al 3 %
de la seva vora. Les dues textures es llegeixen sempre (dins d'un `if` per píxel, el mipmap no estaria definit);
mipmaps i filtre anisotròpic ×16. Els samplers sempre tenen una textura (1 píxel si no n'hi ha).

**Comprovat automàticament** (`python scripts/prova_ortofoto.py vic`): alineació foto–Catastro (vores, 8.294 parts
en 1,5 × 1,5 km): màxim a +0,5 m est, +0,5 m nord (1 píxel); memòria de textura calculada: 85 MB (zona) + 341 MB
(detall) amb RGBA8 i mipmaps (el controlador no la informa; és una estimació); carregar la zona amb l'ortofoto,
el relleu i els edificis: 2,5 s; temps per fotograma (finestra amagada 1280 × 860): 8,7–11,0 ms amb foto i
8,7–10,6 ms sense (+0,0–0,5 ms).

**Inspeccionat visualment** (`captures/proves/ortofoto_vic_*.png` i `ortofoto_vic_lamina.jpg`): des de 400 m i 3 km
es reconeixen la plaça Major, les Rambles, els carrers i els camps; al carrer, la plaça (sauló) és la real però
borrosa; a 60 m, a la vora de la plaça es veuen franges de façanes fotografiades (inclinació dels edificis); a 20
km, frontera visible entre la zona i el color per altitud; al màxim de l'eclipsi, tot molt fosc (amb foto i sense),
i les ombres de la foto no s'hi distingeixen.

**Provat per l'equip:** encara no. Proves: caminar per la plaça Major i carrers del voltant, volar de 50 m a 20 km,
canviar l'hora (16:30, ~19:45 i el màxim) i l'interruptor d'Avançat; valorar les ombres de la foto i decidir si
s'estén a la resta de zones (l'Escala, Vallès amb tres punts, Picos).

**Limitacions.** Ombres del migdia del vol; edificis inclinats a la foto; al carrer, 0,5 m per píxel és borrós i els
arbres i cotxes són taques planes; frontera de color al límit de la zona; 341 MB de textura per a cada detall de
4 × 4 km (al Vallès, si es carreguessin els tres detalls alhora, el triple: ara només es carrega el del punt).

### F19 — Cel i llum de l'atmosfera (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 19.1 | N | Model d'atmosfera (`dades/atmosfera.py`) i cel (`basecode/cel.py`, `shaders/cel.*`) | `FET` |
| 19.2 | C | Llum del Sol amb el color que li dona l'atmosfera, llum del cel i boira del color de l'horitzó (terreny, Terra, edificis, disc del Sol) | `FET` |
| 19.3 | N (prova) | `scripts/prova_cel.py` | `FET` |

**Abans.** El cel era un color pla (`COLOR_CEL` barrejat amb un to de posta i un de nit segons l'elevació del Sol i
la part tapada), la boira era d'aquest color i la llum del terreny era blanca.

**Model** (detalls i aproximacions a `dades/atmosfera.py`; el shader n'és una còpia). Dispersió simple (Nishita):
Rayleigh (β = 5,8 / 13,6 / 33,1 ·10⁻³ km⁻¹, escala 8 km), Mie (escala 1,2 km, g = 0,8) i absorció de l'ozó
(capa de 10–40 km); atmosfera fins a 80 km; 12 mostres per raig, més denses a prop de la càmera (amb mostres
uniformes l'horitzó sortia groc: l'aire proper, que conserva el blau, quedava mal representat), i 4 cap al Sol;
el raig comença a l'altitud de la càmera; l'ombra de la Terra es té en compte. A cada mostra, la part visible
del Sol des d'aquell punt (eclipsi). Compressió dels colors: meitat per canal i meitat sobre la lluminositat,
més un 15 % de desaturació (cap canal saturat sol). Il·lustratiu: exposició; adaptació de l'ull a l'eclipsi
(×visible⁻⁰·⁶, com a molt ×16); llum mínima dins de l'ombra (0,3 %, en lloc de la dispersió múltiple: sense,
el cel de la totalitat era negre); color del cel ambient.

**Integració.** El cel es calcula abans del fotograma en una textura petita (com a molt 400 px d'amplada) i es
copia a la pantalla amb la profunditat màxima i el test "<=", sense escriure profunditat: només on no hi ha res.
El color de la llum del Sol (transmissió per la massa d'aire de Kasten i Young) i el del cel es calculen per
vèrtex al terreny i a la Terra (per fragment costava massa); la boira té el color del cel a l'horitzó (model
de la CPU, cap al Sol i al contrari, recalculat si l'hora canvia o la càmera es mou) i la seva densitat decreix
amb l'altura de la càmera. El disc del Sol i el halo prenen el color de la llum que arriba a la càmera.

**Comprovat automàticament** (`python scripts/prova_cel.py`): shader = model de la CPU (≤ 0,6/255); amb cel i
sense, els 589.543 píxels d'objectes (Sol, Lluna, terreny, edificis) idèntics; de C1 − 30 min a 20 min després de
la posta a Vic, canvi màxim per minut 3,8/255 al terreny i 13,9/255 al cel, al màxim de l'eclipsi (en passos de
10 s, 1,5–4,0/255: continu); cap píxel de cel amb un canal saturat i un altre fosc; a Picos, a la totalitat el
zenit és fosc i l'horitzó oposat en té més, i en una posta amb el Sol a la mateixa altura el zenit és clar. El
mode pla (`captura.py`) dona la mateixa imatge (0 píxels diferents).

**Inspeccionat visualment** (`captures/proves/cel_*.png` i captures de prova): Vic a les 16:30 (blau, resplendor
blanc al voltant del Sol), parcial (horitzó daurat), màxim (blau fosc i taronja a l'horitzó), posta (vermells);
Picos abans de la totalitat (blau fosc, horitzó encès) i a la totalitat (blau marí, resplendor taronja); la
Terra des de l'espai amb el contorn de l'atmosfera.

**Rendiment** (finestra amagada; varia ±3 ms entre execucions): 1280 × 860, ~14–17 ms per fotograma; 2560 × 1720
(pantalla Retina), ~22–42 ms segons la vista, contra ~25 ms a l'últim commit (F14) a la mateixa vista. Mesurat per
passada (GPU, Retina): cel 2,6 ms; la resta de l'augment ve de la zona de 5 m amb l'ortofoto, la Terra i els
edificis. S'han provat filtre anisotròpic ×8 i cel a 256 px: sense millora mesurable.

**Provat per l'equip:** encara no. Proves: posta i eclipsi des del carrer a Vic i a Picos (mirant el Sol i
d'esquena), des de l'aire i des de l'espai; fluïdesa a la finestra real.

**Limitacions.** Dispersió simple (sense dispersió múltiple: el crepuscle profund és massa fosc i la llum dins
de l'ombra és una constant); Terra esfèrica per al cel; sense estrelles; el color del cel ambient és una funció
de l'elevació del Sol, no del model; l'adaptació de l'ull és una tria visual.

### F20 — Aspecte dels edificis (27/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 20.1 | N | Atributs de malla (posició a la façana, llargada, part), triangles cap a fora (`VERSIO_MALLA` = 5) | `FET` |
| 20.2 | N | Façanes procedimentals amb les plantes reals; cobertes amb el color de l'ortofoto (`colors_cobertes`) | `FET` |
| 20.3 | C | Descart de cares del darrere (`CULL_FACE`) i càlculs per vèrtex | `FET` |

**Façanes** (estètic): un color per edifici d'una paleta de sis tons mediterranis; finestres d'1,2 m cada 3,2 m,
centrades a cada costat, una fila per planta (plantes del Catastro, 3 m), més altes a la planta baixa; a més de
400 m o quan una finestra ocupa menys d'un parell de píxels, el seu color mitjà (sense parpelleig). **Cobertes**
(dada real): la mediana de fins a 9 punts de l'ortofoto dins de cada contorn (detall de 0,5 m o zona de 5 m) —
100 % de les parts de Vic. Fora de l'ortofoto, un color de teula o de terrat per edifici.

**Rendiment.** Escriure `gl_FragDepth` impedeix que la GPU descarti abans els fragments tapats: totes les façanes
de darrere executen el shader. Amb els triangles orientats cap a fora (comprovat: 100 % de les cobertes cap amunt
i 3.000 de 3.000 façanes cap a fora) es descarten les cares del darrere, i el color de la part i la boira es
calculen per vèrtex: els edificis han passat d'~11 a ~5,6 ms de GPU (Retina; 4,7 ms abans de les textures).

Conseqüència: des de dins d'un edifici ja no es veu la coberta per dins (es veu a través); la càmera no hi pot
quedar (F17). `prova_obstacles.py` ara comprova que la referència dels quatre punts desplaçats és dins d'un
edifici en lloc de mirar amunt des d'allà. Regressions: totes les proves correctes; mode pla, 0 píxels diferents.

**Provat per l'equip:** encara no. **Limitacions:** finestres i colors de façana inventats; sense balcons ni
portes; les cobertes són planes amb un sol color; els edificis no reben ombres.

### F21 — Fotografia aèria a tot arreu i controls com Google Earth (28/10/2026, petició de l'equip)

| Tasca | Tipus | Canvia | Estat |
|---|---|---|---|
| 21.1 | N | Teselles Web Mercator: fonts, memòria cau al disc, descàrrega en fils (`dades/teselles.py`) | `FET` |
| 21.2 | N | Mosaic de nivells de zoom a la GPU (`basecode/mosaic.py`, `shaders/mosaic.glsl`) al terreny i a la Terra | `FET` |
| 21.3 | N | Controls de la vista aèria: arrossegar, orbitar, roda cap al cursor, inèrcia (`camera_exploracio.py`) | `FET` |
| 21.4 | C | Doble clic → primera persona; edificis segons la vista (`main.py`, `ui.py`) | `FET` |
| 21.5 | C | Boira de la Terra i boira amb la densitat del camí (D70) | `FET` |
| 21.6 | N (prova) | `scripts/prova_mosaic.py`; adaptacions de `validar_edificis.py` i `prova_controls.py` | `FET` |

**Abans.** Fora de les zones de detall el terra tenia el color segons l'altitud (i la Terra, la textura de 2.048 px
de la NASA, ~20 km per píxel); la fotografia aèria només hi era a Vic (F18, fitxers descarregats a mà).

**Com funciona** (un "clipmap", explicat a la web, O2). Les imatges es demanen en teselles de 256 px de la
quadrícula Web Mercator (la de Google Maps i del WMTS de l'IGN): al zoom z, 2^z × 2^z teselles; z = 19 són
~0,22 m per píxel a Catalunya. Per a 12 zooms alhora (del que demana l'altura de la càmera cap avall) hi ha una
finestra de 8 × 8 teselles centrada a sota de la càmera, cada una en una capa d'una `TextureArray` (2.048² px,
~270 MB amb mipmaps). Cada zoom va sempre a la capa z mod 12 i cada tesella a la posició (x mod 8, y mod 8):
quan la càmera es mou o puja, només s'escriuen les teselles noves. El shader tria, per a cada píxel, el nivell
amb un texel per píxel de pantalla (barrejant dos nivells, sense salts) i, si aquella tesella encara no ha
arribat, fa servir la del nivell següent, menys detallat: la imatge sempre és contínua i es va afinant.
Precisió: la coordenada Mercator de cada vèrtex es calcula a la CPU en doble precisió i es passava partida
(alta + baixa en float32); el shader en restava la de la càmera (error ~10⁻⁴ píxels a z = 19 a la CPU; restant
directament en float32 serien ~4 píxels). *A la GPU no va funcionar al pegat de 5 m (vegeu la F22): ara es passa
relativa a l'origen de cada terreny (D71).* A la Terra es calcula per fragment (la diferència de longitud amb un sol `atan`).

**Fonts** (`data/FONTS.md`): PNOA màxima actualitat (IGN) a partir de z = 12; on el PNOA no té imatge (color lila
uniforme) i per sota de z = 12, Sentinel-2 cloudless 2020 (EOX). Per sota de z = 12 el PNOA barreja mosaics
(món molt saturat, mar gris a z = 9–10, mar buit a z = 11) i en canviar de nivell el mar feia un cercle al voltant
de la càmera. Les descàrregues van en 8 fils; el bucle de dibuix només puja les teselles ja descodificades (amb
les reduccions per als mipmaps), com a molt 4 ms per fotograma. Sense connexió: colors d'abans, sense errors.
**Contradicció registrada:** CLAUDE.md deia que la descàrrega progressiva era una ampliació per a més endavant;
la petició explícita de l'equip (28/10) la demana ara (D66).

**Controls (D67, D68, D69).** Vol lliure, cursor lliure: arrossegar agafa el terra pel punt clicat (la càmera
gira al voltant del centre de la Terra perquè el raig del cursor hi torni a passar); en deixar-lo anar en
moviment, inèrcia que s'atura en ~1 s; Shift + arrossegar o botó del mig, orbitar al voltant del punt del centre
de la pantalla (sense passar sota el seu horitzó ni mirar amunt); roda, apropar-se al punt del cursor (×0,74 per
pas, repartit en uns quants fotogrames); si el cursor és al cel, com abans. Doble clic: primera persona al punt.
Edificis: en primera persona sí, a la vista aèria no (opcions al panell).

**Comprovat automàticament** (`python scripts/prova_mosaic.py`, 19 condicions): tesella de Vic a z = 17 igual que
la de l'IGN; precisió alta + baixa; reduccions; sense xarxa no hi ha excepcions; alineació del mosaic contra
l'ortofoto de Vic de la F18 (un altre camí, WMS en UTM): 0,10 m (1 píxel = 0,43 m); Terra contra terreny al
delta de l'Ebre: 4,8 m (1 píxel = 3,3 m; la Terra calcula la latitud en float32, ~1 m, i la seva malla és plana
entre vèrtexs); arrossegar deixa el punt a 0,7 px del cursor; la roda el deixa a 0,1 px i la distància es
multiplica exactament per 1,35⁻²; orbitar el deixa a ~1,3 px del centre i no passa sota el terra; la inèrcia
s'atura; doble clic → primera persona mirant on mirava la càmera; edificis segons la vista. Regressions: totes
correctes (`prova_controls`, `prova_vistes`, `prova_obstacles`, `prova_caminar`, `prova_trajectoria`,
`prova_cel`, `validar_edificis`, `validar_horitzo`, `validar_ombres_relleu --totes`); exercici 1.0 coincideix;
mode pla 0 píxels diferents. `validar_edificis.py` fa servir els edificis també a la vista aèria i desactiva la
fotografia (escena quieta); `prova_controls.py`: el picking de prova accepta un píxel.

**Inspeccionat visualment:** la vista de l'enllaç de Google Earth (Vic a 1,45 km, 35°), Catalunya a 20 km, la
Cerdanya a 6 km, la costa de l'Empordà a 3 km, Montserrat i el Pirineu des del terra, Vic des del carrer amb
edificis, la Terra des de l'espai. Captures a `captures/proves/mosaic_*.png`.

**Rendiment** (finestra amagada): 1280 × 860, 5–11 ms; 2560 × 1720, Vic des del carrer 26 ms (20 sense el
mosaic), Pirineu des de 6 km 12 ms (9 sense). Primera visita a un lloc: ~770 teselles, ~35 s fins a la resolució
màxima (es veu de seguida una imatge borrosa que s'afina); des del disc, ~2 s.

**Provat per l'equip:** encara no. Proves: (1) explorar des de l'aire amb el ratolí (arrossegar, Shift, roda) i
amb les tecles; (2) doble clic en un poble i en una muntanya fora de les zones; (3) la continuïtat en moure's de
pressa; (4) costa i mar; (5) fluïdesa a la finestra real.

**Limitacions.** El relleu fora de les zones de detall continua sent el de 200 m (Google Earth en té de més
detall): de prop, la foto es veu sobre un relleu suau. Els edificis només hi són a les zones de detall. Les
fotos tenen les ombres i la llum del dia del vol. Al mar hi ha diferències entre fonts (reflexos del Sol a les
fotos del PNOA, Sentinel-2 molt fosc). La memòria cau no té límit de mida (es pot esborrar `data/cache/teselles`).
El relleu de França i Portugal és pla (la Terra), amb fotografia.

### F22 — Correccions de la F21, Lluna, Sol i atmosfera vista des de l'espai (28/10/2026, petició de l'equip)

**Prova de l'equip de la F21 (28/10).** Viatjant des de Vic fins a l'Escala, doble clic, primera persona i V: de
tornada a la vista aèria, el mapa es veia esmicolat (Image #6); la Terra des de fora, rància a les vores; la Lluna
de prop, poc detallada; el Sol, massa pàl·lid ("més vermell, com foc"). Pregunta: si la llum de l'eclipsi parcial
a l'Escala és correcta.

**22.1 Foto esmicolada al pegat de 5 m** (`FET`). *Causa:* després del doble clic, al voltant del punt nou hi ha el
pegat de 5 m (un vèrtex per píxel del MDT). La coordenada Mercator de cada vèrtex era correcta a la CPU (error
10⁻⁷ píxels de z = 19, comprovat llegint el VBO), però a la GPU la suma alta + baixa perdia precisió: la foto es
movia de 1 a 5 píxels (~1 m) d'un vèrtex a l'altre. A la graella general (vèrtexs cada 20 m) l'error era el mateix
però variava a poc a poc i no es notava. Diagnòstic: captura amb el pegat i sense, desplaçament bloc a bloc
(correlació de fase), i el pegat aplanat (l'error hi era igual: no venia del relleu). *Correcció (D71):* la
coordenada de cada vèrtex es guarda relativa a l'origen del terreny (`Terrain.origen_merc`) i la CPU passa la de
la càmera també relativa (`render_globus`). Atributs a la cache: versió 3. *Comprovat automàticament:*
`prova_mosaic.py` (nova condició): 9 blocs del centre, pegat contra graella, com a molt 0,1 px.
També: punts taronja dins de les ombres fosques (el color "sense dades" del PNOA coincidia amb algunes ombres);
ara només compten les zones sense dades de 7 × 7 píxels o més (`dades/teselles.py`).

**22.2 La Terra des de l'espai** (`FET`). *Vora:* abans hi havia una línia blava d'1–2 píxels sobre el negre (amb
dents de serra, sense antialiasing). Ara hi ha una closca d'atmosfera (`shaders/atmosfera_terra.*`): cada píxel
suma un blau segons la quantitat d'aire que travessa la mirada (poca mirant avall, molta a la vora; per sobre de
la vora s'esvaeix amb l'altura), només al costat de dia, vermellosa al crepuscle. **Il·lustratiu:** gruix de 400 km
i escala de 70 km, molt més que l'aire real (8 km), perquè es vegi de lluny com a Google Earth. *Pol:* la
fotografia s'acabava de cop a 85° i feia un cercle; ara s'esvaeix entre 80° i 84°.

**22.3 La Lluna** (`FET`). Amb autorització explícita de l'equip (84 MB): color de la LRO a 8192 × 4096 (~1,3 km
per píxel) i altituds del LOLA a 16 píxels per grau (`scripts/descarregar_textures.py --alta`; convertits a
`data/textures/lluna_8k.jpg` i `lluna_altitud.npy`, fora del Git). El shader inclina la normal segons el pendent
del relleu (diferències entre veïns, de la mida d'un píxel de pantalla de lluny): els cràters fan ombra prop del
terminador. Llum de Lambert lunar (barreja de Lambert i Lommel-Seeliger, McEwen): la Lluna plena es veu clara fins
a la vora. Corregida la línia fosca de pol a pol (el salt de la coordenada u a la costura disparava el nivell de
mipmap). De molt a prop, cràters petits (cel·les de 4, 1,1 i 0,33 km, més petits que grans) i variació de color:
**il·lustratius**. Sense les dades d'alta resolució, el programa fa servir la textura d'1k. Sense ombres
projectades (només la inclinació de la normal). GPU: ~180 MB més.

**22.4 El Sol** (`FET`, il·lustratiu, D73): soroll fractal deformat per un altre soroll (flames que es mouen),
granulació, vora fosca i vermella (enfosquiment del limbe, físic). Paleta de vermell fosc a groc pàl·lid.
*Correcció després de la prova de l'equip (28/10):* des del terra es veia estrany (una bola de foc al cel). Ara,
des de dins de l'atmosfera, el Sol és un disc blanc que enlluerna (amb el color de l'atmosfera, daurat a la
posta) i l'aspecte de foc només apareix en pujar (barreja segons `app.atmosfera`, de 0 a 60 km).
Inspeccionat visualment des del terra, a 30 km i a 70 km; `prova_cel` i `prova_vistes` correctes.

**22.5 Llum a l'eclipsi parcial (pregunta de l'equip).** Al màxim, a l'Escala (ajuntament), la Lluna tapa el
98,7 % del disc (taula de §10: 98,67 %): queda l'1,3 % del Sol. El model fa: llum directa = part visible del
disc (per àrea); el cel, per a cada punt del raig, amb la part visible des d'aquell punt (l'aire lluny, fora de
l'ombra, en rep més); l'ull s'adapta a la foscor (×visible^−0,6, il·lustratiu). Resultat: llum directa a l'1,3 %,
cel i llum difusa al ~20 % del normal. Que el cel continuï clar i que no hi hagi corona és el que passa: la corona
és ~10⁻⁶ de la brillantor del disc i l'1 % que queda l'enlluerna. *Correcció trobada en revisar-ho (D74):* la
corona començava amb el 0,4 % del disc visible i a Cerdanyola (99,74 %) se'n veia una part; ara només amb menys
del 0,05 %. *Aproximacions:* la part visible es mesura per àrea, sense enfosquiment del limbe (la falç que queda és
a la vora, més fosca: la llum real seria ~0,6 vegades la calculada); sense dispersió múltiple; l'adaptació de l'ull
es tria per a la pantalla. A l'Escala, des de l'ajuntament, el relleu tapa el Sol al màxim (§10, 6,45° contra 3,7°).

**Inspeccionat visualment:** l'Escala abans i després del doble clic (a migdia i a l'hora de l'eclipsi), la Lluna
a 6.000, 1.500, 200, 20 i 3 km, el Sol des de l'espai, la Terra a 8.000, 14.000 i 20.000 km.
**Rendiment:** la Lluna omplint la pantalla, 7–9 ms per fotograma (1280 × 860, finestra amagada).

**Provat per l'equip:** encara no. Proves: (1) el mateix camí Vic → l'Escala → doble clic → V; (2) la Terra des de
l'espai; (3) acostar-se a la Lluna fins a pocs km; (4) el Sol; (5) a Cerdanyola, al màxim, que no surti la corona.

### F23 — Llum de les façanes i llocs nous amb detall (30/10/2026, petició de l'equip)

**Petició.** A la UAB costava reconèixer la plaça Cívica comparada amb Google Earth (Street View): façanes gairebé
negres a l'ombra. Pregunta: si es poden fer servir les imatges de Google (no: D75) i si es poden carregar edificis a
qualsevol lloc amb doble clic (per exemple, viatjant de Cerdanyola a Manresa). Problemes d'espai al disc.

| Tasca | Tipus | Fitxers | Estat |
|---|---|---|---|
| 23.1 | dades | Neteja de caches que el codi actual no llegeix (1,8 GB) | `FET` |
| 23.2 | N | Llum de les façanes (D76): `shaders/edifici.frag`, `basecode/edificis.py` | `FET` |
| 23.3 | reorganització | Peticions al WCS del MDT i descàrrega del Catastro, de `scripts/` a `dades/mdt_wcs.py` i `dades/catastro.py` (els scripts les importen) | `FET` |
| 23.4 | N | Llocs nous amb doble clic (D77): `dades/llocs.py`, `main.py`, `ui.py` | `FET` |
| 23.5 | N (prova) | `scripts/prova_llocs.py`; `prova_controls.py` sense descàrregues | `FET` |

**23.1 Neteja.** Esborrades (es poden regenerar): les caches del globus de versions antigues (`*.globus_*`,
`*.globus2_*`; la vigent és `globus3`), les rajoles del MDT ja convertides en GeoTIFF (`data/cache/rajoles`) i els
derivats de Luarca, Astúries i `PNOA_MDT05_..._0011` (scripts antics). Les malles dels edificis ara es desen
comprimides (`np.savez_compressed`, ~5 vegades menys; llegir-les costa ~0,1 s més): les existents s'han recomprimit
amb el mateix contingut (comprovat array per array). `data/cache`: de 3,6 a 1,9 GB.

**23.2 Llum de les façanes.** *Abans:* llum = 0,30 cel + 0,70 Sol × Lambert; una façana a l'ombra rebia 0,30 del
cel i, sense correcció gamma, es veia gairebé negra. *Ara (D76):* la paret rep el cel segons la part que en veu
(½ si és vertical), la llum reflectida pel terra (albedo 0,25) per l'altra meitat, i el contrast entre cares es
codifica com el veu la pantalla (gamma 2,2), respecte de la llum d'una cara de cara al Sol: la cara més il·luminada
no canvia i, durant l'eclipsi, la llum total baixa igual que al terreny. Les cobertes fan servir els pesos del
terreny (0,25 / 0,75), perquè tenen el mateix color de foto. **Il·lustratiu**: no és un model de radiància.
*Inspeccionat visualment:* plaça Cívica, 18:31 i 13:00, mirant a 141° i 320° (abans i després).
*Comprovat automàticament:* `validar_edificis.py` (20 OK: la fracció del Sol tapada no depèn del color).

**23.4 Llocs nous.** *Com funciona:* en fer doble clic (Explorar), si el punt és a terra a la península i no hi ha
edificis preparats a menys de 500 m (zones de detall: 2 km al voltant dels seus punts; llocs: el seu quadrat),
`dades/llocs.Preparacio` obre un fil que: (1) baixa 6 × 6 km del MDT de 5 m en una petició; (2) busca als canals
ATOM del Catastro els municipis que toquen el quadrat de 2 × 2 km, baixa els seus ZIP, en llegeix només les parts
dins del quadrat i els esborra; (3) desa el relleu i prepara la malla. Mentrestant, l'observador ja és al punt (sobre
el relleu de 200 m) i la barra del temps mostra el pas. En acabar, si l'observador encara hi és, el programa carrega
el lloc des del fil principal (OpenGL) com una zona de detall més. En reproducció s'espera a la pausa (canviaria el
relleu sota l'observador). *Per què ZIP i no WFS:* el WFS per rectangle accepta com a molt ~1 km² per petició i va
tardar 2,5 min per 1 km² del centre de Manresa (24 MB); el ZIP de tot Manresa, 6,6 MB en 20 s (comprovat el 30/10).
*Espai:* Manresa 108 MB (16 de malla, 33 de derivats del relleu, 46 de la cache del globus, 9 del GeoPackage, 4
del MDT), Igualada 97 MB. Com a molt `MAX_LLOCS` = 3: en preparar-ne un de nou s'esborren els més antics (no el
carregat). Fitxers: `data/mdt/llocs/`, `data/edificis/lloc_*.gpkg`, `data/cache/*lloc_*` (ignorats pel Git).
*Temps:* Manresa 53 s, Igualada 39 s (connexió de l'equip).
*Comprovat automàticament:* `prova_llocs.py --xarxa` (10 OK): clau i cobertura, esborrat dels antics (carpeta
temporal), UAB i mar sense lloc nou, Igualada preparada en segon pla (560 fotogrames dibuixats en 40 s), observador
sobre el relleu de 5 m, espera a la pausa. `prova_vistes` (102), `prova_controls` (69), `prova_caminar` (26),
`prova_obstacles` (25) i `validar_edificis` (20), tots OK.
*Inspeccionat visualment:* Manresa i Igualada des dels ulls i des de l'aire.
*Limitacions:* als llocs no hi ha ortofoto descarregada: les cobertes tenen colors de teula o terrat (des de l'aire
amb "Edificis també a la vista aèria", el centre de Manresa es veu vermell uniforme); el terra sí que té la foto del
mosaic. Sense Navarra ni el País Basc (cadastres propis). Un sol lloc es prepara a la vegada. Si es tanca el programa
a mitja preparació, el lloc pot quedar sense malla: es calcula en carregar-lo (més lent la primera vegada).

**Provat per l'equip:** encara no. Proves: (1) la plaça Cívica al vespre: façanes a l'ombra; (2) viatjar de
Cerdanyola a Manresa, doble clic i esperar el missatge de la barra; (3) tornar a Manresa més tard (ha de ser
immediat).

### O3 — On es veurà l'eclipsi: mapa de visibilitat (proposta, 30/10/2026, petició de l'equip)

**Què es vol.** Una aplicació de dades perquè la gent decideixi on anar a veure un eclipsi: un mapa de calor de
com de bé es veurà des de cada punt (turó, carrer o terrat), estàtic al màxim i dinàmic minut a minut, per al
2026 i els dos eclipsis següents a Espanya. Ha de servir també per preveure on s'acumularà la gent.

**El criteri és geomètric, no de llum.** Un punt "veu" l'eclipsi si, en la direcció del Sol, res no tapa el disc:
ni el relleu (turons, muntanyes, també llunyanes) ni els edificis. No s'agafen els punts més alts, sinó els que
tenen el camí lliure cap al Sol. Al màxim no hi ha llum directa (a la totalitat), per això no es pot fer amb la
llum ni amb el mapa d'ombres de dibuix: es calcula l'**horitzó** (l'angle més alt que tapa la vista) en
l'azimut del Sol i es compara amb l'elevació aparent del Sol (amb refracció).

**Els tres eclipsis** (a comprovar amb les nostres efemèrides, F24):
- 12/08/2026, **total**, al capvespre. El Sol al màxim és a −1–24° (banda 1 del CNIG): el relleu ho decideix.
  Ja ha passat; serveix per validar.
- 02/08/2027, **total** al sud de la península, a mig matí. Amb el Sol alt, el relleu tapa poc: hi compten més els
  carrers estrets i la meteorologia.
- 26/01/2028, **anular** (no total: queda un anell de Sol), a la posta. El Sol molt baix: el relleu i els edificis
  tornen a decidir. El model actual no detecta l'anularitat (F24).

**Què ja tenim i es reutilitza.** El model de l'eclipsi per a qualsevol punt (`dades/model_eclipsi.py`);
l'horitzó cap al Sol (`scripts/validar_horitzo.py`) i el perfil dels edificis (`dades/edificis.perfil_edificis`),
comprovats; els MDT (península 200 m, zones de 5 m, llocs nous) i els edificis del Catastro (amb altures
**estimades**, plantes × 3 m); les capes del CNIG dibuixades sobre el terreny i la barra del temps.
**Referència oficial independent:** la capa `terrain_shadows` del CNIG és un mapa estàtic del 2026 al màxim
(només relleu, GMTED2010 a ~200 m, rutina `insol`, en 4 classes). No l'hem fet servir per ajustar res: comparar-
s'hi és una validació independent. El que hi afegim: 5 m (i 1 m amb edificis), terrats, l'evolució en el temps,
els altres eclipsis i l'afluència.

**Mesura feta (30/10):** horitzó en un azimut per a tots els píxels del Vallès a 5 m (6.331 × 5.692 px,
distàncies de 5 m a 20 km, amb curvatura), NumPy: **~20 s**. És un càlcul per fer una vegada i desar.

| Fase | Tipus | Què | Validació | Estat |
|---|---|---|---|---|
| F24 | reorganització + correcció | Eclipsi com a paràmetre (2026, 2027, 2028): efemèrides de JPL Horizons per a cada data (~40 KB cadascuna), anularitat (C2/C3 quan un disc queda sencer dins de l'altre) | Contactes contra el calculador de la NASA en punts de cada eclipsi (com la F11) | `FET` |
| F25 | N | Circumstàncies en graella (~1 km a les zones, 4 km a la península; vectoritzat): contactes, màxim, fase central, Sol (azimut de quadrícula, elevació aparent) | Contra `ModelEclipsi` punt a punt; 2026, contra les bandes del CNIG (pendent) | `FET` |
| F26 | N | Mapa estàtic al màxim (relleu): horitzó per direccions d'1°, prop amb el MDT del terreny i lluny amb 200 m; marge i classes 0–3 com el CNIG | Contra un raig exacte en ECEF; contra `terrain_shadows` del CNIG | `EN CURS` |
| F27 | N | Edificis, arbres i terrats amb **altures mesurades** (D81, D83): LiDAR de l'ICGC a la UAB baixat; falta fer-lo servir al mapa | Contra `perfil_edificis` en punts de prova | `EN CURS` |
| F28 | N | Mapa dinàmic: per píxel, primer i darrer moment amb el centre del Sol visible; a cada instant, el shader hi afegeix la part tapada per la Lluna; marques a la barra | Hores contra el raig exacte minut a minut | `FET` |
| F29 | N | Aplicació: el menú "Mapa de visibilitat" (al màxim, totalitat visible, instant actual); consulta d'un punt i exportació, pendents | Inspecció de captures | `EN CURS` |
| F30 | — | Afluència | Descartada (D80) | — |

**Índex proposat (P17).** Totalitat (o anularitat): segons de la fase central amb tot el disc per sobre de
l'horitzó (0 si no hi ha fase central); a més, la classe al màxim (0–3). Parcial: la part del Sol tapada al
màxim que es pot veure. Definició transparent i explicable: res de pesos inventats.

**Espai (memòria: disc limitat).** Circumstàncies d'Espanya a ~1 km: desenes de MB per eclipsi. Mapa estàtic de la
península a 200 m: ~50 MB (int16). Zones: a 5 m ~70 MB per zona i eclipsi, a 10 m ~18 MB (P16). Dinàmic: 2 hores
per píxel (2 × uint16) ~6 MB per zona a 25 m. Es calcula la primera vegada que es demana una zona i es desa
(comprimit, a `data/cache/`, amb límit). Pressupost proposat: < 300 MB en total.

**Limitacions previstes.** Sense arbres (el MDT és terra nu; el MDS del LiDAR és l'estudi de §9). Altures dels
edificis estimades. Fora d'Espanya el MDT val 0 (muntanyes del Marroc o de França: no tapen). Sense refracció
terrestre (D18). Sense meteorologia, que en un eclipsi real decideix tant com el relleu (es podria afegir la
probabilitat climatològica de núvols, O1.11, font a verificar). L'afluència és un model, no una mesura.

**Proposta d'ordre.** F24 → F25 → F26 (mapa del 2026 comparat amb el CNIG: la primera evidència forta) → F28 →
F27 → F29, i F30 si l'equip ho decideix.

#### Fet el 30/10 (F24, F25, F26, F28 i menú)

**F24.** `dades/eclipsis.py`: registre dels tres eclipsis (data, tipus, interval de les efemèrides, hora local:
2028 en hora d'hivern, TU + 1). `Efemerides` i `efemerides(clau)` per eclipsi; `scripts/descarregar_efemerides.py
<any>`; `ModelEclipsi` detecta l'anularitat (fase "ANULARITAT"). Al programa, `canviar_eclipsi` (desplegable del
menú): torna a calcular el punt, l'hora (C1 − 1 h), el cub de navegació; les capes del CNIG només el 2026.
*Comprovat automàticament* (`comparar_nasa.py --calcular --eclipsi 2027/2028`, 8 punts cadascun): model − NASA
com a molt 4,3 s (C1), 6,4 s (C2), 3,7 s (màxim), 5,5 s (C3), 3,2 s (C4), 0,07 punts de Sol tapat, 0,01° de
posició del Sol; la diferència és gairebé constant (+3,3 a +3,7 s de mitjana), com al 2026 (escala de temps, §6.3).
El 2026 no canvia (regressió). Resultats: 2027 a Tarifa 4 min 41 s de totalitat a les 10:47 (hora d'estiu), Sol a
l'est a 38°; 2028 anular, Sol tapat un 83 %, de Cadis a Barcelona, amb el Sol a 0–8° a la posta.

**F25, F26 i F28.** `dades/visibilitat.py` (mètode a la capçalera), `scripts/validar_visibilitat.py`,
`scripts/preparar_visibilitat.py`, `basecode/terrain.py` (`posar_visibilitat`, textura RGBA 16 bits),
`shaders/terrain.frag` (`color_mapa`), `main.py` (`actualitzar_mapa`, en un fil), `ui.py`.
*Comprovat automàticament* (lloc de Manresa, 30 píxels a l'atzar): contactes de la graella contra `ModelEclipsi`
≤ 0,01 s (màxim 1,0 s); marge al màxim contra un raig exacte en ECEF (azimut geogràfic, cada 5 m): mediana
0,021°, màxim 0,153°; hores de visibilitat: mediana 2 s, màxim 85 s (el raig exacte es mostreja cada minut).
Toleràncies justificades a l'script. Errors trobats i corregits en comprovar-ho: (1) el relleu de 200 m dins de la
zona de 5 m alçava l'horitzó; ara només compta fora de la zona; (2) llegir el píxel més proper (en lloc
d'interpolar) a 80–400 m donava fins a 0,3° d'error als vessants; ara bilineal a totes les distàncies i 300 passos.
*Temps:* el lloc de Manresa (1,4 M de píxels), 63 s; la península (24 M de píxels, 200 m), 850 s.
*Inspeccionat visualment:* Manresa al màxim i 10 min després (instant actual).

*Península, 2026 (`validar_visibilitat.py peninsula_200m.tif --cnig`):* contactes ≤ 0,13 s; marge contra el raig
exacte, mediana 0,009°, màxim 0,155°; hores, mediana 1 s, màxim 69 s. Primera execució: tres errors trobats i
corregits: (1) el màxim i C2/C3 s'ajustaven amb una paràbola sobre la separació (forma de V): el màxim
s'equivocava fins a 5 s i C3 fins a 42 s a la vora de la franja; ara una paràbola sobre la separació al quadrat
(que ho és) i C2/C3 d'aquesta paràbola: ≤ 0,5 s als tres eclipsis; (2) el raig començava a un píxel (200 m) i un
obstacle dins de la primera cel·la quedava fora: ara comença a un quart de píxel. **Contra el CNIG**
(`terrain_shadows`, calculada a part amb el GMTED2010 i `insol`): mateixa classe al 82,3 % dels píxels i mateixa
resposta a "es veu més de mig Sol" al 88,7 %: l'objectiu provisional (> 90 %) **no s'assoleix**. El desacord
principal: el CNIG diu "tot tapat" on nosaltres veiem el Sol (27 % de la seva classe 0), repartit per tota la
península. En 10 d'aquests píxels a l'atzar, el raig exacte sobre el MDT de l'IGN confirma el nostre marge
(diferència ≤ 0,09°): no és un error del nostre càlcul sinó de les dades (GMTED2010 contra IGN) o del mètode del
CNIG, que no documenta; la seva capa canvia de classe en menys d'1 km (veïnats amb "tot tapat" i "res tapat"
barrejats). Hipòtesi descartada: l'ombra pròpia del pendent (només n'explica el 4 %). Coherent amb la F11 (74–95 %
d'acord local).

**LiDAR de la UAB (F27, D83).** `scripts/descarregar_lidar.py uab`: 9 fulls (2.800 MB en total, de 20 a 32 milions
de punts cadascun, EPSG:25831 a la capçalera), baixats i convertits d'un en un en 8 min; queden
`data/lidar/uab_{mds,terra,edificis}_1m.tif` (44 MB). `scripts/comparar_altures.py uab` (*comprovat automàticament*):
- **Terra:** LiDAR − MDT de 5 m de l'IGN, mediana +0,13 m (p5 a p95: −0,63 a +1,49 m; 200.000 punts): mateix
  sistema vertical (si no, hi hauria ~50 m de diferència) i coherents.
- **Edificis** (2.787 parts del Catastro amb prou punts d'edifici, de 6.855): l'estimació plantes × 3 m queda,
  de mediana, **1,9 m per sota** de la mesurada; error absolut mitjà 2,8 m; només el 36 % dins de ±1,5 m i el 68 %
  dins de ±3 m. Per plantes: 1 planta → 5,3 m mesurats (naus, cobertes inclinades, ampits); 2 → 8,4 m;
  3 → 10,2 m; als edificis alts, ~2,75 m per planta (11 plantes → 30,4 m). Casos extrems: una part d'1 planta
  amb 29 m mesurats (el Catastro i la realitat no coincideixen). Confirma que l'estimació no serveix per decidir si
  un terrat o un carrer veuen el Sol baix (D81).

**Menú (D82).** Seccions: eclipsi, temps, vista, punt d'observació, mapa de visibilitat (amb llegenda), capes;
"Tecles" i "Avançat" tancats; marques a la barra del temps (inici, final, fase central, màxim, posta).
`prova_controls` (69 OK) i `prova_caminar` (26 OK) amb el menú nou.

### F31 — Detall segons la vista a tot Espanya (31/10/2026, petició de l'equip)

**Què es vol.** Obrir la vista aèria, anar fins a València i acostar-se a un carrer, i obtenir progressivament el
mateix detall que hi ha a Vic i la UAB: relleu, fotografia, edificis (amb altures mesurades) i mapa de visibilitat
amb detall local, sense doble clic ni punt d'observació previ. Nom del lloc en triar un punt. D84–D89.

**Com funciona** (`basecode/detall.py`). El *punt de detall* és el que es mira (explorant: el raig del centre de
la pantalla, o el punt de sota la càmera a prop del terra; a les altres vistes, el punt d'observació). Per sota de
15 km d'altura i després d'1 s a la mateixa cel·la, es prepara el que falta del lloc de la quadrícula de 3 km. La
lectura de dades es fa en fils i la preparació pesada (GDAL, malla), en processos; el fil principal només crea els
objectes OpenGL. Les zones fetes a mà (Picos, Vic, l'Escala, el Vallès) es continuen fent servir.

| Tasca | Tipus | Què | Comprovació | Estat |
|---|---|---|---|---|
| 31.0 | R | `Terrain` i `Edificis` separen la part de CPU (fil) de la d'OpenGL; pegats calculats en un fil | Resultat idèntic al camí síncron (altures del pegat i de la graella, `np.array_equal`); fil principal: lloc 57 ms, Vic 0,22 s, Vallès 0,50 s, pegat 3–5 ms (abans 0,3–0,8 s i 0,2 s) | `FET` (comprovat automàticament) |
| 31.1 | N | Relleu de 5 m segons la vista (llocs a la quadrícula de 3 km) | `prova_detall.py`: a València, el relleu del lloc arriba navegant (2–56 s), el punt d'observació no canvia | `FET` (comprovat automàticament) |
| 31.2 | N | Fotografia: comparació amb l'ortofoto de Vic | GetFeatureInfo: vol a 0,25 m a Vic, UAB, València, Tona i Picos; teselles z = 19 (~0,22–0,23 m/px). No cal estendre l'ortofoto de 0,5 m (D86) | `FET` |
| 31.3 | N | Edificis amb altures mesurades (ICGC / IGN) per cel·les; estimades mentre arriben | `validar_alcaries.py` (UAB, 1.078 parts): ICGC COG − núvol de punts +0,10 m (mediana), IGN − ICGC −0,48 m, estimades 2–3 m per sota. Vic: 12.742 parts mesurades a la cel·la de la plaça Major; València: 28.302 de 48.858 (IGN) en 28 s | `FET` (comprovat automàticament) |
| 31.4 | N | Mapa de visibilitat de detall amb edificis i vegetació a qualsevol cel·la | València: mapa del relleu de 5 m (113 s) i de detall (IGN 2,5 m); UAB: el del núvol de punts (1 m) continua; captures | `FET` (comprovat automàticament i inspeccionat visualment) |
| 31.5 | N | Nom del lloc: nucli més proper (NGBE) i municipi (CartoCiudad) | Vic → dins de Vic; Malla (41,896, 2,247) → nucli Malla, municipi Malla; (41,87, 2,24) → nucli el Gurri, municipi Tona; Benimaclet → dins de València; Picos → la Molina a 5,9 km, municipi no disponible; mar → cap | `FET` (comprovat automàticament) |
| 31.6 | N | Panell: estat del terreny, la foto, els edificis i el mapa per separat; casella dels edificis sempre visible; color segons l'origen de l'altura (Avançat) | Captures de Vic i València | `FET` (inspeccionat visualment) |
| 31.7 | C | Navegació fluida mentre es prepara; preparació antiga sense efecte; reutilització | València (primera vegada, amb Catastro, altures i mapes en curs): mediana 16 ms, p99 26 ms, màxim 606 ms per fotograma (4.064 fotogrames); el Cabanyal acaba després de moure's i no canvia la zona; tornar-hi: relleu, edificis mesurats i els dos mapes en 0,7 s, sense cap feina de xarxa ni tesella nova | `FET` (comprovat automàticament) |
| 31.8 | C | El punt d'observació es torna a situar quan el seu relleu de 5 m (o els seus edificis) arriba després de triar-lo | `prova_llocs.py`: Manresa preparat en segon pla (172 s, 3.229 fotogrames dibuixats mentrestant); l'observador queda sobre el relleu de 5 m | `FET` (comprovat automàticament) |

**Errors trobats i corregits en provar-ho:** (1) llegir el Catastro de València en un fil aturava el dibuix 5 min
(GIL): ara en un procés (D89); (2) mesurar tota la zona del Vallès (49.797 parts) llegia una finestra massa gran:
ara per cel·les; (3) la malla dels edificis i el dibuix demanaven el relleu amb un nombre de vèrtexs diferent i la
memòria cau es refeia cada vegada: ara `data_io.vertexs_maxims`; (4) en acabar el Catastro, els edificis no
apareixien a la zona que ja es veia; (5) marcar l'últim ús d'un lloc canviant la data del fitxer del relleu
invalidava totes les memòries cau que en depenen: ara un marcador a part (`<clau>.us`); (6) un mapa desat però antic
es tractava com a "només llegir" i quedava marcat com a fallat: ara es comprova si és vigent; (7) un sol càlcul de mapa
alhora: el del Vallès (36 M de píxels), que ja no es veia, impedia el de València: ara es cancel·la i llegir mapes
desats no espera mai; (8) carregar una zona sense la malla a la memòria cau la feia en un fil: ara en un procés.

**Regressions (comprovat automàticament, 31/10):** `prova_controls`, `prova_caminar` (26 OK), `prova_obstacles` (25),
`prova_vistes` (102), `prova_cel` (7), `prova_mosaic`, `prova_ortofoto`, `validar_ombres_relleu` (GPU contra CPU
100 %), `validar_edificis` (22: ara compara amb la malla que es dibuixa, mesurada a la UAB, i busca el moment parcial
fins a 90 min abans del màxim, perquè els edificis mesurats són més alts), `validar_model` (≤ 1,2 s, igual que abans).

**Proves de l'equip pendents:** navegar amb el ratolí i el teclat reals fins a un lloc nou (p. ex. València) i
comprovar que el moviment no s'encalla; activar els edificis i el mapa; triar punts entre Vic i Tona i llegir el
nom; tornar-hi i veure que tot és immediat.

**Limitacions:** les altures de l'IGN són de 2008–2015; a 2,5 m els carrers estrets queden barrejats; l'ICGC no
distingeix arbres d'edificis; als llocs nous les cobertes no tenen el color de l'ortofoto; el mapa del relleu de
les zones grans fetes a mà (Vallès, 36 M de píxels) tarda molt la primera vegada (es calcula després del detall
del punt); Navarra i el País Basc sense edificis (cadastres propis); sense ortofoto vertadera.

### F32 — Correccions: canviar d'eclipsi (01/11/2026, error trobat per l'equip) — FET

**Error (provat per l'equip):** en triar l'eclipsi del 2027 o el 2028 al panell, el programa es tancava amb
`GLError 1281 (invalid value)` a `glUseProgram`, dins de slimgui. **Causa:** canviar d'eclipsi refà el cub de
navegació i n'allibera el shader; slimgui desa el shader actiu abans de dibuixar el panell i el reactiva en acabar, i
aquell ja era esborrat. **Correcció:** `main.py` deixa la GPU sense shader actiu just abans de dibuixar el panell
(`GL.glUseProgram(0)`). Les proves no ho van detectar perquè cap no dibuixava el panell en canviar d'eclipsi.

Altres problemes del 2027 i el 2028 trobats en provar-ho:
1. A *Avançat*, "Límits de la totalitat (CNIG)" i "Opacitat CNIG" sortien en tots els eclipsis: els límits oficials
   del 2026 es podien dibuixar sobre un altre eclipsi. Ara només surten amb el 2026, com el desplegable de capes.
2. El 2/8/2027 el Sol queda tot cap a un costat i la Terra quedava a ~3,5 milions de km d'una paret del cub de
   navegació: l'avís de la paret (ratlles) es veia a tot l'entorn de la Terra (captura "ombra des de l'espai").
   Ara el cub deixa sempre 10 milions de km lliures al voltant de la Terra (`dades/navegacio.py`, `ESPAI_TERRA_KM`;
   el 2026 no canvia: 1,647 UA).
3. Un càlcul del mapa de visibilitat de detall que ja no calia (mapa tret, un altre eclipsi o una altra cel·la) no
   s'aturava i impedia començar tots els altres. Ara es cancel·la, com els del relleu.

**Comprovat automàticament:** `scripts/prova_eclipsis.py` (nova): els tres eclipsis i tornar al 2026 amb el bucle real
i el panell dibuixat, sense errors d'OpenGL; contactes dins de les efemèrides; "Anar al màxim"; separació Sol–Lluna
de l'escena igual a la del model (< 0,001°); capes del CNIG desactivades fora del 2026; el mapa de visibilitat es
comença a calcular per a l'eclipsi actiu. `prova_controls` (69 OK). **Inspeccionat visualment:** captures
`captures/proves/eclipsi_<any>_*.png` (des del terra al màxim, a Picos, i l'ombra des de l'espai).

### F33 — Rendiment i panells (01/11/2026, petició de l'equip) — FET

L'equip va notar que l'ordinador s'escalfava molt. **Causa:** cap part del programa limitava els fotogrames: el bucle
dibuixava tan de pressa com podia, encara que no canviés res (una finestra buida feia 515 fotogrames/s; amb
`swap_interval(1)`, 84; prova al Mac de l'equip, comprovat automàticament).

1. **Sincronia vertical** (`main.py`, `run`): `glfw.swap_interval(1)`. La imatge és la mateixa; no se'n fan més
   dels que la pantalla mostra. — FET
2. **Repòs** (`main.py`, `repos`): si la càmera, la vista, l'hora i el mapa no canvien durant `REPOS_S` (0,5 s), en
   pausa i sense feines en segon pla (detall, mapes, teselles, nom del lloc), el bucle espera esdeveniments com a molt
   `ESPERA_REPOS_S` (0,25 s): ~4 fotogrames/s. El teclat i el ratolí el desperten a l'instant. La càrrega del detall
   no s'atura: mentre hi ha feina, no hi entra. **Comprovat automàticament:** 60 s quiet a Picos: mentre es baixen
   teselles (~22 s), ritme normal; després, 100 % en repòs a 3–4 fotogrames/s. — FET
3. **Dos panells** (`ui.py`, petició de l'equip): *Eclipsi* a l'esquerra (eclipsi, fase i velocitat, punt
   d'observació, mapa, línies de l'ombra i CNIG) i *Càmera* a la dreta (vista, **on és la càmera**: altura sobre el
   terra dibuixat, altitud i coordenades; què es dibuixa; detall del lloc; tecles i avançat). El botó de reproduir
   només és a la barra de temps. **Inspeccionat visualment:** captura dels dos panells, sense textos tallats. — FET

**Proves de l'equip pendents:** fer servir el programa una estona i comparar la temperatura i el ventilador amb abans;
comprovar que en repòs la resposta al ratolí i al teclat és immediata.

**Provat per l'equip (01/11):** el programa va bé; un cop es va tancar sol en canviar d'ubicació de cop mentre girava
amb les fletxes (sense el missatge d'error). **Comprovat automàticament:** 4 min de canvis d'ubicació a l'atzar (90,
i 126 en una segona tanda) amb fletxes premudes, canvis de vista i "Anar al màxim", amb el bucle i el panell reals:
sense errors. No s'ha pogut reproduir. Ara, si el programa es tanca per un error, el detall queda a
`data/cache/darrer_error.txt` (`main.py`).

### F34 — Colors dels edificis i un sol tractament per a tots els llocs (01/11/2026, petició de l'equip) — FET

Decisió de l'equip: els edificis amb l'altura mesurada (LiDAR) tenen el color real de la coberta; els que tenen
l'altura estimada són blaus (un color que no és d'edifici). La UAB i Vic no han de tenir tractaments especials.

1. **Color de les cobertes a tot arreu** (`dades/edificis.colors_cobertes`): la mitjana dels píxels de les teselles
   PNOA de z = 17 (~0,9 m) dins del contorn, sense 1 m de vora (els contorns massa petits, amb tots els píxels que
   toquen). Només es baixen les teselles amb edificis. Es calcula en un procés la primera vegada que es veu cada zona
   (`basecode/detall.py`, feina `cobertes`) i es desa a `data/cache/cobertes_<zona>.npz`. Substitueix l'ortofoto de
   Vic (F18) com a font del color. **Comprovat automàticament:** Vic, 16.987 parts en 4 s (236 teselles, la majoria
   ja al disc), 1 sense color; un lloc de 6 × 6 km, 1.782 parts en 1,7 s.
2. **Blau per a les altures estimades** (`shaders/edifici.frag`): tot l'edifici (coberta una mica més fosca). Treu
   la casella de depuració "blau mesurat, taronja estimat"; el panell *Càmera* mostra la llegenda.
3. **UAB com la resta:** el mapa de detall fa servir el model d'alçàries de l'ICGC per cel·les, com a tot Catalunya; el
   núvol de punts de la UAB queda només per validar (`validar_alcaries.py`: +0,10 m de mediana entre els dos).

**Comprovat automàticament:** `prova_detall vic uab` (Vic: color de la foto a 16.986 de 16.987 parts; UAB: mapa de
detall del model d'alçàries, 2 m), `prova_cel` (7), `validar_edificis` (22). **Inspeccionat visualment:** Vic des de 400
m (cobertes de teula reals; edificis blaus fora de la zona mesurada) i la UAB amb el mapa. El mapa de detall d'una
cel·la nova tarda ~4 min la primera vegada (223 s, amb un altre càlcul en marxa).

**Mapes de la península del 2027 i el 2028** (`visibilitat_<any>_peninsula_200m.npz`): calculats l'1/11, 71 i 42 min
(compartint el processador amb les proves); ara es llegeixen en obrir el mapa.

**Limitació trobada (per a la propera entrega):** el mapa de detall només es veu mentre el punt de detall (on mira la
càmera) és dins de la seva cel·la de 3 × 3 km: a 50 m de la vora, si la cel·la del costat no en té, desapareix. Caldria
mantenir els mapes ja calculats mentre es vegin.

Pendent de decidir: l'ortofoto de Vic encara es fa servir com a color del terra de reserva (només es veu mentre no
han arribat les teselles); es podria treure del tot.

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
| 27/10/2026 | F15 (petició de l'equip): captura del ratolí corregida (slimgui la desfeia a cada fotograma), Tab i clic dret, sensibilitat única, límits de la mirada, "Mirar l'eclipsi" i vista guiada fins a l'espai. D54–D57. Sense commit (pendent d'autorització). |
| 27/10/2026 | L'equip valida el Mouse Look amb el ratolí real (15.1 `VALIDAT`). F16 (petició de l'equip): mode Caminar dins d'Explorar, diagonal normalitzada, teclat sense focus o amb el panell actiu, proves amb distàncies explícites. D58–D59. Sense commit. |
| 27/10/2026 | F17 (petició de l'equip): punts d'observació a l'exterior (referència i posició efectiva), edificis com a obstacles caminant i en vol lliure, `prova_obstacles.py`. F18: fonts d'ortofoto verificades, ortofoto del PNOA a Vic, `prova_ortofoto.py`. D60–D63 (D53 substituïda). Sense commit. |
| 27/10/2026 | F19 (petició de l'equip): cel per dispersió amb l'ombra de la Lluna, llum i boira de l'atmosfera, `prova_cel.py`. F20: façanes amb finestres per planta i cobertes de l'ortofoto, descart de cares del darrere. D64–D65. Sense commit. |
| 28/10/2026 | F21 (petició de l'equip): fotografia aèria a tot arreu (PNOA + Sentinel-2, per teselles i en segon pla), controls aeris com Google Earth, doble clic a primera persona, edificis segons la vista, boira de la Terra. D66–D70. Sense commit. |
| 28/10/2026 | F22 (prova i petició de l'equip): foto esmicolada al pegat de 5 m (precisió a la GPU) i punts taronja corregits; atmosfera de la Terra des de l'espai i pol; Lluna amb dades de la NASA a 8k i relleu (baixada autoritzada); Sol de foc (il·lustratiu); revisió de la llum de l'eclipsi parcial i corona només a la totalitat. D71–D74. Sense commit. |
| 30/10/2026 | F23 (petició de l'equip): neteja de caches (1,8 GB), llum de les façanes, llocs nous amb detall amb doble clic, malles comprimides, `prova_llocs.py`. D75–D77. Sense commit. |
| 30/10/2026 | Proposta de l'objectiu O3 (mapa de visibilitat, F24–F30), D78 (vistes aparcades) i D79; preguntes P14–P17. Mesurat: horitzó d'un azimut a 5 m al Vallès en ~20 s. Res implementat. |
| 30/10/2026 | O3: F24 (tres eclipsis, anularitat, comparats amb la NASA), F25, F26 i F28 (mapa de visibilitat del relleu, validat contra un raig exacte), menú net (D82). D80–D82, P18. Sense commit. |
| 30/10/2026 | LiDAR de l'ICGC a la UAB (D83): 9 fulls convertits a rasters d'1 m; comparació amb el Catastro (l'estimació plantes × 3 m s'equivoca 2,8 m de mitjana) i amb el MDT de l'IGN (+0,13 m). Península 2026 validada (contra el CNIG, 88,7 %). Sense commit. |
| 31/10/2026 | Commits de l'estat de l'O3 (`6aa3e38`, `864a3df`). F31 (petició de l'equip): detall segons la vista a tot Espanya, altures mesurades (ICGC, IGN), mapa de detall per cel·les, nom del lloc, feines en processos. D84–D89. Sense commit. |
