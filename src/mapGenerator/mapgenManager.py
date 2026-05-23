import logging
import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QObject
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest
from semantic_version import Version

from src import util
from src.config import Settings
from src.fa.maps import getUserMapsFolder
from src.mapGenerator.mapgenProcess import MapGeneratorProcess
from src.mapGenerator.mapgenUtils import generatedMapPattern
from src.vaults.dialogs import download_file

logger = logging.getLogger(__name__)

RELEASE_URL = "https://github.com/FAForever/Neroxis-Map-Generator/releases/"
RELEASE_VERSION_PATH = "download/{version}/NeroxisGen_{version}.jar"
GENERATOR_JAR_NAME = "MapGenerator_{}.jar"


class MapGeneratorManager(QObject):
    new_available = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.latestVersion = Settings.get("mapGenerator/latest_version", "")

        self.currentVersion = Settings.get('mapGenerator/version', "0", str)

        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_request_finished)

        self._update_waiter = QEventLoop()
        self._updates_checked = False
        self.process_stdout = ""

    def set_current_version_number(self, version: str) -> None:
        self.currentVersion = version
        Settings.set("mapGenerator/version", version)

    def set_latest_version(self, version: str) -> None:
        new = Version(version) > Version(self.latestVersion)
        self.latestVersion = version
        Settings.set("mapGenerator/latest_version", version)
        if new:
            self.new_available.emit()

    def update_current_if_needed(self) -> None:
        if self.currentVersion != "0":
            return
        self.check_updates()
        self.set_current_version_number(self.latestVersion)

    def generateMap(self, mapname: str | None = None, args: list[str] | None = None) -> list[str]:
        if mapname is None:
            # Requests latest version once per session
            self.update_current_if_needed()
            version = self.currentVersion
        else:
            matcher = generatedMapPattern.match(mapname)
            assert matcher is not None
            version = matcher[1]
            args = ['--map-name', mapname]

        generator_path = self.get_generator(version)
        if not generator_path:
            return []

        auto = Settings.get("mapGenerator/autostart", default=False, type=bool)
        if not auto and mapname is not None:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle("Generate map")
            msgbox.setText(
                "It looks like you don't have the map being used by this "
                "lobby. Do you want to generate it? <br/><b>{}</b>"
                .format(mapname),
            )
            msgbox.setInformativeText(
                "Map generation is a CPU intensive task and may take some "
                "time.",
            )
            msgbox.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.YesToAll
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            result = msgbox.exec()
            if result == QtWidgets.QMessageBox.StandardButton.No:
                return []
            elif result == QtWidgets.QMessageBox.StandardButton.YesToAll:
                Settings.set("mapGenerator/autostart", True)

        maps_folder = getUserMapsFolder()
        if not os.path.exists(maps_folder):
            os.makedirs(maps_folder)

        # Start generator with progress bar
        process = MapGeneratorProcess(generator_path, maps_folder, args or [])
        process.run()
        self.process_stdout = process.stdout

        # Check if map exists or generator failed
        for name in process.mapnames:
            if not os.path.isdir(os.path.join(maps_folder, name)):
                return []
        else:
            return process.mapnames

    def get_generator(self, version: str) -> str:
        if not version:
            return ""

        name = GENERATOR_JAR_NAME.format(version)
        file_path = os.path.join(util.MAPGEN_DIR, name)

        # Check if required version is already in folder
        if os.path.isdir(util.MAPGEN_DIR):
            for infile in os.listdir(util.MAPGEN_DIR):
                if infile.lower() == name.lower():
                    return file_path

        # Download from github if not
        url = RELEASE_URL + RELEASE_VERSION_PATH.format(version=version)
        if download_file(url, util.MAPGEN_DIR, name, "map generator", silent=False):
            return file_path
        return ""

    def check_updates(self) -> None:
        '''
        Not downloading anything here.
        Just requesting latest version and return the number
        '''
        if self._updates_checked:
            return

        request = QNetworkRequest(QUrl(RELEASE_URL).resolved(QUrl("latest")))
        self.manager.get(request)

        progress = QtWidgets.QProgressDialog()
        progress.setCancelButtonText("Cancel")
        progress.setWindowFlags(Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setValue(0)
        progress.setModal(True)
        progress.setWindowTitle("Looking for updates")
        progress.show()

        self._update_waiter.exec()
        progress.close()
        self._updates_checked = True

    def on_request_finished(self, reply: QNetworkReply) -> None:
        redirect_url = reply.url()
        if "releases/tag/" in redirect_url.toString():
            self.set_latest_version(redirect_url.fileName())
        self._update_waiter.quit()

    def run_help(self) -> None:
        self.update_current_if_needed()
        generator_path = self.get_generator(self.currentVersion)
        process = MapGeneratorProcess(generator_path, ".", ["--help"])
        process.run()
        self.process_stdout = process.stdout
