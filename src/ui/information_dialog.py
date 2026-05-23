from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import QWidget

from src.util import THEME

FormClass, BaseClass = THEME.loadUiType("dialogs/information.ui")


class MessageDialog(FormClass, BaseClass):
    def __init__(self, parent: QWidget | None = None) -> None:
        BaseClass.__init__(self, parent)
        self.setupUi(self)
        self.set_icon()

    def setDetailedText(self, text: str) -> None:
        self.editDetails.setPlainText(text)

    def setText(self, text: str) -> None:
        self.labelText.setText(text)

    def set_icon(self) -> None:
        if p := self.parent():
            style = p.style()
        else:
            style = QApplication.style()
        if not style:
            return
        pixmap = style.standardPixmap(QStyle.StandardPixmap.SP_MessageBoxInformation)
        self.labelIcon.setPixmap(pixmap)


def message_dialog(parent: QWidget | None, title: str, text: str, details: str) -> None:
    dialog = MessageDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setText(text)
    dialog.setDetailedText(details)
    dialog.exec()
    dialog.deleteLater()
