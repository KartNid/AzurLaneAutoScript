"""Regenerate the reviewed adapter from the existing 1440P branch."""
import ast
import argparse
import json
from pathlib import Path
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from alas_1440p.patching import fingerprint, keyed

REPO = None
BASE = '4d88c22d875de3192f8cae2f993e4fe0593114e0'
FEATURE = '2efcbcb4d07bcff5798e577e9f26c4d6d30dc6a4'


def read(revision, path):
    return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=str(REPO)).decode('utf-8')


def snippet(node, source):
    lines = source.splitlines(True)
    first = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
    return textwrap.dedent(''.join(lines[first - 1:node.end_lineno]))


def compare(old, new, source, path=()):
    operations = []
    old_nodes = dict(keyed(old.body))
    new_nodes = keyed(new.body)
    previous = None
    for key, node in new_nodes:
        node_path = list(path) + [key]
        before = old_nodes.get(key)
        if before is None:
            operations.append(dict(action='add', path=node_path, after=previous, source=snippet(node, source)))
        elif isinstance(node, ast.ClassDef):
            header = [node.bases, node.keywords, node.decorator_list]
            old_header = [before.bases, before.keywords, before.decorator_list]
            if fingerprint(header) != fingerprint(old_header):
                shell = ast.ClassDef(name=node.name, bases=node.bases, keywords=node.keywords,
                                     body=[ast.Pass()], decorator_list=node.decorator_list)
                operations.append(dict(action='header', path=node_path, before=fingerprint(old_header),
                                       source=ast.unparse(ast.fix_missing_locations(shell))))
            operations.extend(compare(before, node, source, node_path))
        elif fingerprint(node) != fingerprint(before):
            operations.append(dict(action='replace', path=node_path, before=fingerprint(before),
                                   source=snippet(node, source)))
        previous = key
    removed = set(old_nodes) - {key for key, _ in new_nodes}
    if removed:
        raise RuntimeError('Unexpected deleted units: ' + str(removed))
    return operations


def main():
    global REPO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True, help='Checkout containing both baseline and feature commits')
    REPO = parser.parse_args().repo.resolve()
    paths = subprocess.check_output(['git', 'diff', '--name-only', BASE, FEATURE, '--', 'module'], cwd=str(REPO)).decode().splitlines()
    modules = {}
    for path in paths:
        if path == 'module/device/resolution.py':
            continue
        old, new = read(BASE, path), read(FEATURE, path)
        operations = compare(ast.parse(old), ast.parse(new), new)
        modules[path[:-3].replace('/', '.')] = dict(path=path, operations=operations)
    manifest = dict(schema=1, baseline=BASE, feature=FEATURE, modules=modules)
    (ROOT / 'alas_1440p' / 'patches.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(modules), 'modules;', sum(len(m['operations']) for m in modules.values()), 'guarded changes')


if __name__ == '__main__':
    main()
