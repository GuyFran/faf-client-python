import logging
import os
from stat import S_IWRITE

from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src import util
from src.api.ApiBase import QueryOptions
from src.api.models.Map import Map
from src.api.models.MapVersion import MapSize
from src.api.vaults_api import MapApiConnector
from src.downloadManager import ImageDownloader
from src.fa import maps
from src.fa.maps_.map_utils import get_save_file
from src.vaults import luaparser
from src.vaults.mapvault.mapdetails import MapDetailsWidget
from src.vaults.mapvault.maplistitem import MapDisplayType
from src.vaults.mapvault.maplistitem import MapListItem
from src.vaults.mapvault.maplistitem import MapSortType
from src.vaults.mapvault.maplistwidget import MapListWidget
from src.vaults.vault import Vault

logger = logging.getLogger(__name__)


class MapVault(Vault[Map]):
    def setup(self) -> None:
        self._search_params_ui = "vaults/mapfilters.ui"
        logger.debug("Map Vault tab instantiating")
        super().setup()
        self.image_loader = ImageDownloader(util.MAP_PREVIEW_SMALL_DIR)
        self.installed_maps = maps.getUserMaps()

        for sort_type in MapSortType:
            self.SortTypeList.addItem(sort_type.value)
        for display_type in MapDisplayType:
            self.ShowTypeList.addItem(display_type.value)

        self.searchParams.mapWidthComboBox.addItem("Any")
        self.searchParams.mapHeightComboBox.addItem("Any")
        for i in (5, 10, 20, 40, 80):
            self.searchParams.mapWidthComboBox.addItem(f"{i} km")
            self.searchParams.mapHeightComboBox.addItem(f"{i} km")
        self.searchParams.mapMaxPlayersComboBox.addItem("Any")
        for i in range(1, 17):
            self.searchParams.mapMaxPlayersComboBox.addItem(str(i))

        self.mapApiConnector = MapApiConnector()
        self.mapApiConnector.data_ready.connect(self.items_info)

        self.apiConnector = self.mapApiConnector

    def create_item_widget(self, data: Map) -> MapListWidget:
        return MapListWidget(data, self.image_loader)

    def create_list_item(self, data: Map) -> MapListItem:
        return MapListItem(self.itemList, data)

    def create_details_widget(self, data: Map) -> MapDetailsWidget:
        assert self.client.me.player is not None
        return MapDetailsWidget(data, self.client.me.player)

    def construct_search_filters(self) -> QueryOptions:
        filters: list[str] = []
        if name := self.searchParams.searchInput.text().lower().strip():
            filters.append(f"displayName=='*{name}*'")
        if author := self.searchParams.authorInput.text().lower().strip():
            filters.append(f"author.login=='*{author}*'")

        if self.searchParams.rankedRadio.isChecked():
            filters.append("latestVersion.ranked=='true'")
        elif self.searchParams.unrankedRadio.isChecked():
            filters.append("latestVersion.ranked=='false'")

        if (width_index := self.searchParams.mapWidthComboBox.currentIndex()) > 0:
            size = MapSize.from_side_km(5 * (1 << (width_index - 1)))
            filters.append(f"latestVersion.width=={size.width_px}")
        if (height_index := self.searchParams.mapHeightComboBox.currentIndex()) > 0:
            size = MapSize.from_side_km(5 * (1 << (height_index - 1)))
            filters.append(f"latestVersion.height=={size.height_px}")

        if (players_index := self.searchParams.mapMaxPlayersComboBox.currentIndex()) > 0:
            filters.append(f"latestVersion.maxPlayers=={players_index}")

        return {"filter": ";".join(filters)} if filters else {}

    def reset_search_params(self) -> None:
        super().reset_search_params()
        self.searchParams.mapWidthComboBox.setCurrentIndex(0)
        self.searchParams.mapHeightComboBox.setCurrentIndex(0)
        self.searchParams.mapMaxPlayersComboBox.setCurrentIndex(0)

    @QtCore.pyqtSlot()
    def uploadMap(self):
        mapDir = QtWidgets.QFileDialog.getExistingDirectory(
            self.client,
            "Select the map directory to upload",
            maps.getUserMapsFolder(),
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        logger.debug("Uploading map from: " + mapDir)
        if mapDir != "":
            if maps.isMapFolderValid(mapDir):
                os.chmod(mapDir, S_IWRITE)
                mapName = os.path.basename(mapDir)
                # zipName = mapName.lower() + ".zip"

                scenariolua = luaparser.luaParser(
                    os.path.join(mapDir, maps.getScenarioFile(mapDir)),
                )
                scenarioInfos = scenariolua.parse(
                    {
                        'scenarioinfo>name': 'name',
                        'size': 'map_size',
                        'description': 'description',
                        'count:armies': 'max_players',
                        'map_version': 'version',
                        'type': 'map_type',
                        'teams>0>name': 'battle_type',
                    },
                    {'version': '1'},
                )

                if scenariolua.error:
                    logger.debug(
                        "There were %s errors and %s warnings",
                        scenariolua.errors,
                        scenariolua.warnings,
                    )
                    logger.debug(scenariolua.errorMsg)
                    QtWidgets.QMessageBox.critical(
                        self.client,
                        "Lua parsing error",
                        (
                            "{}\nMap uploading cancelled."
                            .format(scenariolua.errorMsg)
                        ),
                    )
                else:
                    if scenariolua.warning:
                        uploadmap = QtWidgets.QMessageBox.question(
                            self.client,
                            "Lua parsing warning",
                            (
                                "{}\nDo you want to upload the map?"
                                .format(scenariolua.errorMsg)
                            ),
                            QtWidgets.QMessageBox.StandardButton.Yes,
                            QtWidgets.QMessageBox.StandardButton.No,
                        )
                    else:
                        uploadmap = QtWidgets.QMessageBox.StandardButton.Yes
                    if uploadmap == QtWidgets.QMessageBox.StandardButton.Yes:
                        savelua = luaparser.luaParser(get_save_file(mapDir) or "")
                        saveInfos = savelua.parse({
                            'markers>mass*>position': 'mass:__parent__',
                            'markers>hydro*>position': 'hydro:__parent__',
                            'markers>army*>position': 'army:__parent__',
                        })
                        if savelua.error or savelua.warning:
                            logger.debug(
                                "There were %s errors and %s warnings",
                                scenariolua.errors,
                                scenariolua.warnings,
                            )
                            logger.debug(scenariolua.errorMsg)

                        self.__preparePositions(
                            saveInfos,
                            scenarioInfos["map_size"],
                        )

                        tmpFile = maps.processMapFolderForUpload(
                            mapDir,
                            saveInfos,
                        )
                        if not tmpFile:
                            QtWidgets.QMessageBox.critical(
                                self.client,
                                "Map uploading error",
                                (
                                    "Couldn't make previews for {}\n"
                                    "Map uploading cancelled.".format(mapName)
                                ),
                            )
                            return None

                        qfile = QtCore.QFile(tmpFile.name)

                        # TODO: implement uploading via API
                        ...
                        # removing temporary files
                        qfile.remove()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Map selection",
                    "This folder doesn't contain valid map data.",
                )
