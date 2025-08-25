from typing import Any
from typing import Self

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal

from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


class ModelItem(QObject):
    updated = pyqtSignal(object, object)
    before_updated = pyqtSignal(object, object, object)

    def __init__(self):
        QObject.__init__(self)
        self._data_fields: list[str] = []

    def add_field(self, name: str, default: Any) -> None:
        self._data_fields.append(name)
        setattr(self, name, default)

    @property
    def field_dict(self) -> dict[str, Any]:
        return {v: getattr(self, v) for v in self._data_fields}

    def copy(self) -> Self:
        raise NotImplementedError

    def update(self, **kwargs: Any) -> None:
        # Ignore unknown fields for convenience
        for f in self._data_fields:
            if f in kwargs:
                setattr(self, f, kwargs[f])

    @transactional
    def emit_update(
        self,
        old: Self,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        _transaction.emit(self.updated, self, old)
        self.before_updated.emit(self, old, _transaction)

    @property
    def id_key(self) -> Any:
        raise NotImplementedError

    def __hash__(self):
        return hash(self.id_key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelItem):
            return False
        return self.id_key == other.id_key
