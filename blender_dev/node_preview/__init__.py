import os

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from ..util import hex_to_rgba

_handle = None

PREVIEW_SIZE = 256  # tamaño máximo de la imagen en px
MARGIN = 10  # separación con el borde del editor
LABEL_SIZE = 12  # tamaño del texto
LABEL_GAP = 10  # separación entre el texto y la imagen


def _image_node(context):
    node = getattr(context, "active_node", None)
    if node is not None and node.bl_idname == "ShaderNodeTexImage":
        return node
    return None


def _file_name(image):
    """Nombre del archivo; si no tiene ruta (generada/empaquetada), el nombre del datablock."""
    if image.filepath:
        return os.path.basename(bpy.path.abspath(image.filepath))
    return image.name


def _fit_text(font_id, text, max_width):
    """Recorta el texto con '…' si no cabe en max_width."""
    if blf.dimensions(font_id, text)[0] <= max_width:
        return text
    while len(text) > 1 and blf.dimensions(font_id, text + "…")[0] > max_width:
        text = text[:-1]
    return text + "…"


def _draw_callback():
    context = bpy.context
    space = context.space_data
    region = context.region
    if space is None or region is None or space.type != "NODE_EDITOR":
        return
    if space.tree_type != "ShaderNodeTree" or space.edit_tree is None:
        return

    node = _image_node(context)
    if node is None or not node.select or node.image is None:
        return

    img_w, img_h = node.image.size
    if img_w == 0 or img_h == 0:
        return

    # Imagen ajustada a PREVIEW_SIZE manteniendo la proporción
    scale = min(PREVIEW_SIZE / img_w, PREVIEW_SIZE / img_h)
    width, height = img_w * scale, img_h * scale

    # Esquina inferior derecha del editor
    x1 = region.width - MARGIN
    x0 = x1 - width
    y0 = MARGIN
    y1 = y0 + height

    try:
        texture = gpu.texture.from_image(node.image)
    except Exception:
        return

    shader = gpu.shader.from_builtin("IMAGE_SCENE_LINEAR_TO_REC709_SRGB")

    batch = batch_for_shader(
        shader,
        "TRI_FAN",
        {
            "pos": (
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (x0, y1),
            ),
            "texCoord": (
                (0, 0),
                (1, 0),
                (1, 1),
                (0, 1),
            ),
        },
    )

    gpu.state.blend_set("ALPHA")
    shader.uniform_sampler("image", texture)
    batch.draw(shader)
    gpu.state.blend_set("NONE")

    # Nombre del archivo centrado encima de la imagen
    font_id = 0
    blf.size(font_id, LABEL_SIZE * context.preferences.system.ui_scale)
    text = _fit_text(font_id, _file_name(node.image), width)
    text_w, _text_h = blf.dimensions(font_id, text)

    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 1.0)
    blf.shadow_offset(font_id, 1, -1)
    blf.color(font_id, *hex_to_rgba("#abb0b6"))
    blf.position(font_id, x0 + (width - text_w) / 2, y1 + LABEL_GAP, 0)
    blf.draw(font_id, text)
    blf.disable(font_id, blf.SHADOW)


def register():
    global _handle
    if _handle is None:  # evita registrar el handler dos veces
        _handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            _draw_callback, (), "WINDOW", "POST_PIXEL"
        )


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceNodeEditor.draw_handler_remove(_handle, "WINDOW")
        _handle = None
