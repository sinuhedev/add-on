import importlib

from . import lock_proportions, node_preview

modules = (lock_proportions, node_preview)

for m in modules:
    importlib.reload(m)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
