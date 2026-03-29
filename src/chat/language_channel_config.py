from PyQt6.QtCore import QAbstractListModel
from PyQt6.QtCore import Qt

from src.chat.lang import LANGUAGE_CHANNELS
from src.config import SettingsCls
from src.util.theme import ThemeSet


class ChannelEntry:
    def __init__(self, name, icon, checked):
        self.name = name
        self.icon = icon
        self.checked = checked


class LanguageChannelConfig:
    def __init__(self, settings: SettingsCls, theme: ThemeSet) -> None:
        self._settings = settings
        self._theme = theme
        self._model = CheckableStringListModel()

    def model(self) -> CheckableStringListModel:
        return self._model

    def load_data(self) -> None:
        self._model.load_data(self._chan_flag_list())

    def _chan_flag_list(self) -> None:
        checked_channels = self._current_channels()
        channels = []
        for name, langs in LANGUAGE_CHANNELS.items():
            icon = self._country_icon(langs[0])
            checked = name in checked_channels
            channels.append(ChannelEntry(name, icon, checked))

        channels.sort(key=lambda x: x.name)
        return channels

    # TODO - move somewhere
    def _country_icon(self, country):
        return self._theme.icon(f"chat/countries/{country}.png")

    def _current_channels(self):
        checked_channels = self._settings.get('client/lang_channels', "")
        return [c for c in checked_channels.split(';') if c]

    def save_channels(self) -> None:
        channels = self._model.checked_channels()
        self._settings.set('client/lang_channels', ';'.join(channels))


class CheckableStringListModel(QAbstractListModel):
    def __init__(self):
        QAbstractListModel.__init__(self)
        self._items = []

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        item = self._index_item(index)
        if item is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        if role == Qt.ItemDataRole.DecorationRole:
            return item.icon
        if role == Qt.ItemDataRole.CheckStateRole:
            return item.checked
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        item = self._index_item(index)
        if item is None:
            return False
        if role == Qt.ItemDataRole.CheckStateRole:
            item.checked = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        return False

    def _index_item(self, index):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def load_data(self, entries: list[ChannelEntry]) -> None:
        self.modelAboutToBeReset.emit()
        self._items = entries
        self.modelReset.emit()

    def flags(self, index):
        if index.isValid():
            return Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        return 0

    def checked_channels(self):
        return [i.name for i in self._items if i.checked]
