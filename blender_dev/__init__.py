import importlib

from . import baking, lock_proportions, node_preview, undo_history

modules = (baking, lock_proportions, node_preview, undo_history)

for m in modules:
    importlib.reload(m)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
