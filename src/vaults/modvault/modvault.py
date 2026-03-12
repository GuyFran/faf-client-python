import logging
import os

from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src import util
from src.api.ApiBase import QueryOptions
from src.api.models.Mod import Mod
from src.api.models.ModType import ModType
from src.api.vaults_api import ModApiConnector
from src.downloadManager import ImageDownloader
from src.vaults.modvault import utils
from src.vaults.modvault.moddetails import ModDetailsWidget
from src.vaults.modvault.modlistitem import ModDisplayType
from src.vaults.modvault.modlistitem import ModListItem
from src.vaults.modvault.modlistitem import ModSortType
from src.vaults.modvault.modlistwidget import ModListWidget
from src.vaults.modvault.modsmanager import ModsManagerDialog
from src.vaults.vault import BrowseType
from src.vaults.vault import Vault

from .uimodwidget import UIModWidget
from .uploadwidget import UploadModWidget

logger = logging.getLogger(__name__)


class ModVault(Vault[Mod]):
    def setup(self) -> None:
        logger.debug("Mod Vault tab instantiating")
        self._search_params_ui = "vaults/modfilters.ui"
        super().setup()
        self.image_loader = ImageDownloader(util.MOD_PREVIEW_DIR)
        self.UIButton.clicked.connect(self.openUIModForm)
        self.uids = [mod.uid for mod in utils.getInstalledMods()]

        for sort_type in ModSortType:
            self.SortTypeList.addItem(sort_type.value)
        for display_type in ModDisplayType:
            self.ShowTypeList.addItem(display_type.value)

        self.apiConnector = ModApiConnector()
        self.apiConnector.data_ready.connect(self.items_info)

        most_played_row = self.browseComboBox.findText(BrowseType.MOST_PLAYED.value)
        self.browseComboBox.view().setRowHidden(most_played_row, True)
        item = self.browseComboBox.model().item(most_played_row)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.UIButton.show()
        self.mod_type_buttons = QtWidgets.QButtonGroup()
        self.mod_type_buttons.addButton(self.searchParams.allTypesRadio)
        self.mod_type_buttons.addButton(self.searchParams.simRadio)
        self.mod_type_buttons.addButton(self.searchParams.uiRadio)

        self.searchParams.allTypesRadio.setChecked(True)
        self.searchParams.uploaderInput.returnPressed.connect(self.search)
        self.manage_installed_dialog = ModsManagerDialog(self.client)
        self.buttonManageInstalled.clicked.connect(self.manage_installed_dialog.run)

    def construct_search_filters(self) -> QueryOptions:
        filters: list[str] = []
        if name := self.searchParams.searchInput.text().lower().strip():
            filters.append(f"displayName=='*{name}*'")
        if author := self.searchParams.authorInput.text().lower().strip():
            filters.append(f"author=='*{author}*'")
        if uploader := self.searchParams.uploaderInput.text().lower().strip():
            filters.append(f"uploader.login=='*{uploader}*'")

        if self.searchParams.rankedRadio.isChecked():
            filters.append("latestVersion.ranked=='true'")
        elif self.searchParams.unrankedRadio.isChecked():
            filters.append("latestVersion.ranked=='false'")

        if self.searchParams.simRadio.isChecked():
            filters.append(f"latestVersion.type=={ModType.SIM.value}")
        elif self.searchParams.uiRadio.isChecked():
            filters.append(f"latestVersion.type=={ModType.UI.value}")

        return {"filter": ";".join(filters)} if filters else {}

    def reset_search_params(self) -> None:
        super().reset_search_params()
        self.searchParams.uploaderInput.clear()
        self.searchParams.allTypesRadio.setChecked(True)

    def create_item_widget(self, data: Mod) -> ModListWidget:
        return ModListWidget(data, self.image_loader)

    def create_list_item(self, data: Mod) -> ModListItem:
        return ModListItem(self.itemList, data)

    def create_details_widget(self, data: Mod) -> ModDetailsWidget:
        assert self.client.me.player is not None
        return ModDetailsWidget(data, self.client.me.player)

    def on_item_availability_changed(self) -> None:
        current_item = self.itemList.currentItem()
        self.itemList.itemWidget(current_item).update_visibility()

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec()

    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtWidgets.QFileDialog.getExistingDirectory(
            self.client,
            "Select the mod directory to upload",
            utils.MODFOLDER,
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if utils.isModFolderValid(modDir):
                # os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = utils.parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug(
                        "There were %s errors and %s warnings.",
                        modinfofile.error,
                        modinfofile.warnings,
                    )
                    logger.debug(modinfofile.errorMsg)
                    QtWidgets.QMessageBox.critical(
                        self.client,
                        "Lua parsing error",
                        modinfofile.errorMsg + "\nMod uploading cancelled.",
                    )
                else:
                    if modinfofile.warning:
                        uploadmod = QtWidgets.QMessageBox.question(
                            self.client,
                            "Lua parsing warning",
                            (
                                modinfofile.errorMsg
                                + "\nDo you want to upload the mod?"
                            ),
                            QtWidgets.QMessageBox.StandardButton.Yes,
                            QtWidgets.QMessageBox.StandardButton.No,
                        )
                    else:
                        uploadmod = QtWidgets.QMessageBox.StandardButton.Yes
                    if uploadmod == QtWidgets.QMessageBox.StandardButton.Yes:
                        modinfo = utils.ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Mod selection",
                    "This folder doesn't contain a mod_info.lua file",
                )
