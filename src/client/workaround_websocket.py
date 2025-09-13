import logging
import socket
from queue import Queue
from queue import ShutDown
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


class SocketReader(QThread):
    message_received = pyqtSignal(QByteArray)
    error = pyqtSignal()

    def __init__(self, connection: ClientConnection) -> None:
        super().__init__()
        self.connection = connection

    def run(self) -> None:
        try:
            for message in self.connection:
                self.message_received.emit(QByteArray(cast(bytes, message)))
        except (ConnectionAbortedError, ConnectionClosedError) as e:
            logger.error(e)
            self.error.emit()
            return


class SocketWriter(QThread):
    error = pyqtSignal()

    def __init__(self, connection: ClientConnection, send_queue: Queue[bytes]) -> None:
        super().__init__()
        self.send_queue = send_queue
        self.connection = connection

    def run(self) -> None:
        while True:
            try:
                item = self.send_queue.get()
            except ShutDown:
                return
            try:
                self.connection.send(item)
            except (ConnectionAbortedError, ConnectionClosedError) as e:
                logger.error(e)
                self.error.emit()
                return
            self.send_queue.task_done()


class Websocket(QObject):
    binaryMessageReceived = pyqtSignal(QByteArray)
    errorOccurred = pyqtSignal(QAbstractSocket.SocketError)
    stateChanged = pyqtSignal(QAbstractSocket.SocketState)

    def __init__(self, addresses: list[QHostAddress]) -> None:
        super().__init__()
        self.addresses = addresses
        self.socket: socket.socket | None = None
        self.send_queue: Queue[bytes] | None = None
        self._sock_state = QAbstractSocket.SocketState.UnconnectedState

        self.reader_thread: SocketReader | None = None
        self.writer_thread: SocketWriter | None = None
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

    def sync_state(self) -> None:
        assert self.connection is not None
        self.sock_state = self.connection.state

    def sendBinaryMessage(self, message: bytes) -> None:
        assert self.send_queue is not None
        self.send_queue.put(message)

    def state(self) -> QAbstractSocket.SocketState:
        return self._sock_state

    def errorString(self) -> str:
        return "[Not implemented]"

    def close(self) -> None:
        self._sock_state = QAbstractSocket.SocketState.UnconnectedState
        self.stateChanged.emit(self._sock_state)

        if self.send_queue is not None:
            self.send_queue.shutdown()
            self.send_queue = None
        if self.reader_thread is not None:
            self.reader_thread.quit()
            self.reader_thread = None
        if self.writer_thread is not None:
            self.writer_thread.quit()
            self.writer_thread = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.socket = None

    def reader_writer_error(self) -> None:
        self.sync_state()
        self.errorOccurred.emit(QAbstractSocket.SocketError.NetworkError)

    def open(self, url: QUrl) -> None:
        self._sock_state = QAbstractSocket.SocketState.ConnectingState
        self.stateChanged.emit(self._sock_state)

        self.connect()
        assert self.socket is not None

        # prevent leaking lobby access verfication token into logs
        log_level = logger.getEffectiveLevel()
        logger.setLevel(logging.INFO)
        self.connection = connect(url.url(), sock=self.socket, logger=logger)
        logger.setLevel(log_level)

        self.connection.debug = False
        self.connection.protocol.debug = False

        self.start_read_write()
        self.sync_state()

    def start_read_write(self) -> None:
        assert self.connection is not None

        self.reader_thread = SocketReader(self.connection)
        self.reader_thread.message_received.connect(self.binaryMessageReceived.emit)
        self.reader_thread.error.connect(self.reader_writer_error)
        self.reader_thread.start()

        self.send_queue = Queue()
        self.writer_thread = SocketWriter(self.connection, self.send_queue)
        self.writer_thread.error.connect(self.reader_writer_error)
        self.writer_thread.start()
