from logging import Logger
from typing import ClassVar

from PyQt6.QtCore import pyqtSignal

from src.decorators import with_logger
from src.model.game import Game
from src.model.game import GameState
from src.model.modelitemset import ModelItemSet
from src.model.player import Player
from src.model.playerset import Playerset
from src.model.transaction import ModelTransaction
from src.model.transaction import transactional


@with_logger
class Gameset(ModelItemSet[int, Game]):
    """
    Keeps track of currently active games. Removes games that closed. Reports
    creation and state change of games. Gives access to active games.

    Note that it doesn't remember which games ended - the server may choose to
    send a game state for a uid, send a state that closes it, then send a state
    with the same uid again, and it will be reported as a new game.
    """
    _logger: ClassVar[Logger]

    newLobby = pyqtSignal(object)
    newLiveGame = pyqtSignal(object)
    newClosedGame = pyqtSignal(object)
    newLiveReplay = pyqtSignal(object)

    def __init__(self, playerset: Playerset) -> None:
        super().__init__()
        self._playerset = playerset

    @transactional
    def set_item(
        self,
        key: int,
        value: Game,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if value.closed():
            raise ValueError
        super().set_item(key, value)
        value.before_updated.connect(self._at_game_update)
        value.before_replay_available.connect(self._at_live_replay)
        self._at_game_update(value, None, _transaction)
        self._logger.log(5, "Added game, uid %d", value.id_key)
        self.emit_added(value, _transaction)

    @transactional
    def del_item(self, key: int, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        g = super().del_item(key, _transaction=_transaction)
        if g is None:
            return

        g.before_updated.disconnect(self._at_game_update)
        g.before_replay_available.disconnect(self._at_live_replay)
        self._logger.log(5, "Removed game, uid %d", g.id_key)
        self.emit_removed(g, _transaction)

    @transactional
    def clear(self, *, _transaction: ModelTransaction = ModelTransaction()) -> None:
        # Abort_game removes g from dict, so 'for g in values()' complains
        for g in list(self._items.values()):
            g.abort_game(_transaction=_transaction)

    def _at_game_update(
        self,
        new: Game,
        old: Game | None,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if new.closed():
            self.del_item(new.id_key, _transaction=_transaction)
        if old is None or new.state != old.state:
            self._new_state(new, _transaction)

    def _new_state(self, g: Game, _transaction: ModelTransaction = ModelTransaction()) -> None:
        self._logger.log(5, "New game state %s, uid %d", g.state, g.id_key)
        if g.state == GameState.OPEN:
            _transaction.emit(self.newLobby, g)
        elif g.state == GameState.PLAYING:
            _transaction.emit(self.newLiveGame, g)
        elif g.state == GameState.CLOSED:
            _transaction.emit(self.newClosedGame, g)

    def _at_live_replay(
        self,
        game: Game,
        *,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        _transaction.emit(self.newLiveReplay, game)


class PlayerGameIndex:
    # Helper class that keeps track of player / game relationship and helps
    # assign games to players that reconnected.
    def __init__(self, gameset: Gameset, playerset: Playerset) -> None:
        self._playerset = playerset
        self._gameset = gameset
        self._playerset.before_added.connect(self._on_player_added)
        self._playerset.before_removed.connect(self._on_player_removed)
        self._gameset.before_added.connect(self._on_game_added)
        self._gameset.before_removed.connect(self._on_game_removed)

        self._idx: dict[str, Game] = {}

    def player_game(self, pname: str) -> Game | None:
        return self._idx.get(pname)

    def _on_game_added(
        self,
        game: Game,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        game.before_updated.connect(self._at_game_update)
        for p in game.players:
            self._set_relation(p, game, _transaction)

    def _on_game_removed(
        self,
        game: Game,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        game.before_updated.disconnect(self._at_game_update)
        for p in game.players:
            self._remove_relation(p, game, _transaction)

    def _at_game_update(
        self,
        new: Game,
        old: Game,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        news: set[str] = set() if new.closed() else set(new.players)
        olds: set[str] = set() if old.closed() else set(old.players)
        removed = olds - news
        added = news - olds
        for p in removed:
            self._remove_relation(p, new, _transaction)
        for p in added:
            self._set_relation(p, new, _transaction)

    def _remove_relation(
        self,
        pname: str,
        game: Game,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        if pname not in self._idx:
            return
        if self.player_game(pname) != game:
            return

        player = self._playerset.get_by_name(pname)
        del self._idx[pname]

        if player is not None:
            player.set_currentGame(None, _transaction=_transaction)
            game.ingame_player_removed(player, _transaction=_transaction)

    def _set_relation(
        self,
        pname: str,
        game: Game,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        oldgame = self.player_game(pname)
        if not self._player_did_change_game(game, oldgame):
            return

        player = self._playerset.get_by_name(pname)
        self._idx[pname] = game

        if player is not None:
            player.set_currentGame(game, _transaction=_transaction)
            if oldgame is not None:
                oldgame.ingame_player_removed(player, _transaction=_transaction)
            game.ingame_player_added(player, _transaction=_transaction)

    def _player_did_change_game(self, new: Game | None, old: Game | None) -> bool:
        # Removing or setting new game should always happen
        if new is None or old is None:
            return True

        if new.id_key == old.id_key:
            return False

        # Games should be not closed now
        # Lobbies always take precedence - if there are 2 at once, tough luck
        if new.state == GameState.OPEN:
            return True
        if old.state == GameState.OPEN:
            return False

        # Both games have started, pick later one
        if new.launched_at is None:
            return False
        if old.launched_at is None:
            return True
        return new.launched_at > old.launched_at

    def _on_player_added(
        self,
        player: Player,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        pgame = self.player_game(player.login)
        if pgame is not None:
            player.set_currentGame(pgame, _transaction=_transaction)
            pgame.ingame_player_added(player, _transaction=_transaction)

    def _on_player_removed(
        self,
        player: Player,
        _transaction: ModelTransaction = ModelTransaction(),
    ) -> None:
        pgame = self.player_game(player.login)
        if pgame is not None:
            pgame.ingame_player_removed(player, _transaction=_transaction)
