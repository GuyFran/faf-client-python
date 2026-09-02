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
                     {"type":"source_offline"}                   (PC not logged into FAF yet)
                     {"type":"snapshot_begin","epoch":N}
                     <game_info line> ...            (current open lobbies)
                     {"type":"snapshot_end","epoch":N}
                     <game_info line> ...            (live add/update/close, streamed)

Source-ready contract: the phone shows CONNECTED only while the desktop actually holds a live
FAF lobby link (has sent an authoritative game_info batch). Before the PC logs in, and after it
disconnects, the phone stays WAITING with an empty map — never a misleading empty "connected".

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
MAX_CLIENTS = 4          # paired phones
MAX_PENDING = 8          # sockets awaiting auth
MAX_HELLO_BYTES = 4096   # a hello is tiny; anything larger is junk/abuse


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
        self.enabled = (
            Settings.get("companion/enabled", False, type=bool)
            or os.environ.get("FAF_COMPANION_ENABLED", "").lower() in ("1", "true", "yes")
        )
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
        self._source_ready = False        # desktop currently holds a live FAF lobby link?

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if not self.enabled:
            logger.info(
                "Companion relay disabled — set companion/enabled=true (or env "
                "FAF_COMPANION_ENABLED=1) and restart. See COMPANION.md.",
            )
            return
        if self._server is not None:
            return
        self._server = QWebSocketServer(
            "FAF Companion", QWebSocketServer.SslMode.NonSecureMode, self,
        )
        # Resolve the LAN address ONCE and use it consistently for bind/log/pairing —
        # re-evaluating it can record a different IP than the one actually bound.
        ip = _local_ip()
        # Fail closed: bind to the LAN interface only; do NOT fall back to all interfaces.
        if not self._server.listen(QHostAddress(ip), self.port):
            logger.error("Companion relay failed to bind %s:%s; disabled", ip, self.port)
            _noexcept(self._server.close)
            self._server = None
            return
        if ip == "127.0.0.1":
            logger.warning(
                "Companion relay bound to 127.0.0.1 (no LAN address yet?) — the phone will "
                "NOT be able to reach it. Restart the client once the network is up.",
            )
        # Cap Qt's own pre-allocation boundaries, not just our application-level lists.
        _noexcept(self._server.setMaxPendingConnections, MAX_PENDING)
        self._server.newConnection.connect(self._safe(self._on_new_connection))
        bound = self._server.serverAddress().toString()
        self._write_pairing_file(bound)
        logger.info(
            "Companion relay (trusted-LAN) listening on %s:%s — pairing info written to %s",
            bound, self.port, self._pairing_path(),
        )
        # Explicitly stop on application teardown (frees the port, closes phone sockets).
        try:
            from PyQt6.QtCore import QCoreApplication
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._safe(self.stop))
        except Exception:
            pass

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

    def _write_pairing_file(self, bound_ip: str) -> None:
        # Keep the token out of the rolling app log; write it to a file the user opens.
        path = self._pairing_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    "FAF Mobile companion pairing\n"
                    f"IP:    {bound_ip}\n"
                    f"PORT:  {self.port}\n"
                    f"TOKEN: {self.token}\n",
                )
            _noexcept(os.chmod, path, 0o600)  # owner-only where the OS honours it
        except Exception:
            pass

    def regenerate_token(self) -> str:
        """Mint a new pairing token, persist it, rewrite the pairing file, and drop every
        currently-paired phone (their old pairing must die). For the future settings UI."""
        self.token = secrets.token_hex(16)
        Settings.set("companion/token", self.token)
        if self._server is not None:
            self._write_pairing_file(self._server.serverAddress().toString())
        for sock in list(self._clients):
            _noexcept(sock.close)
            self._drop(sock)
        return self.token

    # -- source (FAF) lifecycle -------------------------------------------
    def on_source_offline(self) -> None:
        """Desktop lost its FAF lobby link — clear state and tell phones to go back to WAITING."""
        if not self.enabled or self._server is None:
            return
        try:
            self._source_ready = False
            self._games.clear()
            self._broadcast_control({"type": "source_offline"})
        except Exception:
            self._disable("on_source_offline error")

    # -- ingest from the FAF connection -----------------------------------
    def on_server_line(self, line: str) -> None:
        """Called for every raw lobby line the client receives. An unparseable line is skipped
        (never disables the relay); a genuine internal error self-disables. Either way this never
        raises, so the real client's dispatch is untouched."""
        if not self.enabled or self._server is None:
            return
        import json
        try:
            action = json.loads(line)
        except Exception:
            return  # not our concern / malformed — skip without disabling
        try:
            if str(action.get("command", "")).lower() not in FORWARDED_COMMANDS:
                return
            is_batch = isinstance(action.get("games"), list)
            # Readiness comes ONLY from an authoritative full batch. Incremental updates that
            # arrive before the first batch have no baseline to apply to — ignore them, and never
            # let one flip us to "ready".
            if not is_batch and not self._source_ready:
                return
            self._record_game_info(action, json)
            if is_batch:
                self._source_ready = True
                # Full batch = desktop (re)synced with FAF. Resync every phone, moving any
                # WAITING phone to CONNECTED.
                self._broadcast_snapshot_all()
            else:
                self._broadcast(line if line.endswith("\n") else line + "\n")
        except Exception:
            self._disable("on_server_line error")

    def _record_game_info(self, action: dict, json) -> bool:
        games = action.get("games")
        if isinstance(games, list):
            self._games.clear()
            for g in games:
                self._store_game(g, json)
            return True
        self._store_game(action, json)
        return False

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
        if sock is None:
            return
        if len(self._pending) >= MAX_PENDING or len(self._clients) >= MAX_CLIENTS:
            _noexcept(sock.close)
            return
        # Bound the incoming message size at the Qt allocation boundary too (a phone only ever
        # sends a tiny hello).
        _noexcept(sock.setMaxAllowedIncomingMessageSize, MAX_HELLO_BYTES)
        self._pending.append(sock)
        sock.textMessageReceived.connect(self._safe(lambda msg, s=sock: self._on_client_message(s, msg)))
        sock.disconnected.connect(self._safe(lambda s=sock: self._drop(s)))
        QTimer.singleShot(AUTH_TIMEOUT_MS, self._safe(lambda s=sock: self._auth_timeout(s)))

    def _auth_timeout(self, sock) -> None:
        if sock in self._pending:
            _noexcept(sock.close)
            self._drop(sock)

    def _on_client_message(self, sock, msg: str) -> None:
        # Only unauthenticated sockets may send hello; ignore anything from paired sockets
        # (prevents a paired phone from forcing unbounded snapshot replays).
        if sock not in self._pending:
            return
        if len(msg) > MAX_HELLO_BYTES:
            _noexcept(sock.close)
            self._drop(sock)
            return
        import json
        for line in msg.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            # Untrusted pre-auth input must NEVER reach the internal-fault kill switch:
            # valid-JSON-non-object (e.g. `5`, `[1]`) is just a bad hello, not a relay error.
            if not isinstance(data, dict):
                continue
            if data.get("type") == "hello":
                token = str(data.get("token", ""))
                # Compare as bytes: compare_digest raises TypeError on non-ASCII str input,
                # which a hostile/buggy peer could otherwise use to trip _disable via _safe.
                ok = secrets.compare_digest(
                    token.encode("utf-8", "replace"),
                    self.token.encode("utf-8"),
                )
                if ok:
                    self._authenticate(sock)
                else:
                    logger.warning("Companion: bad pairing token — closing")
                    _noexcept(sock.close)
                    self._drop(sock)
                return  # one hello per pending socket

    def _authenticate(self, sock) -> None:
        # Enforce the phone cap at auth time too — MAX_PENDING sockets could all present the
        # valid token, which must not grow _clients past MAX_CLIENTS.
        if len(self._clients) >= MAX_CLIENTS:
            _noexcept(sock.close)
            self._drop(sock)
            return
        if sock in self._pending:
            self._pending.remove(sock)
        if sock not in self._clients:
            self._clients.append(sock)
        logger.info("Companion: phone paired (%d connected)", len(self._clients))
        import json
        self._send(sock, json.dumps({"type": "hello_ok"}))
        if self._source_ready:
            self._send_snapshot(sock)
        else:
            self._send(sock, json.dumps({"type": "source_offline"}))

    def _send_snapshot(self, sock) -> None:
        import json
        self._epoch += 1
        self._send(sock, json.dumps({"type": "snapshot_begin", "epoch": self._epoch}))
        for line in self._games.values():
            self._send(sock, line)
        self._send(sock, json.dumps({"type": "snapshot_end", "epoch": self._epoch}))

    def _broadcast_snapshot_all(self) -> None:
        for sock in list(self._clients):
            try:
                self._send_snapshot(sock)
            except Exception:
                self._drop(sock)

    def _broadcast_control(self, obj) -> None:
        import json
        self._broadcast(json.dumps(obj) + "\n")

    def _send(self, sock, line: str) -> None:
        sock.sendTextMessage(line if line.endswith("\n") else line + "\n")

    def _broadcast(self, line: str) -> None:
        for sock in list(self._clients):
            try:
                sock.sendTextMessage(line)
            except Exception:
                self._drop(sock)

    def _drop(self, sock) -> None:
        # Tear the connection down, not just forget it — a socket dropped after a send failure
        # must actually close so the phone's reconnect logic kicks in (closing an already
        # closed socket is a no-op).
        _noexcept(sock.close)
        _noexcept(sock.deleteLater)
        if sock in self._clients:
            self._clients.remove(sock)
        if sock in self._pending:
            self._pending.remove(sock)
