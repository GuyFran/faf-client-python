from __future__ import annotations

import enum
import re
from collections.abc import Sequence
from operator import itemgetter
from typing import NamedTuple
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings
from src.fa.factions import Factions
from src.qt.utils import block_signals
from src.replays.replaydetails.chatnotifiers import ACU_BLUEPRINTS
from src.replays.replaydetails.chatnotifiers import ACU_UPGRADE_NOTIFIERS
from src.replays.replaydetails.chatnotifiers import UNIT_NOTIFIERS
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.pixmaps import enhancement_pixmap
from src.replays.replaydetails.pixmaps import units_pixmaps
from src.replays.replaydetails.replayreader import ReplayParser
from src.replays.replaydetails.utils import PLAYER_COLORS


class EventType(enum.Enum):
    ACU_UPGRADE = enum.auto()
    HQ_UPGRADE = enum.auto()
    UNIT = enum.auto()
    LAST_COMMAND = enum.auto()


class ReplayEvent(NamedTuple):
    typ: EventType
    picture_name: str


class EventWidget(QWidget):
    def __init__(
        self,
        tick: int,
        login: str,
        text: str,
        faction: str,
        event: ReplayEvent,
    ) -> None:
        super().__init__()
        self.tick = tick
        self.login = login
        self.text = text
        self.faction = faction
        self.typ, self.picname = event

        self.pic = QLabel()
        self.timing = QLabel()
        self.timing.setObjectName("replayEventTime")

    def setup(self) -> None:
        layout = QVBoxLayout(self)
        layout.setStretch(0, 2)
        self.pic.setPixmap(self._pixmap())

        self.timing.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timing.setText(seconds_to_human(self.tick // 10))
        layout.addWidget(self.pic)
        layout.addWidget(self.timing)

    def _pixmap(self) -> QPixmap:
        if self.typ is EventType.ACU_UPGRADE:
            return enhancement_pixmap(self.faction, self.picname)
        else:
            return units_pixmaps()[self.picname]


class EventsTabUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QHBoxLayout(widget)
        self.eventsLayout = QListWidget()
        self.eventsLayout.setObjectName("replayEvents")
        self.eventsLayout.setFlow(QListWidget.Flow.LeftToRight)
        self.eventsLayout.setWrapping(True)
        self.eventsLayout.setUniformItemSizes(True)
        self.eventsLayout.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.eventsLayout, 3)

        self.filter_tab_widget = QTabWidget(widget)

        self.filter_upgrades_widget = QWidget()
        self.filter_upgrades_widget.setObjectName("overview_widget")

        self.filter_players_widget = QWidget()
        self.filter_players_widget.setObjectName("overview_widget")

        self.filter_tab_widget.addTab(self.filter_upgrades_widget, "Upgrades")
        self.filter_tab_widget.addTab(self.filter_players_widget, "Players")

        self.filterUpgradesLayout = QVBoxLayout(self.filter_upgrades_widget)

        self.selectAllUpgradesCheckBox = QCheckBox("Select All")

        self.acuUpgradesCheckBox = QCheckBox("ACU Upgrade")
        self.factoryUpgradesCheckBox = QCheckBox("HQ Upgrade")
        self.expCheckBox = QCheckBox("Experimental/Arty/Nuke")
        self.lastCommandCheckBox = QCheckBox("Approximate Death (Last Command)")

        for btn in (
            self.selectAllUpgradesCheckBox,
            self.acuUpgradesCheckBox,
            self.factoryUpgradesCheckBox,
            self.expCheckBox,
            self.lastCommandCheckBox,
        ):
            btn.setChecked(True)

        self.filterUpgradesLayout.addWidget(self.selectAllUpgradesCheckBox)
        self.filterUpgradesLayout.addSpacing(6)
        self.filterUpgradesLayout.addWidget(self.acuUpgradesCheckBox)
        self.filterUpgradesLayout.addWidget(self.factoryUpgradesCheckBox)
        self.filterUpgradesLayout.addWidget(self.expCheckBox)
        self.filterUpgradesLayout.addWidget(self.lastCommandCheckBox)
        self.filterUpgradesLayout.addStretch()

        self.filterPlayersLayout = QVBoxLayout(self.filter_players_widget)

        self.selectAllPlayersCheckBox = QCheckBox("Select All")
        self.selectAllPlayersCheckBox.setChecked(True)

        self.filterPlayersLayout.addWidget(self.selectAllPlayersCheckBox)
        self.filterPlayersLayout.addSpacing(6)

        layout.addWidget(self.filter_tab_widget, 1)


class EventsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.ui = EventsTabUI()
        self.ui.setupUi(self)
        self.events = []
        self.finished_pattern = re.compile(r"(.+) (done!|готов!)")

        self.visible_upgrades: list[int] = Settings.get_list(
            "replaycard.events/visible_upgrades",
            default=[1] * (len(tuple(EventType)) + 1),  # +1 for 'Select All' checkbox
            type=int,
        )
        self.ui.selectAllUpgradesCheckBox.setChecked(all(self.visible_upgrades[1:]))

        self.upgrade_filter_group = QButtonGroup()
        self.upgrade_filter_group.setExclusive(False)
        for i, btn in enumerate((
            self.ui.selectAllUpgradesCheckBox,
            self.ui.acuUpgradesCheckBox,
            self.ui.factoryUpgradesCheckBox,
            self.ui.expCheckBox,
            self.ui.lastCommandCheckBox,
        )):
            self.upgrade_filter_group.addButton(btn, i)
            if i != 0:
                btn.setChecked(bool(self.visible_upgrades[i]))
        self.upgrade_filter_group.buttonToggled.connect(self.on_upgrade_filter_changed)

        self.players_filter_group = QButtonGroup()
        self.players_filter_group.setExclusive(False)
        self.players_filter_group.addButton(self.ui.selectAllPlayersCheckBox)
        self.players_filter_group.buttonToggled.connect(self.on_player_filter_changed)

        self.armies: dict[int, dict[str, str | float]] = {}
        self.players: dict[int, str] = {}
        self.chat_lines: Sequence[tuple[int, str, str, str, int]] = ()
        self.last_activity: dict[int, int] = {}

    def on_upgrade_filter_changed(self, button: QCheckBox) -> None:
        if button is self.ui.selectAllUpgradesCheckBox:
            with block_signals(self.upgrade_filter_group) as group:
                for btn in group.buttons():
                    btn.setChecked(button.isChecked())
        elif self.ui.selectAllUpgradesCheckBox.isChecked():
            with block_signals(self.upgrade_filter_group):
                self.ui.selectAllUpgradesCheckBox.setChecked(False)

        self.update_visibility()

    def on_player_filter_changed(self, button: QCheckBox) -> None:
        if button is self.ui.selectAllPlayersCheckBox:
            with block_signals(self.players_filter_group) as group:
                for btn in group.buttons():
                    btn.setChecked(button.isChecked())
        elif self.ui.selectAllPlayersCheckBox.isChecked():
            with block_signals(self.players_filter_group):
                self.ui.selectAllPlayersCheckBox.setChecked(False)

        self.update_visibility()

    def update_visibility(self) -> None:
        for row in range(self.ui.eventsLayout.count()):
            item = self.ui.eventsLayout.item(row)
            assert item is not None

            event_type, sender = item.data(Qt.ItemDataRole.UserRole)

            player_btn = self.players_filter_group.button(sender)
            assert player_btn is not None

            event_btn = self.upgrade_filter_group.button(event_type.value)
            assert event_btn is not None

            item.setHidden(not player_btn.isChecked() or not event_btn.isChecked())

    def add_event_widget(
        self,
        tick: int,
        sender: int,
        event: ReplayEvent,
        enh_desc: str,
        faction: str,
    ) -> None:
        login = cast(str, self.armies[sender]["PlayerName"])
        event_widget = EventWidget(tick, login, enh_desc, faction, event)
        event_widget.setup()
        color_num = int(self.armies[sender]["PlayerColor"])
        color = PLAYER_COLORS[color_num - 1]
        list_widget_item = QListWidgetItem(self.ui.eventsLayout)
        list_widget_item.setSizeHint(event_widget.sizeHint())
        list_widget_item.setBackground(QColor(color))
        list_widget_item.setToolTip(f"{enh_desc}\n[{login}]")
        list_widget_item.setData(Qt.ItemDataRole.UserRole, (event.typ, sender))
        list_widget_item.setHidden(not self.visible_upgrades[event.typ.value])
        self.ui.eventsLayout.addItem(list_widget_item)
        self.ui.eventsLayout.setItemWidget(list_widget_item, event_widget)

    def identify_event(self, faction: str, desc: str) -> ReplayEvent | None:
        try:
            ret, _ = ACU_UPGRADE_NOTIFIERS[faction][desc]
            return ReplayEvent(EventType.ACU_UPGRADE, ret)
        except KeyError:
            pass
        try:
            ret = UNIT_NOTIFIERS[faction][desc]
            return ReplayEvent(EventType.UNIT if "230" in ret else EventType.HQ_UPGRADE, ret)
        except KeyError:
            pass
        try:
            return ReplayEvent(EventType.UNIT, UNIT_NOTIFIERS["experimentals"][desc])
        except KeyError:
            return None

    def initialize(self, parser: ReplayParser) -> None:
        self.armies = parser.army
        self.players = parser.players
        self.chat_lines = parser.chatLine
        self.last_activity = parser.last_activity
        self.teams = parser.teams

        self.add_events()
        self.add_player_checkboxes()

    def add_events(self) -> None:
        sorted_last_coms = sorted(self.last_activity.items(), key=itemgetter(1))

        events_gen = (line for line in self.chat_lines if line[2] == "notify")
        for tick, *_, text, sender in events_gen:
            if not (found := self.finished_pattern.match(text)):
                continue

            # ACU death/last command is not present in chat notifications
            if sorted_last_coms and sorted_last_coms[0][1] <= tick:
                dead_army, death_tick = sorted_last_coms.pop(0)
                faction = Factions(self.armies[dead_army]["Faction"]).name.lower()
                unit = ACU_BLUEPRINTS[faction]
                self.add_event_widget(
                    death_tick,
                    dead_army,
                    ReplayEvent(EventType.LAST_COMMAND, unit),
                    "Last Command",
                    faction,
                )

            faction = Factions(self.armies[sender]["Faction"]).name.lower()
            enh_desc = found.group(1).strip()

            identified_event = self.identify_event(faction, enh_desc.replace("upgrade", "").strip())
            if identified_event is None:
                continue
            self.add_event_widget(
                tick,
                sender,
                identified_event,
                enh_desc,
                faction,
            )

    def add_player_checkboxes(self) -> None:
        if len(self.players) == len(self.teams):
            for army_id in self.players:
                self._add_player_checkbox(army_id)
        else:
            for _, players in self.teams.items():
                for army_id in players:
                    self._add_player_checkbox(army_id)
                self.ui.filterPlayersLayout.addSpacing(6)

        self.ui.filterPlayersLayout.addStretch()

    def _add_player_checkbox(self, army_id: int) -> None:
        chkbx = QCheckBox(cast(str, self.armies[army_id]["PlayerName"]))
        chkbx.setChecked(True)
        self.ui.filterPlayersLayout.addWidget(chkbx)
        self.players_filter_group.addButton(chkbx, army_id)

    def save_settings(self) -> None:
        Settings.set(
            "replaycard.events/visible_upgrades",
            [int(btn.isChecked()) for btn in self.upgrade_filter_group.buttons()],
        )
