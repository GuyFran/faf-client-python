from __future__ import annotations

from typing import Any
from typing import Self

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.model.chat.channelchatterset import ChannelChatterRelation
from src.model.chat.channelchatterset import ChannelChatterset
from src.model.chat.channelset import Channelset
from src.model.chat.chatterset import Chatterset
from src.model.playerset import Playerset


class Chat(QObject):
    new_server_message = pyqtSignal(str)
    connect_event = pyqtSignal()
    disconnect_event = pyqtSignal()

    def __init__(
        self,
        channelset: Channelset,
        chatterset: Chatterset,
        channelchatterset: ChannelChatterset,
        cc_relation: ChannelChatterRelation,
    ) -> None:
        QObject.__init__(self)
        self.channels = channelset
        self.chatters = chatterset
        self.channelchatters = channelchatterset
        self._cc_relation = cc_relation
        self._connected = False

    @classmethod
    def build(cls, playerset: Playerset, **kwargs: Any) -> Self:
        channels = Channelset.build(**kwargs)
        chatters = Chatterset(playerset)
        channelchatters = ChannelChatterset()
        cc_relation = ChannelChatterRelation(
            channels, chatters, channelchatters,
        )
        return cls(channels, chatters, channelchatters, cc_relation)

    def add_server_message(self, msg: str) -> None:
        self.new_server_message.emit(msg)

    # Does not affect model contents, only tells if the user is connected.
    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value: bool) -> None:
        self._connected = value
        if self._connected:
            self.connect_event.emit()
        else:
            self.disconnect_event.emit()
