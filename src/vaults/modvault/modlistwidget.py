from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.Mod import Mod
from src.api.models.ModVersion import ModVersion
from src.vaults.listwidget import VaultListWidget
from src.vaults.modvault import utils


class ModListWidget(VaultListWidget):
    def is_installed(self) -> bool:
        assert isinstance(self.item_version, ModVersion)
        return self.item_version.uid in [mod.uid for mod in utils.installedMods]

    def set_author(self) -> None:
        if self.item_data.author:
            self.ui.authorLabel.setText(f"<b>By:</b> {self.item_data.author}")

    def grid_elements(self) -> list[QWidget | QLayout]:
        notice_label = QLabel()
        notice_label.setProperty("ranked_mod", "true")
        if self.item_version.ranked:
            notice_label.setText("ⓘ Ranked")

        assert isinstance(self.item_data, Mod)
        uploader_label = QLabel()
        if self.item_data.uploader is not None:
            uploader_label.setText(f"<b>Uploader:</b> {self.item_data.uploader.login}")

        assert isinstance(self.item_version, ModVersion)
        type_label = QLabel(f"<b>Type:</b> {self.item_version.typ}")

        return [
            notice_label,          self.recommended_label(),
            uploader_label,        type_label,
            self.uploaded_label(), self.rating_layout(),
        ]
