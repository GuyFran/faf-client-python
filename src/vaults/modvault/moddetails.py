import os

from PyQt6.QtWidgets import QLabel

from src import util
from src.api.models.Mod import Mod
from src.api.models.ModVersion import ModVersion
from src.vaults.detailswidget import DetailsWidget
from src.vaults.modvault import utils


class ModDetailsWidget(DetailsWidget):
    def is_installed(self) -> bool:
        assert isinstance(self.item_version, ModVersion)
        return self.item_version.uid in [mod.uid for mod in utils.installedMods]

    def set_author(self) -> None:
        assert isinstance(self.item_data, Mod)
        if self.item_data.author:
            author_label = QLabel(f"{self.item_data.author}")
            self.ui.authorLayout.addWidget(author_label)
        else:
            self.ui.authorLayout.addWidget(QLabel("Unknown Author"))
        if self.item_data.uploader:
            uploader_label = QLabel(f"{self.item_data.uploader.login}")
            self.ui.authorLayout.addWidget(uploader_label)

    def set_type(self) -> None:
        assert isinstance(self.item_version, ModVersion)
        self.ui.typeLabel.setText(f"Type: {self.item_version.typ}")

    def set_additional_info(self) -> None:
        assert isinstance(self.item_version, ModVersion)
        self.ui.additionalInfoLabel.setText(f"UID: {self.item_version.uid}")

    def version_info(self) -> list[tuple[str, str]]:
        assert isinstance(self.item_version, ModVersion)
        return [
            ("Version:", str(self.item_version.version)),
            ("Filename:", self.item_version.filename),
            ("Type:", self.item_version.typ),
            ("Ranked:", "Yes" if self.item_version.ranked else "No"),
            ("Hidden:", "Yes" if self.item_version.hidden else "No"),
        ]

    def technical_info(self) -> list[tuple[str, str]]:
        assert isinstance(self.item_version, ModVersion)
        return [
            ("UID", self.item_version.uid),
            ("Filename", self.item_version.filename),
            ("Version", str(self.item_version.version)),
            ("Type", self.item_version.typ),
            ("Ranked", "Yes" if self.item_version.ranked else "No"),
            ("Hidden", "Yes" if self.item_version.hidden else "No"),
            ("Download URL", self.item_version.download_url),
            ("Thumbnail URL", self.item_version.thumbnail_url),
        ]

    def download_item(self) -> None:
        utils.downloadMod(self.item_version.download_url, self.item_data.display_name)

    def remove_item(self) -> None:
        mod = utils.getModInfoFromFolder(self.item_data.display_name)
        utils.removeMod(mod)

    def view_folder(self) -> None:
        full_path = os.path.join(utils.MODFOLDER, self.item_data.display_name)
        util.showDirInFileBrowser(full_path)
