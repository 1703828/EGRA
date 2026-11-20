"""
Textures d'imatge de les facanes (F53): fotografies de materials reals d'ambientCG (https://ambientcg.com), amb
llicencia CC0 1.0 (domini public: es poden fer servir, modificar i redistribuir sense atribucio obligatoria; la citem
igualment a data/FONTS.md i a data/textures/facanes/fonts.json).

De cada material es baixa el paquet 1K-JPG (~5-8 MB, es llegeix en memoria i no es desa) i se'n guarden tres mapes:
  <id>_color.jpg      1024 x 1024, color (sRGB)
  <id>_normal.jpg     512 x 512, normal en convencio OpenGL (verd = amunt; ambientCG en dona les dues)
  <id>_rugositat.jpg  512 x 512, rugositat (blanc = mat)
a data/textures/facanes/. La mida real de cada textura (m) es la d'ambientCG quan la publica; si no, s'estima comptant
peces a la imatge (maons, filades) i es diu a 'escala'. Mida total ~7 MB.

Executa (des de l'arrel, amb l'entorn egra):  python scripts/descarregar_textures_facanes.py
"""
import io
import json
import os
import sys
import zipfile

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTI = os.path.join(ARREL, 'data', 'textures', 'facanes')
# (id d'ambientCG, material, mida real (amplada, altura) en m, com se sap)
MATERIALS = [
    ('Plaster001', 'arrebossat', (2.0, 2.0), 'estimada: arrebossat llis, sense peces'),
    ('Plaster007', 'arrebossat', (2.0, 2.0), 'estimada: arrebossat amb taques, sense peces'),
    ('PaintedPlaster017', 'arrebossat', (2.0, 2.0), 'estimada: arrebossat pintat, sense peces'),
    ('Bricks051', 'mao', (1.25, 1.25), 'ambientCG (dimensionX/Y)'),
    ('Bricks085', 'mao', (2.40, 1.20), 'ambientCG (dimensionX/Y)'),
    ('Bricks097', 'mao', (1.50, 1.50), 'estimada: 20 filades de ~7,5 cm'),
    ('Bricks053', 'mao', (1.30, 1.30), 'ambientCG (dimensionX/Y)'),
    ('Bricks099', 'pedra', (2.0, 2.0), 'estimada: pedres de 15-40 cm'),
    ('Bricks066', 'pedra', (2.40, 2.40), 'ambientCG (dimensionX/Y)'),
    ('Bricks068', 'pedra', (1.50, 1.50), 'ambientCG (dimensionX/Y)'),
    ('Concrete034', 'formigo', (1.10, 0.55), 'ambientCG (dimensionX/Y)'),
    ('Concrete031', 'formigo', (2.40, 2.40), 'estimada: un plafo d\'encofrat d\'1,2 m'),
    ('CorrugatedSteel005', 'xapa', (2.0, 2.0), 'estimada: grecat de ~20 cm'),
]
MIDA_COLOR, MIDA_ALTRES = 1024, 512
CAPCALERA = {'User-Agent': 'Mozilla/5.0'}    # (el servei rebutja els clients sense navegador; cap dada de l'usuari)


def main():
    import requests
    from PIL import Image
    os.makedirs(DESTI, exist_ok=True)
    fonts = []
    for aid, material, mida, com in MATERIALS:
        fitxers = {k: os.path.join(DESTI, f'{aid}_{k}.jpg') for k in ('color', 'normal', 'rugositat')}
        if not all(os.path.exists(f) for f in fitxers.values()):
            url = f'https://ambientcg.com/get?file={aid}_1K-JPG.zip'
            print(f'Baixant {aid}...', flush=True)
            r = requests.get(url, headers=CAPCALERA, timeout=120)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                noms = z.namelist()

                def llegir(sufix):
                    nom = next(n for n in noms if n.endswith(sufix))
                    return Image.open(io.BytesIO(z.read(nom)))
                llegir('_Color.jpg').convert('RGB').resize((MIDA_COLOR, MIDA_COLOR), Image.LANCZOS).save(
                    fitxers['color'], quality=90)
                llegir('_NormalGL.jpg').convert('RGB').resize((MIDA_ALTRES, MIDA_ALTRES), Image.LANCZOS).save(
                    fitxers['normal'], quality=92)
                llegir('_Roughness.jpg').convert('L').resize((MIDA_ALTRES, MIDA_ALTRES), Image.LANCZOS).save(
                    fitxers['rugositat'], quality=90)
        fonts.append(dict(id=aid, material=material, mida_m=list(mida), escala=com,
                          url=f'https://ambientcg.com/a/{aid}', llicencia='CC0 1.0 (ambientCG)'))
    with open(os.path.join(DESTI, 'fonts.json'), 'w') as f:
        json.dump(fonts, f, indent=1, ensure_ascii=False)
    total = sum(os.path.getsize(os.path.join(DESTI, n)) for n in os.listdir(DESTI))
    print(f'{len(fonts)} materials a {DESTI} ({total / 1e6:.1f} MB)')


if __name__ == '__main__':
    sys.exit(main())
