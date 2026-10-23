import argparse
import json
import os
from pathlib import Path
import sys

from . import __version__
from .loader import PACKAGE, check, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Alas external 1440P adapter')
    parser.add_argument('command', choices=['status', 'check', 'enable', 'disable', 'probe'])
    parser.add_argument('--alas', type=Path, default=Path.cwd())
    args, extra = parser.parse_known_args(argv)
    if args.command == 'probe':
        from . import activate
        root = args.alas.resolve()
        sys.path.insert(0, str(root))
        os.chdir(str(root))
        activate(root)
        from . import probe
        probe.ROOT = root
        return probe.main(extra)
    if extra:
        parser.error('Unrecognized arguments: ' + ' '.join(extra))
    path = PACKAGE / 'settings.json'
    settings = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(schema=1, enabled=False, roots=[])
    if args.command in ('enable', 'disable'):
        if not path.exists():
            parser.error('Install the plugin first with the official Alas Python interpreter.')
        if args.command == 'enable':
            for root in settings['roots']:
                check(root)
        settings['enabled'] = args.command == 'enable'
        path.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
        print('Plugin ' + args.command + 'd. Restart Alas to apply.')
    elif args.command == 'check':
        result = check(args.alas)
        print('Compatible: ' + str(len(result)) + ' upstream modules; no files changed.')
    else:
        print(json.dumps(dict(version=__version__, settings=settings,
                              baseline=manifest()['baseline'], package=str(PACKAGE)), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
