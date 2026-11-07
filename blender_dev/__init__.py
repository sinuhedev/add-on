import importlib

from . import hola, lock_proportions

modules = (hola, lock_proportions)

for m in modules:
    importlib.reload(m)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
