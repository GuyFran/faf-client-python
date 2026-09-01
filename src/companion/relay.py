"""
Companion relay for the FAF Mobile companion app.

Runs a small LAN WebSocket server inside the desktop client and mirrors the open-lobby
messages the client already receives (game_info) to paired phones on the same network. The
phone is a read-only viewer — it never authenticates to FAF and never touches the anti-smurf
UID; the desktop client remains the only authenticated party.

Security tier: **trusted-LAN, experimental.** The pairing token travels over cleartext ws://,
so this protects against casual access, NOT against a malicious device on the same Wi-Fi that
can sniff/alter LAN traffic. Do not treat it as more than that. Off unless enabled in Settings.

Protocol (one JSON object per WebSocket text message, each also newline-terminated):
    phone -> relay : {"type":"hello","token":"<pairing token>"}
    relay -> phone : {"type":"snapshot_begin","epoch":N}
                     <game_info line> ...            (current open lobbies)
                     {"type":"snapshot_end","epoch":N}
                     <game_info line> ...            (live add/update/close, streamed)

The relay is fully isolated: any failure disables it and is never allowed to disturb the real
FAF client (see CompanionRelay.create_safe and on_server_line's guard).
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
FORWARDED_COMMANDS = {"game_info"}  # open lobbies + their players (teams). Nothing else leaves the PC.
MAX_BAD_TOKENS = 3


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
    @staticmethod
    def create_safe(parent: QObject | None = None) -> "CompanionRelay | None":
        """Construct + start the relay, swallowing every failure. A broken relay must never
        stop the real FAF client from starting."""
        try:
            relay = CompanionRelay(parent)
            relay.start()
            return relay
        except BaseException:
            logger.exception("Companion relay failed to initialise; disabled")
            return None

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.enabled = Settings.get("companion/enabled", False, type=bool)
        self.port = Settings.get("companion/port", DEFAULT_PORT, type=int)
        self.token = Settings.get("companion/token", "", type=str)
        if not self.token:
            self.token = secrets.token_hex(4)  # 8 hex chars, easy to type on a phone
            Settings.set("companion/token", self.token)

        self._server: QWebSocketServer | None = None
        self._clients: list = []          # authenticated phone sockets
        self._pending: dict = {}          # socket -> bad-token count
        self._games: dict[int, str] = {}  # uid -> latest game_info line (snapshot)
        self._epoch = 0

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
        self._server.newConnection.connect(self._safe(self._on_new_connection))
        logger.info(
            "Companion relay (trusted-LAN) listening on %s:%s | pair phone with "
            "IP=%s PORT=%s TOKEN=%s", _local_ip(), self.port, _local_ip(), self.port, self.token,
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

    def _disable(self, why: str) -> None:
        logger.exception("Companion relay disabled: %s", why)
        try:
            self.stop()
        finally:
            self.enabled = False

    def _safe(self, fn):
        """Wrap a Qt callback so a relay error can never escape into the client."""
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except BaseException:
                self._disable("callback error")
        return wrapper

    # -- ingest from the FAF connection -----------------------------------
    def on_server_line(self, line: str) -> None:
        """Called for every raw lobby line the client receives. Fully guarded: on any error the
        relay disables itself and returns normally so the real client is untouched."""
        if not self.enabled or self._server is None:
            return
        try:
            action = json.loads(line)
            if str(action.get("command", "")).lower() not in FORWARDED_COMMANDS:
                return
            self._record_game_info(action)
            self._broadcast(line if line.endswith("\n") else line + "\n")
        except BaseException:
            self._disable("on_server_line error")

    def _record_game_info(self, action: dict) -> None:
        games = action.get("games")
        if isinstance(games, list):
            # An initial/full batch is authoritative — replace the snapshot wholesale.
            self._games.clear()
            for g in games:
                self._store_game(g)
        else:
            self._store_game(action)

    def _store_game(self, g: dict) -> None:
        uid = g.get("uid")
        if uid is None:
            return
        if str(g.get("state", "")).lower() == "closed":
            self._games.pop(uid, None)
        else:
            # Each snapshot entry must be a self-contained game_info record for the phone.
            entry = dict(g)
            entry["command"] = "game_info"
            self._games[uid] = json.dumps(entry)

    # -- websocket server plumbing ----------------------------------------
    def _on_new_connection(self) -> None:
        sock = self._server.nextPendingConnection()
        self._pending[sock] = 0
        sock.textMessageReceived.connect(self._safe(lambda msg, s=sock: self._on_client_message(s, msg)))
        sock.disconnected.connect(self._safe(lambda s=sock: self._drop(s)))

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
                    self._pending[sock] = self._pending.get(sock, 0) + 1
                    logger.warning("Companion: bad pairing token")
                    if self._pending[sock] >= MAX_BAD_TOKENS:
                        sock.close()

    def _authenticate(self, sock) -> None:
        self._pending.pop(sock, None)
        if sock not in self._clients:
            self._clients.append(sock)
        logger.info("Companion: phone paired (%d connected)", len(self._clients))
        self._send_snapshot(sock)

    def _send_snapshot(self, sock) -> None:
        self._epoch += 1
        self._send(sock, json.dumps({"type": "snapshot_begin", "epoch": self._epoch}))
        for line in self._games.values():
            self._send(sock, line)
        self._send(sock, json.dumps({"type": "snapshot_end", "epoch": self._epoch}))

    def _send(self, sock, line: str) -> None:
        sock.sendTextMessage(line if line.endswith("\n") else line + "\n")

    def _broadcast(self, line: str) -> None:
        for sock in list(self._clients):
            try:
                sock.sendTextMessage(line)
            except Exception:
                self._drop(sock)

    def _drop(self, sock) -> None:
        if sock in self._clients:
            self._clients.remove(sock)
        self._pending.pop(sock, None)
