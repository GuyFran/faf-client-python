import html
import string
import time
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QWidget

from src.decorators import with_logger
from src.model.modelitem import ModelItem
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional
from src.protocol.lobbyprotocol import ServerMessage
from src.util.gameurl import GameUrl
from src.util.gameurl import GameUrlType

if TYPE_CHECKING:
    from src.model.player import Player
    from src.model.playerset import Playerset


class GameState(Enum):
    OPEN = "open"
    PLAYING = "playing"
    CLOSED = "closed"


# This enum has a counterpart on the server
class GameVisibility(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"


class GameType(Enum):
    COOP = "coop"
    CUSTOM = "custom"
    MATCHMAKER = "matchmaker"


@with_logger
class Game(ModelItem):
    """
    Represents a game happening on the server. Updates for the game state are
    sent from the server, identified by game uid. Updates are propagated with
    signals.

    The game with a given uid starts when we receive the first game message and
    ends with some update, or is ended manually. Once the game ends, it
    shouldn't be updated or ended again. Update and game end are propagated
    with signals.
    """
    before_replay_available = pyqtSignal(object, object)
    liveReplayAvailable = pyqtSignal(object)

    ingamePlayerAdded = pyqtSignal(object, object)
    ingamePlayerRemoved = pyqtSignal(object, object)

    OBSERVER_TEAMS = ['-1', 'null']
    LIVE_REPLAY_DELAY_SECS = 60 * 5

    def __init__(
        self,
        playerset: Playerset,
        uid: int,
        state: GameState,
        launched_at: float | None,
        num_players: int,
        max_players: int,
        title: str,
        host: str,
        mapname: str,
        map_file_path: str,
        teams: dict[str, list[str]],
        featured_mod: str,
        sim_mods: dict[str, str],
        password_protected: bool,
        visibility: GameVisibility,
        game_type: str,
        hosted_at: str | None,
        enforce_rating_range: bool,
        rating_min: float | None,
        rating_max: float | None,
        **kwargs: Any,
    ):

        super().__init__()

        self._playerset = playerset

        self.uid = uid
        self.state = state
        self.launched_at = launched_at
        self.num_players = num_players
        self.max_players = max_players
        self.title = title
        self.host = host
        self.mapname = mapname
        self.map_file_path = map_file_path
        self.teams = teams
        self.featured_mod = featured_mod
        self.sim_mods = sim_mods
        self.password_protected = password_protected
        self.visibility = visibility
        self.game_type = GameType(game_type)
        self.hosted_at = hosted_at
        self.enforce_rating_range = enforce_rating_range
        self.rating_min = rating_min
        self.rating_max = rating_max
        self._data_fields.extend((
            "state",
            "launched_at",
            "num_players",
            "max_players",
            "title",
            "host",
            "mapname",
            "map_file_path",
            "teams",
            "featured_mod",
            "sim_mods",
            "password_protected",
            "visibility",
            "game_type",
            "hosted_at",
            "enforce_rating_range",
            "rating_min",
            "rating_max",
        ))
        self._aborted = False

        self._live_replay_timer = QTimer()
        self._live_replay_timer.setSingleShot(True)
        self._live_replay_timer.setInterval(self.LIVE_REPLAY_DELAY_SECS * 1000)
        self._live_replay_timer.timeout.connect(self._emit_live_replay)
        self.has_live_replay = False
        self._check_live_replay_timer()

    @property
    def id_key(self) -> int:
        return self.uid

    def copy(self) -> Self:
        old = self.__class__(self._playerset, self.uid, **self.field_dict)
        old._aborted = self._aborted
        old.has_live_replay = self.has_live_replay
        return old

    @transactional
    def update(self, *, _transaction: ModelTransaction = ModelTransaction(), **kwargs: Any) -> None:
        if self._aborted:
            return
        old = self.copy()
        super().update(**kwargs)
        self._check_live_replay_timer()
        self.emit_update(old, _transaction=_transaction)

    def _check_live_replay_timer(self) -> None:
        if (
            self.state != GameState.PLAYING
            or self._live_replay_timer.isActive()
            or self.launched_at is None
        ):
            return

        if self.has_live_replay:
            return

        time_elapsed = round(time.time() - self.launched_at, 0)
        time_to_replay = max(self.LIVE_REPLAY_DELAY_SECS - time_elapsed, 0)
        self._live_replay_timer.start(int(time_to_replay * 1000))

    @transactional
    def _emit_live_replay(self, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        if self.state != GameState.PLAYING:
            return
        self.has_live_replay = True
        _transaction.emit(self.liveReplayAvailable, self)
        self.before_replay_available.emit(self, _transaction)

    def closed(self) -> bool:
        return self.state == GameState.CLOSED or self._aborted

    # Used when the server confuses us whether the game is valid anymore.
    @transactional
    def abort_game(self, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        if self.closed():
            return

        old = self.copy()
        self.state = GameState.CLOSED
        self._aborted = True
        self.emit_update(old, _transaction=_transaction)

    def to_dict(self) -> dict[str, Any]:
        data = self.field_dict
        data["uid"] = self.uid
        data["state"] = data["state"].value
        data["visibility"] = data["visibility"].value
        data["game_type"] = data["game_type"].value
        data["command"] = "game_info"   # For compatibility
        return data

    def url(self, player_id: int) -> GameUrl | None:
        if self.state == GameState.CLOSED:
            return None
        if self.state == GameState.OPEN:
            gtype = GameUrlType.OPEN_GAME
        else:
            gtype = GameUrlType.LIVE_REPLAY

        return GameUrl(gtype, self.mapname, self.featured_mod, self.uid, player_id, self.sim_mods)

    # Utility functions start here.

    def is_connected(self, name: str) -> bool:
        return self.to_player(name) is not None

    def is_ingame(self, name: str) -> bool:
        return (
            not self.closed()
            and (player := self._playerset.get_by_name(name)) is not None
            and player.currentGame == self
        )

    def to_player(self, name: str) -> Player | None:
        return self._playerset.get_by_name(name)

    @property
    def players(self) -> list[str]:
        return [name for team in self.teams.values() for name in team]

    @property
    def observers(self) -> list[str]:
        return [
            name
            for tname, team in self.teams.items()
            if tname in self.OBSERVER_TEAMS
            for name in team
        ]

    @property
    def playing_teams(self) -> dict[str, list[str]]:
        return {
            n: t
            for n, t in self.teams.items()
            if n not in self.OBSERVER_TEAMS
        }

    @property
    def playing_players(self):
        return [name for team in self.playing_teams.values() for name in team]

    @property
    def host_player(self) -> Player | None:
        try:
            return self._playerset.get_by_name(self.host)
        except KeyError:
            return None

    @transactional
    def ingame_player_added(
        self,
        player: Player,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        _transaction.emit(self.ingamePlayerAdded, self, player)

    @transactional
    def ingame_player_removed(
        self,
        player: Player,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        _transaction.emit(self.ingamePlayerRemoved, self, player)

    @property
    def average_rating(self) -> float:
        players = [
            self.to_player(name)
            for team in self.playing_teams.values()
            for name in team
        ]
        online_players = [p for p in players if p is not None]
        if len(online_players) == 0:
            return 0
        return sum(p.global_estimate for p in online_players) / len(online_players)

    @property
    def mapdisplayname(self):
        if self.mapname in OFFICIAL_MAPS:
            return OFFICIAL_MAPS[self.mapname][0]

        # cut off ugly version numbers, replace "_" with space.
        pretty = self.mapname.rsplit(".v0", 1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)
        return pretty

    def warn_live_delay(self, parent: QWidget | None = None) -> None:
        assert self.launched_at is not None
        delta = time.gmtime(self.LIVE_REPLAY_DELAY_SECS - (time.time() - self.launched_at))
        wait_str = time.strftime('%M Min %S Sec', delta)
        QMessageBox.information(
            parent,
            "5 Minute Live Game Delay",
            (
                "It is too early to join the Game.\n"
                f"You have to wait {wait_str} to join."
            ),
        )


def message_to_game_args(m: ServerMessage) -> bool:
    if "command" in m:
        del m["command"]

    try:
        m['state'] = GameState(m['state'])
        m['visibility'] = GameVisibility(m['visibility'])
        m["game_type"] = GameType(m["game_type"])
        # Server sends HTML-escaped names, which is needlessly confusing
        m['title'] = html.unescape(m['title'])
    except (KeyError, ValueError):
        return False

    return True


OFFICIAL_MAPS = {  # official Forged Alliance Maps
    "scmp_001": ("Burial Mounds", "1024x1024", 8),
    "scmp_002": ("Concord Lake", "1024x1024", 8),
    "scmp_003": ("Drake's Ravine", "1024x1024", 4),
    "scmp_004": ("Emerald Crater", "1024x1024", 4),
    "scmp_005": ("Gentleman's Reef", "2048x2048", 7),
    "scmp_006": ("Ian's Cross", "1024x1024", 4),
    "scmp_007": ("Open Palms", "512x512", 6),
    "scmp_008": ("Seraphim Glaciers", "1024x1024", 8),
    "scmp_009": ("Seton's Clutch", "1024x1024", 8),
    "scmp_010": ("Sung Island", "1024x1024", 5),
    "scmp_011": ("The Great Void", "2048x2048", 8),
    "scmp_012": ("Theta Passage", "256x256", 2),
    "scmp_013": ("Winter Duel", "256x256", 2),
    "scmp_014": ("The Bermuda Locket", "1024x1024", 8),
    "scmp_015": ("Fields Of Isis", "512x512", 4),
    "scmp_016": ("Canis River", "256x256", 2),
    "scmp_017": ("Syrtis Major", "512x512", 4),
    "scmp_018": ("Sentry Point", "256x256", 3),
    "scmp_019": ("Finn's Revenge", "512x512", 2),
    "scmp_020": ("Roanoke Abyss", "1024x1024", 6),
    "scmp_021": ("Alpha 7 Quarantine", "2048x2048", 8),
    "scmp_022": ("Artic Refuge", "512x512", 4),
    "scmp_023": ("Varga Pass", "512x512", 2),
    "scmp_024": ("Crossfire Canal", "1024x1024", 6),
    "scmp_025": ("Saltrock Colony", "512x512", 6),
    "scmp_026": ("Vya-3 Protectorate", "512x512", 4),
    "scmp_027": ("The Scar", "1024x1024", 6),
    "scmp_028": ("Hanna oasis", "2048x2048", 8),
    "scmp_029": ("Betrayal Ocean", "4096x4096", 8),
    "scmp_030": ("Frostmill Ruins", "4096x4096", 8),
    "scmp_031": ("Four-Leaf Clover", "512x512", 4),
    "scmp_032": ("The Wilderness", "512x512", 4),
    "scmp_033": ("White Fire", "512x512", 6),
    "scmp_034": ("High Noon", "512x512", 4),
    "scmp_035": ("Paradise", "512x512", 4),
    "scmp_036": ("Blasted Rock", "256x256", 4),
    "scmp_037": ("Sludge", "256x256", 3),
    "scmp_038": ("Ambush Pass", "256x256", 4),
    "scmp_039": ("Four-Corners", "256x256", 4),
    "scmp_040": ("The Ditch", "1024x1024", 6),
    "x1mp_001": ("Crag Dunes", "256x256", 2),
    "x1mp_002": ("Williamson's Bridge", "256x256", 2),
    "x1mp_003": ("Snoey Triangle", "512x512", 3),
    "x1mp_004": ("Haven Reef", "512x512", 4),
    "x1mp_005": ("The Dark Heart", "512x512", 6),
    "x1mp_006": ("Daroza's Sanctuary", "512x512", 4),
    "x1mp_007": ("Strip Mine", "1024x1024", 4),
    "x1mp_008": ("Thawing Glacier", "1024x1024", 6),
    "x1mp_009": ("Liberiam Battles", "1024x1024", 8),
    "x1mp_010": ("Shards", "2048x2048", 8),
    "x1mp_011": ("Shuriken Island", "2048x2048", 8),
    "x1mp_012": ("Debris", "4096x4096", 8),
    "x1mp_014": ("Flooded Strip Mine", "1024x1024", 4),
    "x1mp_017": ("Eye Of The Storm", "512x512", 4),
}
