from collections.abc import ItemsView
from collections.abc import Iterator
from collections.abc import KeysView
from collections.abc import ValuesView

from PyQt6.QtCore import QObject


class QObjectMapping[KT, VT](QObject):
    """
    ABC similar to collections.abc.MutableMapping.
    Used since we can't mixin the above with QObject.
    """

    def __len__(self) -> int:
        return 0

    def __iter__(self) -> Iterator[KT]:
        while False:
            yield None

    def __getitem__(self, key: KT, /) -> VT:
        raise KeyError

    def __setitem__(self, key: KT, value: VT, /) -> None:
        raise KeyError

    def __delitem__(self, key: KT, /) -> None:
        raise KeyError

    __marker = object()

    def pop(self, key: KT, default: VT = __marker) -> VT:
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def get(self, key: KT, default: VT | None = None) -> VT | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: KT, /) -> bool:
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def keys(self) -> KeysView[KT]:
        return KeysView(self)  # type: ignore[arg-type]

    def values(self) -> ValuesView[VT]:
        return ValuesView(self)  # type: ignore[arg-type]

    def items(self) -> ItemsView[KT, VT]:
        return ItemsView(self)  # type: ignore[arg-type]
