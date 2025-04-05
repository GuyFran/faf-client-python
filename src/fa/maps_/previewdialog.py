
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.util import THEME

STYLESHEET = THEME.readstylesheet("client/client.css")


class MapPreviewDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Map Preview")
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        self.preview_label = QLabel()
        self.preview_label.setPixmap(pixmap)
        layout.addWidget(self.preview_label)
        self.setLayout(layout)
        self.setStyleSheet(STYLESHEET)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self.preview_label.setPixmap(pixmap)
