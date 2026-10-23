import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest

from alas_1440p.loader import AdapterFinder, check, manifest
from alas_1440p.patching import CompatibilityError
from conftest import ROOT, UPSTREAM


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'official'
    for entry in manifest()['modules'].values():
        destination = root / entry['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(UPSTREAM / entry['path']), str(destination))
    return root


def run(arguments, cwd, **kwargs):
    completed = subprocess.run([str(a) for a in arguments], cwd=str(cwd), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True, **kwargs)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout.strip()


def test_unrelated_upstream_updates_are_preserved(checkout):
    path = checkout / 'module/device/connection.py'
    path.write_text(path.read_text() + '\nUPSTREAM_NEW_FEATURE = True\n', encoding='utf-8')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    codes = check(checkout)
    assert 'UPSTREAM_NEW_FEATURE' in codes['module.device.connection'].co_names
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_changed_backend_is_rejected_before_any_adapter_executes(checkout):
    path = checkout / 'module/device/method/adb.py'
    source = path.read_text(encoding='utf-8')
    assert "self.adb_shell(['input', 'tap', x, y])" in source
    path.write_text(source.replace("self.adb_shell(['input', 'tap', x, y])",
                                   "self.adb_shell(['input', 'tap', y, x])"), encoding='utf-8')
    finder = AdapterFinder()
    with pytest.raises(CompatibilityError, match='Upstream method changed'):
        finder.prepare(checkout)
    assert not finder.cache and not finder.loaded


def test_already_patched_fork_is_not_patched_a_second_time(checkout):
    (checkout / 'module/device/resolution.py').touch()
    with pytest.raises(CompatibilityError, match='already has a resolution adapter'):
        check(checkout)


def test_official_update_remains_enabled_and_calls_the_original_updater():
    from deploy.git import GitManager
    updater = object.__new__(GitManager)
    updater.AutoUpdate = True
    updater.GitOverCdn = False
    updater.Repository = 'https://github.com/LmeSzinc/AzurLaneAutoScript'
    updater.Branch = 'master'
    updater.git_repository_init = Mock()
    updater.git_install()
    updater.git_repository_init.assert_called_once_with(
        repo=updater.Repository, source='origin', branch='master',
        proxy=updater.GitProxy, ssl_verify=updater.SSLVerify)
    assert updater.AutoUpdate is True


def test_normal_start_spawn_update_disable_and_uninstall(checkout, tmp_path):
    runtime = tmp_path / 'runtime'
    run([sys.executable, '-m', 'venv', '--without-pip', runtime], tmp_path)
    executable = runtime / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    for args in [
        ['init'], ['config', 'user.name', 'Plugin Test'],
        ['config', 'user.email', 'plugin-test@example.invalid'],
        ['add', '.'], ['commit', '-m', 'Official source snapshot'],
    ]:
        run(['git'] + args, checkout)
    run([executable, ROOT / 'install.py', '--alas', checkout], tmp_path)
    assert run(['git', 'status', '--porcelain'], checkout) == ''
    worker = tmp_path / 'spawn_probe.py'
    worker.write_text('''
import json
import multiprocessing
import sys
from pathlib import Path

def worker(queue, root):
    import alas_1440p.loader as loader
    active = loader._finder is not None and Path(root) in loader._finder.roots
    queue.put([active, len(loader._finder.prepare(Path(root)))])

if __name__ == '__main__':
    import alas_1440p.loader as loader
    assert loader._finder is not None
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    process = context.Process(target=worker, args=(queue, sys.argv[1]))
    process.start()
    value = queue.get(timeout=30)
    process.join(timeout=30)
    assert process.exitcode == 0
    print(json.dumps(value))
''', encoding='utf-8')
    assert json.loads(run([executable, worker, checkout], tmp_path)) == [True, 16]
    run(['git', 'reset', '--hard', 'HEAD'], checkout)
    assert json.loads(run([executable, worker, checkout], tmp_path)) == [True, 16]
    run([executable, '-m', 'alas_1440p', 'disable'], tmp_path)
    assert run([executable, '-I', '-c', 'import alas_1440p.loader as p; print(p._finder is None)'], tmp_path) == 'True'
    run([executable, '-m', 'alas_1440p', 'enable'], tmp_path)
    assert json.loads(run([executable, worker, checkout], tmp_path)) == [True, 16]
    # Reinstallation exercises the installed old package's startup hook too.
    run([executable, ROOT / 'install.py', '--alas', checkout], tmp_path)
    run([executable, ROOT / 'install.py', '--alas', checkout, '--uninstall'], tmp_path)
    assert run([executable, '-I', '-c', 'import importlib.util; print(importlib.util.find_spec("alas_1440p"))'], tmp_path) == 'None'
    assert run(['git', 'status', '--porcelain'], checkout) == ''
