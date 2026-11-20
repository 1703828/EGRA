"""
Textures d'imatge de les facanes (F53): fotografies de materials reals (ambientCG, CC0; les baixa
scripts/descarregar_textures_facanes.py a data/textures/facanes/, amb fonts.json: font, llicencia i mida real).

Totes les textures van en dues texture arrays (una textura amb moltes capes de la mateixa mida; OpenGL 3.0, dins del
3.3 core) que comparteixen tots els edificis i totes les zones: es carreguen un sol cop per programa.
  - color: 1024 x 1024 per capa (RGBA8, ~5,6 MB amb mipmaps cadascuna);
  - normal i rugositat: 512 x 512 (RG normal en convencio OpenGL, B rugositat; ~1,4 MB cadascuna).
Amb mipmaps i filtre anisotropic: de lluny, la GPU fa servir versions reduides de la imatge (sense parpelleig) i el
detall no s'apaga a ma. Per a 13 materials, ~91 MB de memoria de GPU.

Cada material (arrebossat, mao, pedra, formigo, xapa) te un grup de capes consecutives; dins del grup, primer les
'rustiques' (mao vell, pedra de paredat, arrebossat tacat), que nomes fan servir les cases i els edificis agraris
(dades/edificis.aspecte_parts). Mida real de cada capa (m) i color mitja (per tenyir els arrebossats amb la paleta) van en uniforms.
"""
import json
import os

import moderngl as mgl
import numpy as np

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'textures', 'facanes')
MATERIALS = ('arrebossat', 'mao', 'pedra', 'formigo', 'xapa')     # el mateix ordre que les constants d'edifici.vert
RUSTIQUES = {'Plaster007', 'Bricks097', 'Bricks099'}
MAX_CAPES = 16                                                     # (mida dels arrays d'uniforms del shader)
UNITAT_COLOR, UNITAT_NR = 2, 3


class TexturesFacanes:
    def __init__(self, ctx):
        from PIL import Image
        self.ctx = ctx
        self.capes, self.grups = [], []      # grups: (primera capa, quantes, quantes rustiques) per material
        cami = os.path.join(DIR, 'fonts.json')
        fonts = json.load(open(cami)) if os.path.exists(cami) else []
        for m in MATERIALS:
            g = sorted((f for f in fonts if f['material'] == m and all(
                os.path.exists(os.path.join(DIR, f'{f["id"]}_{k}.jpg')) for k in ('color', 'normal', 'rugositat'))),
                key=lambda f: f['id'] not in RUSTIQUES)
            self.grups.append((len(self.capes), len(g), sum(f['id'] in RUSTIQUES for f in g)))
            self.capes += g
        self.capes = self.capes[:MAX_CAPES]
        n = max(len(self.capes), 1)
        color = np.full((n, 1024, 1024, 4), 200, 'u1')
        nr = np.full((n, 512, 512, 4), 128, 'u1')
        nr[..., 2] = 200
        self.mitjanes = np.full((MAX_CAPES, 3), 0.8, 'f4')
        for i, f in enumerate(self.capes):
            c = np.asarray(Image.open(os.path.join(DIR, f'{f["id"]}_color.jpg')).convert('RGB'))
            color[i, ..., :3] = c
            self.mitjanes[i] = c.reshape(-1, 3).mean(axis=0) / 255.0
            nr[i, ..., :2] = np.asarray(Image.open(os.path.join(DIR, f'{f["id"]}_normal.jpg')).convert('RGB'))[..., :2]
            nr[i, ..., 2] = np.asarray(Image.open(os.path.join(DIR, f'{f["id"]}_rugositat.jpg')).convert('L'))
        self.color = ctx.texture_array((1024, 1024, n), 4, color.tobytes())
        self.nr = ctx.texture_array((512, 512, n), 4, nr.tobytes())
        for t in (self.color, self.nr):
            t.build_mipmaps()
            t.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
            t.repeat_x = t.repeat_y = True
            t.anisotropy = 8.0
        self.mides = np.ones((MAX_CAPES, 2), 'f4')
        for i, f in enumerate(self.capes):
            self.mides[i] = f['mida_m']
        self.memoria_mb = (color.nbytes + nr.nbytes) * 4 / 3 / 1e6
        self.disponibles = bool(self.capes)

    def aplicar(self, sp):
        self.color.use(UNITAT_COLOR)
        self.nr.use(UNITAT_NR)
        sp['tex_facana'].value = UNITAT_COLOR
        sp['tex_facana_nr'].value = UNITAT_NR

    def uniforms_fixos(self, sp):
        """Una vegada per programa: la mida real i el color mitja de cada capa (la capa de cada part la tria
        dades/edificis.aspecte_parts amb self.grups i self.mitjanes)."""
        sp['mida_capa'].write(self.mides.tobytes())
        sp['mitjana_capa'].write(self.mitjanes.tobytes())

    def destroy(self):
        self.color.release()
        self.nr.release()
