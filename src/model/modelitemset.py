from collections.abc import Iterator

from PyQt6.QtCore import pyqtSignal

from src.model.modelitem import ModelItem
from src.model.qobjectmapping import QObjectMapping
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class ModelItemSet[KT, VT: ModelItem](QObjectMapping[KT, VT]):
    added = pyqtSignal(object)
    removed = pyqtSignal(object)
    before_added = pyqtSignal(object, object)
    before_removed = pyqtSignal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[KT, VT] = {}

    def __getitem__(self, item: KT) -> VT:
        return self._items[item]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[KT]:
        return iter(self._items)

    def emit_added(self, value: VT, _transaction: ModelTransaction | None = None) -> None:
        _transaction.emit(self.added, value)
        self.before_added.emit(value, _transaction)

    def emit_removed(self, value: VT, _transaction: ModelTransaction | None = None) -> None:
        _transaction.emit(self.removed, value)
        self.before_removed.emit(value, _transaction)

    @transactional
    def set_item(self, key: KT, value: VT, _transaction: ModelTransaction | None = None) -> None:
        if key in self:
            raise ValueError
        if key != value.id_key:
            raise ValueError
        self._items[key] = value

    def __setitem__(self, key: KT, value: VT) -> None:
        # CAVEAT: use only as an entry point for model changes.
        self.set_item(key, value)

    @transactional
    def del_item(self, item: KT, _transaction: ModelTransaction | None = None) -> VT | None:
        return self._items.pop(item, None)

    def __delitem__(self, item: KT) -> None:
        # CAVEAT: use only as an entry point for model changes.
        self.del_item(item)

    @transactional
    def clear(self, _transaction: ModelTransaction | None = None) -> None:
        items = list(self.keys())
        for item in items:
            self.del_item(item, _transaction)
