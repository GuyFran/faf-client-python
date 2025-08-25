import logging
from enum import Enum
from typing import Any
from typing import Self

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.client.connection import ServerConnection
from src.config import Settings
from src.model.playerset import Playerset

logger = logging.getLogger(__name__)


class BanPeriod(Enum):
    HOUR = 'HOUR'
    DAY = 'DAY'
    WEEK = 'WEEK'
    MONTH = 'MONTH'
    YEAR = 'YEAR'


class PowerActions:
    def __init__(
        self,
        lobby_connection: ServerConnection,
        playerset: Playerset,
        settings: type[Settings],
    ) -> None:
        self._lobby_connection = lobby_connection
        self._playerset = playerset
        self._settings = settings

    @classmethod
    def build(
        cls,
        lobby_connection: ServerConnection,
        playerset: Playerset,
        settings: type[Settings],
        **kwargs: Any,
    ) -> Self:
        return cls(lobby_connection, playerset, settings)

    def close_fa(self, username: str) -> bool:
        player = self._playerset.get_by_name(username)
        if player is None:
            return False
        logger.info("Closing FA for %s", player.login)
        self._lobby_connection.send({
            "command": "admin",
            "action": "closeFA",
            "user_id": player.id,
        })
        return True

    def kick_player(self, username: str) -> bool:
        player = self._playerset.get_by_name(username)
        if player is None:
            return False
        logger.info("Closing lobby for %s", player.login)
        self._lobby_connection.send({
            "command": "admin",
            "action": "closelobby",
            "user_id": player.id,
        })
        return True

    # TODO: ban with API
    def ban_player(self, username: str, reason: str, duration: float, period: float) -> bool:
        player = self._playerset.get_by_name(username)
        if player is None:
            return False
        message = {
            "command": "admin",
            "action": "closelobby",
            "user_id": player.id,
        }
        self._lobby_connection.send(message)
        return True

    def send_the_orcs(self, username: str) -> None:
        player = self._playerset.get_by_name(username)
        target = username if player is None else player.id
        route = self._settings.get('mordor/host')
        QDesktopServices.openUrl(QUrl(f"{route}/users/{target}"))
