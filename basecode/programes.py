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


def carregar_programa(ctx, nom, defines=(), vertex=None, geometry=True):
    """Vertex i fragment shader (nom.vert, nom.frag) i, si hi es, el geometry shader (nom.geom; OpenGL 3.2, dins del
    3.3 core: entre el vertex i el fragment, rep primitives senceres i en pot emetre de noves).
    vertex: un altre vertex shader (vertex.vert) amb el mateix fragment; geometry=False: sense el geometry shader."""
    fonts = {}
    for ext in ('vert', 'geom', 'frag'):
        cami = os.path.join(SHADERS_DIR, f'{vertex if ext == "vert" and vertex else nom}.{ext}')
        if ext == 'geom' and (not geometry or not os.path.exists(cami)):
            continue
        with open(cami, encoding='utf-8') as f:
            linies = incloure(f.read()).split('\n', 1)
        fonts[ext] = linies[0] + '\n' + ''.join(f'#define {d}\n' for d in defines) + linies[1]
    return ctx.program(vertex_shader=fonts['vert'], geometry_shader=fonts.get('geom'), fragment_shader=fonts['frag'])
