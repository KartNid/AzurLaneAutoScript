"""Load device adapters without changing the official Alas checkout."""
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys

from . import __version__
from .patching import CompatibilityError, transform

PACKAGE = Path(__file__).resolve().parent
_finder = None


def manifest():
    return json.loads((PACKAGE / 'patches.json').read_text(encoding='utf-8'))


def check(root):
    root = Path(root).resolve()
    if (root / 'module' / 'device' / 'resolution.py').exists():
        raise CompatibilityError('This checkout already has a resolution adapter. Use an official 720P installation: ' + str(root))
    compiled = {}
    for name, entry in manifest()['modules'].items():
        path = root / entry['path']
        if not path.is_file():
            raise CompatibilityError('Upstream module is missing: ' + str(path))
        source = path.read_text(encoding='utf-8-sig')
        tree = transform(source, entry['operations'], str(path))
        compiled[name] = compile(tree, str(path), 'exec')
    return compiled


class AdapterLoader(importlib.abc.Loader):
    def __init__(self, finder, root, fullname, original=None):
        self.finder, self.root, self.fullname = finder, root, fullname
        self.original_loader = original.loader if original is not None else None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        compiled = self.finder.prepare(self.root)
        if self.fullname == 'module.device.resolution':
            path = PACKAGE / 'resolution.py'
            code = compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        else:
            code = compiled[self.fullname]
        exec(code, module.__dict__)
        module.__alas_1440p_version__ = __version__
        self.finder.loaded.add(self.fullname)

    def get_source(self, fullname):
        if self.original_loader is not None and hasattr(self.original_loader, 'get_source'):
            return self.original_loader.get_source(fullname)
        return (PACKAGE / 'resolution.py').read_text(encoding='utf-8')


class AdapterFinder(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.roots = set()
        self.cache = {}
        self.loaded = set()
        self.modules = manifest()['modules']

    def prepare(self, root):
        if root not in self.cache:
            # Validate every touched interface before executing the first adapter.
            self.cache[root] = check(root)
            sys.stderr.write('[Alas 1440P plugin ' + __version__ + '] active: ' + str(root) + '\n')
        return self.cache[root]

    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'module.device.resolution':
            for root in self.roots:
                directory = root / 'module' / 'device'
                if path and any(Path(p).resolve() == directory for p in path):
                    loader = AdapterLoader(self, root, fullname)
                    return importlib.util.spec_from_file_location(fullname, str(PACKAGE / 'resolution.py'), loader=loader)
            return None
        if fullname not in self.modules:
            return None
        original = importlib.machinery.PathFinder.find_spec(fullname, path)
        if original is None or original.origin is None:
            return None
        for root in self.roots:
            if Path(original.origin).resolve() == root / self.modules[fullname]['path']:
                original.loader = AdapterLoader(self, root, fullname, original)
                return original
        return None


def activate(root):
    global _finder
    root = Path(root).resolve()
    if _finder is not None and root in _finder.roots:
        return _finder
    names = set(manifest()['modules']) | {'module.device.resolution'}
    for name in names:
        module = sys.modules.get(name)
        origin = getattr(module, '__file__', None)
        if origin and root in Path(origin).resolve().parents:
            raise CompatibilityError('The device modules are already loaded. Restart Alas before enabling the plugin.')
    if _finder is None:
        _finder = AdapterFinder()
        sys.meta_path.insert(0, _finder)
    _finder.roots.add(root)
    return _finder


def autoload():
    if os.environ.get('ALAS_1440P_DISABLE') == '1':
        return None
    settings_path = PACKAGE / 'settings.json'
    if not settings_path.is_file():
        return None
    settings = json.loads(settings_path.read_text(encoding='utf-8'))
    if settings.get('schema') != 1:
        raise CompatibilityError('Unsupported 1440P plugin configuration; reinstall the plugin.')
    if settings.get('enabled', True):
        for root in settings['roots']:
            activate(root)
    return _finder
