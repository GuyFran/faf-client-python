from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QLabel


class ClickableLabel(QLabel):
    clicked = pyqtSignal(QMouseEvent)

    def mousePressEvent(self, ev: QMouseEvent | None) -> None:
        if ev is None or ev.button() != Qt.MouseButton.LeftButton:
            return
        self.clicked.emit(ev)
        QLabel.mousePressEvent(self, ev)
