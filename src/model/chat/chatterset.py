from __future__ import annotations

from src.model.chat.chatter import Chatter
from src.model.modelitemset import ModelItemSet
from src.model.player import Player
from src.model.playerset import Playerset
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class Chatterset(ModelItemSet[str, Chatter]):
    def __init__(self, playerset: Playerset) -> None:
        super().__init__()
        self._playerset = playerset
        playerset.before_added.connect(self._at_player_added)
        playerset.before_removed.connect(self._at_player_removed)

    @transactional
    def set_item(
        self,
        key: str,
        value: Chatter,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        super().set_item(key, value, _transaction=_transaction)
        # Don't put newly added element's signal in the transaction
        if (player := self._playerset.get_by_name(value.id_key)) is not None:
            value.player = player

        value.before_updated.connect(self._at_user_updated)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key: str, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        chatter = super().del_item(key, _transaction=_transaction)
        if chatter is None:
            return
        chatter.before_updated.disconnect(self._at_user_updated)
        self.emit_removed(chatter, _transaction)

    def _at_player_added(
        self,
        player: Player,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if player.login in self:
            self[player.login].set_player(player, _transaction=_transaction)

    def _at_player_removed(
        self,
        player: Player,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if player.login in self:
            self[player.login].set_player(None, _transaction=_transaction)

    def _at_user_updated(
        self,
        user: Chatter,
        olduser: Chatter,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if user.name != olduser.name:
            self._handle_rename(user, olduser, _transaction)

    def _handle_rename(
        self,
        user: Chatter,
        olduser: Chatter,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        # We should never rename to an existing user, but let's handle it
        if user.name in self:
            self.del_item(user.name, _transaction=_transaction)

        if olduser.name in self._items:
            del self._items[olduser.name]
        self._items[user.name] = user

        newplayer = self._playerset.get_by_name(user.name)
        user.set_player(newplayer, _transaction=_transaction)
