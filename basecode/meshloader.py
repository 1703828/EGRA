"""Carrega de models (.obj, .stl...) amb trimesh: escrits a ma pels alumnes o descarregats per al projecte final.

Cada model ha de viure a la seva propia carpeta (model.obj + el seu .mtl i les
textures que faci servir, si en te) -- trimesh resol les rutes relatives del
.mtl agafant com a base la carpeta on esta el .obj, aixi que mentre cada model
tingui la seva carpeta funciona sense haver de tocar res.
"""
import numpy as np
import trimesh
from PIL import Image


def load_mesh_vertex_data(path, color=(1, 1, 0)):
    """Retorna un array (color, normal, position) x 3 vertexs per triangle, llest per un VBO '3f 3f 3f'."""
    mesh = trimesh.load(path, force='mesh')
    idx = mesh.faces.reshape(-1)
    positions = mesh.vertices[idx].astype('f4')
    normals = mesh.vertex_normals[idx].astype('f4')
    colors = np.tile(np.array(color, dtype='f4'), (len(idx), 1))
    return np.hstack([colors, normals, positions]).astype('f4')


def load_textured_mesh(path, fallback_color=(1, 1, 0)):
    """Retorna (vertex_data, imatge). vertex_data: array (normal, uv, position) x 3
    vertexs per triangle, llest per un VBO '3f 2f 3f'. imatge: la textura difusa
    del material (PIL, RGBA) si el model en te, o un color pla fallback_color si no."""
    mesh = trimesh.load(path, force='mesh')
    idx = mesh.faces.reshape(-1)
    positions = mesh.vertices[idx].astype('f4')
    normals = mesh.vertex_normals[idx].astype('f4')

    visual = mesh.visual
    uv = None
    if isinstance(visual, trimesh.visual.texture.TextureVisuals) and visual.uv is not None:
        uv = np.asarray(visual.uv)[idx].astype('f4')
    if uv is None:
        uv = np.zeros((len(idx), 2), dtype='f4')

    vertex_data = np.hstack([normals, uv, positions]).astype('f4')

    image = None
    material = getattr(visual, 'material', None)
    if material is not None:
        image = getattr(material, 'image', None)
    if image is None:
        image = Image.new('RGB', (1, 1), tuple(int(c * 255) for c in fallback_color))
    image = image.convert('RGBA')

    return vertex_data, image
