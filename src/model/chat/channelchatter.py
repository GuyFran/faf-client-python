from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from src.model.chat.chatter import Chatter
from src.model.modelitem import ModelItem
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional

if TYPE_CHECKING:
    from src.model.chat.channel import Channel
    from src.model.chat.channel import ChannelID


class ChannelChatter(ModelItem):
    MOD_ELEVATIONS = "~&@%+"

    def __init__(self, channel: Channel, chatter: Chatter, elevation: str) -> None:
        ModelItem.__init__(self)
        self.channel = channel
        self.chatter = chatter
        self.elevation = elevation
        self._data_fields.append("elevation")

    @property
    def id_key(self) -> tuple[ChannelID, str]:
        return (self.channel.id_key, self.chatter.id_key)

    def copy(self) -> Self:
        return self.__class__(self.channel, self.chatter, **self.field_dict)

    @transactional
    def update(self, *, _transaction: ModelTransaction = ModelTransaction(), **kwargs: Any) -> None:
        old = self.copy()
        super().update(**kwargs)
        self.emit_update(old, _transaction=_transaction)

    @transactional
    def set_elevation(
        self,
        value: str,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        self.update(elevation=value, _transaction=_transaction)

    def is_mod(self) -> bool:
        e = self.elevation
        return e != '' and e in self.MOD_ELEVATIONS
