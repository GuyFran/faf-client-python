from typing import Any
from typing import Self

from PyQt6.QtCore import pyqtSignal

from src.model.chat.channel import Channel
from src.model.modelitem import ModelItem
from src.model.player import Player
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class IrcUser(ModelItem):
    newPlayer = pyqtSignal(object, object, object)

    def __init__(self, name: str, hostname: str) -> None:
        super().__init__()
        self.elevation: dict[Channel, str] = {}
        self.name = name
        self.hostname = hostname
        self._data_fields.extend(("name", "hostname"))
        self._player: Player | None = None

    @property
    def id_key(self) -> str:
        return self.name

    def copy(self) -> Self:
        old = self.__class__(**self.field_dict)
        for channel in self.elevation:
            old.set_elevation(channel, self.elevation[channel])
        return old

    @transactional
    def update(self, *, _transaction: ModelTransaction = ModelTransaction(), **kwargs: Any) -> None:
        olduser = self.copy()
        super().update(**kwargs)
        self.emit_update(olduser, _transaction=_transaction)

    @transactional
    def set_elevation(
        self,
        channel: Channel,
        elevation: str | None,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        olduser = self.copy()
        if elevation is None:
            if channel in self.elevation:
                del self.elevation[channel]
        else:
            self.elevation[channel] = elevation
        self.emit_update(olduser, _transaction=_transaction)

    @property
    def player(self) -> Player | None:
        return self._player

    @transactional
    def set_player(
        self,
        val: Player | None,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        oldplayer = self._player
        self._player = val
        _transaction.emit(self.newPlayer, self, val, oldplayer)

    @player.setter
    def player(self, val: Player | None) -> None:
        # CAVEAT: this will emit signals immediately!
        self.set_player(val)

    def is_mod(self, channel: Channel) -> bool:
        if channel not in self.elevation:
            return False
        return self.elevation[channel] in "~&@%+"
