import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty


def _make_getter(axis):
    def getter(self):
        obj = bpy.context.object
        return obj.dimensions[axis] if obj else 0.0

    return getter


def _make_setter(axis):
    def setter(self, value):
        obj = bpy.context.object
        if obj is None:
            return
        dims = obj.dimensions.copy()
        old = dims[axis]
        if self.lock and old != 0.0:
            # Con el candado activo, escala los tres ejes con el mismo factor
            dims = dims * (value / old)
        else:
            dims[axis] = value
        obj.dimensions = dims

    return setter


def _dim_prop(axis, name):
    return FloatProperty(
        name=name,
        subtype="DISTANCE",
        unit="LENGTH",
        get=_make_getter(axis),
        set=_make_setter(axis),
    )


class DIMLOCK_Props(bpy.types.PropertyGroup):
    lock: BoolProperty(
        name="Lock Proportions",
        description="Keep the proportions of the dimensions when editing one axis",
        default=True,
    )
    x: _dim_prop(0, "X")
    y: _dim_prop(1, "Y")
    z: _dim_prop(2, "Z")


class DIMLOCK_PT_panel(bpy.types.Panel):
    bl_label = "Proportional Dimensions"
    bl_idname = "DIMLOCK_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        props = context.window_manager.dimlock
        row = self.layout.row(align=True)

        col = row.column(align=True)
        col.prop(props, "x")
        col.prop(props, "y")
        col.prop(props, "z")

        lock_col = row.column(align=True)
        lock_col.scale_y = 3.0
        lock_col.prop(
            props,
            "lock",
            text="",
            icon="LOCKED" if props.lock else "UNLOCKED",
        )


classes = (DIMLOCK_Props, DIMLOCK_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.dimlock = PointerProperty(type=DIMLOCK_Props)


def unregister():
    del bpy.types.WindowManager.dimlock
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
