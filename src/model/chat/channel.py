from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.model.modelitem import ModelItem
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional

if TYPE_CHECKING:
    from src.model.chat.channelchatter import ChannelChatter
    from src.model.chat.chatline import ChatLineMetadata

PARTY_CHANNEL_SUFFIX = "'sParty"


class ChannelType(Enum):
    PUBLIC = 1
    PRIVATE = 2


class ChannelID:
    def __init__(self, type_: ChannelType, name: str) -> None:
        self.type = type_
        self.name = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ChannelID):
            return NotImplemented
        return self.type == other.type and self.name == other.name

    def __hash__(self):
        return hash((self.name, self.type))

    @classmethod
    def private_cid(cls, name: str) -> Self:
        return cls(ChannelType.PRIVATE, name)


class Lines(QObject):
    added = pyqtSignal()
    removed = pyqtSignal(int)

    def __init__(self) -> None:
        QObject.__init__(self)
        self._lines: list[ChatLineMetadata] = []

    def add_line(self, line: ChatLineMetadata) -> None:
        self._lines.append(line)
        self.added.emit()

    def remove_lines(self, number: int) -> None:
        number = min(number, len(self))
        if number < 0:
            raise ValueError
        if number == 0:
            return
        del self._lines[0:number]
        self.removed.emit(number)

    def __getitem__(self, n: int, /) -> ChatLineMetadata:
        return self._lines[n]

    def __iter__(self) -> Iterator[ChatLineMetadata]:
        return iter(self._lines)

    def __len__(self) -> int:
        return len(self._lines)


class Channel(ModelItem):
    added_chatter = pyqtSignal(object)
    removed_chatter = pyqtSignal(object)

    def __init__(
        self,
        id_: ChannelID,
        lines: Lines,
        topic: str,
        is_base: bool = False,
    ) -> None:
        ModelItem.__init__(self)
        self.is_base = is_base
        self.topic = topic
        self._data_fields.extend(("topic", "is_base"))
        self.lines = lines
        self.id = id_
        self.chatters: dict[tuple[ChannelID, str], ChannelChatter] = {}

    @property
    def id_key(self) -> ChannelID:
        return self.id

    def copy(self) -> Self:
        return self.__class__(self.id, self.lines, **self.field_dict)

    @transactional
    def update(self, *, _transaction: ModelTransaction = ModelTransaction(), **kwargs: Any) -> None:
        old = self.copy()
        super().update(**kwargs)
        self.emit_update(old, _transaction=_transaction)

    @transactional
    def set_topic(self, topic: str, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        self.update(topic=topic, _transaction=_transaction)

    @transactional
    def add_chatter(
        self,
        cc: ChannelChatter,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        self.chatters[cc.id_key] = cc
        _transaction.emit(self.added_chatter, cc)

    @transactional
    def remove_chatter(
        self,
        cc: ChannelChatter,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        del self.chatters[cc.id_key]
        _transaction.emit(self.removed_chatter, cc)
