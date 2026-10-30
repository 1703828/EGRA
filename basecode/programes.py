"""
Carrega un shader del projecte (basecode/shaders/) amb definicions de preprocessador opcionals.

Fa el mateix que basecode/shaders.load_program (el del professor, que no es toca), pero permet
afegir linies "#define NOM" just despres de "#version". Aixi un mateix fitxer .vert/.frag pot tenir
parts que nomes es compilen en un mode: per exemple, la profunditat logaritmica de l'escena del globus,
que el mode pla dels scripts no ha de fer servir.

Tambe substitueix les linies '#include "fitxer.glsl"' pel contingut d'aquell fitxer de basecode/shaders/ (GLSL no
te includes): aixi una funcio que fan servir dos shaders (p. ex. el mosaic d'imatges, mosaic.glsl) es escriu un
sol cop.
"""
import os

from .shaders import SHADERS_DIR


def incloure(font):
    sortida = []
    for linia in font.split('\n'):
        if linia.strip().startswith('#include'):
            with open(os.path.join(SHADERS_DIR, linia.split('"')[1]), encoding='utf-8') as f:
                linia = f.read()
        sortida.append(linia)
    return '\n'.join(sortida)


def carregar_programa(ctx, nom, defines=()):
    fonts = []
    for ext in ('vert', 'frag'):
        with open(os.path.join(SHADERS_DIR, f'{nom}.{ext}'), encoding='utf-8') as f:
            linies = incloure(f.read()).split('\n', 1)
        fonts.append(linies[0] + '\n' + ''.join(f'#define {d}\n' for d in defines) + linies[1])
    return ctx.program(vertex_shader=fonts[0], fragment_shader=fonts[1])
