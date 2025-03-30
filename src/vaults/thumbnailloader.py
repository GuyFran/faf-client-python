from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest

type PixmapLoaderCallback = Callable[[QPixmap | None], None]


class ThumbnailLoader:
    def __init__(self) -> None:
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.handle_response)
        self.pending_requests: dict[QNetworkReply, PixmapLoaderCallback] = {}

    def load(self, url: str, callback: PixmapLoaderCallback) -> None:
        request = QNetworkRequest(QUrl(url))
        if (reply := self.network_manager.get(request)) is None:
            return
        self.pending_requests[reply] = callback

    def handle_response(self, reply: QNetworkReply) -> None:
        callback = self.pending_requests.pop(reply, None)
        if not callback:
            return
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            callback(pixmap)
        else:
            callback(None)
        reply.deleteLater()
