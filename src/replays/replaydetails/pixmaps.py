import os
from functools import lru_cache

from PyQt6.QtGui import QPixmap

from src.replays.replaydetails.utils import ACTION_ICONS
from src.replays.replaydetails.utils import UNIT_ICONS
from src.util import COMMON_DIR


@lru_cache
def enhancement_pixmap(faction: str, name: str) -> QPixmap:
    filepath = os.path.join(COMMON_DIR, "replays", "enhancements", faction, f"{name}.png")
    return QPixmap(filepath)


@lru_cache(1)
def units_pixmaps() -> dict[str, QPixmap]:
    pixmap = QPixmap(os.path.join(COMMON_DIR, "unitdb", "units.png"))
    return {
        name.lower(): pixmap.copy(0, i * 64, 64, 64)
        for i, name in enumerate(UNIT_ICONS)
    }


@lru_cache(1)
def action_pixmaps() -> dict[str, QPixmap]:
    pixmap = QPixmap(os.path.join(COMMON_DIR, "replays", "actions48.png"))
    return {
        name: pixmap.copy(0, i * 48, 48, 48)
        for i, name in enumerate(ACTION_ICONS)
    }
