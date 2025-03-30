from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Map import Map
from src.api.models.MapVersion import MapVersion
from src.fa import maps
from src.vaults.listwidget import VaultListWidget


class MapListWidget(VaultListWidget):
    def is_installed(self) -> bool:
        assert isinstance(self.item_version, MapVersion)
        return maps.isMapAvailable(self.item_version.folder_name)

    def set_author(self) -> None:
        assert isinstance(self.item_data, Map)
        if self.item_data.author:
            self.ui.authorLabel.setText(f"<b>By:</b> {self.item_data.author.login}")

    def grid_elements(self) -> list[QWidget | QLayout]:
        notice_label = QLabel()
        notice_label.setProperty("unranked_map", "true")
        if not self.item_version.ranked:
            notice_label.setText("ⓘ Unranked")

        assert isinstance(self.item_version, MapVersion)
        width = self.item_version.size.width_km
        height = self.item_version.size.height_km
        size_label = QLabel(f"<b>Size (km):</b> {width} x {height}")

        games_label = QLabel(f"<b>Games:</b> {self.item_version.games_played}")
        return [
            notice_label,          self.recommended_label(),
            size_label,            games_label,
            self.uploaded_label(), self.rating_layout(),
        ]
