from __future__ import annotations

import re
import time
from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING
from typing import cast

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtGui import QAction

from src import util
from src.api.models.Game import Game
from src.config import Settings
from src.downloadManager import DownloadRequest
from src.fa import maps
from src.fa.replay import WatchedReplaysTracker
from src.games.moditem import mods
from src.replays.scoreboard import Scoreboard

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow
    from src.replays._replayswidget import ReplaysWidget


class ReplayItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(
        self,
        painter: QtGui.QPainter | None,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        if painter is None:
            return
        self.initStyleOption(option, index)

        painter.save()

        replay_item = cast(ReplayItem | None, index.data(QtCore.Qt.ItemDataRole.UserRole))
        if replay_item is not None and replay_item.count_as_watched():
            factor = 300 if option.state & QtWidgets.QStyle.StateFlag.State_MouseOver else 200
            color = option.palette.text().color().darker(factor).name()
            option.text = re.sub(r"color=\".+?\"", f"color=\"{color}\"", option.text or "")

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())

        # clear icon and text before letting the control draw itself because
        # we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget,
        )

        # Shadow
        if index.data(QtCore.Qt.ItemDataRole.UserRole) is not None:
            painter.fillRect(
                option.rect.left()+8-1, option.rect.top()+8-1,
                iconsize.width(), iconsize.height(),
                QtGui.QColor("#202020"),
            )

        # Icon
        icon_rect = option.rect.adjusted(3, 0, 0, 0)
        if index.data(QtCore.Qt.ItemDataRole.UserRole) is not None:
            painter.fillRect(
                QtCore.QRect(icon_rect.x(), icon_rect.y(), iconsize.width(), iconsize.height()),
                QtGui.QColor("#202020"),
            )
        if replay_item is not None and replay_item.count_as_watched():
            icon_mode = icon.Mode.Disabled
        else:
            icon_mode = icon.Mode.Normal
        icon.paint(
            painter, icon_rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            icon_mode,
        )

        # Frame around the icon
        if index.data(QtCore.Qt.ItemDataRole.UserRole) is not None:
            pen = QtGui.QPen()
            pen.setWidth(1)
            # FIXME: This needs to come from theme.
            pen.setBrush(QtGui.QColor("#303030"))

            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawRect(
                icon_rect.left(), icon_rect.top(),
                iconsize.width(), iconsize.height(),
            )

        # Description
        painter.translate(
            option.rect.left() + iconsize.width() + 10,
            option.rect.top() + 10,
        )
        clip = QtCore.QRectF(
            0, 0, option.rect.width() - iconsize.width() - 15,
            option.rect.height(),
        )
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtCore.QSize:
        clip = index.model().data(index, QtCore.Qt.ItemDataRole.UserRole)
        if clip:
            return QtCore.QSize(215, clip.height)
        else:
            return QtCore.QSize(215, 35)


class ReplayItem(QtWidgets.QTreeWidgetItem):
    REPLAY_TREE_ITEM_FORMATTER = str(util.THEME.readfile("replays/formatters/replay.html"))

    def __init__(self, uid: int, parent: ReplaysWidget) -> None:
        super().__init__()

        self.uid = uid
        self.parent_widget = parent
        self.height = 70
        self.viewtext = None
        self.mapname = None
        self.mapdisplayname = None
        self.client = None
        self.game = None

        self.startDate = None
        self.duration = None
        self.live_delay = False

        self.extra_info_loaded = False
        self.spoiled = False
        self.url = "{}/{}".format(Settings.get('replay_vault/host'), self.uid)

        self.teams = {}
        self.mod = None
        self.moddisplayname = None

        self.options = []
        self.players = []
        self.numberplayers = 0
        self.winner = None
        self.teamWin = None

        self.setHidden(True)

        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._on_map_preview_downloaded)

    def update(self, replay: dict, client: ClientWindow) -> None:
        """ Updates this item from the message dictionary supplied """
        self.game = Game(**replay)
        self.replay = replay

        self.client = client
        self.name = replay["name"]

        if "id" in replay["mapVersion"]:
            self.mapid = replay["mapVersion"]["id"]
            self.mapname = replay["mapVersion"]["folderName"]
            self.previewUrlLarge = replay["mapVersion"]["thumbnailUrlLarge"]
        elif replay["featuredMod"]["technicalName"].lower() != "coop":
            self.mapname = "Neroxis Map Generator"
        else:
            self.mapname = "unknown"

        startDt = datetime.strptime(replay["startTime"], '%Y-%m-%dT%H:%M:%SZ')
        # local time
        startDt = startDt.replace(tzinfo=timezone.utc).astimezone(tz=None)

        if replay["endTime"] is None:
            seconds = time.time() - startDt.timestamp()
            if seconds > 86400:  # more than 24 hours
                self.duration = (
                    "<font color='darkgrey'>end time<br />&nbsp;missing</font>"
                )
            elif seconds > 7200:  # more than 2 hours
                self.duration = (
                    time.strftime('%H:%M:%S', time.gmtime(seconds))
                    + "<br />?playing?"
                )
            elif seconds < 300:  # less than 5 minutes
                self.duration = (
                    time.strftime('%H:%M:%S', time.gmtime(seconds))
                    + "<br />&nbsp;<font color='darkred'>playing</font>"
                )
                self.live_delay = True
            else:
                self.duration = (
                    time.strftime('%H:%M:%S', time.gmtime(seconds))
                    + "<br />&nbsp;playing"
                )
        else:
            endDt = datetime.strptime(replay["endTime"], '%Y-%m-%dT%H:%M:%SZ')
            # local time
            endDt = endDt.replace(tzinfo=timezone.utc).astimezone(tz=None)
            self.duration = time.strftime(
                '%H:%M:%S',
                time.gmtime((endDt - startDt).total_seconds()),
            )

        self.startHour = startDt.strftime("%H:%M")
        self.startDate = startDt.strftime("%Y-%m-%d")

        self.modid = replay["featuredMod"]["id"]
        self.mod = replay["featuredMod"]["technicalName"]

        # Map preview code
        self.mapdisplayname = maps.getDisplayName(self.mapname)

        if self.mapname == "Neroxis Map Generator":
            self.thumbnail = maps.get_preview_for_generated_map(self.mapname)
        else:
            self.thumbnail = maps.preview(self.mapname)
        if not self.thumbnail:
            self.thumbnail = util.THEME.icon("games/unknown_map.png")
            if self.mapname != "unknown":
                self.client.map_preview_downloader.download_preview(
                    self.mapname, self._map_dl_request,
                )

        if self.mod in mods:
            self.moddisplayname = mods[self.mod].name
        else:
            self.moddisplayname = self.mod

        availability = "" if self.game.replay_available else "ⓘ Unavailable"
        self.viewtext = self.REPLAY_TREE_ITEM_FORMATTER.format(
            time=self.startHour, name=self.name, map=self.mapdisplayname,
            duration=self.duration, mod=self.moddisplayname, availability=availability,
        )

    def _on_map_preview_downloaded(self, mapname: str, pixmap: QtGui.QPixmap) -> None:
        self.thumbnail = QtGui.QIcon(pixmap)
        self.setIcon(0, self.thumbnail)

    def load_extra_info(self) -> None:
        """
        processes information from the server about a replay into readable
        extra information for the user, also calls method to show the
        information
        """

        self.extra_info_loaded = True
        playersList = self.replay['playerStats']
        self.numberplayers = len(playersList)

        mvpscore = 0
        mvp = None
        scores = {}

        for player in playersList:  # player highscore
            if "score" in player:
                if player["score"] > mvpscore:
                    mvp = player
                    mvpscore = player["score"]

        # player -> teams & playerscore -> teamscore
        for player in playersList:
            # get ffa like into one team
            if self.mod == "phantomx" or self.mod == "murderparty":
                team = 1
            else:
                team = int(player["team"])

            if team == -1:
                continue

            if "score" in player:
                if team in scores:
                    scores[team] = scores[team] + player["score"]
                else:
                    scores[team] = player["score"]
            if team not in self.teams:
                self.teams[team] = [player]
            else:
                self.teams[team].append(player)

        if self.numberplayers == len(self.teams):  # some kind of FFA
            self.teams = {}
            scores = {}
            team = 1
            for player in playersList:  # player -> team (1)
                if team not in self.teams:
                    self.teams[team] = [player]
                else:
                    self.teams[team].append(player)

        if len(self.teams) == 1 or len(self.teams) == len(playersList):
            self.winner = mvp
        elif len(scores) > 0:  # team highscore
            mvt = 0
            for team in scores:
                if scores[team] > mvt:
                    self.teamWin = team
                    mvt = scores[team]

    def generate_scoreboard(self) -> Scoreboard:
        if not self.extra_info_loaded:
            self.load_extra_info()
        self.spoiled = not self.parent_widget.spoilerCheckbox.isChecked()
        assert self.client is not None
        assert self.game is not None
        scoreboard = Scoreboard(
            self.mod, self.winner, self.spoiled,
            self.duration, self.teamWin, self.uid, self.teams,
            self.client.player_ctx_menu, self.game,
        )
        scoreboard.setup()
        return scoreboard

    def pressed(self) -> None:
        menu = QtWidgets.QMenu(self.parent_widget)
        action_watched = QAction(f"Mark as {'unwatched' if self.watched() else 'watched'}", menu)
        action_watched.triggered.connect(self.change_watched_status)
        actionDownload = QAction("Download replay", menu)
        actionDownload.triggered.connect(self.downloadReplay)
        menu.addAction(action_watched)
        menu.addAction(actionDownload)
        menu.popup(QtGui.QCursor.pos())

    def downloadReplay(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.url))

    def display(self, column):
        if column == 0:
            return self.viewtext
        if column == 1:
            return self.viewtext

    def data(self, column, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.display(column)
        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return self
        return super().data(column, role)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """
        if not self.client:
            return True  # If not initialized...
        if not other.client:
            return False
        # Default: uid
        return self.uid < other.uid

    def change_watched_status(self) -> None:
        if self.watched():
            WatchedReplaysTracker.discard(self.uid)
        else:
            WatchedReplaysTracker.add(self.uid)
        self.parent_widget.onlineTree.update()

    def watched(self) -> bool:
        return self.uid in WatchedReplaysTracker

    def count_as_watched(self) -> bool:
        return (
            Settings.get("replay/markWatched", True, type=bool)
            and self.watched()
        )
