from functools import cache

from PyQt6.QtMultimedia import QSoundEffect

from src.util.theme import ThemeSet


@cache
def sound_effect(theme: ThemeSet) -> QSoundEffect:
    sound = QSoundEffect()
    sound.setSource(theme.sound("chat/sfx/query.wav"))
    return sound
