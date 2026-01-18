import logging
import os.path
from typing import Any

from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QSize
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QToolTip
from PyQt6.QtWidgets import QWidget

from src import util
from src.config import Settings
from src.downloadManager import Downloader
from src.downloadManager import DownloadRequest

from .newsitem import NewsItem
from .newsitem import NewsItemDelegate
from .newsmanager import NewsManager

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("news/news.ui")


class NewsWidget(FormClass, BaseClass):
    IMAGE_SIZE = QSize(600, 338)

    def __init__(self, parent: QWidget | None = None) -> None:
        BaseClass.__init__(self, parent)

        self.setupUi(self)

        self._downloader = Downloader(util.NEWS_CACHE_DIR)
        self._images_dl_request = DownloadRequest()
        self._images_dl_request.done.connect(self.item_image_downloaded)

        self.newsManager = NewsManager(self)
        self.newsItems: list[NewsItem] = []

        self.settingsFrame.hide()
        self.hideNewsEdit.setText(Settings.get('news/hideWords', ""))

        self.newsList.setIconSize(QSize(0, 0))
        self.newsList.setItemDelegate(NewsItemDelegate(self))
        self.newsList.currentItemChanged.connect(self.itemChanged)
        self.newsSettings.pressed.connect(self.showSettings)
        self.showAllButton.pressed.connect(self.showAll)
        self.hideNewsEdit.textEdited.connect(self.updateNewsFilter)
        self.hideNewsEdit.cursorPositionChanged.connect(self.showEditToolTip)
        self.newsLinkButton.clicked.connect(self.open_news_in_browser)

    def addNews(self, newsPost: dict[str, Any]) -> None:
        newsItem = NewsItem(newsPost, self.newsList)
        self.newsItems.append(newsItem)

    def download_image(self, img_url: str) -> None:
        name = os.path.basename(img_url)
        self._downloader.download(name, self._images_dl_request, img_url)

    def item_image_downloaded(self, image_name: str, result: tuple[str, bool]) -> None:
        image_path, download_failed = result
        if not download_failed:
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(self.IMAGE_SIZE)
            self.imageLabel.setPixmap(scaled)
        else:
            self.imageLabel.clear()
        self.show_newspage()

    def itemChanged(self, current: NewsItem | None, previous: NewsItem | None) -> None:
        if current is None:
            return

        url = current.newsPost["img_url"]
        image_name = os.path.basename(url)
        image_path = os.path.join(util.NEWS_CACHE_DIR, image_name)
        if os.path.isfile(image_path):
            self.imageLabel.setPixmap(QPixmap(image_path).scaled(self.IMAGE_SIZE))
            self.show_newspage()
        else:
            self.imageLabel.clear()
            self._downloader.download(image_name, self._images_dl_request, url)

    def show_newspage(self) -> None:
        current = self.newsList.currentItem()
        if current is None:
            return
        content = current.newsPost["excerpt"].strip().removeprefix("<p>").removesuffix("</p>")
        self.newsTitleLabel.setText(current.newsPost["title"])
        self.bodyLabel.setText(content)

    def showAll(self) -> None:
        for item in self.newsItems:
            item.setHidden(False)
        self.updateLabel(0)

    def showEditToolTip(self) -> None:
        """
        Default tooltips are too slow and disappear when user starts typing
        """
        widget = self.hideNewsEdit
        position = widget.mapToGlobal(
            QPoint(int(widget.width()), -widget.height() // 2),
        )
        QToolTip.showText(
            position,
            "To separate multiple words use commas: nomads,server,dev",
        )

    def showSettings(self):
        if self.settingsFrame.isHidden():
            self.settingsFrame.show()
        else:
            self.settingsFrame.hide()

    def updateNewsFilter(self, text=False):
        if text is not False:
            Settings.set('news/hideWords', text)

        filterList = Settings.get('news/hideWords', "").lower().split(",")
        newsHidden = 0

        if filterList[0]:
            for item in self.newsItems:
                for word in filterList:
                    if word in item.newsPost["title"].lower():
                        item.setHidden(True)
                        newsHidden += 1
                        break
                    else:
                        item.setHidden(False)
        else:
            for item in self.newsItems:
                item.setHidden(False)

        self.updateLabel(newsHidden)

    def updateLabel(self, number):
        self.totalHidden.setText("NEWS HIDDEN: " + str(number))

    def open_news_in_browser(self) -> None:
        current = self.newsList.currentItem()
        if current is None:
            return
        if current.newsPost["external_link"] == "":
            external_link = current.newsPost["link"]
        else:
            external_link = current.newsPost["external_link"]
        QDesktopServices.openUrl(QUrl(external_link))

    def on_news_loaded(self) -> None:
        self.stackedWidget.setCurrentIndex(1)
