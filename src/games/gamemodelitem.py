from __future__ import annotations

from collections.abc import Callable

from src.client.user import User
from src.client.user import UserRelations
from src.downloadManager import DownloadRequest
from src.downloadManager import MapSmallPreviewDownloader
from src.fa import maps
from src.model.game import Game
from src.qt.models.qtlistmodel import QtListModelItem
from src.util import pretty_decoded_basename


class GameModelItem(QtListModelItem):
    """
    UI representation of a running game. Tracks and signals changes that game
    display widgets would like to know about.
    """
    def __init__(
            self,
            game: Game,
            relations: UserRelations,
            me: User,
            preview_dler: MapSmallPreviewDownloader,
    ) -> None:
        super().__init__()

        self.game = game
        self.game.updated.connect(self._game_updated)
        self.user_relations = relations
        self.user_relations.trackers.players.updated.connect(self._host_relation_changed)
        self._me = me
        self._me.clan_changed.connect(self._host_relation_changed)
        self._preview_dler = preview_dler
        self._preview_dl_request = DownloadRequest()
        self._preview_dl_request.done.connect(self._at_preview_downloaded)

    @classmethod
    def builder(
            cls,
            relations: UserRelations,
            me: User,
            preview_dler: MapSmallPreviewDownloader,
    ) -> Callable[[Game], GameModelItem]:
        def build(game: Game) -> GameModelItem:
            return cls(game, relations, me, preview_dler)
        return build

    def _game_updated(self):
        self.updated.emit(self)
        self._download_preview_if_needed()

    def _host_relation_changed(self):
        # This should never happen bar server screwups.
        if self.game.host_player is None:
            return
        self.updated.emit(self)

    def _download_preview_if_needed(self):
        if self.game.mapname is None:
            return
        name = self.game.mapname.lower()
        if self.game.password_protected or maps.preview(name) is not None:
            return
        self._preview_dler.download_preview(name, self._preview_dl_request)

    def _at_preview_downloaded(self, preview_file: str) -> None:
        if pretty_decoded_basename(preview_file) == self.game.mapname:
            self.updated.emit(self)

    def tooltip(self) -> None:
        # TODO: implement this and remove tricks with GameTooltipFilter
        ...
