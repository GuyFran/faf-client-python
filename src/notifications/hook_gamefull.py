"""
Settings for notifications: If a game is full
"""
from src.notifications.ns_hook import NsHook
from src.notifications.ns_type import NsType


class NsHookGameFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, NsType.GAME_FULL)
