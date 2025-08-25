from src.model.chat.channel import Channel
from src.model.chat.channel import ChannelID
from src.model.chat.channelchatter import ChannelChatter
from src.model.chat.channelset import Channelset
from src.model.chat.chatter import Chatter
from src.model.chat.chatterset import Chatterset
from src.model.modelitemset import ModelItemSet
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class ChannelChatterset(ModelItemSet[tuple[ChannelID, str], ChannelChatter]):
    @transactional
    def set_item(
        self,
        key: tuple[ChannelID, str],
        value: ChannelChatter,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        super().set_item(key, value, _transaction=_transaction)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(
        self,
        key: tuple[ChannelID, str],
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        chatter = super().del_item(key, _transaction=_transaction)
        if chatter is None:
            return
        self.emit_removed(chatter, _transaction)


class ChatterChannelIndex:
    def __init__(self):
        self._by_channel: dict[ChannelID, set[ChannelChatter]] = {}
        self._by_chatter: dict[str, set[ChannelChatter]] = {}

    def ccs_by_chatter(self, chatter: Chatter) -> set[ChannelChatter]:
        return self._by_chatter.setdefault(chatter.id_key, set())

    def ccs_by_channel(self, channel: Channel) -> set[ChannelChatter]:
        return self._by_channel.setdefault(channel.id_key, set())

    def add_cc(self, cc: ChannelChatter) -> None:
        self.ccs_by_chatter(cc.chatter).add(cc)
        self.ccs_by_channel(cc.channel).add(cc)

    def remove_cc(self, cc: ChannelChatter) -> None:
        chat_ccs = self.ccs_by_chatter(cc.chatter)
        chat_ccs.remove(cc)
        if not chat_ccs:
            del self._by_chatter[cc.chatter.id_key]

        chan_ccs = self.ccs_by_channel(cc.channel)
        chan_ccs.remove(cc)
        if not chan_ccs:
            del self._by_channel[cc.channel.id_key]


class ChannelChatterRelation:
    def __init__(
        self,
        channels: Channelset,
        chatters: Chatterset,
        channelchatters: ChannelChatterset,
    ) -> None:
        self._channels = channels
        self._chatters = chatters
        self._channelchatters = channelchatters
        self._index = ChatterChannelIndex()

        self._channelchatters.before_added.connect(self._new_cc)
        self._channelchatters.before_removed.connect(self._removed_cc)
        self._chatters.before_removed.connect(self._removed_chatter)
        self._channels.before_removed.connect(self._removed_channel)

    def _new_cc(
        self,
        cc: ChannelChatter,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        self._index.add_cc(cc)
        cc.channel.add_chatter(cc, _transaction=_transaction)
        cc.chatter.add_channel(cc, _transaction=_transaction)

    def _removed_cc(
        self,
        cc: ChannelChatter,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        self._index.remove_cc(cc)
        cc.channel.remove_chatter(cc, _transaction=_transaction)
        cc.chatter.remove_channel(cc, _transaction=_transaction)

    def _removed_chatter(
        self,
        chatter: Chatter,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        ccs = set(self._index.ccs_by_chatter(chatter))
        for cc in ccs:
            self._channelchatters.del_item(cc.id_key, _transaction=_transaction)

    def _removed_channel(self, channel: Channel, _transaction: ModelTransaction) -> None:
        ccs = set(self._index.ccs_by_channel(channel))
        for cc in ccs:
            self._channelchatters.del_item(cc.id_key, _transaction=_transaction)
