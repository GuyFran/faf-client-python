import random
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDoubleSpinBox
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QWidget

from src import config
from src.qt.widgets.checkablecombobox import CheckableComboBox


class OptionMixin:
    def reset(self) -> None:
        raise NotImplementedError

    def set_value(self, value: Any) -> None:
        raise NotImplementedError

    def value(self) -> Any:
        raise NotImplementedError

    def active(self) -> bool:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def as_cmd_arg(self) -> list[str]:
        raise NotImplementedError


class MapGenOption[T: QWidget](OptionMixin):
    def __init__(
        self,
        name: str,
        ui_elem: T,
        typ: type = str,
        default: Any | None = None,
    ) -> None:
        self.name = name
        self.ui_elem = ui_elem
        self.typ = typ
        self.default = default

    def reset(self) -> None:
        if self.default is not None:
            self.set_value(self.default)

    def load(self) -> None:
        self.set_value(
            config.Settings.get(
                f"mapGenerator/{self.ui_elem.objectName()}",
                default=self.default,
                type=self.typ,
            ),
        )

    def save(self) -> None:
        config.Settings.set(
            f"mapGenerator/{self.ui_elem.objectName()}",
            self.value(),
        )

    def as_cmd_arg(self) -> list[str]:
        return [f"--{self.name}", str(self.value())]


class _ComboBoxOption[T: QComboBox](MapGenOption[T]):
    def __init__(
        self,
        name: str,
        ui_elem: T,
        default: str | None = None,
        opts: list[str] | None = None,
    ) -> None:
        super().__init__(name, ui_elem, str, default)
        self.opts = opts

    def set_opts(self, opts: list[str] | None) -> None:
        self.opts = opts

    def set_value(self, value: str) -> None:
        self.ui_elem.setCurrentText(value)

    def value(self) -> str:
        return self.ui_elem.currentText()

    def active(self) -> bool:
        return self.ui_elem.isEnabled() and self.value() != self.default

    def populate(self) -> None:
        if self.opts is None:
            return
        self.ui_elem.clear()
        for index, opt in enumerate(sorted(self.opts)):
            self.ui_elem.addItem(opt)
            self.ui_elem.setItemData(index, opt, Qt.ItemDataRole.ToolTipRole)

    def load(self) -> None:
        self.populate()
        super().load()


class ComboBoxOption(_ComboBoxOption[QComboBox]):
    ...


class CheckableComboBoxOption(_ComboBoxOption[CheckableComboBox]):
    def __init__(
        self,
        name: str,
        ui_elem: CheckableComboBox,
        default: str,
        opts: list[str] | None = None,
    ) -> None:
        ui_elem.setNoChoiceText(default)
        super().__init__(name, ui_elem, default, opts)

    def save(self) -> None:
        config.Settings.set(
            f"mapGenerator/{self.ui_elem.objectName()}",
            self.ui_elem.delimiter().join(self.ui_elem.currentData()),
        )

    def as_cmd_arg(self) -> list[str]:
        return [f"--{self.name}", random.choice(self.ui_elem.currentData())]


class SpinBoxOption(MapGenOption[QSpinBox]):
    def set_value(self, value: int) -> None:
        self.ui_elem.setValue(value)

    def value(self) -> int:
        return self.ui_elem.value()

    def active(self) -> bool:
        return self.ui_elem.isEnabled()


class DoubleSpinBoxOption(MapGenOption[QDoubleSpinBox]):
    def set_value(self, value: float) -> None:
        self.ui_elem.setValue(value)

    def value(self) -> float:
        return self.ui_elem.value()

    def active(self) -> bool:
        return self.ui_elem.isEnabled()


class RangeOption(OptionMixin):
    def __init__(
            self,
            name: str,
            minimum: SpinBoxOption,
            maximum: SpinBoxOption,
    ) -> None:
        self.name = name
        self.minimum = minimum
        self.maximum = maximum

    def reset(self) -> None:
        self.minimum.reset()
        self.maximum.reset()

    def value(self) -> float:
        minval = min(self.minimum.value(), self.maximum.value())
        maxval = max(self.minimum.value(), self.maximum.value())
        return random.randrange(round(minval), round(maxval + 1)) / 100

    def active(self) -> bool:
        return self.minimum.active() and self.maximum.active()

    def load(self) -> None:
        self.minimum.load()
        self.maximum.load()

    def save(self) -> None:
        self.minimum.save()
        self.maximum.save()

    def as_cmd_arg(self) -> list[str]:
        return [f"--{self.name}", str(self.value())]
