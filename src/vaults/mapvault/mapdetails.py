import os
import shutil

from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.fa import maps
from src.vaults.detailswidget import DetailsWidget

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class MapDetailsWidget(DetailsWidget):
    def __init__(
            self,
            item_data: Map,
            parent: QWidget | None = None,
    ) -> None:
        DetailsWidget.__init__(self, item_data, util.MAP_PREVIEW_LARGE_DIR, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

    def is_installed(self) -> bool:
        return maps.isMapAvailable(self.item_version.folder_name)

    def set_author(self) -> None:
        if self.item_data.author:
            author_label = QLabel(f"{self.item_data.author.login}")
            self.ui.authorLayout.addWidget(author_label)
        else:
            self.ui.authorLayout.addWidget(QLabel("Unknown Author"))

    def set_type(self) -> None:
        self.ui.typeLabel.setText(f"Type: {self.item_data.map_type}")

    def set_additional_info(self) -> None:
        self.ui.additionalInfoLabel.setText(f"🎮 {self.item_data.games_played} games played")

    def version_info(self) -> list[tuple[str, str]]:
        height = self.item_version.size.height_km
        width = self.item_version.size.width_km
        return [
            ("Version:", str(self.item_version.version)),
            ("Dimensions (km):", f"{width} x {height}"),
            ("Max Players:", str(self.item_version.max_players)),
            ("Games Played:", str(self.item_version.games_played)),
            ("Ranked:", "Yes" if self.item_version.ranked else "No"),
            ("Hidden:", "Yes" if self.item_version.hidden else "No"),
        ]

    def technical_info(self) -> list[tuple[str, str]]:
        return [
            ("Folder Name", self.item_version.folder_name),
            ("Width", str(self.item_version.size.width_km)),
            ("Height", str(self.item_version.size.height_km)),
            ("Max Players", str(self.item_version.max_players)),
            ("Version", str(self.item_version.version)),
            ("Games Played", str(self.item_version.games_played)),
            ("Ranked", "Yes" if self.item_version.ranked else "No"),
            ("Hidden", "Yes" if self.item_version.hidden else "No"),
            ("Download URL", self.item_version.download_url),
            ("Small Thumbnail", self.item_version.thumbnail_url_small),
            ("Large Thumbnail", self.item_version.thumbnail_url_large),
        ]

    def download_item(self) -> None:
        maps._doDownloadMap(
            self.item_version.folder_name,
            self.item_version.download_url,
            silent=False,
        )

    def remove_item(self) -> None:
        full_path = os.path.join(maps.getUserMapsFolder(), self.item_version.folder_name)
        shutil.rmtree(full_path)

    def view_folder(self) -> None:
        util.showDirInFileBrowser(maps.folderForMap(self.item_version.folder_name))
