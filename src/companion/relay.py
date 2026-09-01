"""
Companion relay for the FAF Mobile companion app.

Runs a small LAN WebSocket server inside the desktop client and mirrors the open-lobby
messages the client already receives (game_info) to paired phones on the same network. The
phone is a read-only viewer — it never authenticates to FAF and never touches the anti-smurf
UID; the desktop client remains the only authenticated party.

Security tier: **trusted-LAN, experimental.** The 128-bit pairing token travels over cleartext
ws://, so this protects against casual access, NOT against a malicious device on the same Wi-Fi
that can sniff/alter LAN traffic. Off unless enabled in Settings. Pinned wss:// is the planned
gate before the app is shared beyond the user's own devices.

Protocol (one JSON object per WebSocket text message, each also newline-terminated):
    phone -> relay : {"type":"hello","token":"<pairing token>"}
    relay -> phone : {"type":"hello_ok"}                         (auth accepted)
                     {"type":"snapshot_begin","epoch":N}
                     <game_info line> ...            (current open lobbies)
                     {"type":"snapshot_end","epoch":N}
                     <game_info line> ...            (live add/update/close, streamed)
On the desktop losing its FAF lobby link the relay publishes an empty authoritative snapshot so
the phone doesn't show stale lobbies during an outage.

Isolation contract: NOTHING here may disturb the real client. The import is guarded at the call
site, construction/start/callbacks are wrapped, and cleanup never throws.
"""
import logging
import os
import secrets
import socket

from PyQt6.QtCore import QObject
from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QHostAddress
from PyQt6.QtWebSockets import QWebSocketServer

from src.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_PORT = 6900
FORWARDED_COMMANDS = {"game_info"}  # open lobbies + their players (teams). Nothing else leaves the PC.
AUTH_TIMEOUT_MS = 10_000


def _local_ip() -> str:
    """Best-effort LAN IP of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # no packets sent; just picks the outbound iface
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


def _noexcept(fn, *args) -> None:
    try:
        fn(*args)
    except Exception:
        pass


class CompanionRelay(QObject):
    @staticmethod
    def create_safe(parent: QObject | None = None) -> "CompanionRelay | None":
        """Construct + start the relay, swallowing every failure. A broken relay must never
        stop the real FAF client from starting."""
        try:
            relay = CompanionRelay(parent)
            relay.start()
            return relay
        except Exception:
            logger.exception("Companion relay failed to initialise; disabled")
            return None

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.enabled = Settings.get("companion/enabled", False, type=bool)
        self.port = Settings.get("companion/port", DEFAULT_PORT, type=int)
        self.token = Settings.get("companion/token", "", type=str)
        if not self.token or len(self.token) < 32:
            self.token = secrets.token_hex(16)  # 128-bit
            Settings.set("companion/token", self.token)

        self._server: QWebSocketServer | None = None
        self._clients: list = []          # authenticated phone sockets
        self._pending: list = []          # connected, not yet authenticated
        self._games: dict[int, str] = {}  # uid -> latest game_info line (snapshot)
        self._epoch = 0

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if not self.enabled or self._server is not None:
            return
        self._server = QWebSocketServer(
            "FAF Companion", QWebSocketServer.SslMode.NonSecureMode, self,
        )
        # Bind to the LAN interface only, not every interface.
        bind = QHostAddress(_local_ip())
        if not self._server.listen(bind, self.port):
            # Fall back to Any if the specific bind fails (e.g. IP changed mid-session).
            if not self._server.listen(QHostAddress.SpecialAddress.Any, self.port):
                logger.error("Companion relay failed to listen on port %s", self.port)
                self._server = None
                return
        self._server.newConnection.connect(self._safe(self._on_new_connection))
        self._write_pairing_file()
        logger.info(
            "Companion relay (trusted-LAN) listening on %s:%s — pairing info written to %s",
            _local_ip(), self.port, self._pairing_path(),
        )

    def stop(self) -> None:
        for c in list(self._clients) + list(self._pending):
            _noexcept(c.close)
        self._clients.clear()
        self._pending.clear()
        if self._server is not None:
            _noexcept(self._server.close)
            self._server = None

    def _disable(self, why: str) -> None:
        try:
            logger.exception("Companion relay disabled: %s", why)
        except Exception:
            pass
        _noexcept(self.stop)   # cleanup must never throw
        self.enabled = False

    def _safe(self, fn):
        """Wrap a Qt callback so a relay error can never escape into the client."""
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                self._disable("callback error")
        return wrapper

    # -- pairing surface ---------------------------------------------------
    def _pairing_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), "faf_companion_pairing.txt")

    def _write_pairing_file(self) -> None:
        # Keep the token out of the rolling app log; write it to a file the user opens.
        try:
            with open(self._pairing_path(), "w", encoding="utf-8") as f:
                f.write(
                    "FAF Mobile companion pairing\n"
                    f"IP:    {_local_ip()}\n"
                    f"PORT:  {self.port}\n"
                    f"TOKEN: {self.token}\n",
                )
        except Exception:
            pass

    # -- source (FAF) lifecycle -------------------------------------------
    def on_source_offline(self) -> None:
        """Desktop lost its FAF lobby link — publish an empty authoritative snapshot so the
        phone stops showing stale lobbies."""
        if not self.enabled or self._server is None:
            return
        try:
            self._games.clear()
            for sock in list(self._clients):
                self._send_snapshot(sock)
        except Exception:
            self._disable("on_source_offline error")

    # -- ingest from the FAF connection -----------------------------------
    def on_server_line(self, line: str) -> None:
        """Called for every raw lobby line the client receives. Fully guarded: on any error the
        relay disables itself and returns normally so the real client is untouched."""
        if not self.enabled or self._server is None:
            return
        try:
            import json
            action = json.loads(line)
            if str(action.get("command", "")).lower() not in FORWARDED_COMMANDS:
                return
            self._record_game_info(action)
            self._broadcast(line if line.endswith("\n") else line + "\n")
        except Exception:
            self._disable("on_server_line error")

    def _record_game_info(self, action: dict) -> None:
        import json
        games = action.get("games")
        if isinstance(games, list):
            # An initial/full batch is authoritative — replace the snapshot wholesale.
            self._games.clear()
            for g in games:
                self._store_game(g, json)
        else:
            self._store_game(action, json)

    def _store_game(self, g: dict, json) -> None:
        uid = g.get("uid")
        if uid is None:
            return
        if str(g.get("state", "")).lower() == "closed":
            self._games.pop(uid, None)
        else:
            entry = dict(g)
            entry["command"] = "game_info"
            self._games[uid] = json.dumps(entry)

    # -- websocket server plumbing ----------------------------------------
    def _on_new_connection(self) -> None:
        sock = self._server.nextPendingConnection()
        self._pending.append(sock)
        sock.textMessageReceived.connect(self._safe(lambda msg, s=sock: self._on_client_message(s, msg)))
        sock.disconnected.connect(self._safe(lambda s=sock: self._drop(s)))
        # Drop sockets that never authenticate.
        QTimer.singleShot(AUTH_TIMEOUT_MS, self._safe(lambda s=sock: self._auth_timeout(s)))

    def _auth_timeout(self, sock) -> None:
        if sock in self._pending:
            _noexcept(sock.close)
            self._drop(sock)

    def _on_client_message(self, sock, msg: str) -> None:
        import json
        for line in msg.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if data.get("type") == "hello":
                token = str(data.get("token", ""))
                if secrets.compare_digest(token, self.token):
                    self._authenticate(sock)
                else:
                    logger.warning("Companion: bad pairing token — closing")
                    _noexcept(sock.close)
                    self._drop(sock)

    def _authenticate(self, sock) -> None:
        if sock in self._pending:
            self._pending.remove(sock)
        if sock not in self._clients:
            self._clients.append(sock)
        logger.info("Companion: phone paired (%d connected)", len(self._clients))
        import json
        self._send(sock, json.dumps({"type": "hello_ok"}))
        self._send_snapshot(sock)

    def _send_snapshot(self, sock) -> None:
        import json
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
        if sock in self._pending:
            self._pending.remove(sock)
