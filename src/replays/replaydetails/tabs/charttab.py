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
import json
import os
from collections.abc import Generator
from functools import lru_cache

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src import util
from src.replays.replaydetails.chart import ChartWidget
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.replayformat import cmdTypeToString
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.utils import ACTION_ICONS
from src.replays.replaydetails.utils import PLAYER_COLORS


@lru_cache(1)
def units_pixmaps(units_dir: str) -> dict[str, QPixmap]:
    pixmaps = {}
    pixmap = QPixmap()
    for file in os.listdir(units_dir):
        icon = os.path.join(units_dir, file)
        pixmap.load(icon)
        unit, *_ = file.lower().partition(".")
        pixmaps[unit] = pixmap.scaled(48, 48)
    return pixmaps


@lru_cache(1)
def action_pixmaps(file: str) -> dict[str, QPixmap]:
    pixmap = QPixmap()
    pixmap.load(file)
    return {
        name: pixmap.copy(0, i * 48, 48, 48)
        for i, name in enumerate(ACTION_ICONS)
    }


class ChartsTabUI:
    def setupUi(self, widget: QWidget) -> None:
        main_layout = QVBoxLayout(widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cpms = ChartWidget()
        self.cpms.setMaximumHeight(330)
        main_layout.addWidget(self.cpms)

        actions_layout = QHBoxLayout()
        self.actionsDisplay = QTextBrowser()
        actions_layout.addWidget(self.actionsDisplay)

        self.actionsFilterLayout = QVBoxLayout()
        self.showAllPlayers = QCheckBox("Select all")
        self.showAllPlayers.setChecked(True)
        self.actionsFilterLayout.addWidget(self.showAllPlayers)

        actions_layout.addLayout(self.actionsFilterLayout)
        main_layout.addLayout(actions_layout)


class ChartsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.replay = ReplayParser()
        self.ui = ChartsTabUI()
        self.ui.setupUi(self)
        self.show_player_actions = {"all": self.ui.showAllPlayers}
        self.action_icons = os.path.join(util.COMMON_DIR, "replays", "actions48.png")
        self.units_icons = os.path.join(util.COMMON_DIR, "unitdb", "units")
        db_path = os.path.join(util.COMMON_DIR, "unitdb", "unitdb.json")
        with open(db_path) as file:
            self.unitsdb = json.loads(file.read())

    def clear_old_checkboxes(self) -> None:
        # FIXME?: maybe we should create and remove the whole widget
        # with checkboxes and avoid this surgeoning
        self.ui.showAllPlayers.disconnect()
        while layout_item := self.ui.actionsFilterLayout.takeAt(1):
            if checkbox_line := layout_item.layout():
                while innter_item := checkbox_line.takeAt(0):
                    widget = innter_item.widget()
                    if widget is None:
                        continue
                    widget.setParent(None)
                    widget.deleteLater()
                    checkbox_line.removeWidget(widget)
            self.ui.actionsFilterLayout.removeItem(layout_item)

    def initialize(self, replay: ReplayParser) -> None:
        self.replay = replay
        self.clear_old_checkboxes()
        self.gen_chart()
        self.populate_player_selection()
        self.ui.cpms.selected_tick_signal.connect(self.on_mouse_moved)

    def add_resources(self) -> None:
        document = self.ui.actionsDisplay.document()
        assert document is not None
        source_type = document.ResourceType.ImageResource
        for name, pixmap_ in action_pixmaps(self.action_icons).items():
            document.addResource(source_type, QUrl(name), pixmap_)
        for name, pixmap_ in units_pixmaps(self.units_icons).items():
            document.addResource(source_type, QUrl(name), pixmap_)

    def gen_chart(self) -> None:
        self.ui.actionsDisplay.clear()
        self.add_resources()
        players_number = len(self.replay.players)
        ticks_number = self.replay.ticks
        max_h_val = 0

        self.cpmData = [[] for _ in range(players_number)]
        for i in range(players_number):
            if i not in self.replay.cpmChart:
                continue
            self.cpmData[i] = [0] * (ticks_number + 600)
            for tick in self.replay.cpmChart[i]:
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
            self.ui.actionsDisplay.setText("<b>No actions</b>")
            self.ui.cpms.reset()
            self.ui.cpms.update()
            return

        colors = [
                PLAYER_COLORS[int(self.replay.army[i]["PlayerColor"]) - 1]
                for i in range(players_number)
        ]
        self.ui.cpms.graph(self.cpmData, max_h_val, colors, ticks_number)

    def populate_player_selection(self) -> None:
        self.ui.showAllPlayers.checkStateChanged.connect(
            lambda state: [
                checkbox.setChecked(state == Qt.CheckState.Checked)
                for key, checkbox in self.show_player_actions.items()
                if key != "all"
            ],
        )

        army = self.replay.army
        for id, name in self.replay.players.items():
            line = QHBoxLayout()
            line.setSpacing(6)

            checkbox = QCheckBox(text=name)
            checkbox.setChecked(True)

            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            label.setMaximumSize(10, 10)

            pixmap = QPixmap(10, 10)
            pixmap.fill(QColor(PLAYER_COLORS[int(army[id]["PlayerColor"]) - 1]))
            label.setPixmap(pixmap)

            line.addWidget(checkbox)
            line.addWidget(label)

            self.ui.actionsFilterLayout.addLayout(line)
            self.show_player_actions[id] = checkbox

    def _gen_player_actions(self, tick: int) -> Generator[str, None, None]:
        yield (
            f"time: {seconds_to_human(tick//10)}"
            f" to {seconds_to_human(min(tick+600, self.replay.ticks)//10)}"
            f"<br/>"
        )
        for player_id in self.replay.cpmChart:
            yield (
                f"<b style='color:{self.ui.cpms.colors[player_id]}'>"
                f"{self.replay.army[player_id]['PlayerName']}</b>: "
                f"{self.cpmData[player_id][tick] or 'no'} actions<br/>"
            )
            if (
                    player_id in self.show_player_actions
                    and not self.show_player_actions[player_id].isChecked()
            ):
                continue

            for action in self.replay.commands[player_id]:
                if action["tick"] < tick or action["tick"] >= tick + 600:
                    continue

                command = cmdTypeToString[action["cmd_type"]]
                match command:
                    case "BuildFactory" | "BuildMobile" | "Upgrade":
                        blueprint = action["blueprint"]
                        unit_name = self.unitsdb.get(blueprint, "")
                        yield f"<img title='{unit_name}' src=\"{blueprint}\"/>"
                    case "Script":
                        if "Enhancement" in action["upgrades"]:
                            yield f"{command}: {action['upgrades']['Enhancement']}"
                        elif "TaskName" in action["upgrades"]:
                            yield f"{command}: {action['upgrades']['TaskName']}"
                    case _:
                        url = f"{command.lower()}_pix"
                        if url in ACTION_ICONS:
                            yield f"<img title='{command}' src=\"{url}\"/>"
            yield "<br/>" * 2

    def on_mouse_moved(self, tick: int) -> None:
        if not self.replay.commands:
            return
        self.ui.actionsDisplay.setText("".join(self._gen_player_actions(tick)))
