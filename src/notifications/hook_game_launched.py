import src.notifications as ns
from src.notifications.ns_hook import NsHook


class NsHookGameLaunched(NsHook):
    def __init__(self):
        super().__init__(ns.Notifications.GAME_LAUNCHED)
        self.ingame = True
