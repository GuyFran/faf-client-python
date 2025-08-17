from typing import Any
from typing import Self

from src.model.chat.channel import Channel
from src.model.chat.channel import ChannelID
from src.model.chat.channel import ChannelType
from src.model.modelitemset import ModelItemSet
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class Channelset(ModelItemSet):

    def __init__(self, base_channels: dict[ChannelID, Channel]) -> None:
        ModelItemSet.__init__(self)
        self.base_channels = base_channels

    @classmethod
    def build(cls, base_channels: dict[ChannelID, Channel], **kwargs: Any) -> Self:
        return cls(base_channels)

    @transactional
    def set_item(
        self,
        key: ChannelID,
        value: Channel,
        _transaction: ModelTransaction | None = None,
    ) -> None:
        value.is_base = (
            key.type == ChannelType.PUBLIC
            and key.name in self.base_channels
        )
        ModelItemSet.set_item(self, key, value, _transaction)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key, _transaction=None):
        channel = ModelItemSet.del_item(self, key, _transaction)
        if channel is None:
            return
        self.emit_removed(channel, _transaction)
