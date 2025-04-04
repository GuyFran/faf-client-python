from __future__ import annotations

from enum import Enum

from PyQt6.QtWidgets import QListWidget

from src.api.models.Map import Map
from src.fa import maps
from src.vaults.listitem import VaultListItem


class MapSortType(Enum):
    NONE = "None"
    ALPHABETICAL = "Alphabetic"
    DATE = "Date"
    RATING = "Rating"
    SIZE = "Size"
    GAMES_PLAYED = "Games Played"


class MapDisplayType(Enum):
    ALL = "All"
    UNRANKED = "Unranked"
    RANKED = "Ranked"
    INSTALLED = "Installed"


class MapListItem(VaultListItem):
    def __init__(self, parent: QListWidget, item_data: Map) -> None:
        VaultListItem.__init__(self, parent, item_data)
        self.item_data = item_data
        self.display_type = MapDisplayType.ALL
        self.sort_type = MapSortType.ALPHABETICAL
        assert item_data.version is not None
        self.item_version = item_data.version

    def on_sort_type_changed(self, index: int) -> None:
        self.sort_type = tuple(MapSortType)[index]

    def on_display_type_changed(self, index: int) -> None:
        self.display_type = tuple(MapDisplayType)[index]

    def set_display_type(self, index: int) -> None:
        self.on_display_type_changed(index)

    def should_be_visible(self) -> bool:
        match self.display_type:
            case MapDisplayType.ALL:
                return True
            case MapDisplayType.UNRANKED:
                return not self.item_version.ranked
            case MapDisplayType.RANKED:
                return self.item_version.ranked
            case MapDisplayType.INSTALLED:
                return maps.isMapAvailable(self.item_version.folder_name)

    def _lt_size(self, other: MapListItem) -> bool:
        if self.item_version.size == other.item_version.size:
            return self._lt_alphabetical(other)
        return self.item_version.size < other.item_version.size

    def _lt_games_played(self, other: MapListItem) -> bool:
        return self.item_data.games_played < other.item_data.games_played

    def _less_than(self, other: VaultListItem) -> bool:
        if not isinstance(other, MapListItem):
            return VaultListItem._less_than(self, other)
        match self.sort_type:
            case MapSortType.NONE:
                return VaultListItem._less_than(self, other)
            case MapSortType.ALPHABETICAL:
                return self._lt_alphabetical(other)
            case MapSortType.RATING:
                return self._lt_rating(other)
            case MapSortType.DATE:
                return self._lt_date(other)
            case MapSortType.SIZE:
                return self._lt_size(other)
            case MapSortType.GAMES_PLAYED:
                return self._lt_games_played(other)
