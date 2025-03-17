"""MIT License

Copyright (c) 2020 fafafaf

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
from __future__ import annotations

import json
import os
from functools import lru_cache

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtNetwork
from PyQt6 import QtWidgets

from src import util
from src.fa.maps import downloadMap
from src.fa.maps import getBaseMapsFolder
from src.fa.maps import getUserMapsFolder
from src.fa.maps import isMapAvailable
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.mapGenerator.mapgenUtils import isGeneratedMap
from src.replays.replaydetails.chart import ChartWidget
from src.replays.replaydetails.gamestats import StatsVisualizer
from src.replays.replaydetails.heatmap import Heatmap
from src.replays.replaydetails.replayformat import cmdTypeToString
from src.replays.replaydetails.replayreader import Replay
from src.replays.replaydetails.replayreader import ReplayException
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.utils import ACTION_ICONS
from src.replays.replaydetails.utils import PLAYER_COLORS


@lru_cache(1)
def units_pixmaps(units_dir: str) -> dict[str, QtGui.QPixmap]:
    pixmaps = {}
    pixmap = QtGui.QPixmap()
    for file in os.listdir(units_dir):
        icon = os.path.join(units_dir, file)
        pixmap.load(icon)
        unit, *_ = file.lower().partition(".")
        pixmaps[unit] = pixmap.scaled(48, 48)
    return pixmaps


@lru_cache(1)
def action_pixmaps(file: str) -> dict[str, QtGui.QPixmap]:
    pixmap = QtGui.QPixmap()
    pixmap.load(file)
    return {
        name: pixmap.copy(0, i * 48, 48, 48)
        for i, name in enumerate(ACTION_ICONS)
    }


def seconds_to_human(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)


class ReplayLoader(QtCore.QThread):
    replayLoaded = QtCore.pyqtSignal(int)
    replayPercentage = QtCore.pyqtSignal(int)
    replayException = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)
        self.replay = ReplayParser()

    def load_file(self, filename: str) -> None:
        if not filename:
            return

        replay = Replay.from_file(filename)
        self.replay = ReplayParser(replay)
        self.start()

    def load_data(self, data: QtNetwork.QNetworkReply) -> None:
        replay = Replay.from_qreply(data)
        self.replay = ReplayParser(replay)
        self.start()

    def run(self) -> None:
        try:
            self.replay.replayPercentage.connect(self.replayPercentage.emit)
            time = QtCore.QElapsedTimer()
            time.restart()
            self.replay.do_stuff()
            self.replayLoaded.emit(time.elapsed())
            del time
        except ReplayException as e:
            self.replayException.emit(e.args[0])


class ReplayDetailsCard(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs) -> None:
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))
        self.setWindowFlags(QtCore.Qt.WindowType.Widget)
        self.setModal(True)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.setBaseSize(800, 700)
        self.loader = ReplayLoader()
        self.loader.replayLoaded.connect(self.populatePages)
        self.loader.replayException.connect(self.show_replay_exception_msg)

        self.downloader = QtNetwork.QNetworkAccessManager(self)
        self.downloader.finished.connect(self.on_download_finished)

        self.setWindowTitle("Replay Details")
        # self.setWindowIcon(QtGui.QIcon(os.path.join(COMMON_DIR, "replays", "showreel.png")))

        downloadAction = QtGui.QAction('Download replay', self)
        downloadAction.triggered.connect(self.download_dialog)
        loadAction = QtGui.QAction('Load', self)
        loadAction.triggered.connect(self.select_file)

        self.aboutAction = QtGui.QAction('About', self)
        self.aboutAction.triggered.connect(self.show_about)
        menubar = QtWidgets.QMenuBar()
        filemenu = menubar.addMenu('&File')
        assert filemenu is not None

        filemenu.addAction(loadAction)
        filemenu.addAction(downloadAction)
        filemenu.addSeparator()
        menubar.addAction(self.aboutAction)

        self.replayInfo = QtWidgets.QTextBrowser()
        self.replayInfo.setText(
            "<h2>No replay loaded</h2>"
            "<p>To load a replay click <b>File</b> menu <b>Load</b> option</p>",
        )
        self.replayInfo.setReadOnly(True)

        self.replayInfoMap = QtWidgets.QLabel()
        self.replayInfoMap.setMinimumHeight(256)
        self.replayInfoMap.setMinimumWidth(256)
        self.replayInfoMap.setMaximumWidth(256)

        self.map_description = QtWidgets.QLabel()
        self.map_description.setWordWrap(True)
        self.map_description.setMaximumWidth(256)
        interaction_flag = QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        self.map_description.setTextInteractionFlags(interaction_flag)
        self.map_layout = QtWidgets.QHBoxLayout()
        self.map_layout.setSpacing(6)
        self.map_layout.addWidget(self.replayInfoMap)
        self.map_layout.addWidget(self.map_description)

        self.settingsTab = QtWidgets.QTextBrowser()
        self.settingsTab.setReadOnly(True)
        self.settingsTab.setVisible(False)

        self.get_map_button = QtWidgets.QPushButton("Generate map")
        self.get_map_button.setVisible(False)
        self.get_map_button.clicked.connect(self.obtain_map)

        self.replayInfoTabLayout = QtWidgets.QGridLayout()
        self.replayInfoTabLayout.addWidget(self.replayInfo, 0, 0, 4, 1)
        self.replayInfoTabLayout.addItem(self.map_layout, 0, 1)
        self.replayInfoTabLayout.addWidget(self.get_map_button, 1, 1)
        self.replayInfoTabLayout.addWidget(self.settingsTab, 2, 1)

        self.replayInfoTab = QtWidgets.QWidget()
        self.replayInfoTab.setLayout(self.replayInfoTabLayout)

        self.chatTab = QtWidgets.QTextEdit()
        self.chatTab.setReadOnly(True)

        self.heatmap_tab = Heatmap()

        self.cpms = ChartWidget()
        self.cpms.setMaximumHeight(330)
        self.cpms.selected_tick_signal.connect(self.on_mouse_moved)

        self.actionsDisplay = QtWidgets.QTextBrowser()

        action_icons = os.path.join(util.COMMON_DIR, "replays", "actions48.png")
        self.action_pixes = action_pixmaps(action_icons)
        self.unit_pixes = units_pixmaps(os.path.join(util.COMMON_DIR, "unitdb", "units"))

        self.chartsTabLayout = QtWidgets.QVBoxLayout()
        self.chartsTabLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
#        self.chartsTabLayout.setMargin(0)
        self.chartsTabLayout.addWidget(self.cpms)
        actions_layout = QtWidgets.QHBoxLayout()
        actions_layout.addWidget(self.actionsDisplay)
        self.playerActionFilter = QtWidgets.QWidget()
        actions_layout.addWidget(self.playerActionFilter)
        self.chartsTabLayout.addItem(actions_layout)

        self.chartsTab = QtWidgets.QWidget()
        self.chartsTab.setLayout(self.chartsTabLayout)

        self.game_stats_tab = StatsVisualizer()

        self.replayTabs = QtWidgets.QTabWidget()
        self.replayTabs.addTab(self.replayInfoTab, "Info")
        self.replayTabs.addTab(self.chatTab, "Chat")
        self.replayTabs.addTab(self.heatmap_tab, "Heatmap")
        self.replayTabs.addTab(self.chartsTab, "Graph")
        self.replayTabs.addTab(self.game_stats_tab, "Game Stats")
#        self.replayTabs.addTab(self.settingsTab,"Settings")

        self.loadingBar = QtWidgets.QProgressBar()
        self.loadingBar.hide()
        self.statusBar = QtWidgets.QStatusBar()
        # self.statusBar.setMaximumHeight(20)
        self.statusBar.setSizeGripEnabled(False)
        self.statusBar.addWidget(self.loadingBar, 1)

        db_path = os.path.join(util.COMMON_DIR, "unitdb", "unitdb.json")
        with open(db_path) as file:
            self.unitsdb = json.loads(file.read())

        self._layout.addWidget(self.replayTabs)
        self._layout.addWidget(self.statusBar)
        self._layout.setMenuBar(menubar)
        self.setLayout(self._layout)
        self.resize(1024, 768)
        self.generator = MapGeneratorManager()

    def update_map_pixmap(self) -> None:
        pixmap = self.map_preview_pixmap(self.loader.replay.luaScenarioInfo["map"])
        self.replayInfoMap.setPixmap(pixmap)

    def obtain_map(self) -> None:
        map_folder = self.loader.replay.map_folder_name()
        if isGeneratedMap(map_folder):
            self.generator.generateMap(map_folder)
        else:
            downloadMap(map_folder)
        self.update_map_pixmap()
        self.update_get_map_button()

    def show_replay_exception_msg(self, msg: str) -> None:
        self.statusBar.showMessage("")
        msg = f"Can't parse this replay.<br/><br/>Error message:<br/><b>{msg}</b>"
        QtWidgets.QMessageBox.warning(self, "Error", msg)

    def download_dialog(self) -> None:
        def start_it():
            try:
                self.download_by_id(int(replayInput.text()))
                dialog.close()
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'Error', 'Replay id must be number')
                replayInput.clear()
                pass
        dialog = QtWidgets.QDialog(
            None,
            QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowSystemMenuHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint,
        )
        dialog.setWindowTitle("Download FAF replay")
        dialogLayout = QtWidgets.QVBoxLayout()
        replayInput = QtWidgets.QLineEdit()
        replayInput.setPlaceholderText("replay id")
        replayInput.returnPressed.connect(start_it)
        connectButton = QtWidgets.QToolButton()
        connectButton.setText("Download")
        connectButton.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        connectButton.clicked.connect(start_it)
        dialogLayout.addWidget(QtWidgets.QLabel("Please enter the replay id"))
        dialogLayout.addWidget(replayInput)
        dialogLayout.addWidget(connectButton, 0)
        dialog.setLayout(dialogLayout)
        dialog.exec()

    def download_by_id(self, id: int) -> None:
        url = f"https://replay.faforever.com/{id}"
        self.statusBar.showMessage("Downloading replay...")
        self.downloader.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))

    def download_by_url(self, qurl: QtCore.QUrl) -> None:
        self.statusBar.showMessage("Downloading replay...")
        self.downloader.get(QtNetwork.QNetworkRequest(qurl))

    def on_download_finished(self, reply: QtNetwork.QNetworkReply) -> None:
        if (
            reply.error() == reply.NetworkError.NoError
            and reply.header(QtNetwork.QNetworkRequest.KnownHeaders.ContentLengthHeader) != 0
        ):
            self.statusBar.showMessage("Parsing the replay file..")
            self.loader.load_data(reply)
            self.setWindowTitle(reply.url().url())
        else:
            self.statusBar.showMessage("Download failed")
            QtWidgets.QMessageBox.warning(self, 'Error', 'Can\'t download that replay')
        reply.deleteLater()

    def map_preview_pixmap(self, map_path: str) -> QtGui.QPixmap:
        try:
            # FIXME: both functions from fa.maps and map_path include "/maps/" suffix/prefix
            mapdirs = [
                os.path.dirname(getBaseMapsFolder()),
                os.path.dirname(getUserMapsFolder()),
            ]

            faf_path = os.path.join(util.APPDATA_DIR, "fa_path.lua")
            if os.path.exists(faf_path):
                try:
                    with open(faf_path, "rt") as f:
                        mapdir = f.readline().split("'")[1].replace("\\\\", "\\")
                    if os.path.exists(mapdir):
                        mapdirs.append(mapdir)
                except Exception:
                    pass

            file = None
            saveFile = None
            for dirName in mapdirs:
                if os.path.exists(dirName + map_path):
                    file = os.path.join(dirName + map_path)
                    saveFile = file.replace(".scmap", "_save.lua")
                    break

            if file and saveFile:
                with open(file, "rb") as f:
                    f.seek(30)  # scmap header
                    sizebuf = bytearray(f.read(4))
                    ddsSize = sizebuf[0] | sizebuf[1] << 8 | sizebuf[2] << 16 | sizebuf[3] << 24
                    f.seek(127, 1)  # dds header
                    img = bytearray(ddsSize-127)
                    f.readinto(img)
                    del img[::4]

                    size = int((len(img)/3) ** (1.0/2))

                mapImg = QtGui.QImage(
                    bytes(img),
                    size,
                    size,
                    QtGui.QImage.Format.Format_RGB888,
                ).rgbSwapped()

                if os.path.exists(saveFile):
                    with open(saveFile, 'rt') as f:
                        # find positions in mapname_save.lua file
                        armyPos = dict()
                        army = None
                        for line in f:
                            if line.find("ARMY_") > -1:
                                army = line.strip().split("'")
                            if line.find("position") > -1 and army:
                                if army:
                                    # ['position'] = VECTOR3
                                    x, _, y = line.strip()[24:-3].split(", ", 3)
                                    armyPos[army[1]] = float(x), float(y)
                                    army = None

                        # draw positions to the map preview image
                        acuIcon = QtGui.QPixmap(os.path.join(util.COMMON_DIR, "replays", "acu.png"))
                        color = QtGui.QColor(192, 165, 32)
                        mask = acuIcon.createMaskFromColor(color, QtCore.Qt.MaskMode.MaskOutColor)

                        p = QtGui.QPainter()
                        p.begin(mapImg)

                        text_option = QtGui.QTextOption(QtCore.Qt.AlignmentFlag.AlignCenter)
                        pen_style = QtCore.Qt.PenStyle.SolidLine

                        for id, player in self.loader.replay.army.items():
                            if id != 255 and player["ArmyName"] in armyPos:
                                x, y = armyPos[player["ArmyName"]]
                                x *= size / float(self.loader.replay.luaScenarioInfo["size"][1.0])
                                y *= size / float(self.loader.replay.luaScenarioInfo["size"][2.0])
                                x, y = round(x), round(y)

                                color = QtGui.QColor(PLAYER_COLORS[int(player["PlayerColor"]) - 1])
                                p.setPen(QtGui.QPen(color, 1, pen_style))

                                p.drawPixmap(x-5, y-5, 12, 12, acuIcon)
                                p.drawPixmap(x-5, y-5, 12, 12, QtGui.QPixmap(mask))

                                p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 1, pen_style))
                                contour = QtCore.QRectF(x-51, y+11, 100, 12)
                                p.drawText(contour, player["PlayerName"], text_option)

                                p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.white, 1, pen_style))
                                content = QtCore.QRectF(x-50, y+10, 100, 12)
                                p.drawText(content, player["PlayerName"], text_option)
                        p.end()
                return QtGui.QPixmap(mapImg)
            else:
                raise IOError
        except IOError:
            return QtGui.QPixmap(os.path.join(util.COMMON_DIR, "replays", "nomap.png"))

    def show_about(self) -> None:
        # flags = QtCore.Qt.WindowType.WindowTitleHint | QtCore.Qt.WindowType.WindowSystemMenuHint
        about = QtWidgets.QDialog(None, QtCore.Qt.WindowType.Widget)
        about.setWindowTitle("About")
        aboutText = (
            """
                <h3>Based on Synced Live Replay server</h3>
                <h5>by PattogoTehen in 2013</h5>
                <p>
                    More info on faf forum: <a href="http://forums.faforever.com/viewtopic.php?f=41&t=5774">http://forums.faforever.com/viewtopic.php?f=41&t=5774</a> <br/>  # noqa: E501
                    Source available on GitHub: <a href="https://github.com/fafafaf/livereplayserver">https://github.com/fafafaf/livereplayserver</a> <br/>  # noqa: E501
                    Online replay parser: <a href="https://fafafaf.github.io">https://fafafaf.github.io<a/>  # noqa: E501
                </p>
                <p>
                    Huge thanks to Aulex and TA4Life for testing, and Domino for lua support
                </p>
            """
        )
        aboutLabel = QtWidgets.QLabel(aboutText)
        aboutLabel.setWordWrap(True)
        aboutLabel.setOpenExternalLinks(True)
        aboutLabel.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            | QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse,
        )
        aboutLayout = QtWidgets.QVBoxLayout()
        aboutLayout.addWidget(aboutLabel)
        about.setLayout(aboutLayout)
        about.exec()

    @QtCore.pyqtSlot(int)
    def populatePages(self, ms: int) -> None:
        self.replayInfo.setText(self.loader.replay.get_info())
        self.chatTab.setText(self.loader.replay.get_chat())
        self.settingsTab.setVisible(True)
        self.settingsTab.setText(self.loader.replay.get_settings())

        self.heatmap_tab.set_pts(self.loader.replay.pts)
        self.heatmap_tab.create_heatmap(self.loader.replay.ticks)

        self.statusBar.showMessage(f"Replay loaded in {ms} ms")
        self.update_map_pixmap()
        self.replayInfoMap.setToolTip(self.loader.replay.map_display_name())
        self.map_description.setText(self.loader.replay.luaScenarioInfo["description"])
        self.update_get_map_button()
        self.gen_chart()
        self.populate_player_selection()
        self.game_stats_tab.draw_stats(self.loader.replay.game_stats)

    def populate_player_selection(self) -> None:
        select_all = QtWidgets.QCheckBox("Select all")
        select_all.setChecked(True)
        select_all.checkStateChanged.connect(
            lambda state: [
                checkbox.setChecked(state == QtCore.Qt.CheckState.Checked)
                for key, checkbox in self.show_player_actions.items()
                if key != "all"
            ],
        )

        self.show_player_actions = {"all": select_all}

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(select_all)
        army = self.loader.replay.army
        for id, name in self.loader.replay.players.items():
            line = QtWidgets.QHBoxLayout()
            line.setSpacing(6)

            checkbox = QtWidgets.QCheckBox(text=name)
            checkbox.setChecked(True)

            label = QtWidgets.QLabel()
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            label.setMaximumSize(10, 10)

            pixmap = QtGui.QPixmap(10, 10)
            pixmap.fill(QtGui.QColor(PLAYER_COLORS[int(army[id]["PlayerColor"]) - 1]))
            label.setPixmap(pixmap)

            line.addWidget(checkbox)
            line.addWidget(label)

            layout.addItem(line)
            self.show_player_actions[id] = checkbox
        self.playerActionFilter.setLayout(layout)

    def update_get_map_button(self) -> None:
        map_folder = self.loader.replay.map_folder_name()
        self.get_map_button.setVisible(not isMapAvailable(map_folder))
        text = "Generate map" if isGeneratedMap(map_folder) else "Download map"
        self.get_map_button.setText(text)

    def add_resources(self) -> None:
        document = self.actionsDisplay.document()
        assert document is not None
        source_type = document.ResourceType.ImageResource
        for name, pixmap_ in self.action_pixes.items():
            document.addResource(source_type, QtCore.QUrl(name), pixmap_)
        for name, pixmap_ in self.unit_pixes.items():
            document.addResource(source_type, QtCore.QUrl(name), pixmap_)

    def gen_chart(self) -> None:
        self.actionsDisplay.clear()
        self.add_resources()
        players_number = len(self.loader.replay.players)
        ticks_number = self.loader.replay.ticks
        max_h_val = 0

        self.cpmData = [[] for _ in range(players_number)]
        for i in range(players_number):
            if i not in self.loader.replay.cpmChart:
                continue
            self.cpmData[i] = [0] * (ticks_number + 600)
            for tick in self.loader.replay.cpmChart[i]:
                self.cpmData[i][tick] += 1

            num = sum(self.cpmData[i][0:600])
            prev_num = self.cpmData[i][0]
            for tick in range(1, ticks_number):
                num = num - prev_num + self.cpmData[i][tick+600]
                prev_num = self.cpmData[i][tick]
                if num > max_h_val:
                    max_h_val = num
                self.cpmData[i][tick] = num

            del self.cpmData[i][ticks_number:]

        if max_h_val == 0:
            self.actionsDisplay.setText("<b>No actions</b>")
            self.cpms.reset()
            self.cpms.update()
            return

        colors = [
                PLAYER_COLORS[int(self.loader.replay.army[i]["PlayerColor"]) - 1]
                for i in range(players_number)
        ]
        self.cpms.graph(self.cpmData, max_h_val, colors, ticks_number)

    def on_mouse_moved(self, tick: int) -> None:
        if not self.loader.replay.commands:
            return

        text = (
            f"time: {seconds_to_human(tick//10)}"
            f" to {seconds_to_human(min(tick+600, self.loader.replay.ticks)//10)}"
            f"<br/>"
        )
        for playerId in self.loader.replay.cpmChart:
            if not self.show_player_actions[playerId].isChecked():
                continue

            text += (
                f"<b style='color:{self.cpms.colors[playerId]}'>"
                f"{self.loader.replay.army[playerId]['PlayerName']}</b>: "
                f"{self.cpmData[playerId][tick] or 'no'} actions<br/>"
            )

            for action in self.loader.replay.commands[playerId]:
                if action["tick"] < tick or action["tick"] >= tick + 600:
                    continue

                command = cmdTypeToString[action["cmd_type"]]
                match command:
                    case "BuildFactory" | "BuildMobile" | "Upgrade":
                        blueprint = action["blueprint"]
                        unit_name = self.unitsdb.get(blueprint, "")
                        text += f"<img title='{unit_name}' src=\"{blueprint}\"/>"
                    case "Script":
                        if "Enhancement" in action["upgrades"]:
                            text += f"{command}: {action['upgrades']['Enhancement']}"
                        elif "TaskName" in action["upgrades"]:
                            text += f"{command}: {action['upgrades']['TaskName']}"
                    case _:
                        url = f"{command.lower()}_pix"
                        if url in ACTION_ICONS:
                            text += f"<img title='{command}' src=\"{url}\"/>"
            text += "<br/>" * 2

        self.actionsDisplay.setText(text)

    @QtCore.pyqtSlot()
    def select_file(self) -> None:
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select FA replay",
            os.path.join(util.APPDATA_DIR, "replays"),
            "*.fafreplay;;*.SCFAReplay",
        )
        if file:
            self.replay(file)

    def replay(self, path: str) -> None:
        self.replayTabs.setCurrentIndex(0)
        self.setWindowTitle(os.path.basename(str(path)))
        self.statusBar.showMessage("Parsing the replay file..")
        self.loader.load_file(path)
