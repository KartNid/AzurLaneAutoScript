"""Exercise native frames through recognition and the input transport boundary.

No emulator, network access or Connection initialization is used in these tests.
"""
import json
import struct
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
from lxml import etree
from PIL import Image

from module.base.button import Button
from module.base.mask import Mask
from module.base.template import Template
from module.base.utils import crop, get_color
from module.device.control import Control
from module.device.method.adb import Adb, load_screencap
from module.device.method.droidcast import DroidCast, DroidCastVersionIncompatible
from module.device.method.maatouch import MaatouchBuilder
from module.device.method.minitouch import CommandBuilder
from module.device.method.scrcpy.control import ControlSender
from module.device.method.scrcpy.options import ScrcpyOptions
from module.device.method.utils import HierarchyButton
from module.device.resolution import ASSET_SIZE, Resolution, normalize_screenshot
from module.device.screenshot import Screenshot
from module.exception import RequestHumanTakeover
from module.ocr.ocr import Ocr


@pytest.fixture
def logical_image():
    image = np.full((720, 1280, 3), 40, dtype=np.uint8)
    # A textured target prevents a constant template from matching everywhere.
    pattern = np.random.RandomState(7).randint(0, 2, (30, 80, 1)).astype(np.uint8) * 255
    image[120:150, 100:180] = np.repeat(pattern, 3, axis=2)
    image[400:440, 700:760] = (210, 150, 80)
    return image


def screenshot_device(image, method='ADB'):
    device = object.__new__(Screenshot)
    device.config = SimpleNamespace(
        Emulator_ScreenshotMethod=method, Emulator_ScreenshotDedithering=False,
        Emulator_Serial='test', Error_SaveError=True, Error_ScreenshotLength=3)
    device.orientation = 0
    device._screenshot_interval = SimpleNamespace(wait=Mock(), reset=Mock())
    device.__dict__['screenshot_methods'] = {method: lambda: image}
    return device


def control_device(size):
    device = object.__new__(Control)
    device.set_screen_size(*size)
    device.config = SimpleNamespace(DEVICE_OVER_HTTP=False, Emulator_ControlMethod='ADB')
    device.sleep = Mock()
    device.__dict__['u2'] = Mock()
    device.adb_shell = Mock()
    return device


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
@pytest.mark.parametrize('method', [
    'ADB', 'ADB_nc', 'uiautomator2', 'aScreenCap', 'aScreenCap_nc',
    'DroidCast', 'DroidCast_raw', 'scrcpy', 'nemu_ipc', 'ldopengl',
])
def test_every_screenshot_dispatch_normalizes_before_recognition(logical_image, size, method):
    raw = cv2.resize(logical_image, size, interpolation=cv2.INTER_NEAREST)
    device = screenshot_device(raw, method)
    np.testing.assert_array_equal(device.screenshot(), logical_image)
    assert device.native_screen_size == size
    assert device.image_native is raw
    assert device.screenshot_deque[-1]['image'].shape == (720, 1280, 3)


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
@pytest.mark.parametrize('orientation', [1, 3])
def test_portrait_capture_rotates_then_normalizes(logical_image, size, orientation):
    landscape = cv2.resize(logical_image, size, interpolation=cv2.INTER_NEAREST)
    rotation = cv2.ROTATE_90_CLOCKWISE if orientation == 1 else cv2.ROTATE_90_COUNTERCLOCKWISE
    device = screenshot_device(cv2.rotate(landscape, rotation))
    device.orientation = orientation
    device.get_orientation = Mock(return_value=orientation)
    np.testing.assert_array_equal(device.screenshot(), logical_image)
    assert device.native_screen_size == size


def test_landscape_backend_is_not_rotated_twice(logical_image):
    device = screenshot_device(cv2.resize(logical_image, (2560, 1440)))
    device.orientation = 1
    assert device.screenshot().shape == (720, 1280, 3)


def test_size_is_rechecked_after_resolution_changes(logical_image):
    device = screenshot_device(logical_image)
    device.screenshot()
    device.screenshot_methods['ADB'] = lambda: np.full((1440, 2560, 3), 100, np.uint8)
    device.screenshot()
    assert device.control_point(600, 300) == (1200, 600)
    device.image = np.zeros((1080, 1920, 3), np.uint8)
    device.app_is_running = lambda: True
    with pytest.raises(RequestHumanTakeover):
        device.check_screen_size()


def test_720p_normalization_is_zero_copy(logical_image):
    assert normalize_screenshot(logical_image) is logical_image


def test_capture_resize_does_not_modify_native_pixels(logical_image):
    native = cv2.resize(logical_image, (2560, 1440))
    original = native.copy()
    normalized = normalize_screenshot(native)
    normalized[:] = 0
    np.testing.assert_array_equal(native, original)


def test_templates_color_masks_and_click_share_the_same_geometry(logical_image, tmp_path):
    asset = tmp_path / 'button.png'
    Image.fromarray(logical_image).save(str(asset))
    device = screenshot_device(cv2.resize(logical_image, (2560, 1440), interpolation=cv2.INTER_NEAREST))
    image = device.screenshot()
    area = (100, 120, 180, 150)
    button = Button(area, tuple(get_color(logical_image, area)), area, file=str(asset), name='target')
    for method in (button.match, button.match_binary, button.match_luma):
        assert method(image, offset=(20, 20), similarity=0.99)
        assert tuple(button.button) == area
    assert button.appear_on(image)
    assert get_color(image, (700, 400, 760, 440)) == pytest.approx((210, 150, 80))

    template = Template(str(asset))
    template.image = crop(logical_image, area)
    matches = template.match_multi(image, similarity=0.99)
    assert len(matches) == 1
    assert tuple(matches[0].button) == area

    mask = Mask(str(asset))
    mask.image = np.full_like(logical_image, 255)
    mask.image[:, :640] = 0
    masked = mask.apply(image)
    np.testing.assert_array_equal(masked[:, 640:], logical_image[:, 640:])
    assert not masked[:, :640].any()

    control = control_device((2560, 1440))
    control.click(button)
    command = control.adb_shell.call_args[0][0]
    x, y = command[-2:]
    assert 200 <= x <= 360 and 240 <= y <= 300


def test_ocr_receives_the_correct_1440p_crop(logical_image, monkeypatch):
    model = Mock()
    model.atomic_ocr_for_single_lines.return_value = [['1', '2', '3']]
    monkeypatch.setattr(Ocr, 'cnocr', property(lambda self: model))
    ocr = Ocr((700, 400, 760, 440), name='resolution_ocr')
    device = screenshot_device(cv2.resize(logical_image, (2560, 1440), interpolation=cv2.INTER_NEAREST))
    assert ocr.ocr(device.screenshot()) == '123'
    supplied = model.atomic_ocr_for_single_lines.call_args[0][0][0]
    np.testing.assert_array_equal(supplied, ocr.pre_process(crop(logical_image, ocr.buttons[0])))


@pytest.mark.parametrize('size,factor', [(ASSET_SIZE, 1), ((2560, 1440), 2)])
def test_adb_tap_swipe_and_native_hierarchy_coordinates(size, factor):
    device = control_device(size)
    device.click_adb(100, 200)
    device.adb_shell.assert_called_with(['input', 'tap', 100 * factor, 200 * factor])
    device.swipe_adb((100, 200), (400, 500), duration=0.25)
    device.adb_shell.assert_called_with(['input', 'swipe', 100 * factor, 200 * factor,
                                       400 * factor, 500 * factor, 250])
    device.click_adb(200, 400, native=True)
    device.adb_shell.assert_called_with(['input', 'tap', 200, 400])


@pytest.mark.parametrize('size,factor', [(ASSET_SIZE, 1), ((2560, 1440), 2)])
def test_uiautomator_tap_hold_swipe_and_drag_path(size, factor):
    device = control_device(size)
    device.click_uiautomator2(100, 200)
    device.u2.click.assert_called_once_with(100 * factor, 200 * factor)
    device.long_click_uiautomator2(100, 200, duration=1.3)
    device.u2.long_click.assert_called_once_with(100 * factor, 200 * factor, duration=1.3)
    device.swipe_uiautomator2((100, 200), (400, 500), duration=0.3)
    device.u2.swipe.assert_called_once_with(100 * factor, 200 * factor, 400 * factor, 500 * factor, duration=0.3)
    device._drag_along([(100, 200, 0.1), (400, 500, 0.2), (400, 500, 0)])
    device.u2.touch.down.assert_called_once_with(100 * factor, 200 * factor)
    device.u2.touch.move.assert_called_once_with(400 * factor, 500 * factor)
    device.u2.touch.up.assert_called_once_with(400 * factor, 500 * factor)


def test_hermit_uses_native_pixels():
    device = control_device((2560, 1440))
    device.hermit_send = Mock()
    device.click_hermit(123, 234)
    device.hermit_send.assert_called_once_with('/click', x=246, y=468)


@pytest.mark.parametrize('builder_type', [CommandBuilder, MaatouchBuilder])
@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_touch_builders_scale_both_fingers_and_moves(builder_type, size):
    device = control_device(size)
    device.max_x, device.max_y = size
    device.orientation = 0
    first = builder_type(device, contact=0)
    second = builder_type(device, contact=1)
    first.down(320, 180).move(640, 360).up()
    second.down(960, 540).move(640, 360).up()
    assert first.commands[0].x == size[0] // 4
    assert first.commands[0].y == size[1] // 4
    assert second.commands[0].x == size[0] * 3 // 4
    assert second.commands[0].y == size[1] * 3 // 4
    for builder, contact in [(first, 0), (second, 1)]:
        assert builder.commands[1].x == size[0] // 2
        assert builder.commands[1].y == size[1] // 2
        assert all(command.contact == contact for command in builder.commands)


@pytest.mark.parametrize('orientation', [0, 1, 2, 3])
def test_minitouch_http_remains_normalized(orientation):
    device = control_device((2560, 1440))
    device.config.DEVICE_OVER_HTTP = True
    device.max_x, device.max_y = ASSET_SIZE
    device.orientation = orientation
    builder = CommandBuilder(device)
    builder.down(320, 180)
    event = json.loads(builder.to_atx_agent()[0])
    expected = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)][orientation]
    assert (event['xP'], event['yP']) == expected


def test_maatouch_over_http_still_requires_physical_pixels():
    device = control_device((2560, 1440))
    device.config.DEVICE_OVER_HTTP = True
    device.max_x, device.max_y = (2560, 1440)
    builder = MaatouchBuilder(device)
    builder.down(100, 200)
    assert (builder.commands[0].x, builder.commands[0].y) == (200, 400)


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_scrcpy_packet_coordinates_and_declared_dimensions_agree(size):
    parent = SimpleNamespace(_scrcpy_control_socket=None, _scrcpy_resolution=size)
    sender = ControlSender(parent)
    packet = sender.touch(640, 360, action=0, touch_id=2)
    event = struct.unpack('>BBqiiHHHi', packet)
    assert event[2:7] == (2, size[0] // 2, size[1] // 2, *size)
    scroll = struct.unpack('>BiiHHii', sender.scroll(640, 360, 1, -1))
    assert scroll[1:5] == (size[0] // 2, size[1] // 2, *size)
    assert scroll[-2:] == (1, -1)


def test_scrcpy_click_does_not_fall_back_to_adb():
    device = control_device((2560, 1440))
    device.config.Emulator_ControlMethod = 'scrcpy'
    device.click_scrcpy = Mock()
    device.click(Button((100, 200, 100, 200), (), (100, 200, 100, 200), name='point'))
    device.click_scrcpy.assert_called_once_with(100, 200)
    device.adb_shell.assert_not_called()


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_scrcpy_requests_native_capture_and_sufficient_codec_level(size):
    old = ScrcpyOptions.command_v120(max_size=size[0])
    new = ScrcpyOptions.command_v125(max_size=size[0])
    level = 'key_level=4096' if size == ASSET_SIZE else 'key_level=16384'
    assert old[6] == str(size[0])
    assert any(level in option for option in old)
    assert f'max_size={size[0]}' in new
    assert any(level in option for option in new)


def test_nemu_input_scales_before_its_backend_rotation():
    device = control_device((2560, 1440))
    ipc = SimpleNamespace(width=2560, height=1440, down=Mock(), up=Mock())
    device.__dict__['nemu_ipc'] = ipc
    device.nemu_ipc_down(320, 180)
    ipc.down.assert_called_once_with(640, 360)
    device.long_click_nemu_ipc(640, 360, duration=1)
    ipc.down.assert_called_with(1280, 720)
    ipc.up.assert_called_once_with()


def test_hierarchy_click_is_not_scaled_twice():
    device = control_device((2560, 1440))
    hierarchy = etree.fromstring(b'<hierarchy><node text="target" bounds="[800,400][1000,600]"/></hierarchy>')
    device.click(HierarchyButton(hierarchy, '//*[@text="target"]'))
    x, y = device.adb_shell.call_args[0][0][-2:]
    assert 800 <= x <= 1000 and 400 <= y <= 600


def test_control_before_first_screenshot_discovers_size_once():
    device = object.__new__(Adb)
    device.adb_shell = Mock(return_value='Physical size: 1280x720\nOverride size: 2560x1440\n')
    assert device.control_point(100, 200) == (200, 400)
    assert device.control_point(200, 300) == (400, 600)
    device.adb_shell.assert_called_once_with(['wm', 'size'])


def test_resource_release_invalidates_display_size():
    device = control_device((2560, 1440))
    device._screen_size_checked = device._screen_black_checked = True
    device.release_resource()
    assert device._native_screen_size is None
    assert not device._screen_size_checked and not device._screen_black_checked


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_adb_raw_header_dimensions_are_respected(size):
    width, height = size
    rgba = np.full((height, width, 4), 90, np.uint8)
    payload = np.array([width, height, 1], dtype=np.uint32).tobytes() + rgba.tobytes()
    frame = load_screencap(payload)
    assert frame.shape == (height, width, 3)
    assert normalize_screenshot(frame).shape == (720, 1280, 3)


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_droidcast_raw_reads_full_native_frame(size):
    device = object.__new__(DroidCast)
    device.set_screen_size(*size)
    device.config = SimpleNamespace(DROIDCAST_VERSION='DroidCast_raw')
    device.__dict__['is_mumu_over_version_356'] = False
    device._droidcast_port = 12345
    payload = np.full((size[1], size[0]), 0xf800, dtype=np.uint16).tobytes()
    session = Mock()
    session.get.return_value.content = payload
    device.__dict__['droidcast_session'] = session
    frame = device.screenshot_droidcast_raw()
    assert frame.shape == (size[1], size[0], 3)
    np.testing.assert_array_equal(frame[0, 0], (255, 0, 0))


@pytest.mark.parametrize('size', [ASSET_SIZE, (2560, 1440)])
def test_droidcast_png_detects_raw_server_at_both_resolutions(size):
    device = object.__new__(DroidCast)
    device.config = SimpleNamespace(DROIDCAST_VERSION='DroidCast')
    device.__dict__['is_mumu_over_version_356'] = False
    device._droidcast_port = 12345
    session = Mock()
    session.get.return_value.status_code = 200
    session.get.return_value.content = bytes(size[0] * size[1] * 2)
    device.__dict__['droidcast_session'] = session
    # Inspect the actual decoder diagnosis without the transport retry loop.
    with pytest.raises(DroidCastVersionIncompatible):
        DroidCast.screenshot_droidcast.__wrapped__(device)


@pytest.mark.parametrize('method', ['ADB', 'uiautomator2', 'minitouch', 'MaaTouch', 'scrcpy', 'Hermit', 'nemu_ipc'])
@pytest.mark.parametrize('operation', ['click', 'long_click', 'swipe', 'drag'])
@pytest.mark.parametrize('size,factor', [(ASSET_SIZE, 1), ((2560, 1440), 2)])
def test_full_gestures_reach_each_transport_without_double_scaling(method, operation, size, factor):
    device = control_device(size)
    device.config.Emulator_ControlMethod = method
    device.max_x, device.max_y = size
    device.orientation = 0
    points = []

    def adb_command(command):
        if command[:2] == ['input', 'tap']:
            points.append(tuple(command[2:4]))
        elif command[:2] == ['input', 'swipe']:
            points.extend([tuple(command[2:4]), tuple(command[4:6])])

    device.adb_shell.side_effect = adb_command
    device.u2.click.side_effect = lambda x, y: points.append((x, y))
    device.u2.long_click.side_effect = lambda x, y, **kwargs: points.append((x, y))
    device.u2.swipe.side_effect = lambda x, y, ex, ey, **kwargs: points.extend([(x, y), (ex, ey)])
    for event in (device.u2.touch.down, device.u2.touch.move, device.u2.touch.up):
        event.side_effect = lambda x, y: points.append((x, y))

    def publish(builder):
        points.extend((c.x, c.y) for c in builder.commands if c.operation in ('d', 'm'))
        builder.clear()

    device.__dict__['_minitouch_builder'] = CommandBuilder(device)
    device.__dict__['_maatouch_builder'] = MaatouchBuilder(device)
    device.minitouch_send = publish
    device.maatouch_send = publish
    device.maatouch_send_sync = lambda builder, mode=2: publish(builder)
    device.hermit_send = lambda url, x, y: points.append((x, y))
    device.__dict__['nemu_ipc'] = SimpleNamespace(
        width=size[0], height=size[1], down=lambda x, y: points.append((x, y)), up=Mock())

    # Check reentrancy without risking a hanging test on a non-reentrant lock.
    lock = device._scrcpy_control_socket_lock
    with lock:
        acquired = lock.acquire(blocking=False)
        assert acquired, 'Scrcpy gesture and packet serialization share this lock'
        lock.release()
    device._scrcpy_alive = True
    device._scrcpy_resolution = size
    transport = Mock()
    transport.send.side_effect = lambda packet: points.append(struct.unpack('>BBqiiHHHi', packet)[3:5])
    device._scrcpy_control_socket = transport

    button = Button((100, 200, 100, 200), (), (100, 200, 100, 200), name='point')
    if operation == 'click':
        device.click(button)
    elif operation == 'long_click':
        device.long_click(button, duration=1.1)
    elif operation == 'swipe':
        device.swipe((100, 200), (400, 300))
    else:
        device.drag((100, 200), (400, 300), point_random=(0, 0, 0, 0),
                    shake=(0, 0), shake_random=(0, 0, 0, 0), hold_duration=0.5)
    assert points[0] == (100 * factor, 200 * factor)
    end = (400 * factor, 300 * factor) if operation in ('swipe', 'drag') else points[0]
    if operation == 'swipe' and method in ('minitouch', 'MaaTouch', 'nemu_ipc'):
        # insert_swipe drops points less than ten logical pixels apart, which
        # can omit the exact end point. This existing tolerance must scale too.
        assert np.linalg.norm(np.subtract(points[-1], end)) <= 10 * factor
    else:
        assert points[-1] == end
    assert all(0 <= x < size[0] and 0 <= y < size[1] for x, y in points)


@pytest.mark.parametrize('orientation,expected', [(1, (1080, 640)), (3, (360, 1920))])
def test_scrcpy_portrait_input_undoes_screenshot_rotation(orientation, expected):
    sender = ControlSender(SimpleNamespace(
        _scrcpy_control_socket=None, _scrcpy_resolution=(1440, 2560), orientation=orientation))
    event = struct.unpack('>BBqiiHHHi', sender.touch(320, 180))
    assert event[3:7] == (*expected, 1440, 2560)


@pytest.mark.parametrize('orientation,expected', [
    (0, (640, 360)), (1, (1080, 640)), (2, (1920, 1080)), (3, (360, 1920)),
])
def test_minitouch_physical_orientation(orientation, expected):
    size = (2560, 1440) if orientation % 2 == 0 else (1440, 2560)
    device = control_device((2560, 1440))
    device.max_x, device.max_y = size
    device.orientation = orientation
    builder = CommandBuilder(device)
    builder.down(320, 180)
    assert (builder.commands[0].x, builder.commands[0].y) == expected


def test_portrait_android_hierarchy_remains_in_native_pixels():
    device = control_device((2560, 1440))
    device.config.Emulator_ControlMethod = 'MaaTouch'
    hierarchy = etree.fromstring(b'<hierarchy><node text="settings" bounds="[500,1800][700,2000]"/></hierarchy>')
    button = HierarchyButton(hierarchy, '//*[@text="settings"]')
    device.click(button)
    x, y = device.adb_shell.call_args[0][0][-2:]
    assert 500 <= x <= 700 and 1800 <= y <= 2000
    device.long_click(button, duration=1)
    command = device.adb_shell.call_args[0][0]
    assert command[:2] == ['input', 'swipe']
    assert 500 <= command[2] <= 700 and 1800 <= command[3] <= 2000


def test_login_hierarchy_is_converted_before_cropping_or_dragging():
    from module.handler.login import LoginHandler
    from uiautomator2.xpath import XPathSelector
    handler = object.__new__(LoginHandler)
    handler.device = control_device((2560, 1440))
    selector = Mock(spec=XPathSelector)
    selector.exists = True
    selector.bounds = (200, 400, 600, 800)
    assert handler.get_for_any_ele([selector]) == (100, 200, 300, 400)


@pytest.mark.parametrize('method', ['uiautomator2', 'nemu_ipc'])
def test_dorm_persistent_press_uses_physical_pixels(method, monkeypatch):
    from module.dorm.dorm import RewardDorm
    monkeypatch.setattr('module.dorm.dorm.time.sleep', lambda _: None)
    dorm = object.__new__(RewardDorm)
    dorm.config = SimpleNamespace(DEVICE_CONTROL_METHOD=method)
    dorm.device = control_device((2560, 1440))
    dorm.device.screenshot = Mock()
    dorm._dorm_has_food = lambda button: False
    ipc = SimpleNamespace(width=2560, height=1440, down=Mock(), up=Mock())
    dorm.device.__dict__['nemu_ipc'] = ipc
    button = Button((100, 200, 100, 200), (), (100, 200, 100, 200), name='food')
    dorm._dorm_feed_long_tap(button, count=1)
    if method == 'uiautomator2':
        dorm.device.u2.touch.down.assert_called_once_with(200, 400)
        dorm.device.u2.touch.move.assert_called_once_with(200, 400)
        dorm.device.u2.touch.up.assert_called_once_with(200, 400)
    else:
        ipc.down.assert_called_once_with(200, 400)
        ipc.up.assert_called_once_with()


@pytest.mark.parametrize('mode', ['main', 'os'])
def test_map_mask_perspective_grid_and_input_use_one_coordinate_space(logical_image, mode):
    from module.map_detection.grid import Grid
    from module.map_detection.view import View

    device = screenshot_device(cv2.resize(logical_image, (2560, 1440), interpolation=cv2.INTER_NEAREST))
    image = device.screenshot()
    view = object.__new__(View)
    view.mode = mode
    np.testing.assert_array_equal(view._image_clear_ui(image), view._image_clear_ui(logical_image))

    config = SimpleNamespace(GRID_IMAGE_A_MULTIPLY=1, MAP_ENEMY_TEMPLATE=[], MAP_HAS_SIREN=False,
                             HOMO_TILE=(100, 100))
    corner = np.array([[600, 300], [700, 300], [590, 400], [710, 400]], dtype=float)
    grid = Grid((0, 0), image, corner, config)
    reference = Grid((0, 0), logical_image, corner, config)
    np.testing.assert_array_equal(grid.image_trans, reference.image_trans)
    np.testing.assert_array_equal(grid.image_homo, reference.image_homo)
    center = grid.grid2screen([[0.5, 0.5]])
    np.testing.assert_allclose(grid.screen2grid(center), [[0.5, 0.5]], atol=1e-6)
    native = device.control_point(*center[0])
    np.testing.assert_allclose(native, reference.grid2screen([[0.5, 0.5]])[0] * 2, atol=1)
    assert 1180 <= native[0] <= 1420 and 600 <= native[1] <= 800


def test_control_points_are_clamped_to_native_display():
    device = control_device((2560, 1440))
    assert device.control_point(-10, -10) == (0, 0)
    assert device.control_point(1280, 720) == (2559, 1439)


def test_changing_native_size_rechecks_black_frames():
    device = control_device(ASSET_SIZE)
    device._screen_black_checked = True
    device.set_screen_size(2560, 1440)
    assert not device._screen_black_checked


@pytest.mark.parametrize('size', [(1920, 1080), (2560, 1600), (0, 0)])
def test_unsupported_aspect_ratios_and_resolutions_are_rejected(size):
    with pytest.raises(RequestHumanTakeover):
        control_device(size)
