import logging
import sys
from queue import Queue
from threading import Thread
from typing import Any
from typing import ClassVar
from typing import cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtWidgets import QMessageBox

from src.api.ApiAccessors import UserApiAccessor
from src.config import Settings
from src.decorators import with_logger
from src.fa.replay import replay
from src.util.gameurl import GameUrl

if sys.platform == "win32":
    import win32file
    import win32pipe
    import win32security


@with_logger
class StreamWriter(QObject):
    _logger: ClassVar[logging.Logger]

    ready = pyqtSignal()
    not_ready = pyqtSignal()
    closed = pyqtSignal()

    _close = pyqtSignal()
    _abort = pyqtSignal()

    def __init__(self, gurl: GameUrl) -> None:
        super().__init__()
        self.game_url = gurl

        self.socket = QWebSocket()
        self.socket.binaryMessageReceived.connect(self.on_server_message)
        self.socket.connected.connect(self.on_socket_connected)
        self.socket.disconnected.connect(self.on_socket_disconnected)

        self.pipe_connected: int | None = None

        self.queue: Queue[bytes] = Queue()
        self._thread = Thread(target=self.stream, daemon=True)

        # we can't simply call methods from different threads
        # with Qt, but we are safe to connect signals
        self._abort.connect(self.abort)
        self._close.connect(self.close)

        self._ready = False
        self._finished = True

        # Game process doesn't want to end replay like it does with TCP socket
        # or regular .scfareplay file -- it just hangs
        #
        # Sending 2048+ bytes of invalid replay data deals with hanging, but
        # in-game replay still won't end "properly" -- the simulation will
        # just stop and spectator won't be able to click around -- only to exit
        #
        # Maybe there is a way to force a "proper" ending, but for now we'll
        # just prevent hanging
        self._terminator = b"\x00" * 2048

        self._close_intended = False

    def start(self) -> None:
        self._finished = False
        self._logger.debug("Starting named pipe thread...")
        self._thread.start()

    def stream(self) -> None:
        pipe = win32pipe.CreateNamedPipe(
            Settings.get("replay_stream/pipe_path", ""),
            win32pipe.PIPE_ACCESS_OUTBOUND,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, win32security.SECURITY_ATTRIBUTES(),
        )
        self.pipe_connected = cast(int, win32pipe.ConnectNamedPipe(pipe, None))

        if self.pipe_connected != 0:
            self._logger.warning(
                "Coul not connect named pipe. ConnectNamedPipe returned %s",
                self.pipe_connected,
            )
            win32file.CloseHandle(pipe)
            self._close.emit()
            return

        while True:
            data = self.queue.get()
            try:
                win32file.WriteFile(pipe, data)
                if data == self._terminator:
                    self._logger.debug("Ending live replay normaly...")
                    self._close.emit()
                    break
            except Exception as e:
                self._logger.debug("Ending live replay abrubtly: %s", e)
                self._abort.emit()
                break
            else:
                self.queue.task_done()
        win32file.CloseHandle(pipe)

    def connect_to_replay_server(self, url: QUrl) -> None:
        self.socket.open(url)

    def on_socket_connected(self) -> None:
        # instead of player login/id there can be anything -- this was used
        # in the past presumably to identify from who we want to receive replay data.
        # nowadays replay server merges data from all players, but the format remained
        # the same, because the game uses this format
        msg = f"G/{self.game_url.uid}/{self.game_url.player}.scfareplay\x00".encode()
        self.socket.sendBinaryMessage(msg)

    def on_socket_disconnected(self) -> None:
        self._logger.info("Replay server disconnected")
        if not self._finished:
            self.queue.put(self._terminator)
        elif (
            not self._close_intended
            and self.socket.error() == QAbstractSocket.SocketError.UnknownSocketError
        ):
            self.not_ready.emit()

    def on_server_message(self, message: QByteArray) -> None:
        self.queue.put(message.data())
        if not self._ready:
            self.ready.emit()
            self._ready = True

    def abort(self) -> None:
        self._close_intended = True
        self.socket.abort()
        self.shutdown()

    def close(self) -> None:
        self._close_intended = True
        self.socket.close()
        self.shutdown()

    def shutdown(self) -> None:
        self.queue.shutdown()
        self.pipe_connected = None

        self._finished = True

        self.closed.emit()
        self._logger.debug("Stream writer closed")


@with_logger
class LiveReplayStreamer(QObject):
    _logger: ClassVar[logging.Logger]

    def __init__(self) -> None:
        super().__init__()
        self.api = UserApiAccessor()

        self.game_url: GameUrl | None = None
        self.writer: StreamWriter | None = None

    def start_live_replay(self, gurl: GameUrl) -> None:
        # TODO: handle linux too
        if sys.platform == "win32" and Settings.get("game/pipe_live_replay", True, type=bool):
            self.game_url = gurl
            self.api.get("/replay/access", self.on_replay_access_url)
        else:
            replay(gurl)

    def on_replay_access_url(self, data: dict[str, Any]) -> None:
        if self.writer is not None:
            self._logger.warning("Another instance of StreamWriter is not finished yet.")
            QMessageBox.warning(None, "Live Replay", "Another live replay is already running.")
            return

        assert self.game_url is not None
        self.writer = StreamWriter(self.game_url)
        self.writer.ready.connect(self.on_writer_ready)
        self.writer.not_ready.connect(self.on_writer_not_ready)
        self.writer.closed.connect(self.on_writer_closed)
        self.writer.connect_to_replay_server(QUrl(data["accessUrl"]))

    def on_writer_ready(self) -> None:
        assert self.game_url is not None
        assert self.writer is not None
        if replay(self.game_url):
            self.writer.start()
        else:
            self.writer.abort()

    def on_writer_not_ready(self) -> None:
        msg = "Could not start live replay.\nReplay server disconnected for no reason"
        QMessageBox.warning(None, "Error", msg)
        self.on_writer_closed()

    def on_writer_closed(self) -> None:
        self.writer = None
