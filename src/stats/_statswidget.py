import logging
import time

from PyQt6 import QtCore

from src import util
from src.api.models.Leaderboard import Leaderboard
from src.api.stats_api import LeaderboardApiConnector
from src.qt.utils import block_signals
from src.ui.busy_widget import BusyWidget

from .leaderboard_widget import LeaderboardWidget

logger = logging.getLogger(__name__)

ANTIFLOOD = 0.1

FormClass, BaseClass = util.THEME.loadUiType("stats/stats.ui")


class StatsWidget(BaseClass, FormClass, BusyWidget):

    # signals
    laddermaplist = QtCore.pyqtSignal(dict)

    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.client = client

        self.selected_player = None
        self.selected_player_loaded = False
        self.currentChanged.connect(self.busy_entered)
        self.pagesDivisions = {}
        self.pagesDivisionsResults = {}
        self.pagesAllLeagues = {}

        self.floodtimer = time.time()

        self.currentLeague = 0
        self.currentDivision = 0

        self.FORMATTER_LADDER = str(
            util.THEME.readfile("stats/formatters/ladder.qthtml"),
        )
        self.FORMATTER_LADDER_HEADER = str(
            util.THEME.readfile("stats/formatters/ladder_header.qthtml"),
        )

        # setup other tabs

        self.apiConnector = LeaderboardApiConnector()
        self.apiConnector.data_ready.connect(self.process_leaderboards_info)
        self.apiConnector.requestData({"sort": "id"})

        # hiding some non-functional tabs
        self.removeTab(self.indexOf(self.ladderTab))
        self.removeTab(self.indexOf(self.laddermapTab))

        self.leaderboardNames = []
        self.client.authorized.connect(self.onAuthorized)

    def onAuthorized(self):
        if not self.leaderboardNames:
            self.refreshLeaderboards()

    def refreshLeaderboards(self):
        with block_signals(self.leaderboards):
            while self.leaderboards.widget(0) is not None:
                self.leaderboards.widget(0).deleteLater()
                self.leaderboards.removeTab(0)
            self.apiConnector.requestData(dict(sort="id"))

    @QtCore.pyqtSlot(int)
    def leaderboardsTabChanged(self, curr):
        if self.leaderboards.widget(curr) is not None:
            self.leaderboards.widget(curr).entered()

    def process_leaderboards_info(self, message: dict[str, list[Leaderboard]]) -> None:
        self.leaderboardNames.clear()
        for index, leaderboard in enumerate(message["values"]):
            self.leaderboardNames.append(leaderboard.technical_name)
            self.leaderboards.insertTab(
                index,
                LeaderboardWidget(self.client, self, leaderboard.technical_name),
                leaderboard.pretty_name,
            )
        self.leaderboards.setCurrentIndex(1)
        self.leaderboards.currentChanged.connect(self.leaderboardsTabChanged)

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if self.currentIndex() == self.indexOf(self.leaderboardsTab):
            self.leaderboards.currentChanged.emit(
                self.leaderboards.currentIndex(),
            )
