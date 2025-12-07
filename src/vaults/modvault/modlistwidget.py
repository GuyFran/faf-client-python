from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Mod import Mod
from src.downloadManager import ImageDownloader
from src.vaults.listwidget import VaultListWidget
from src.vaults.modvault import utils


class ModListWidget(VaultListWidget[Mod]):
    def __init__(
        self,
        item_data: Mod,
        image_loader: ImageDownloader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(item_data, image_loader, parent)
        self.item_version = item_data.version

    def is_installed(self) -> bool:
        return self.item_version.uid in [mod.uid for mod in utils.installedMods]

    def set_author(self) -> None:
        if self.item_data.author:
            self.ui.authorLabel.setText(f"<b>By:</b> {self.item_data.author}")

    def grid_elements(self) -> list[QWidget | QLayout]:
        notice_label = QLabel()
        notice_label.setProperty("ranked_mod", "true")
        if self.item_version.ranked:
            notice_label.setText("ⓘ Ranked")

        uploader_label = QLabel()
        if self.item_data.uploader is not None:
            uploader_label.setText(f"<b>Uploader:</b> {self.item_data.uploader.login}")

        type_label = QLabel(f"<b>Type:</b> {self.item_version.typ}")

        return [
            notice_label,          self.recommended_label(),
            uploader_label,        type_label,
            self.created_label(), self.rating_layout(),
        ]
