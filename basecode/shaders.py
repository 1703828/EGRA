"""Carrega de shaders des de fitxers .vert/.frag (carpeta basecode/shaders/).

Aixi es poden editar els shaders sense tocar el codi Python -- util per al
projecte final, on normalment es va afegint un shader nou per efecte.
"""
import os

SHADERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shaders')


def load_program(ctx, name, shaders_dir=SHADERS_DIR):
    """Llegeix {shaders_dir}/{name}.vert i {name}.frag i crea el programa amb moderngl."""
    vert_path = os.path.join(shaders_dir, f'{name}.vert')
    frag_path = os.path.join(shaders_dir, f'{name}.frag')
    with open(vert_path, encoding='utf-8') as f:
        vertex_shader = f.read()
    with open(frag_path, encoding='utf-8') as f:
        fragment_shader = f.read()
    return ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
