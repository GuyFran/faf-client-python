"""
Companion relay for the FAF Mobile companion app.

Runs a small LAN WebSocket server inside the desktop client and mirrors the lobby
messages the client already receives (game_info / player_info) to paired phones on the
same network. The phone is a read-only viewer — it never authenticates to FAF and never
touches the anti-smurf UID; the desktop client remains the only authenticated party.

Protocol (newline-delimited JSON, ws://<pc-ip>:<port>):
    phone -> relay : {"type":"hello","token":"<pairing token>"}
    relay -> phone : raw FAF lobby lines (game_info batches + updates, player_info)

On a new phone connection the relay replays the current game snapshot so the phone shows
open lobbies immediately instead of waiting for the next update.
"""
import json
import logging
import secrets
import socket

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QHostAddress
from PyQt6.QtWebSockets import QWebSocketServer

from src.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_PORT = 6900
# Lobby commands worth forwarding to the phone (keeps chat/private data off the wire).
FORWARDED_COMMANDS = {"game_info", "player_info"}


def _local_ip() -> str:
    """Best-effort LAN IP of this machine (for display only)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # no packets sent; just picks the outbound iface
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


class CompanionRelay(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.enabled = Settings.get("companion/enabled", True, type=bool)
        self.port = Settings.get("companion/port", DEFAULT_PORT, type=int)
        self.token = Settings.get("companion/token", "", type=str)
        if not self.token:
            self.token = secrets.token_hex(4)  # 8 hex chars, easy to type on a phone
            Settings.set("companion/token", self.token)

        self._server: QWebSocketServer | None = None
        self._clients: list = []          # authenticated phone sockets
        self._pending: list = []          # connected, not yet authenticated
        self._games: dict[int, str] = {}  # uid -> latest game_info line (snapshot)
        self._players_line: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if not self.enabled or self._server is not None:
            return
        self._server = QWebSocketServer(
            "FAF Companion", QWebSocketServer.SslMode.NonSecureMode, self,
        )
        if not self._server.listen(QHostAddress.SpecialAddress.Any, self.port):
            logger.error("Companion relay failed to listen on port %s", self.port)
            self._server = None
            return
        self._server.newConnection.connect(self._on_new_connection)
        logger.info(
            "Companion relay listening on %s:%s  |  pair the phone with  IP=%s  PORT=%s  TOKEN=%s",
            _local_ip(), self.port, _local_ip(), self.port, self.token,
        )

    def stop(self) -> None:
        for c in list(self._clients) + list(self._pending):
            try:
                c.close()
            except Exception:
                pass
        self._clients.clear()
        self._pending.clear()
        if self._server is not None:
            self._server.close()
            self._server = None

    # -- ingest from the FAF connection -----------------------------------
    def on_server_line(self, line: str) -> None:
        """Called for every raw lobby line the client receives."""
        if not self.enabled or self._server is None:
            return
        try:
            action = json.loads(line)
        except Exception:
            return
        command = str(action.get("command", "")).lower()
        if command not in FORWARDED_COMMANDS:
            return

        # Maintain a snapshot so newly-connected phones get current state.
        if command == "game_info":
            self._record_game_info(action, line)
        elif command == "player_info":
            self._players_line = line

        self._broadcast(line)

    def _record_game_info(self, action: dict, line: str) -> None:
        games = action.get("games")
        entries = games if isinstance(games, list) else [action]
        for g in entries:
            uid = g.get("uid")
            if uid is None:
                continue
            if str(g.get("state", "")).lower() == "closed":
                self._games.pop(uid, None)
            else:
                # store each game as its own one-line game_info for replay
                self._games[uid] = json.dumps(g)

    # -- websocket server plumbing ----------------------------------------
    def _on_new_connection(self) -> None:
        sock = self._server.nextPendingConnection()
        self._pending.append(sock)
        sock.textMessageReceived.connect(lambda msg, s=sock: self._on_client_message(s, msg))
        sock.disconnected.connect(lambda s=sock: self._drop(s))

    def _on_client_message(self, sock, msg: str) -> None:
        for line in msg.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if data.get("type") == "hello":
                if data.get("token") == self.token:
                    self._authenticate(sock)
                else:
                    logger.warning("Companion: rejected phone with bad token")
                    sock.close()

    def _authenticate(self, sock) -> None:
        if sock in self._pending:
            self._pending.remove(sock)
        self._clients.append(sock)
        logger.info("Companion: phone paired (%d connected)", len(self._clients))
        self._send_snapshot(sock)

    def _send_snapshot(self, sock) -> None:
        for line in self._games.values():
            sock.sendTextMessage(line)
        if self._players_line:
            sock.sendTextMessage(self._players_line)
        sock.sendTextMessage(json.dumps({"type": "snapshot_end"}))

    def _broadcast(self, line: str) -> None:
        for sock in list(self._clients):
            try:
                sock.sendTextMessage(line)
            except Exception:
                self._drop(sock)

    def _drop(self, sock) -> None:
        if sock in self._clients:
            self._clients.remove(sock)
        if sock in self._pending:
            self._pending.remove(sock)
