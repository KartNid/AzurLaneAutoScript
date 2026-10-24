"""Small, measured 1440P template variants; retain upstream thresholds and areas."""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import module.config.server as server
from module.base.utils import area_offset, crop
from module.ui.switch import Switch

ASSETS = Path(__file__).resolve().parent / 'assets' / 'cn'
# Each variant must keep the original search geometry. Do not reuse it for a
# similarly named button with a different region after an upstream UI update.
AREAS = {'NAV_GENERAL': (52, 436, 127, 457),
         'CLEAR_MODE_TITLE': (960, 586, 1036, 606)}


@lru_cache(maxsize=16)
def template(name):
    with Image.open(str(ASSETS / (name + '.png'))) as image:
        return np.array(image.convert('RGB'))


def match_1440p(main, button, offset=(20, 20), similarity=0.85):
    """Fallback only for measured CN controls on a normalized native 1440P frame."""
    if server.server != 'cn' or getattr(main.device, '_native_screen_size', None) != (2560, 1440):
        return False
    image = main.device.image
    if image.shape[:2] != (720, 1280) or tuple(button.area) != AREAS.get(button.name):
        return False
    if isinstance(offset, tuple):
        delta = (-offset[0], -offset[1], offset[0], offset[1]) if len(offset) == 2 else offset
    else:
        delta = (-3, -offset, 3, offset)
    search_area = np.array(button.area) + np.array(delta)
    search = crop(image, search_area, copy=False)
    variant = template(button.name)
    if search.shape[0] < variant.shape[0] or search.shape[1] < variant.shape[1]:
        return False
    _, score, _, point = cv2.minMaxLoc(cv2.matchTemplate(search, variant, cv2.TM_CCOEFF_NORMED))
    if score <= similarity:
        return False
    button._button_offset = area_offset(button._button, np.array(delta[:2]) + point)
    return True


class HighResolutionSwitch(Switch):
    def get(self, main):
        state = super().get(main)
        if state != 'unknown':
            return state
        for data in self.state_list:
            if match_1440p(main, data['check_button'], data['offset']):
                return data['state']
        return 'unknown'


def is_dock_full_popup(main):
    """Let upstream retirement handle a full-dock modal before countdown tips.

    On CN 1440P the dimmed event backdrop can match GAME_TIPS4's tiny digit.
    Require both existing dock controls; keep their thresholds and actions.
    """
    if server.server != 'cn' or getattr(main.device, '_native_screen_size', None) != (2560, 1440):
        return False
    if main.device.image.shape[:2] != (720, 1280):
        return False
    from module.retire.assets import RETIRE_APPEAR_1, RETIRE_APPEAR_3
    return (main.appear(RETIRE_APPEAR_1, offset=(20, 20))
            and main.appear(RETIRE_APPEAR_3, offset=(20, 20)))
