"""Bridge asset coordinates and the device's physical display.

Recognition (including fixed crops, masks, OCR and map geometry) uses the asset
coordinate system. Only screenshot acquisition and input injection cross this
boundary; scaling business logic or touch builders a second time is incorrect.
"""
import re

import cv2

from module.exception import RequestHumanTakeover
from module.logger import logger


ASSET_SIZE = (1280, 720)
SUPPORTED_SCREEN_SIZES = (ASSET_SIZE, (2560, 1440))


def landscape_size(width, height):
    return max(int(width), int(height)), min(int(width), int(height))


def scale_point(x, y, source, target):
    """Scale pixels, retaining subpixel coordinates until input injection."""
    return x * target[0] / source[0], y * target[1] / source[1]


def normalize_screenshot(image):
    """Return an RGB frame in asset coordinates, without mutating native pixels."""
    size = image.shape[1], image.shape[0]
    if size == ASSET_SIZE:
        return image
    if size == (2560, 1440):
        return cv2.resize(image, ASSET_SIZE, interpolation=cv2.INTER_AREA)
    # Startup may temporarily show a portrait Android screen. The screenshot
    # checks decide whether it is safe to continue or request human takeover.
    return image


class Resolution:
    _native_screen_size = None

    def set_screen_size(self, width, height):
        size = landscape_size(width, height)
        if size not in SUPPORTED_SCREEN_SIZES:
            logger.critical(f'Resolution not supported: {width}x{height}')
            logger.critical('Please set emulator resolution to 1280x720 or 2560x1440')
            raise RequestHumanTakeover
        if size != self._native_screen_size:
            self._screen_black_checked = False
        self._native_screen_size = size
        return size

    @property
    def native_screen_size(self):
        """Discover size before the first input, even if no screenshot was taken."""
        if self._native_screen_size is None:
            if hasattr(self, 'resolution_uiautomator2'):
                self.set_screen_size(*self.resolution_uiautomator2())
            else:
                # Adb can also be used without the uiautomator2 mixin. Android
                # reports physical size first and the active override last.
                output = self.adb_shell(['wm', 'size'])
                sizes = re.findall(r'(\d+)x(\d+)', output)
                if not sizes:
                    logger.critical('Unable to determine device resolution')
                    raise RequestHumanTakeover
                self.set_screen_size(*map(int, sizes[-1]))
        return self._native_screen_size

    def control_point(self, x, y, size=None):
        """Convert logical pixels to the selected backend's physical pixels."""
        target = self.native_screen_size if size is None else size
        x, y = scale_point(x, y, ASSET_SIZE, target)
        return max(0, min(int(x), target[0] - 1)), max(0, min(int(y), target[1] - 1))

    def logical_point(self, x, y):
        """Convert Android hierarchy coordinates to asset coordinates."""
        return scale_point(x, y, self.native_screen_size, ASSET_SIZE)

    def logical_area(self, area):
        return (*self.logical_point(*area[:2]), *self.logical_point(*area[2:]))
