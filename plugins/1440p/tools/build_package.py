"""Build a portable plugin ZIP and a per-file verification manifest."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--passed', type=int, required=True)
    parser.add_argument('--skipped', type=int, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / 'alas_1440p/__init__.py').read_text(encoding='utf-8'))
    version = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets))
    patches = json.loads((root / 'alas_1440p/patches.json').read_text(encoding='utf-8'))
    files = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if (not path.is_file() or '__pycache__' in relative.parts
                or path.suffix == '.pyc' or path.name in ('settings.json', 'BUILD_MANIFEST.json')
                or any(part.startswith('.pytest') for part in relative.parts)):
            continue
        files[relative.as_posix()] = path.read_bytes()
    manifest = dict(version=version, upstream=patches['baseline'],
                    tests=dict(passed=args.passed, skipped=args.skipped),
                    files={name: dict(sha256=hashlib.sha256(data).hexdigest(), size=len(data))
                           for name, data in files.items()})
    files['BUILD_MANIFEST.json'] = (json.dumps(manifest, indent=2)+'\n').encode('utf-8')
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / ('Alas-1440P-Plugin-'+version+'.zip')
    with zipfile.ZipFile(str(archive), 'w', zipfile.ZIP_DEFLATED) as output:
        for name, data in files.items():
            output.writestr(name, data)
    with zipfile.ZipFile(str(archive)) as output:
        assert set(output.namelist()) == set(files)
        for name, record in manifest['files'].items():
            assert hashlib.sha256(output.read(name)).hexdigest() == record['sha256'], name
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n', encoding='utf-8')
    print(str(archive))
    print('SHA256: '+digest)
    print('Verified '+str(len(manifest['files']))+' packaged files.')


if __name__ == '__main__':
    main()
