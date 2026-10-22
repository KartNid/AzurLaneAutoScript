"""Read-only local emulator checks. Uses the current checkout, never starts Alas.

Run using an existing Alas Python environment:
    toolkit/python.exe dev_tools/resolution_probe.py --serial 127.0.0.1:16448
An offline screenshot can be checked with --image native.png instead.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def adb_command(adb, arguments, timeout=20):
    completed = subprocess.run([str(adb)] + list(arguments), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout, check=False)
    if completed.returncode:
        error = completed.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError('ADB command failed: ' + error)
    return completed.stdout


def find_adb(explicit=None):
    if explicit:
        executable = Path(explicit).expanduser().resolve()
        if not executable.is_file():
            raise RuntimeError('ADB executable does not exist: ' + str(executable))
        return str(executable)
    for relative in ('tools/platform-tools/adb.exe',
                     'toolkit/Lib/site-packages/adbutils/binaries/adb.exe',
                     'bin/adb/adb.exe'):
        candidate = ROOT / relative
        if candidate.is_file():
            return str(candidate)
    executable = shutil.which('adb')
    if executable:
        return executable
    raise RuntimeError('ADB was not found. Specify --adb with its executable path.')


def capture(adb, serial):
    # Connect only the explicitly selected device. Do not kill another ADB server,
    # enumerate private files, install applications or change display settings.
    if ':' in serial:
        adb_command(adb, ['connect', serial])
    prefix = ['-s', serial]
    state = adb_command(adb, prefix + ['get-state']).decode('utf-8').strip()
    if state != 'device':
        raise RuntimeError('ADB device is not ready: ' + state)
    display = adb_command(adb, prefix + ['shell', 'dumpsys', 'display']).decode('utf-8', errors='replace')
    match = re.search(r'DisplayViewport\{[^\n]*?orientation=(\d+)', display)
    orientation = int(match.group(1)) if match else 0
    png = adb_command(adb, prefix + ['exec-out', 'screencap', '-p'])
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('ADB did not return a PNG screenshot.')
    return png, orientation


def recognize(raw, orientation, server_name, output, skip_ocr=False):
    import numpy as np
    from PIL import Image, ImageDraw
    import module.config.server as server
    server.set_server(server_name)
    from module.device.screenshot import Screenshot

    # Exercise the same public screenshot pipeline as the application, without
    # initializing Connection, starting game tasks, or touching user config.
    device = object.__new__(Screenshot)
    device.orientation = orientation
    device.config = SimpleNamespace(
        Emulator_ScreenshotMethod='ADB', Emulator_ScreenshotDedithering=False,
        Emulator_Serial='probe', Error_SaveError=False)
    device._screenshot_interval = SimpleNamespace(wait=lambda: None, reset=lambda: None)
    device.__dict__['screenshot_methods'] = {'ADB': lambda: raw}
    device.get_orientation = lambda: orientation
    image = device.screenshot()
    if image.shape[:2] != (720, 1280):
        raise RuntimeError('Screenshot did not normalize to a 1280x720 game frame.')
    Image.fromarray(device.image_native).save(str(output / 'native.png'))
    Image.fromarray(image).save(str(output / 'recognition.png'))

    result = {'native_size': list(device.native_screen_size),
              'recognition_size': [image.shape[1], image.shape[0]],
              'input_mapping': {'status': 'calculated_only', 'events_sent': 0,
                                'logical_center': [640, 360],
                                'native_center': list(device.control_point(640, 360))},
              'pages': [], 'template_errors': []}
    from module.ui.page import Page
    overlay = Image.fromarray(device.image_native.copy())
    draw = ImageDraw.Draw(overlay)
    for page in Page.iter_pages():
        button = page.check_button
        if button is None:
            continue
        try:
            matched = bool(button.match(image, offset=(20, 20), similarity=0.85))
            if matched:
                area = [int(value) for value in button.button]
                native_area = (*device.control_point(*area[:2]), *device.control_point(*area[2:]))
                result['pages'].append({'page': page.name, 'button': button.name,
                                        'logical_area': area, 'native_area': list(native_area)})
                draw.rectangle(native_area, outline=(255, 0, 0), width=3)
        except Exception as error:
            result['template_errors'].append({'page': page.name, 'error': str(error)})
    overlay.save(str(output / 'recognition_overlay.png'))

    main_visible = any(item['page'] in ('page_main', 'page_main_white') for item in result['pages'])
    if skip_ocr:
        result['ocr'] = {'status': 'skipped', 'reason': '--skip-ocr was specified'}
    elif not main_visible:
        result['ocr'] = {'status': 'skipped', 'reason': 'Resource counter OCR requires the game home page'}
    else:
        # Use the bundled model locally. This avoids selecting an OCR RPC server
        # or rewriting deploy.yaml from an existing user installation.
        from module.base.utils import crop, extract_letters
        from module.campaign.assets import OCR_COIN
        from module.ocr.models import OCR_MODEL
        letter = (201, 201, 201) if server_name == 'jp' else (239, 239, 239)
        region = crop(image, OCR_COIN.area)
        Image.fromarray(region).save(str(output / 'ocr_coin_crop.png'))
        prepared = extract_letters(region, letter=letter, threshold=128).astype(np.uint8)
        model = OCR_MODEL.azur_lane_jp if server_name == 'jp' else OCR_MODEL.azur_lane
        text = ''.join(model.atomic_ocr_for_single_line(prepared, '0123456789IDSB'))
        result['ocr'] = {'status': 'executed_requires_visual_check', 'coin_text': text,
                         'logical_area': list(OCR_COIN.area)}
    return result


def write_report(output, report):
    path = output / 'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    archive_path = output / 'resolution-report.zip'
    with zipfile.ZipFile(str(archive_path), 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output.iterdir()):
            if item.is_file() and item.suffix in ('.json', '.png'):
                archive.write(str(item), item.name)
    return archive_path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only Alas resolution and recognition probe')
    parser.add_argument('--serial', default='127.0.0.1:16448')
    parser.add_argument('--adb')
    parser.add_argument('--image', type=Path, help='Check an existing screenshot without connecting to ADB')
    parser.add_argument('--orientation', type=int, choices=(0, 1, 2, 3), default=0,
                        help='Orientation of an offline screenshot')
    parser.add_argument('--server', choices=('cn', 'en', 'jp', 'tw'), default='cn')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--skip-ocr', action='store_true')
    args = parser.parse_args(argv)
    image_path = args.image.resolve() if args.image else None
    output = args.output.resolve() if args.output else ROOT / 'log/resolution_probe' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'failed', 'read_only': True, 'device_actions_verified': False,
              'source': 'offline_image' if image_path else 'adb',
              'serial': None if image_path else args.serial, 'server': args.server,
              'python_version': sys.version.split()[0]}
    sys.path.insert(0, str(ROOT))
    os.chdir(str(ROOT))
    exit_code = 1
    try:
        import io
        import numpy as np
        from PIL import Image
        if image_path:
            png = image_path.read_bytes()
            orientation = args.orientation
        else:
            png, orientation = capture(find_adb(args.adb), args.serial)
        with Image.open(io.BytesIO(png)) as image:
            raw = np.array(image.convert('RGB'))
        (output / 'capture.png').write_bytes(png)
        report['orientation'] = orientation
        report['checks'] = recognize(raw, orientation, args.server, output, args.skip_ocr)
        pages = report['checks']['pages']
        if report['checks']['template_errors']:
            report['status'] = 'recognition_errors'
        elif pages:
            report['status'] = 'recognition_checked_input_not_exercised'
            exit_code = 0
        else:
            report['status'] = 'no_known_game_page_detected'
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        print('Probe failed: ' + report['error'])
    archive = write_report(output, report)
    print('Status: ' + report['status'])
    print('No clicks, swipes, game tasks, app installation or display changes were sent.')
    print('Report: ' + str(archive))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
