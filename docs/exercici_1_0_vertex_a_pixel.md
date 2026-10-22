# Exercici 1.0 — D'un vèrtex del terreny a un píxel de la pantalla

Objectiu de la web: **O2.1** (com es dibuixa un fotograma) i **O2.2** (càmeres i matrius).
Tasca del pla: **1.0**. Script: [`scripts/exercici_fotograma.py`](../scripts/exercici_fotograma.py).

> Aquesta pàgina és provisional: quan es construeixi la web (`docs/`, tasca 5.1), el contingut
> passarà als desplegables del subobjectiu O2.1/O2.2.

---

## Què es vol aconseguir

Seguir **un sol punt** del terreny des de les seves coordenades al món fins al píxel on apareix a
la pantalla, fent a mà els mateixos càlculs que fa la GPU, i comprovar que el resultat coincideix
amb el que la GPU ha dibuixat de debò.

## Estat i criteris de comprovació

| Criteri | Qui el comprova | Estat |
|---|---|---|
| El script s'executa i diu `RESULTAT: COINCIDEIX` | Claude (fet el 22/10) i l'equip | **Validat** per l'equip el 22/10 |
| La creu vermella de la captura cau sobre el terreny, al lloc del vèrtex | Claude (captura revisada) i l'equip | Claude: sí. Equip: pendent |
| L'equip prediu l'efecte de la modificació proposada abans d'executar-la | L'equip | Opcional (l'equip va donar l'activitat per tancada) |

---

## Teoria (la mínima per entendre l'exercici)

### Tres paraules que no són el mateix

- **Vèrtex:** un punt de la malla. El terreny en té 1024 × 1024. Cada vèrtex passa pel *vertex
  shader* (`basecode/shaders/terrain.vert`), que en calcula la posició.
- **Fragment:** quan la GPU omple un triangle, genera un candidat per a cada píxel que el triangle
  cobreix. Les seves dades (profunditat, color...) són una barreja dels tres vèrtexs del triangle.
  Passa pel *fragment shader* (`terrain.frag`).
- **Píxel:** una casella de la imatge final. Es queda el fragment que és més a prop de la càmera
  (test de profunditat).

Un vèrtex gairebé mai cau just al centre d'un píxel: per això, a l'exercici, la profunditat que
llegim del píxel és la del triangle en aquell centre, no exactament la del vèrtex.

### El camí del punt, pas a pas

Una matriu 4 × 4 és una manera compacta d'escriure "mou, gira i escala" en una sola operació.
Multiplicar un punt per una matriu vol dir aplicar-li aquella transformació.

1. **Al món** (km): x = est, y = amunt, z = sud. El punt té una quarta coordenada w = 1.
2. **`m_model`** porta el punt del sistema de l'objecte al món. Per al terreny és la identitat
   (no fa res): el terreny ja es construeix en coordenades del món.
3. **`m_view`** (`glm.lookAt`) recol·loca el món com el veu la càmera: la càmera queda a l'origen
   mirant cap a −z. Després d'aquest pas, **−z és la profunditat del punt segons l'eix de visió de la càmera** (no la distància en línia recta fins al punt: un punt al costat de la imatge és més lluny en línia recta però pot tenir la mateixa −z).
4. **`m_proj`** (`glm.perspective`) prepara la perspectiva. El resultat és el que el vertex shader
   escriu a `gl_Position` (coordenades de *clip*). La w que surt és aquesta −z: la profunditat segons l'eix de visió.
5. **Divisió per w** (la fa la GPU sola): x, y i z es divideixen per aquesta profunditat. **Aquí és on el
   que és lluny es fa petit.** El resultat (NDC) va de −1 a 1 a tota la pantalla.
6. **Viewport:** les NDC es passen a píxels: x = (ndc.x + 1)/2 · amplada, i igual per a y (amb
   l'origen a baix a l'esquerra, com fa OpenGL).
7. **Profunditat:** ndc.z es passa a 0..1 i es guarda al *depth buffer*.

### Per què no fem servir el cim del MDT

La GPU no dibuixa el MDT de 5 m: el vertex shader llegeix l'altura amb
`textureLod(tex_altitud, uv, lod_vertexs)`, amb un nivell de detall ~1,97. Això vol dir que fa
servir les versions reduïdes de la textura (*mipmaps*), on cada valor és la mitjana d'un bloc. El
cim més alt del MDT (2647 m) no existeix a la superfície dibuixada. Per això l'exercici tria **un
vèrtex de la graella** i n'obté l'altura de la mateixa manera que la GPU.

---

## Implementació i fitxers relacionats

| Fitxer | Paper a l'exercici |
|---|---|
| `scripts/exercici_fotograma.py` | L'exercici (no modifica cap altre fitxer) |
| `scripts/captura.py` | D'aquí es reutilitza l'"app" sense finestra (`AppSenseFinestra`) |
| `basecode/terrain.py` | La graella (`build_grid`), les textures i `render()` |
| `basecode/shaders/terrain.vert` | El càlcul real que reproduïm a mà |
| `basecode/camera_exploracio.py` | `update()`: calcula `m_view` i `m_proj` |

El script:
1. Tria el vèrtex (columna 640, fila 512 per defecte: uns 2,5 km a l'est del centre de Picos).
2. Llegeix els mipmaps de la textura d'altituds **de la GPU** i calcula l'altura com `textureLod`.
3. Fa els passos 1–7 de la teoria i els escriu tots.
4. Comprova que el vèrtex és dins de la pantalla i que no hi ha relleu entre la càmera i el punt.
5. Renderitza el terreny (sense antialiasing), llegeix la profunditat del píxel i la compara.
6. Fa una comprovació extra: executa el vertex shader real per a aquest sol vèrtex
   (*transform feedback*) i en compara la posició amb la calculada a mà.
7. Desa una captura amb una creu vermella al píxel predit.

---

## Activitat

### 1. Executar-lo

Des de l'arrel del repositori:

```bash
conda activate egra
python scripts/exercici_fotograma.py
```

La captura es desa a `captures/exercici_1_0.png` (la carpeta `captures/` no es puja al Git).

### 2. Què hauria d'aparèixer i com llegir-ho

- **`=== 1. EL VERTEX ===`**: l'altura del MDT de 5 m i la que dibuixa la GPU en aquell punt (al
  voltant d'1 m de diferència, per la mitjana dels mipmaps) i la posició al món en km.
- **`=== 2. DEL MON A LA PANTALLA ===`**: cada etapa del camí.
  - Fixeu-vos que la **w** de la línia de *clip* és igual a la **profunditat segons l'eix de visió** (−z) de la línia anterior.
  - Les **NDC** són valors petits (entre −1 i 1): 0 és el centre de la pantalla.
  - El **píxel** surt amb decimals: el vèrtex cau entre centres de píxels.
- **`=== 3. EL QUE HA DIBUIXAT LA GPU ===`**:
  - La posició segons el vertex shader real ha de diferir **pocs centímetres** de la nostra.
  - La profunditat llegida i la predita, i la diferència en metres segons l'eix de visió (uns pocs
    metres a ~19 km).
  - `RESULTAT: COINCIDEIX` vol dir que la diferència és menor que la tolerància calculada.
- **La captura**: la creu vermella ha de caure sobre el vessant del terreny.

### 3. Una modificació per predir

Abans d'executar-la, **escriviu la vostra predicció**:

```bash
python scripts/exercici_fotograma.py --distancia 0.5
```

La càmera s'acosta al centre del terreny fins a la meitat de la distància, sense girar-se.

> Predicció: el punt vermell, **cap on es mourà a la pantalla** (més a prop o més lluny del
> centre)? **Quant** canviarà el valor `NDC x`? Què passarà amb la **profunditat** (−z) de la línia
> `m_view * p` i amb la **w**?

Després d'executar-la, compareu-ho amb la vostra predicció i obriu la solució.

<details>
<summary>Solució (obrir després de provar-ho)</summary>

Resultat que va obtenir Claude el 22/10 (podeu comparar-lo amb el vostre):

| | `--distancia 1.0` | `--distancia 0.5` |
|---|---|---|
| `m_view * p`: x, y | 2,1708, −0,4765 | 2,1708, −0,4765 |
| Profunditat segons l'eix (−z) i w | 18,790 km | 8,790 km |
| NDC x | 0,1652 | 0,3531 |
| Píxel | (699,1, 378,3) | (811,8, 353,5) |

- La càmera s'ha mogut **al llarg de la seva línia de visió**: per això x i y vistos des de la
  càmera **no canvien**; només canvia la profunditat segons l'eix de visió (−z), que baixa exactament 10 km.
- La NDC és x / w: 2,1708 / 18,790 → 2,1708 / 8,790. Es multiplica per 18,790 / 8,790 ≈ **2,14**,
  no exactament per 2: el punt no és al centre, de manera que la seva profunditat no es redueix a la
  meitat.
- El punt **s'allunya del centre** de la pantalla: és la divisió per w (perspectiva). Els objectes
  propers es veuen més grans i més separats.

</details>

---

## Complement: la tolerància de la profunditat

(No és necessari per a l'objectiu principal.) La profunditat predita i la llegida no han de ser
iguals, i la diferència permesa es **calcula per a cada punt**:

- **Centre del píxel** (el terme més gran): el píxel guarda la profunditat del triangle al seu
  centre, que és a ~0,3–0,4 píxels del vèrtex. La diferència és aquest desplaçament multiplicat per
  quant canvia la profunditat d'un píxel al següent (mesurat amb els píxels veïns). Aquest terme és
  una **estimació**: suposa que la superfície és plana al voltant del vèrtex.
- **Depth buffer**: si guarda 24 bits, un pas és 2⁻²⁴ ≈ 6·10⁻⁸ (el script no pot consultar els bits
  reals; és el format habitual).
- **Arrodoniment float32** de les matrius (~10⁻⁶).
- **Altura**: la diferència entre la nostra altura i la del vertex shader real (pocs centímetres).

La profunditat no és lineal: té molta més precisió a prop de la càmera. Per això també es mostra
la diferència en metres. Amb `--distancia 0.5`, la diferència (2,3·10⁻⁵) va quedar a prop de la
tolerància (2,8·10⁻⁵): és un recordatori que la tolerància és una estimació raonada, no un marge
universal.

---

## Evidències (Claude, 22/10/2026)

Executat amb l'entorn `egra`, sense finestra, a l'ordinador del projecte:

| Execució | Diferència vèrtex: shader real vs. a mà | Diferència de profunditat | Tolerància | En metres | Resultat |
|---|---|---|---|---|---|
| per defecte | 1,37 cm | 1,27·10⁻⁵ | 6,55·10⁻⁵ | 2,06 m | COINCIDEIX |
| `--distancia 0.5` | 1,37 cm | 2,29·10⁻⁵ | 2,76·10⁻⁵ | 1,46 m | COINCIDEIX |

Les dues captures s'han revisat: la creu cau sobre el vessant del terreny.
L'equip ho va executar el 22/10 amb `COINCIDEIX` i va donar l'activitat per tancada.

## Limitacions

- L'escena és la de `captura.py` (sense Sol, Lluna ni personatge) i amb la curvatura desactivada,
  com el programa actual. Quan la curvatura s'activi (tasca 3.4), el punt baixarà una mica.
- El *near* de la càmera és força gran (~2 km a la distància per defecte): ho decideix
  `CameraExploracio.update()` segons la distància; no afecta l'exercici.
- La comprovació de visibilitat recorre el raig a passos (2000) i no detectaria un obstacle més
  petit que un pas (uns 10 m).
- Els 1,37 cm de diferència amb el vertex shader real venen, probablement, de la precisió amb què
  la GPU barreja els mipmaps; no s'ha investigat més perquè són molt petits.
