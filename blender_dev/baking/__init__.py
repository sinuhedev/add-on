import bpy


class HOLA_OT_mundo(bpy.types.Operator):
    """Muestra un saludo"""

    bl_idname = "hola.mundo"
    bl_label = "Decir Hola"

    def execute(self, context):
        self.report({"INFO"}, "¡Hola Mundo!")
        return {"FINISHED"}


class HOLA_PT_panel(bpy.types.Panel):
    bl_label = "Hola Mundo"
    bl_idname = "HOLA_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Hola"

    def draw(self, context):
        self.layout.operator("hola.mundo")


classes = (HOLA_OT_mundo, HOLA_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
