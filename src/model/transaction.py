from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import pyqtBoundSignal

type SignalArgs = tuple[object, ...]


class ModelTransaction:
    """
    Allows model classes to postpone side effects of a model update (such as
    emitting signals) until after the model is in a consistent state.
    """

    def __init__(self) -> None:
        self._signals: list[tuple[pyqtBoundSignal, SignalArgs]] = []

    def emit(self, signal: pyqtBoundSignal, *args: Any) -> None:
        self._signals.append((signal, args))

    def finalize(self) -> None:
        for signal, sigargs in self._signals:
            signal.emit(*sigargs)
        self._signals.clear()


# An easy way for a function to create a transaction if it's called without one
# and finalize it once it's done, and otherwise use a supplied transaction.
#
# In order to use it, a function has to define a _transaction keyword argument
# and should not accept another transaction instance. The transaction
# argument will be added to kwargs if any were defined and _transaction was not
# among them

def transactional[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    def trans_fn(*args: P.args, **kwargs: P.kwargs) -> R:
        if not kwargs or "_transaction" not in kwargs:
            transaction = ModelTransaction()
            kwargs["_transaction"] = transaction
            ret = fn(*args, **kwargs)
            transaction.finalize()
        else:
            ret = fn(*args, **kwargs)
        return ret
    return trans_fn
