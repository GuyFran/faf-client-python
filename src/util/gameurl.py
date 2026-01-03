from collections.abc import Iterable
from enum import Enum
from typing import ClassVar
from typing import Self

from PyQt6.QtCore import QUrl
from PyQt6.QtCore import QUrlQuery


class GameUrlType(Enum):
    LIVE_REPLAY = "faflive"
    OPEN_GAME = "fafgame"


class GameUrl:
    PORT: ClassVar[int] = -1
    REPLAY_SUFFIX = ".SCFAreplay"

    def __init__(
        self,
        game_type: GameUrlType,
        map_: str,
        mod: str,
        uid: int,
        player: str | int,
        mods: Iterable[str] | None = None,
    ) -> None:
        self.game_type = game_type
        self.map = map_
        self.mod = mod
        self.mods = mods
        self.uid = uid
        self.player = player    # Can be both name and uid

    def to_url(self) -> QUrl:
        url = QUrl()
        url.setHost("127.0.0.1")
        url.setPort(self.PORT)
        url.setScheme(self.game_type.value)
        query = QUrlQuery()
        query.addQueryItem("map", self.map)
        query.addQueryItem("mod", self.mod)
        if self.mods:
            query.addQueryItem("mods", ";".join(self.mods))

        if self.game_type == GameUrlType.OPEN_GAME:
            url.setPath(f"/{self.player}")
            query.addQueryItem("uid", str(self.uid))
        else:
            url.setPath(
                f"/{self.uid}/{self.player}{self.REPLAY_SUFFIX}",
            )

        url.setQuery(query)
        return url

    @classmethod
    def from_url(cls, u: str | QUrl, /) -> Self:
        try:
            url = QUrl(u)
            query = QUrlQuery(url)
            map_ = cls._get_query_item(query, "map")
            mod = cls._get_query_item(query, "mod")
            game_type = GameUrlType(url.scheme())

            path = url.path().split("/")

            if game_type == GameUrlType.OPEN_GAME:
                uid = int(cls._get_query_item(query, "uid"))
                player = path[1]
            else:
                uid = int(path[1])
                player = path[2]
                if not player.endswith(cls.REPLAY_SUFFIX):
                    raise ValueError
                player = player[:-len(cls.REPLAY_SUFFIX)]

        except (ValueError, TypeError, IndexError):
            raise ValueError

        try:
            mods = cls._get_query_item(query, "mods")
        except ValueError:
            mods = None
        return cls(game_type, map_, mod, uid, player, mods)

    @classmethod
    def _get_query_item(cls, query: QUrlQuery, name: str) -> str:
        if not query.hasQueryItem(name):
            raise ValueError
        return query.queryItemValue(name)

    @classmethod
    def is_game_url(cls, u: str, /) -> bool:
        return QUrl(u).scheme() in [e.value for e in GameUrlType]
