
from __future__ import annotations

from enum import Enum

from PyQt6.QtWidgets import QListWidget

from src.api.models.Mod import Mod
from src.api.models.ModType import ModType
from src.vaults.listitem import VaultListItem
from src.vaults.modvault import utils


class ModSortType(Enum):
    NONE = "None"
    ALPHABETICAL = "Alphabetic"
    DATE = "Date"
    RATING = "Rating"


class ModDisplayType(Enum):
    ALL = "All"
    UNRANKED = "Unranked"
    RANKED = "Ranked"
    INSTALLED = "Installed"
    SIM = "Sim Only"
    UI = "UI Only"


class ModListItem(VaultListItem):
    def __init__(self, parent: QListWidget, item_data: Mod) -> None:
        VaultListItem.__init__(self, parent, item_data)
        self.item_data = item_data
        self.display_type = ModDisplayType.ALL
        self.sort_type = ModSortType.ALPHABETICAL
        assert item_data.version is not None
        self.item_version = item_data.version

    def on_sort_type_changed(self, index: int) -> None:
        self.sort_type = tuple(ModSortType)[index]

    def on_display_type_changed(self, index: int) -> None:
        self.display_type = tuple(ModDisplayType)[index]

    def should_be_visible(self) -> bool:
        if self.display_type == ModDisplayType.ALL:
            return True
        elif self.display_type == ModDisplayType.UNRANKED:
            return not self.item_version.ranked
        elif self.display_type == ModDisplayType.RANKED:
            return self.item_version.ranked
        elif self.display_type == ModDisplayType.INSTALLED:
            return self.item_version.uid in [mod.uid for mod in utils.installedMods]
        elif self.display_type == ModDisplayType.SIM:
            return self.item_version.modtype == ModType.SIM
        elif self.display_type == ModDisplayType.UI:
            return self.item_version.modtype == ModType.UI

        else:
            return True

    def _less_than(self, other: VaultListItem) -> bool:
        match self.sort_type:
            case ModSortType.NONE:
                return VaultListItem._less_than(self, other)
            case ModSortType.ALPHABETICAL:
                return self._lt_alphabetical(other)
            case ModSortType.RATING:
                return self._lt_rating(other)
            case ModSortType.DATE:
                return self._lt_date(other)
