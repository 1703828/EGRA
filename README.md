# EGRA — Simulació d'un eclipsi sobre terreny real

Projecte de l'assignatura EGRA (Alícia Martí, Oriol Mota, Elena Gutiérrez): l'eclipsi total de Sol
del 12 d'agost de 2026 sobre el terreny real d'Espanya.

## Execució

```
conda activate egra
python terreny.py                                # selector: Peninsula, Asturies, Picos, Luarca
python terreny.py data/mdt05/PNOA_MDT05_ETRS89_HU30_0011_LID.tif   # afegeix un altre MDT (EPSG:25830)
```

Al panell hi ha els **overlays de l'eclipsi** (enfosquiment màxim, durada de la totalitat i ombres
del relleu del CNIG) i, fent **doble clic** sobre el terreny, els valors de l'eclipsi en aquell punt
(hores en CEST) amb el botó **Sol al maxim de l'eclipsi**.

Cada terreny es carrega la primera vegada que se selecciona al panell. La primera càrrega d'un MDT
calcula els derivats (gradient, distància a la costa...) i els desa a `data/cache/<nom>.derivats.npz`;
les següents són d'una fracció de segon. Al panell també hi ha la **curvatura de la Terra** i els
rectangles de les **zones de detall** (a Peninsula i Asturies).

## Controls de la càmera

| Acció | Control |
|---|---|
| Girar la càmera (gir i inclinació) | arrossegar amb el **botó esquerre** |
| Desplaçar l'objectiu sobre el terreny | arrossegar amb el **botó dret** (o **Maj + esquerre**) |
| Zoom (cap al punt del cursor) | **roda** del ratolí |
| Centrar l'objectiu en un punt i triar-lo com a punt d'observació | **doble clic** sobre el terreny |
| Tornar a la vista inicial | botó **Reiniciar camera** del panell |

Els sliders del panell (gir, inclinació, distància) també funcionen. Sobre el panell, el ratolí no mou
la càmera. L'objectiu queda sempre enganxat al terreny i la càmera no pot baixar sota el terra.

## Captures (fora de pantalla)

```
python scripts/captura.py data/cache/detall_5m.tif captures/picos.png --azimut 281.4 --elevacio 9.6 --gir -115 --inclinacio 30
python scripts/captura.py data/cache/peninsula_200m.tif captures/peninsula.png --azimut 281.4 --elevacio 9.6 --gir -35 --inclinacio 40
```
Curvatura de la Terra (vista de perfil de la península, sense i amb curvatura):
```
python scripts/captura.py data/cache/peninsula_200m.tif captures/peninsula_sense_curvatura.png --gir 0 --inclinacio 2 --distancia 1.1 --elevacio 20
python scripts/captura.py data/cache/peninsula_200m.tif captures/peninsula_amb_curvatura.png --gir 0 --inclinacio 2 --distancia 1.1 --elevacio 20 --curvatura
```
Overlays de l'eclipsi:
```
python scripts/captura.py data/cache/peninsula_200m.tif captures/peninsula_enfosquiment.png --overlay enfosquiment --opacitat 0.65 --limits --gir -35 --inclinacio 45 --elevacio 30
python scripts/captura.py data/cache/asturias_25m.tif captures/asturies_durada.png --overlay durada --gir -20 --inclinacio 45 --distancia 0.7 --elevacio 30
python scripts/captura.py data/cache/detall_5m.tif captures/picos_ombres_cnig.png --overlay ombres --opacitat 0.55 --sol-maxim --gir -115 --inclinacio 30
```
(Sol de les captures de Picos i peninsula: posicio al maxim de l'eclipsi a Picos de Europa, segons el
dataset del CNIG. Altres opcions: `--objectiu LAT LON`, `--zones`, `--exageracio`, `--boira`.)

## Dades del MDT (servei WCS de l'IGN)

`scripts/descarregar_mdt.py` descarrega el MDT en EPSG:25830 del WCS de l'IGN
(`https://servicios.idee.es/wcs-inspire/mdt`) i el desa com un sol GeoTIFF a `data/cache/`.
Les rajoles ja descarregades es guarden a `data/cache/rajoles/` i no es tornen a baixar.

```
python scripts/descarregar_mdt.py peninsula                    # 200 m -> peninsula_200m.tif
python scripts/descarregar_mdt.py asturias                     # 25 m  -> asturias_25m.tif
python scripts/descarregar_mdt.py detall --centre 43.54 -6.54  # 5 m, 20x20 km -> detall_5m.tif
python scripts/descarregar_mdt.py --res 25 --bbox 43.3 43.6 -6.8 -6.3 --sortida zona_25m.tif
```

## Reconeixement

MDT i dades de l'eclipsi © Instituto Geográfico Nacional / CNIG (llicència CC BY 4.0).

Dades de l'eclipsi: "Official astronomical information provided by the National Geographic Institute
based on calculations made by the National Astronomical Observatory" (veure `data/eclipsi2026/LLEGENDA.md`).
