"""Real 1440P full-dock dialog must reach the configured enhancement handler."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

import module.config.server as server
from module.handler.info_handler import InfoHandler
from module.handler.assets import GAME_TIPS4
from module.retire.retirement import Retirement
from module.retire.assets import RETIRE_APPEAR_1, RETIRE_APPEAR_3, IN_RETIREMENT_CHECK

FIXTURE = Path(__file__).parent / 'fixtures/real_1440p/dock_full.png'


def handler(size=(2560, 1440), image=None):
    obj = object.__new__(Retirement)
    clicks = []
    obj.device = SimpleNamespace(
        image=np.array(Image.open(str(FIXTURE)).convert('RGB')) if image is None else image,
        _native_screen_size=size, stuck_record_add=lambda button: None, click=clicks.append)
    obj.config = SimpleNamespace(BUTTON_OFFSET=(20, 20), Retirement_RetireMode='enhance')
    obj.interval_timer = {}
    obj._unable_to_enhance = False
    return obj, clicks


def test_real_dock_full_is_not_a_game_tip():
    obj, clicks = handler()
    # The tiny countdown template also matches the dimmed background.
    assert obj.appear(GAME_TIPS4, offset=(20, 20))
    assert obj.appear(RETIRE_APPEAR_1, offset=(20, 20))
    assert obj.appear(RETIRE_APPEAR_3, offset=(20, 20))
    assert not obj.handle_game_tips()
    assert clicks == []


def test_real_full_dock_uses_configured_enhancement():
    obj, clicks = handler()
    assert not obj.handle_retirement()
    assert clicks == [RETIRE_APPEAR_3]


def test_720p_keeps_upstream_tip_handling():
    obj, clicks = handler(size=(1280, 720))
    assert obj.handle_game_tips()
    assert len(clicks) == 1


def test_other_servers_keep_upstream_tip_handling(monkeypatch):
    obj, clicks = handler()
    monkeypatch.setattr(server, 'server', 'en')
    assert obj.handle_game_tips()
    assert len(clicks) == 1


def test_one_matching_control_does_not_suppress_real_tips():
    obj, clicks = handler()
    obj.device.image[477:553, 784:896] = 0
    assert obj.handle_game_tips()
    assert len(clicks) == 1


def test_blank_screen_neither_clicks_nor_opens_dock():
    obj, clicks = handler(image=np.zeros((720, 1280, 3), dtype=np.uint8))
    assert not obj.handle_game_tips()
    assert not obj.appear(RETIRE_APPEAR_1, offset=(20, 20))
    assert clicks == []


def transition_handler(last_click='MAP_PREPARATION', settled=None):
    image = np.array(Image.open(str(FIXTURE.with_name('dock_full_opening.png'))).convert('RGB'))
    obj, clicks = handler(image=image)
    operations = []
    obj.device.click_record = [last_click]
    obj.device.sleep = lambda seconds: operations.append(('sleep', seconds))

    def screenshot():
        operations.append(('screenshot',))
        if settled is None:
            obj.device.image = np.array(Image.open(str(FIXTURE)).convert('RGB'))
        else:
            obj.device.image = settled.copy()

    obj.device.screenshot = screenshot
    return obj, clicks, operations


def test_real_opening_animation_refreshes_before_tip_click():
    obj, clicks, operations = transition_handler()
    assert obj.appear(GAME_TIPS4, offset=(20, 20))
    assert not obj.appear(RETIRE_APPEAR_1, offset=(20, 20))
    assert not obj.handle_game_tips()
    assert clicks == []
    assert operations == [('sleep', 0.5), ('screenshot',)]


def test_opening_animation_reaches_configured_enhancement():
    obj, clicks, operations = transition_handler()
    assert not obj.handle_retirement()
    assert clicks == [RETIRE_APPEAR_3]


def test_other_click_context_does_not_wait():
    obj, clicks, operations = transition_handler(last_click='DOCK_FILTER')
    assert obj.handle_game_tips()
    assert len(clicks) == 1
    assert operations == []


def test_tip_not_blocked_if_refresh_does_not_find_dock_modal():
    opening = np.array(Image.open(str(FIXTURE.with_name('dock_full_opening.png'))).convert('RGB'))
    obj, clicks, operations = transition_handler(settled=opening)
    assert obj.handle_game_tips()
    assert len(clicks) == 1
    assert operations == [('sleep', 0.5), ('screenshot',)]


def test_720p_animation_does_not_refresh():
    obj, clicks, operations = transition_handler()
    obj.device._native_screen_size = (1280, 720)
    assert obj.handle_game_tips()
    assert len(clicks) == 1
    assert operations == []
