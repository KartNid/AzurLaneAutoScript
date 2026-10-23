"""Regressions from MuMu12/CN, 2560x1440, 360 dpi, 2026-10-23.

Fixtures retain only navigation and control pixels; account data is excluded.
"""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import module.config.server as server
from alas_1440p.recognition import match_1440p

from module.shop.assets import NAV_GENERAL, NAV_MONTHLY
from module.shop.ui import ShopUI
from module.handler.auto_search import AutoSearchHandler
from module.handler.assets import AUTO_SEARCH_MAP_OPTION_OFF
from module.handler.fast_forward import FastForwardHandler, CLEAR_MODE, AUTO_SEARCH

FIXTURES = Path(__file__).parent / 'fixtures' / 'real_1440p'


def shop(frame, size=(2560, 1440)):
    main = object.__new__(ShopUI)
    main.device = SimpleNamespace(image=frame, _native_screen_size=size,
                                  stuck_record_add=lambda button: None)
    main.config = SimpleNamespace(BUTTON_OFFSET=(20, 20))
    main.interval_timer = {}
    return main


def frame(name):
    return np.array(Image.open(str(FIXTURES / name)).convert('RGB'))


def test_real_general_shop_navigation():
    main = shop(frame('shop_general.png'))
    assert main.shop_nav_250814.get(main) == NAV_GENERAL


def test_real_monthly_shop_navigation():
    main = shop(frame('shop_monthly.png'))
    assert main.shop_nav_250814.get(main) == NAV_MONTHLY


def test_shop_navigation_rejects_unrelated_page():
    main = shop(np.zeros((720, 1280, 3), dtype=np.uint8))
    assert main.shop_nav_250814.get(main) == 'unknown'


def test_720p_keeps_upstream_shop_template():
    original = np.array(Image.open(NAV_GENERAL.file).convert('RGB'))
    main = shop(original, size=(1280, 720))
    assert main.shop_nav_250814.get(main) == NAV_GENERAL
    assert not match_1440p(main, NAV_GENERAL)


def test_1440p_variant_keeps_threshold_and_click_offset():
    image = frame('shop_general.png')
    shifted = np.zeros_like(image)
    shifted[6:, 7:] = image[:-6, :-7]
    main = shop(shifted)
    assert main.shop_nav_250814.get(main) == NAV_GENERAL
    assert tuple(NAV_GENERAL.button) == tuple(np.array(NAV_GENERAL._button) + (7, 6, 7, 6))
    assert not match_1440p(main, NAV_GENERAL, similarity=1.01)


def test_general_variant_rejects_inactive_state():
    assert not match_1440p(shop(frame('shop_monthly.png')), NAV_GENERAL)


def test_cn_variant_is_not_used_for_other_servers(monkeypatch):
    monkeypatch.setattr(server, 'server', 'en')
    assert not match_1440p(shop(frame('shop_general.png')), NAV_GENERAL)


def test_real_map_off_state_requests_the_correct_click():
    main = object.__new__(AutoSearchHandler)
    clicks = []
    main.device = SimpleNamespace(image=frame('map_off.png'), _native_screen_size=(2560, 1440),
                                  stuck_record_add=lambda button: None, click=clicks.append)
    main.config = SimpleNamespace(BUTTON_OFFSET=(20, 20))
    main.interval_timer = {}
    assert not main.is_auto_search_running()
    assert main.handle_auto_search_map_option()
    assert clicks == [AUTO_SEARCH_MAP_OPTION_OFF]


def preparation(name, clear=True, auto=True):
    main = object.__new__(FastForwardHandler)
    main.device = SimpleNamespace(image=frame(name), _native_screen_size=(2560, 1440),
                                  stuck_record_add=lambda button: None)
    main.config = SimpleNamespace(BUTTON_OFFSET=(20, 20), Campaign_Name='13-4',
        STAR_REQUIRE_3=3, StopCondition_MapAchievement='non_stop',
        MAP_CLEAR_PERCENTAGE_SHORT=False, Campaign_UseClearMode=clear,
        Campaign_UseAutoSearch=auto, Campaign_Use2xBook=False)
    main.interval_timer = {}
    return main


def test_real_clear_mode_is_not_lost_before_entering_map():
    main = preparation('preparation_on.png')
    assert CLEAR_MODE.get(main) == 'on'
    assert AUTO_SEARCH.get(main) == 'off'
    main.map_get_info()
    assert main.map_has_clear_mode
    main.handle_fast_forward()
    assert main.map_is_clear_mode
    assert main.map_is_auto_search


def test_blank_preparation_does_not_unlock_clear_mode():
    main = preparation('map_off.png')
    main.map_get_info()
    assert not main.map_has_clear_mode
    main.handle_fast_forward()
    assert not main.map_is_auto_search


def test_auto_search_preference_remains_independent():
    main = preparation('preparation_on.png', auto=False)
    main.map_get_info()
    main.handle_fast_forward()
    assert main.map_is_clear_mode
    assert not main.map_is_auto_search


def test_real_clear_off_and_auto_on_states():
    assert CLEAR_MODE.get(preparation('preparation_off.png')) == 'off'
    assert AUTO_SEARCH.get(preparation('preparation_auto_on.png')) == 'on'


def test_disabled_clear_mode_keeps_auto_search_disabled():
    main = preparation('preparation_off.png', clear=False)
    main.map_get_info()
    assert main.map_has_clear_mode
    main.handle_fast_forward()
    assert not main.map_is_clear_mode
    assert not main.map_is_auto_search


def test_incomplete_stage_is_not_granted_clear_mode():
    main = preparation('preparation_on.png')
    main.get_map_clear_percentage = lambda: 0.5
    main.map_get_info()
    assert not main.map_has_clear_mode
    main.handle_fast_forward()
    assert not main.map_is_auto_search
