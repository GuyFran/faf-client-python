import logging
from typing import Any
from typing import cast

from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from src import util

logger = logging.getLogger(__name__)


class NewsItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

        self.html = QtGui.QTextDocument()
        to = QtGui.QTextOption()
        to.setWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        self.html.setDefaultTextOption(to)
        self.html.setTextWidth(NewsItem.TEXTWIDTH)

    def paint(
        self,
        painter: QtGui.QPainter | None,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        if painter is None:
            return

        self.initStyleOption(option, index)
        painter.save()

        self.html.setHtml(option.text)

        # clear icon and text before letting the control draw itself because
        # we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""

        style = cast(QtWidgets.QStyle, option.widget.style())
        style.drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget,
        )

        painter.translate(option.rect.left() + 10, option.rect.top() + 10)
        clip = QtCore.QRectF(0, 0, option.rect.width() - 10 - 5, option.rect.height())
        self.html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtCore.QSize:
        self.initStyleOption(option, index)
        self.html.setHtml(option.text)
        return QtCore.QSize(NewsItem.TEXTWIDTH + NewsItem.PADDING, NewsItem.TEXTHEIGHT)


class NewsItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    TEXTHEIGHT = 85
    PADDING = 10

    FORMATTER = util.THEME.readfile("news/formatters/newsitem.qhtml")
    COLORS = util.THEME.find_stylesheet_style_as_dict("NewsItemFormatter::custom")

    def __init__(
        self,
        newsPost: dict[str, Any],
        parent: QtWidgets.QListWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.newsPost = newsPost

        self.setText(
            self.FORMATTER.format(
                author=newsPost['author'][0]['name'],
                date=newsPost['date'],
                title=newsPost['title'],
                **self.COLORS,
            ),
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, NewsItem):
            return False
        return self.newsPost['date'].__lt__(other.newsPost['date'])
