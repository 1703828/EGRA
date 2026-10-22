# Projecte EGRA — Instruccions de treball

## Propòsit

Projecte universitari d’Entorns Gràfics amb Python i OpenGL per representar l’eclipsi solar del 12 d’agost de 2026 sobre terreny real d’Espanya.

La prioritat és que l’equip entengui el codi, aprengui els conceptes gràfics i pugui explicar les decisions. La qualitat visual també importa, però no justifica afegir complexitat que l’equip no pugui comprendre.

## Documents de referència

- `CLAUDE.md`: instruccions estables sobre com treballar.
- `PLA_DE_TREBALL.md`: tasques, decisions, dependències, comprovacions i estat actual.
- `README.md`: instal·lació, execució i ús real del programa.
- `data/FONTS.md`, quan es creï: procedència i reproducció de les dades.
- `docs/`, quan es creï: seguiment i explicació de l’aprenentatge.

Llegeix el pla abans de començar una tasca i contrasta’l amb el codi actual. Una funcionalitat planificada no s’ha de descriure com si ja estigués implementada.

`CLAUDE_ANTIC.md` és només un arxiu històric. `TASQUES_TERRENY.md` no és la cua de treball vigent; consulta’l només com a antecedent.

Les instruccions explícites més recents de l’equip prevalen sobre aquests documents. Si detectes una contradicció, assenyala-la i actualitza la documentació dins de l’abast autoritzat.

## Manera de treballar

Treballa en una tasca petita cada vegada.

Abans d’implementar, explica breument:
- Quin problema resol.
- Quin concepte aprendrem.
- Quins fitxers tocaràs.
- Com comprovarem el resultat.

Un cop autoritzada la tasca, completa els passos necessaris i les comprovacions sense demanar permís repetidament per accions ja incloses en aquella autorització. Si apareix una decisió que amplia l’abast o canvia el disseny acordat, consulta-la.

En acabar:
- Explica què ha canviat i per què.
- Indica què has comprovat tu i què ha de provar l’equip.
- Dona una comprovació curta, concreta i entenedora.
- Actualitza el pla i la documentació corresponent.
- Atura’t abans de començar la tasca següent.

Estats del pla:
- PENDENT: sense començar.
- EN CURS: s’hi està treballant.
- FET: implementat i amb les comprovacions de Claude descrites; pendent de revisió de l’equip.
- VALIDAT: l’equip ha fet i confirmat la comprovació indicada.

No marquis una tasca com a VALIDAT perquè l’equip hagi executat una ordre sense entendre’n el resultat.

## Abast i disseny acordats

No volem un videojoc ni un personatge de dues esferes. La retirada del personatge i dels salts està planificada; no s’ha de barrejar amb una reorganització que promet conservar el comportament.

Volem:
- Explorar l’escena amb una càmera sense personatge.
- Seleccionar un punt d’observació.
- Observar l’eclipsi a l’altura dels ulls, inicialment 1,7 m sobre el terreny.
- Bloquejar la ubicació durant la reproducció des del terreny, permetent girar la mirada i fer zoom.
- Poder explorar una vista il·lustrativa des de la Lluna.
- Incorporar una representació visual del Sol amb textura i, eventualment, animació.

La ubicació de l’observador és una dada independent de qualsevol marcador o objecte dibuixat.

La vista astronòmicament coherent des de la Lluna és una ampliació diferent de la vista il·lustrativa. El model actual, ajustat a l’observació terrestre i amb distàncies artificials, no la garanteix.

Ubicacions objectiu: Vic, l’Escala, Cerdanyola, Montmeló i la UAB. Picos es conserva provisionalment com a cas de totalitat. Els punts concrets i les seves fonts es documenten al pla.

No introdueixis funcionalitats noves per iniciativa pròpia sense relacionar-les amb una tasca acordada.

## Organització del codi

Segueix l’estructura acceptada a PLA_DE_TREBALL.md i la referència real de repte4.

- Conserva sense canvis els fitxers originals del professor a `basecode/`.
- Es poden afegir fitxers propis a `basecode/`.
- El principal coordina l’escena; la interfície pròpia s’organitza a `ui.py`.
- `dades/` conté lectura, preparació de dades i càlculs sense dependència del context gràfic.
- Els shaders del projecte s’organitzen a `basecode/shaders/`.
- `scripts/` conté eines de preparació, captura i comprovació.
- `models/` conté els models externs.

Aquesta és l’estructura de destinació. No pressuposis que els moviments ja s’han fet.

No afegeixis capes, gestors o abstraccions sense una necessitat concreta. Evita dependències circulars i duplicació de constants.

Separa en tasques diferents:
- Reorganització sense canvis de comportament.
- Correccions o canvis de comportament.
- Funcionalitats noves.

## Entorn

Entorn conda `egra`, Python 3.11. Executa des de l’arrel del repositori amb aquest entorn, no amb l’Anaconda base. Comprova l’intèrpret disponible; no pressuposis una ruta personal fixa.

Execució habitual: `python main.py`.

Tecnologies actuals: GLFW, ModernGL, PyGLM, NumPy, slimgui i les dependències geogràfiques documentades al projecte.

Mantén compatibilitat amb l’objectiu OpenGL 3.3 core. No introdueixis requisits de versions superiors.

Demana autorització abans d’instal·lar dependències i documenta les aprovades a requirements.txt. No instal·lis una llibreria si la necessitat es pot resoldre raonablement amb les existents.

## Convencions gràfiques i geogràfiques

- Unitats del món local: quilòmetres.
- Eixos locals: X cap a l’est de quadrícula, Y amunt i Z cap al sud de quadrícula.
- Les altituds dels MDT s’emmagatzemen habitualment en metres: fes explícites les conversions.
- CRS actual de treball: EPSG:25830. Llegeix i comprova el CRS de cada font; no assignis un CRS per substituir una reprojecció.
- Distingeix nord geogràfic i nord de quadrícula. Converteix les direccions astronòmiques al marc de l’escena amb el signe comprovat.
- Azimut geogràfic: des del nord en sentit horari.
- Conserva el temps de càlcul en TU i identifica explícitament les conversions. Per a aquesta data, la visualització local és CEST, TU + 2.

Mode normal acordat:
- Curvatura terrestre geomètrica activa.
- Exageració vertical igual a 1.
- Radi terrestre aproximat de 6371 km.
- Sense correcció de radi efectiu del terreny per refracció terrestre, llevat d’un canvi acordat.

Distingeix refracció astronòmica del Sol i refracció terrestre del relleu. Documenta les aproximacions i evita aplicar correccions duplicades.

El terreny dibuixat, la ubicació de l’observador i els scripts de comprovació han d’utilitzar convencions compatibles.

Els controls per exagerar el relleu o desactivar la curvatura són eines didàctiques o de depuració, identificades com a tals.

## Model de l’eclipsi i precisió

Distingeix sempre:
- Dades oficials llegides.
- Valors calculats pel nostre model.
- Ajustos del model a les dades.
- Efectes visuals il·lustratius.

La coincidència amb dades emprades per ajustar el model comprova la implementació de l’ajust, però no és una validació independent.

Font externa acordada: calculador de circumstàncies locals de la NASA per a l’eclipsi de 2026. Documenta l’enllaç, les coordenades consultades, les convencions i les limitacions.

Abans de comparar resultats, comprova hora, altitud de l’observador, refracció, definició dels contactes i altres paràmetres rellevants.

Els llindars del pla són objectius provisionals, no garanties de precisió física. Prioritza els errors pel seu efecte sobre la visualització i l’objectiu docent.

Distingeix:
- Cobertura del Sol per la Lluna.
- Ocultació del Sol pel relleu.
- Efectes de l’atmosfera.

No presentis com a precisió coneguda allò que només s’ha estimat o ajustat.

## Dades i rendiment

Els MDT nous i les caches van a carpetes ignorades per Git. Picos es conserva versionat com a exemple inicial, segons el pla.

Documenta font, cobertura, resolució, CRS, llicència i procediment de reproducció. Conserva l’atribució IGN/CNIG i les atribucions de les altres fonts utilitzades.

Abans d’eliminar dades, comprova dependències i com recuperar-les.

No facis peticions de xarxa ni operacions llargues que bloquegin el bucle de renderitzat. La descàrrega progressiva és una ampliació planificada, no una ordre d’implementar-la ara. Els recursos OpenGL s’han de gestionar des del context adequat.

MDT i MDS tenen funcions diferents: l’observador es col·loca sobre el MDT. Un possible MDS s’estudiarà com a representació d’obstacles; no el substitueix automàticament.

## Comprovacions

Fes comprovacions proporcionades a cada canvi.

- Compilar Python no demostra que els imports, els shaders o la interacció funcionin.
- Una captura de terreny no valida tot el programa.
- Compara imatges amb una escena i condicions reproduïbles. La igualtat píxel a píxel és útil en el mateix entorn controlat; no és una garantia universal entre GPUs.
- En comprovacions de profunditat, considera la superfície realment renderitzada, la interpolació i la precisió del buffer. Justifica les toleràncies.
- Identifica les proves manuals que l’equip ha de fer.

No afirmis que has obert una finestra, provat controls o consultat una font si no ho has fet. Separa resultats observats, deduccions i punts pendents.

## Documentació i web

La web de seguiment s’organitza per objectius i subobjectius desplegables.

Cada subobjectiu recull:
- Què es vol aconseguir.
- Estat i criteris de comprovació.
- Teoria apresa.
- Implementació i fitxers relacionats.
- Captures o exemples.
- Evidències i limitacions.

Els percentatges deriven dels criteris validats. No inventis percentatges de progrés.

Comença amb HTML senzill i desplegables natius. Els exemples WebGL són opcionals i no han de convertir-se en un segon projecte.

Referència docent: https://www.labri.fr/perso/nrougier/python-opengl/
Relaciona els conceptes amb el nostre codi i explica les diferències de llibreries quan sigui necessari.

Escriu les explicacions, comentaris i missatges en català. Conserva els noms de les API. Si la font de la interfície no mostra accents, documenta aquesta limitació; no l’estenguis als documents.

## Git i autoritzacions

Abans de preparar un commit, revisa els canvis i inclou només els fitxers de l’abast autoritzat.

No facis commits, push, instal·lacions, descàrregues grans, eliminacions de dades ni reescriptures de l’historial sense autorització explícita. Una autorització ja donada per una acció concreta no necessita repetir-se.

No descartis canvis de l’equip ni moguis etiquetes existents sense permís.

La branca de treball i els identificadors dels commits són estat del projecte: consulta Git i registra’ls al pla quan sigui necessari. No els fixis aquí com si fossin permanents.

CLAUDE_ANTIC.md es conserva localment i queda fora dels commits. La política de versionament del nou CLAUDE.md es manté com està fins que l’equip decideixi canviar-la.
