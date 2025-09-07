import logging
from collections.abc import Iterator
from typing import cast

from PyQt6.QtCore import QDateTime
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkReply

from src.api.ApiAccessors import ApiAccessor
from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import PreParsedApiResponse
from src.api.ApiBase import PreProcessedApiResponse
from src.api.ApiBase import QueryOptions
from src.api.models.Achievement import Achievement
from src.api.models.Leaderboard import Leaderboard
from src.api.models.LeagueSeasonScore import LeagueSeasonScore
from src.api.models.PlayerAchievement import PlayerAchievement
from src.api.models.PlayerEvent import PlayerEvent
from src.api.parsers.LeaderboardParser import LeaderboardParser
from src.api.parsers.LeaderboardRatingParser import LeaderboardRatingParser

logger = logging.getLogger(__name__)


class LeaderboardRatingApiConnector(DataApiAccessor):
    player_ratings_ready = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__('/data/leaderboardRating')

    def get_player_ratings(self, pid: str) -> None:
        query = {
            "include": "leaderboard",
            "filter": f"player.id=={pid}",
        }
        self.get_by_query(query, self.handle_player_ratings)

    def handle_player_ratings(self, message: dict) -> None:
        ratings = {"values": LeaderboardRatingParser.parse_many(message)}
        self.player_ratings_ready.emit(ratings)


class LeaderboardApiConnector(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__("/data/leaderboard")

    def prepare_data(self, message: dict) -> dict[str, list[Leaderboard]]:
        return {"values": LeaderboardParser.parse_many(message)}


class LeaderboardRatingJournalApiConnector(ApiAccessor):
    ratings_ready = pyqtSignal(dict)
    api_error = pyqtSignal(str)

    def __init__(self, pid: str, leaderboard: str) -> None:
        super().__init__("/data/leaderboardRatingJournal")
        self.query: QueryOptions = {
            "include": "gamePlayerStats",
            "filter": (
                f"gamePlayerStats.player.id=={pid!r};"
                f"leaderboard.technicalName=={leaderboard!r};"
                "gamePlayerStats.scoreTime=isnull='false'"
            ),
            "sort": "-gamePlayerStats.scoreTime",
        }

    def handle_page(self, message: PreProcessedApiResponse) -> None:
        meta = message.get("meta")
        assert meta is not None
        total_pages = meta["page"]["totalPages"]
        current_page = meta["page"]["number"]
        self.ratings_ready.emit(message)
        if current_page < total_pages:
            self.get_history_page(current_page + 1)

    def get_history_page(self, page: int) -> None:
        self.query.update({
            "page[size]": 10000,
            "page[number]": page,
            "page[totals]": "",
        })
        self.get_by_query(self.query, self.handle_page, self.on_error)

    def on_error(self, reply: QNetworkReply) -> None:
        self.api_error.emit(reply.errorString())


class LeagueSeasonScoreApiConnector(DataApiAccessor):
    score_ready = pyqtSignal(LeagueSeasonScore)
    scores_ready = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__("/data/leagueSeasonScore")
        self.include = (
            "leagueSeasonDivisionSubdivision",
            "leagueSeasonDivisionSubdivision.leagueSeasonDivision",
            "leagueSeason",
            "leagueSeason.leaderboard",
        )

    def filters(self, player_id: str) -> tuple[str, str, str]:
        utc_str = QDateTime.currentDateTime().toUTC().toString(Qt.DateFormat.ISODate)
        return (
            f"loginId=={player_id!r}",
            f"leagueSeason.startDate=le={utc_str}",
            f"leagueSeason.endDate=ge={utc_str}",
        )

    def prepare_data(self,  message: dict) -> dict[str, list[LeagueSeasonScore]]:
        return {"values": [LeagueSeasonScore(**entry) for entry in message["data"]]}

    def handle_score(self, message: dict) -> None:
        if message["data"]:
            self.score_ready.emit(LeagueSeasonScore(**message["data"][0]))

    def get_player_score_in_leaderboard(self, player_id: str, leaderboard: str) -> None:
        filters = (
            *self.filters(player_id),
            f"leagueSeason.leaderboard.technicalName=={leaderboard!r}",
        )
        query_params = {"include": ",".join(self.include), "filter": ";".join(filters)}
        self.get_by_query(query_params, self.handle_score)

    def handle_season_scores(self, message: PreParsedApiResponse) -> None:
        scores = message["data"]
        assert isinstance(scores, list)
        if scores:
            self.scores_ready.emit([LeagueSeasonScore(**score_data) for score_data in scores])

    def get_player_scores(self, player_id: str) -> None:
        query_params = {
            "include": ",".join(self.include),
            "filter": ";".join(self.filters(player_id)),
        }
        self.get_by_query(cast(QueryOptions, query_params), self.handle_season_scores)


class PlayerEventApiAccessor(DataApiAccessor):
    events_ready = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__("/data/playerEvent")

    def get_player_events(self, player_id: str) -> None:
        query = {
            "include": "event",
            "filter": f"player.id=={player_id}",
        }
        self.get_by_query(query, self.handle_player_events)

    def handle_player_events(self, message: dict) -> None:
        self.events_ready.emit([PlayerEvent(**entry) for entry in message["data"]])


class PlayerAchievementApiAccessor(DataApiAccessor):
    achievments_ready = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__("/data/playerAchievement")

    def get_achievements(self, player_id: str | int) -> None:
        query = {
            "include": "achievement",
            "filter": f"player.id=={player_id}",
            "sort": "achievement.order",
        }
        self.get_by_query(query, self.handle_achievements)

    def handle_achievements(self, message: dict) -> None:
        self.achievments_ready.emit(PlayerAchievement(**entry) for entry in message["data"])


class AchievementsApiAccessor(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__("/data/achievement")

    def prepare_data(self, message: dict) -> dict[str, Iterator[Achievement]]:
        return {"values": (Achievement(**entry) for entry in message["data"])}
