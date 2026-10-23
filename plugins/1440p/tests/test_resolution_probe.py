import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

from PIL import Image
import pytest

from dev_tools import resolution_probe as probe


def png_bytes(size=(2560, 1440)):
    stream = io.BytesIO()
    Image.new('RGB', size, (40, 40, 40)).save(stream, format='PNG')
    return stream.getvalue()


def test_capture_only_sends_read_only_adb_commands(monkeypatch):
    commands = []
    screenshot = png_bytes()

    def command(adb, arguments, timeout=20):
        commands.append(arguments)
        if arguments == ['connect', '127.0.0.1:16448']:
            return b'connected'
        if arguments[-1] == 'get-state':
            return b'device\n'
        if arguments[-2:] == ['dumpsys', 'display']:
            return b'DisplayViewport{valid=true, orientation=1, deviceWidth=1440, deviceHeight=2560}'
        if arguments[-3:] == ['exec-out', 'screencap', '-p']:
            return screenshot
        raise AssertionError(arguments)

    monkeypatch.setattr(probe, 'adb_command', command)
    assert probe.capture('adb.exe', '127.0.0.1:16448') == (screenshot, 1)
    assert len(commands) == 4
    assert all('input' not in command and 'install' not in command for command in commands)


def test_capture_rejects_non_png_data(monkeypatch):
    def command(adb, arguments, timeout=20):
        return b'device' if arguments[-1] == 'get-state' else b'not a screenshot'
    monkeypatch.setattr(probe, 'adb_command', command)
    with pytest.raises(RuntimeError, match='PNG'):
        probe.capture('adb', 'emulator-5554')


def test_adb_failure_is_preserved(monkeypatch):
    monkeypatch.setattr(probe.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=b'', stderr=b'device offline'))
    with pytest.raises(RuntimeError, match='device offline'):
        probe.adb_command('adb', ['-s', 'test', 'get-state'])


def test_readiness_state_is_checked_even_if_connect_returns_zero(monkeypatch):
    monkeypatch.setattr(probe, 'adb_command', lambda adb, arguments: (
        b'offline' if arguments[-1] == 'get-state' else b'failed to connect'))
    with pytest.raises(RuntimeError, match='not ready'):
        probe.capture('adb', '127.0.0.1:16448')


def test_report_contains_only_explicit_json_and_image_artifacts(tmp_path):
    (tmp_path / 'native.png').write_bytes(png_bytes((1280, 720)))
    (tmp_path / 'unrelated.txt').write_text('do not include')
    archive = probe.write_report(tmp_path, {'read_only': True})
    with zipfile.ZipFile(str(archive)) as content:
        assert set(content.namelist()) == {'report.json', 'native.png'}
        assert json.loads(content.read('report.json')) == {'read_only': True}


@pytest.mark.parametrize('factor', [1, 2])
def test_offline_probe_runs_full_recognition_pipeline(tmp_path, factor, monkeypatch):
    root = Path(probe.ROOT)
    with Image.open(str(root / 'assets/cn/ui/MAIN_GOTO_FLEET.png')) as source:
        source.resize((1280 * factor, 720 * factor), resample=Image.NEAREST).save(str(tmp_path / 'source.png'))
    output = tmp_path / 'report'
    monkeypatch.setattr(probe, 'capture', lambda *args: pytest.fail('Offline mode must not contact ADB'))
    code = probe.main(['--image', str(tmp_path / 'source.png'), '--output', str(output), '--skip-ocr'])
    report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    assert code == 0, report
    assert report['read_only'] and not report['device_actions_verified']
    assert report['checks']['native_size'] == [1280 * factor, 720 * factor]
    assert report['checks']['recognition_size'] == [1280, 720]
    assert report['checks']['input_mapping']['events_sent'] == 0
    assert report['checks']['ocr']['status'] == 'skipped'
    assert any(page['page'] == 'page_main' for page in report['checks']['pages'])
    assert (output / 'resolution-report.zip').is_file()


def test_failed_capture_still_creates_a_diagnostic_report(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, 'find_adb', lambda explicit: 'adb')
    def refused(*args):
        raise RuntimeError('Connection refused')
    monkeypatch.setattr(probe, 'capture', refused)
    output = tmp_path / 'failure'
    assert probe.main(['--output', str(output)]) == 1
    report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    assert report['status'] == 'failed'
    assert 'Connection refused' in report['error']
    assert not report['device_actions_verified']
