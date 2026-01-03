from typing import Any
from typing import cast

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import ApiAccessor


class IceServersPoller(QObject):
    ice_servers_received = pyqtSignal()

    def __init__(self, game_uid: int) -> None:
        super().__init__()
        self._game_uid = game_uid
        self._api_accessor = ApiAccessor()
        self.force_relay = False
        self.servers: list[dict[str, str | list[str]]] = []

    def request_ice_servers(self) -> None:
        self._api_accessor.get(
            f"/ice/session/game/{self._game_uid}",
            self.handle_ice_servers,
        )

    def handle_ice_servers(self, message: dict[str, Any]) -> None:
        self.servers = message["servers"]
        self.force_relay = cast(bool, message["forceRelay"])
        self.ice_servers_received.emit()
