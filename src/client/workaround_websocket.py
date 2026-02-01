import logging
import socket
from typing import cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QThread
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtNetwork import QHostAddress
from websockets.exceptions import ConnectionClosedError
from websockets.protocol import State
from websockets.sync.client import ClientConnection
from websockets.sync.client import connect

from src.config import Settings

logger = logging.getLogger(__name__)


class SocketReader(QObject):
    message_received = pyqtSignal(QByteArray)
    error = pyqtSignal(object)

    def __init__(self, connection: ClientConnection | None = None) -> None:
        super().__init__()
        self.connection: ClientConnection | None = connection

    def set_connection(self, conn: ClientConnection, /) -> None:
        self.connection = conn

    def read(self) -> None:
        if self.connection is None:
            logger.warning("Trying to read without any connection")
            return
        try:
            for message in self.connection:
                self.message_received.emit(QByteArray(cast(bytes, message)))
        except (ConnectionAbortedError, ConnectionClosedError) as e:
            self.error.emit(e)


class Websocket(QObject):
    binaryMessageReceived = pyqtSignal(QByteArray)
    errorOccurred = pyqtSignal(QAbstractSocket.SocketError)
    stateChanged = pyqtSignal(QAbstractSocket.SocketState)
    sendMessageRequest = pyqtSignal(bytes)
    _start_read = pyqtSignal()

    def __init__(self, addresses: list[QHostAddress]) -> None:
        super().__init__()
        self.addresses = addresses
        self.socket: socket.socket | None = None
        self._sock_state = QAbstractSocket.SocketState.UnconnectedState

        self.reader_thread = QThread()

        self.reader = SocketReader()
        self.reader.moveToThread(self.reader_thread)
        self.reader.message_received.connect(self.binaryMessageReceived.emit)
        self.reader.error.connect(self.handle_error)
        self._start_read.connect(self.reader.read)

        self.connection: ClientConnection | None = None

        self._states = (
            QAbstractSocket.SocketState.ConnectingState,
            QAbstractSocket.SocketState.ConnectedState,
            QAbstractSocket.SocketState.ClosingState,
            QAbstractSocket.SocketState.UnconnectedState,
        )

    def connect(self) -> None:
        for addr in self.addresses:
            self.socket = socket.socket()
            self.socket.settimeout(1)
            try:
                self.socket.connect((addr.toString(), Settings.get("lobby/port", 443)))
                return
            except TimeoutError:
                pass
        else:
            self.errorOccurred.emit(QAbstractSocket.SocketError.NetworkError)

    @property
    def sock_state(self) -> QAbstractSocket.SocketState:
        return self._sock_state

    @sock_state.setter
    def sock_state(self, value: State) -> None:
        self._sock_state = self._states[value]
        self.stateChanged.emit(self._sock_state)

    def sendBinaryMessage(self, message: bytes) -> None:
        if self.connection is not None:
            try:
                self.connection.send(message)
            except (ConnectionAbortedError, ConnectionClosedError) as e:
                self.handle_error(e)
        else:
            logger.warning("Trying to write without any connection")

    def state(self) -> QAbstractSocket.SocketState:
        return self._sock_state

    def errorString(self) -> str:
        return "[Not implemented]"

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None
        self.socket = None
        self.sock_state = State.CLOSED

    def handle_error(self, error: Exception) -> None:
        logger.error(error)
        self.errorOccurred.emit(QAbstractSocket.SocketError.NetworkError)
        self.close()

    def open(self, url: QUrl) -> None:
        self.sock_state = State.CONNECTING

        self.connect()
        assert self.socket is not None

        # prevent leaking lobby access verfication token into logs
        log_level = logger.getEffectiveLevel()
        logger.setLevel(logging.INFO)
        self.connection = connect(url.url(), sock=self.socket, logger=logger)
        logger.setLevel(log_level)

        self.connection.debug = False
        self.connection.protocol.debug = False

        self.reader.set_connection(self.connection)
        if not self.reader_thread.isRunning():
            self.reader_thread.start()
        self._start_read.emit()

        self.sock_state = self.connection.state
