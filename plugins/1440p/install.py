"""Install using the Python interpreter belonging to the official Alas copy."""
import argparse
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile

SOURCE = Path(__file__).resolve().parent / 'alas_1440p'
PTH_CONTENT = b'import alas_1440p; alas_1440p.autoload()\n'


def local_loader():
    # An older installed version may have been imported by its .pth at startup.
    name = '_alas_1440p_installer'
    spec = importlib.util.spec_from_file_location(name, str(SOURCE / '__init__.py'),
                                                submodule_search_locations=[str(SOURCE)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return importlib.import_module(name + '.loader')


def read_settings(package):
    path = package / 'settings.json'
    if not path.exists():
        return dict(schema=1, enabled=True, roots=[])
    settings = json.loads(path.read_text(encoding='utf-8'))
    if settings.get('schema') != 1:
        raise RuntimeError('Unknown existing plugin configuration; preserve it and upgrade manually.')
    return settings


def install(root, site):
    local_loader().check(root)
    site.mkdir(parents=True, exist_ok=True)
    destination = site / 'alas_1440p'
    pth = site / 'alas_1440p.pth'
    old_pth = pth.read_bytes() if pth.exists() else None
    if old_pth is not None and old_pth != PTH_CONTENT:
        raise RuntimeError('An unrelated alas_1440p.pth exists; leaving it untouched.')
    settings = read_settings(destination)
    if str(root) not in settings['roots']:
        settings['roots'].append(str(root))
    settings['enabled'] = True
    with tempfile.TemporaryDirectory(prefix='alas-plugin-install-', dir=str(site)) as temporary:
        stage = Path(temporary)
        package = stage / 'package'
        shutil.copytree(str(SOURCE), str(package), ignore=shutil.ignore_patterns('__pycache__', 'settings.json'))
        (package / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
        backup = stage / 'previous'
        if destination.exists():
            destination.rename(backup)
        try:
            package.rename(destination)
            pth.write_bytes(PTH_CONTENT)
            code = ('import alas_1440p.loader as p; from pathlib import Path; '
                    'assert p._finder is not None and Path(' + repr(str(root)) + ').resolve() in p._finder.roots; '
                    'print("Alas 1440P startup hook OK")')
            result = subprocess.run([sys.executable, '-I', '-c', code], cwd=temporary,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode != 0:
                raise RuntimeError('Python did not load the .pth startup hook. Installation rolled back.\n' + result.stderr)
        except Exception:
            if destination.exists():
                shutil.rmtree(str(destination))
            if backup.exists():
                backup.rename(destination)
            if old_pth is None:
                if pth.exists():
                    pth.unlink()
            else:
                pth.write_bytes(old_pth)
            raise
    print('Installed: ' + str(destination))
    print('Use the original Alas.exe launcher; its updater and configuration are unchanged.')


def uninstall(root, site):
    package = site / 'alas_1440p'
    pth = site / 'alas_1440p.pth'
    settings = read_settings(package)
    settings['roots'] = [p for p in settings['roots'] if Path(p).resolve() != root]
    if settings['roots']:
        (package / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
    else:
        if pth.exists():
            if pth.read_bytes() != PTH_CONTENT:
                raise RuntimeError('Startup file changed; leaving the installation untouched.')
            pth.unlink()
        if package.exists():
            shutil.rmtree(str(package))
    print('Plugin removed for ' + str(root) + '. Restart Alas and use 1280x720.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alas', required=True, type=Path, help='Official Alas directory')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args(argv)
    root = args.alas.expanduser().resolve()
    site = Path(sysconfig.get_path('purelib')).resolve()
    if args.uninstall:
        uninstall(root, site)
    else:
        install(root, site)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('1440P plugin: ' + str(error), file=sys.stderr)
        sys.exit(1)
