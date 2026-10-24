"""Optional 1440P adapter for an otherwise unmodified Alas installation."""
__version__ = '0.1.2'


def autoload():
    from .loader import autoload as load
    return load()


def activate(root):
    from .loader import activate as load
    return load(root)
