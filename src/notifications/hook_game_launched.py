from src.notifications.ns_hook import NsHook
from src.notifications.ns_type import NsType


class NsHookGameLaunchedCustom(NsHook):
    def __init__(self):
        super().__init__(NsType.CUSTOM_GAME_LAUNCHED)
        self.ingame = True


class NsHookGameLaunchedLadder(NsHook):
    def __init__(self):
        super().__init__(NsType.LADDER_GAME_LAUNCHED)
        self.ingame = True
