import math

import blf
import bpy
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader

# Máximo de pasos que se cuentan (Preferences > System > Memory & Limits > Undo Steps)
MAX_STEPS = 32
# Estados fuera de Sculpt que se toleran entre dos sesiones (cambio de pestaña, etc.)
MAX_SKIP = 2

LABEL = "Undo History"
HEIGHT = 30  # alto del slider (px, escala con la UI), como un widget nativo
MAX_WIDTH = 512  # ancho máximo del slider
WIDTH_FRAC = 0.7  # ancho respecto al área libre del viewport
TOP_OFFSET = 10  # distancia desde arriba del área libre
TEXT_PAD = 8  # margen interior del texto
HIT_PAD = 4  # zona extra clicable alrededor del slider
HOVER_CURSOR = "DEFAULT"  # cursor sobre el slider: "DEFAULT" = flecha, "HAND" = mano

# depth = pasos de Sculpt disponibles (0 = sin cambios). Persiste entre pestañas
# back  = cuántos pasos estamos hacia atrás respecto al último estado
# dirty = hay que volver a revisar el historial (al regresar a Sculpt)
# Posición del slider = depth - back  (0 .. depth)
_state = {
    "depth": 0,
    "back": 0,
    "dirty": False,
    "busy": False,
    "scrubbing": False,
    "was_sculpt": False,
    "hover": False,
}
_handle = None
_keymaps = []


# ---------- Geometría ----------


def _ui():
    return bpy.context.preferences.system.ui_scale


def _limit(context):
    return max(1, min(MAX_STEPS, context.preferences.edit.undo_steps))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _free_rect(context):
    """Área del viewport no tapada por cabeceras, barra lateral ni toolbar."""
    area, space, win = context.area, context.space_data, context.region
    x0, y0, x1, y1 = 0.0, 0.0, float(win.width), float(win.height)

    visible = {
        "UI": space.show_region_ui,
        "TOOLS": space.show_region_toolbar,
        "HEADER": space.show_region_header,
        "TOOL_HEADER": space.show_region_tool_header,
    }
    for r in area.regions:
        if not visible.get(r.type, False):
            continue
        # Rectángulo de la región en coordenadas de la región principal
        rx0, ry0 = r.x - win.x, r.y - win.y
        rx1, ry1 = rx0 + r.width, ry0 + r.height
        if rx1 <= 0 or ry1 <= 0 or rx0 >= win.width or ry0 >= win.height:
            continue  # no se solapa con el viewport
        if r.type in {"HEADER", "TOOL_HEADER"}:
            if ry0 > win.height / 2:
                y1 = min(y1, ry0)
            else:
                y0 = max(y0, ry1)
        else:
            if rx0 > win.width / 2:
                x1 = min(x1, rx0)
            else:
                x0 = max(x0, rx1)
    return x0, y0, x1, y1


def _bar_rect(context):
    """Slider centrado arriba del área libre del viewport."""
    ui = _ui()
    fx0, fy0, fx1, fy1 = _free_rect(context)
    free_w = fx1 - fx0
    h = HEIGHT * ui
    w = min(free_w, max(120 * ui, min(free_w * WIDTH_FRAC, MAX_WIDTH * ui)))
    x = fx0 + (free_w - w) / 2
    y = max(fy0, fy1 - TOP_OFFSET * ui - h)
    return x, y, x + w, y + h


def _hit_bar(bar, mx, my):
    pad = HIT_PAD * _ui()
    x0, y0, x1, y1 = bar
    return x0 <= mx <= x1 and y0 - pad <= my <= y1 + pad


def _set_hover(window, over):
    """Cambia el cursor solo al entrar o salir del slider (llamadas balanceadas)."""
    if window is None:
        return
    if over and not _state["hover"]:
        window.cursor_modal_set(HOVER_CURSOR)
        _state["hover"] = True
    elif not over and _state["hover"]:
        window.cursor_modal_restore()
        _state["hover"] = False


# ---------- Historial ----------


def _redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _run(op):
    try:
        return op() == {"FINISHED"}
    except RuntimeError:
        return False


def _in_sculpt():
    return bpy.context.mode == "SCULPT"


def _undo_stroke():
    """Retrocede un paso de Sculpt.

    Cruza las fronteras de sesión (los estados fuera de Sculpt que dejan los
    cambios de pestaña). Si no hay más historial, vuelve a donde estaba y
    devuelve False.
    """
    moved, skipped, crossed = 0, 0, False
    while _run(bpy.ops.ed.undo):
        moved += 1
        if _in_sculpt():
            if not crossed:
                return True
            # Misma escultura al otro lado de la frontera: no cuenta como paso
            crossed, skipped = False, 0
            continue
        skipped += 1
        crossed = True
        if skipped > MAX_SKIP:
            break
    for _ in range(moved):  # llegamos al suelo: regresa a donde estaba
        _run(bpy.ops.ed.redo)
    return False


def _redo_stroke():
    """Avanza un paso de Sculpt (misma lógica que _undo_stroke, hacia delante)."""
    moved, skipped, crossed = 0, 0, False
    while _run(bpy.ops.ed.redo):
        moved += 1
        if _in_sculpt():
            if not crossed:
                return True
            crossed, skipped = False, 0
            continue
        skipped += 1
        crossed = True
        if skipped > MAX_SKIP:
            break
    for _ in range(moved):
        _run(bpy.ops.ed.undo)
    return False


def _goto(target):
    """Mueve el historial hasta 'target' pasos atrás, corrigiendo 'depth' si hace falta."""
    back, depth = _state["back"], _state["depth"]
    _state["busy"] = True  # ignora los handlers mientras lo hacemos nosotros
    try:
        while back < target:
            if not _undo_stroke():
                depth = back  # no hay más pasos atrás
                break
            back += 1
        while back > target:
            if not _redo_stroke():
                depth -= back  # ya estamos en el último estado real
                back = 0
                break
            back -= 1
        if back == 0:
            while _run(bpy.ops.ed.redo):  # termina en el último estado real
                pass
    finally:
        _state["busy"] = False
    _state["back"], _state["depth"] = back, max(depth, 0)
    _redraw_all()


def _rescan():
    """Vuelve a revisar el historial: va hasta el fondo, recuenta y regresa."""
    saved = _state["back"]
    _goto(MAX_STEPS)  # llega al suelo y recalcula 'depth'
    _goto(min(saved, _state["depth"]))  # vuelve a la posición anterior
    _state["dirty"] = False


# ---------- Dibujo (con los colores del tema de Blender) ----------


def _rgba(color, alpha=1.0):
    """Los colores del tema pueden tener 3 o 4 componentes."""
    c = tuple(color)
    return c if len(c) == 4 else (c[0], c[1], c[2], alpha)


def _rounded_points(x0, y0, x1, y1, r_left, r_right, seg=8):
    """Contorno de un rectángulo con esquinas redondeadas (izq. y der. independientes)."""
    pts = []

    def arc(cx, cy, r, a0, a1):
        if r <= 0:
            pts.append((cx, cy))  # con r=0 el centro es la esquina
            return
        for i in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * i / seg)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))

    arc(x0 + r_left, y0 + r_left, r_left, 180, 270)
    arc(x1 - r_right, y0 + r_right, r_right, 270, 360)
    arc(x1 - r_right, y1 - r_right, r_right, 0, 90)
    arc(x0 + r_left, y1 - r_left, r_left, 90, 180)
    return pts


def _fill_poly(shader, pts, color):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": [(cx, cy)] + pts + [pts[0]]})
    shader.uniform_float("color", color)
    batch.draw(shader)


def _outline_poly(shader, pts, color):
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": pts + [pts[0]]})
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_callback():
    context = bpy.context
    region = context.region
    if region is None or region.type != "WINDOW":
        return

    if context.mode != "SCULPT":
        _state["was_sculpt"] = False
        _set_hover(context.window, False)
        return
    if not _state["was_sculpt"]:
        # Volvimos a Sculpt (p. ej. al regresar de otra pestaña): el historial
        # se conserva, estamos en la punta y se revisará al usar la barra
        _state["was_sculpt"] = True
        _state["back"] = 0
        _state["dirty"] = True

    ui = _ui()
    theme = context.preferences.themes[0].user_interface.wcol_numslider
    font_size = context.preferences.ui_styles[0].widget.points * ui

    x0, y0, x1, y1 = _bar_rect(context)
    h = y1 - y0
    radius = min(theme.roundness, 1.0) * h / 2

    depth = _state["depth"]
    pos = max(0, depth - _state["back"])
    frac = pos / depth if depth > 0 else 0.0  # sin cambios -> 0

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")

    # Fondo del slider
    inner = theme.inner_sel if _state["scrubbing"] else theme.inner
    body = _rounded_points(x0, y0, x1, y1, radius, radius)
    _fill_poly(shader, body, _rgba(inner))

    # Relleno (borde derecho recto hasta llegar al final, como los sliders nativos)
    fill_w = (x1 - x0) * frac
    if fill_w >= 1.0:
        full = pos >= depth
        fill = _rounded_points(
            x0,
            y0,
            x0 + fill_w,
            y1,
            min(radius, fill_w),
            radius if full else 0.0,
        )
        _fill_poly(shader, fill, _rgba(theme.item))

    # Contorno
    _outline_poly(shader, body, _rgba(theme.outline))

    gpu.state.blend_set("NONE")

    # Texto: etiqueta a la izquierda y valor a la derecha
    blf.size(0, font_size)
    blf.color(0, *_rgba(theme.text))
    _w, text_h = blf.dimensions(0, "Ag")
    ty = y0 + (h - text_h) / 2 + 1 * ui
    pad = TEXT_PAD * ui

    blf.position(0, x0 + pad, ty, 0)
    blf.draw(0, LABEL)

    value = f"{pos} / {depth}"
    value_w, _h = blf.dimensions(0, value)
    blf.position(0, x1 - pad - value_w, ty, 0)
    blf.draw(0, value)


# ---------- Operador: arrastrar el slider ----------


class UNDOBAR_OT_scrub(bpy.types.Operator):
    """Arrastra el slider para moverte por el historial de Sculpt"""

    bl_idname = "undobar.scrub"
    bl_label = "Undo History Slider"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == "SCULPT"
            and context.region is not None
            and context.region.type == "WINDOW"
        )

    def invoke(self, context, event):
        mx, my = event.mouse_region_x, event.mouse_region_y

        # Fuera del slider: deja pasar el evento (esculpir normal)
        if not _hit_bar(_bar_rect(context), mx, my):
            if not event.alt:
                # Un clic en el viewport suele ser un trazo nuevo: descarta el
                # "redo" y suma un paso al historial
                position = _state["depth"] - _state["back"]
                _state["depth"] = min(position + 1, _limit(context))
                _state["back"] = 0
                _redraw_all()
            return {"CANCELLED", "PASS_THROUGH"}

        # Primera vez tras volver a Sculpt: vuelve a revisar el historial
        if _state["dirty"]:
            _rescan()

        self._start_back = _state["back"]
        _state["scrubbing"] = True
        self._scrub(context, mx)
        context.window_manager.modal_handler_add(self)
        _redraw_all()
        return {"RUNNING_MODAL"}

    def _scrub(self, context, mx):
        depth = _state["depth"]
        if depth == 0:
            return  # sin cambios de Sculpt: el slider se queda en 0
        x0, _y0, x1, _y1 = _bar_rect(context)
        frac = _clamp((mx - x0) / (x1 - x0), 0.0, 1.0)
        target = depth - round(frac * depth)
        if target != _state["back"]:
            _goto(target)

    def _end(self, context, event):
        _state["scrubbing"] = False
        over = _hit_bar(_bar_rect(context), event.mouse_region_x, event.mouse_region_y)
        _set_hover(context.window, over)
        _redraw_all()

    def modal(self, context, event):
        if event.type == "MOUSEMOVE":
            self._scrub(context, event.mouse_region_x)
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self._end(context, event)
            return {"FINISHED"}

        if event.type in {"ESC", "RIGHTMOUSE"}:
            _goto(self._start_back)  # cancela: vuelve a donde estaba
            self._end(context, event)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


class UNDOBAR_OT_hover(bpy.types.Operator):
    """Cambia el cursor al pasar el mouse sobre el slider"""

    bl_idname = "undobar.hover"
    bl_label = "Undo History Slider Hover"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == "SCULPT"
            and context.region is not None
            and context.region.type == "WINDOW"
        )

    def invoke(self, context, event):
        over = _hit_bar(_bar_rect(context), event.mouse_region_x, event.mouse_region_y)
        _set_hover(context.window, over)
        return {"CANCELLED", "PASS_THROUGH"}  # el evento sigue su camino


# ---------- Sincronización con Ctrl+Z / Ctrl+Shift+Z ----------


@persistent
def _undo_post(*_args):
    if _state["busy"] or not _in_sculpt():
        return  # fuera de Sculpt no tocamos el historial guardado
    _state["back"] = min(_state["back"] + 1, MAX_STEPS)
    _state["depth"] = max(_state["depth"], _state["back"])
    _redraw_all()


@persistent
def _redo_post(*_args):
    if _state["busy"] or not _in_sculpt():
        return
    _state["back"] = max(_state["back"] - 1, 0)
    _redraw_all()


# ---------- Registro ----------

classes = (UNDOBAR_OT_scrub, UNDOBAR_OT_hover)


def register():
    global _handle
    for cls in classes:
        bpy.utils.register_class(cls)

    _handle = bpy.types.SpaceView3D.draw_handler_add(
        _draw_callback, (), "WINDOW", "POST_PIXEL"
    )
    bpy.app.handlers.undo_post.append(_undo_post)
    bpy.app.handlers.redo_post.append(_redo_post)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Sculpt", space_type="EMPTY")
        kmi = km.keymap_items.new(
            UNDOBAR_OT_scrub.bl_idname, "LEFTMOUSE", "PRESS", head=True
        )
        _keymaps.append((km, kmi))
        kmi = km.keymap_items.new(
            UNDOBAR_OT_hover.bl_idname, "MOUSEMOVE", "ANY", head=True
        )
        _keymaps.append((km, kmi))


def unregister():
    global _handle
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()

    if bpy.context.window:
        _set_hover(bpy.context.window, False)

    if _undo_post in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(_undo_post)
    if _redo_post in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(_redo_post)

    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
