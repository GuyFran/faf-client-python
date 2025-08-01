from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.fa import maps
from src.mapGenerator.mapgenUtils import isGeneratedMap
from src.vaults.listwidget import VaultListWidget


class MapListWidget(VaultListWidget):
    def __init__(self, item_data: Map, parent: QWidget | None = None) -> None:
        VaultListWidget.__init__(self, item_data, util.MAP_PREVIEW_SMALL_DIR, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

    def is_installed(self) -> bool:
        return maps.isMapAvailable(self.item_version.folder_name)

    def set_author(self) -> None:
        if self.item_data.author:
            self.ui.authorLabel.setText(f"<b>By:</b> {self.item_data.author.login}")

    def grid_elements(self) -> list[QWidget | QLayout]:
        notice_label = QLabel()
        notice_label.setProperty("unranked_map", "true")
        if not self.item_version.ranked:
            notice_label.setText("ⓘ Unranked")

        width = self.item_version.size.width_km
        height = self.item_version.size.height_km
        size_label = QLabel(f"<b>Size (km):</b> {width} x {height}")

        games_label = QLabel(f"<b>Games:</b> {self.item_data.games_played}")
        return [
            notice_label,          self.recommended_label(),
            size_label,            games_label,
            self.created_label(), self.rating_layout(),
        ]

    def get_thumbnail(self) -> QPixmap:
        if isGeneratedMap(self.item_data.xd):
            return util.THEME.pixmap("games/generated_map.png")
        return super().get_thumbnail()
