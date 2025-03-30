from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Mod import Mod
from src.vaults.listwidget import VaultListWidget
from src.vaults.modvault import utils


class ModListWidget(VaultListWidget):
    def __init__(self, item_data: Mod, parent: QWidget | None = None) -> None:
        VaultListWidget.__init__(self, item_data, parent)
        self.item_data = item_data
        self.item_version = item_data.version
        self.thumbnail_loader.set_save_dir(util.MOD_PREVIEW_DIR)

    def get_thumbnail(self) -> QPixmap:
        name_option = QUrl.ComponentFormattingOption.EncodeSpaces
        icon_name = QUrl(self.item_version.thumbnail_url).fileName(name_option)
        if (preview_path := utils.getIcon(icon_name)):
            return QPixmap(preview_path)
        return QPixmap()

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
            self.uploaded_label(), self.rating_layout(),
        ]
