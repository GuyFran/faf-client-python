import logging
from typing import TYPE_CHECKING
from typing import Any

from PyQt6 import QtCore
from PyQt6.QtCore import QObject

if TYPE_CHECKING:
    from src.news._newswidget import NewsWidget

from .wpapi import WPAPI

logger = logging.getLogger(__name__)


class NewsManager(QObject):
    def __init__(self, widget: NewsWidget) -> None:
        QObject.__init__(self)
        self.widget = widget

        self.WpApi = WPAPI()
        self.WpApi.newsDone.connect(self.on_wpapi_done)
        self.WpApi.download(page=1, perpage=20)

    @QtCore.pyqtSlot(list)
    def on_wpapi_done(self, items: list[dict[str, Any]]):
        for item in items:
            self.widget.addNews(item)

        self.widget.updateNewsFilter()
        for i in range(len(items)):
            if not self.widget.newsList.item(i).isHidden():
                self.widget.newsList.setCurrentItem(self.widget.newsList.item(i))
                break
        self.widget.on_news_loaded()
