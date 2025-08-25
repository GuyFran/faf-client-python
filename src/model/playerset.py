from src.model.modelitemset import ModelItemSet
from src.model.player import Player
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class Playerset(ModelItemSet[int, Player]):
    def __init__(self) -> None:
        super().__init__()
        # Login -> Player map
        self._logins: dict[str, Player] = {}

    def getID(self, name: str) -> int:
        try:
            return self._logins[name].id
        except KeyError:
            return -1

    def get_by_name(self, name: str) -> Player | None:
        if (idx := self.getID(name)) != -1:
            return self[idx]
        return None

    @transactional
    def set_item(
        self,
        key: int,
        value: Player,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        super().set_item(key, value, _transaction=_transaction)
        self._logins[value.login] = value
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key: int, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        player = super().del_item(key, _transaction=_transaction)
        if player is None:
            return
        del self._logins[player.login]
        self.emit_removed(player, _transaction)

    def __delitem__(self, item: int) -> None:
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)
