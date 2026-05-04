from typing import Any

from PyQt6.QtCore import QEvent
from PyQt6.QtCore import QModelIndex
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimerEvent
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtGui import QStandardItem
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtWidgets import QStyleOptionViewItem
from PyQt6.QtWidgets import QWidget


# https://gis.stackexchange.com/questions/350148/qcombobox-multiple-selection-pyqt5
class CheckableComboBox(QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        # Use custom delegate
        self.setItemDelegate(CheckableComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

        self.no_choice_text = ""

    def setNoChoiceText(self, text: str) -> None:
        self.no_choice_text = text

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # Recompute text to elide as needed
        self.updateText()

    def wheelEvent(self, e: QWheelEvent | None) -> None:
        # TODO
        return

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:  # type: ignore[override]  # noqa: E501
        if obj is None or not self.isEnabled():
            return False

        if event is None:
            return super().eventFilter(obj, event)

        if obj is self.lineEdit():
            if event.type() == QEvent.Type.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if obj is self.view().viewport():
            if event.type() == QEvent.Type.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
                return True
        return False

    def showPopup(self) -> None:
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self) -> None:
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event: QTimerEvent | None) -> None:  # type: ignore[override]
        if event is None:
            return
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self) -> None:
        texts = self.currentData()
        text = self.delimiter().join(texts) if texts else self.no_choice_text

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.TextElideMode.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text: str, data: Any | None = None) -> None:
        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts: list[str], datalist: list[Any] | None = None) -> None:
        if datalist is None:
            return
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentData(self) -> list[Any]:
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.CheckState.Checked:
                res.append(self.model().item(i).data())
        return res

    def setCurrentText(self, text: str | None) -> None:
        if text is None:
            return
        choices = text.split(self.delimiter())
        for i in range(self.model().rowCount()):
            if self.model().item(i).text() in choices:
                self.model().item(i).setCheckState(Qt.CheckState.Checked)

    def delimiter(self) -> str:
        return ", "
