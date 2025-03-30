from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.api.models.Mod import Mod
from src.vaults.detailswidgetui import DetailsWidgetUI

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class DetailsWidget(QWidget):
    item_availability_changed = pyqtSignal()

    def __init__(
            self,
            item_data: Map | Mod,
            parent: QWidget | None = None,
    ) -> None:
        QWidget.__init__(self, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

        self.network_manager = QNetworkAccessManager()
        self.thumbnail = QPixmap()
        self.ui = DetailsWidgetUI()
        self.ui.setupUi(self)
        self.init_ui()

    def is_installed(self) -> bool:
        return False

    def set_author(self) -> None:
        self.ui.authorLayout.addWidget(QLabel("Unknown Author"))

    def set_reviews(self) -> None:
        if summary := self.item_data.reviews_summary:
            rows = (
                ("Average Score:", f"{summary.average_score:.1f}/5.0"),
                ("Total Score:", f"{summary.score:.1f}"),
                ("Reviews:", f"{summary.num_reviews:.0f}"),
                ("Positive:", f"{summary.positive:.1f}"),
                ("Negative:", f"{summary.negative:.1f}"),
                ("Lower Bound:", f"{summary.lower_bound:.1f}"),
            )
            for label, field in rows:
                self.ui.reviewsLayout.addRow(QLabel(label), QLabel(field))
        else:
            self.ui.reviewsLayout.addWidget(QLabel("No reviews available"))

    def version_info(self) -> list[tuple[str, str]]:
        raise NotImplementedError

    def technical_info(self) -> list[tuple[str, str]]:
        raise NotImplementedError

    def set_type(self) -> None:
        raise NotImplementedError

    def set_additional_info(self) -> None:
        raise NotImplementedError

    def update_download_button_text(self) -> None:
        if self.is_installed():
            self.ui.downloadButton.setText(f"Remove {self.item_data.__class__.__name__}")
        else:
            self.ui.downloadButton.setText(f"Download {self.item_data.__class__.__name__}")

    def init_ui(self) -> None:
        self.update_download_button_text()
        self.ui.downloadButton.clicked.connect(self.download_or_remove_item)

        self.ui.viewFolderButton.clicked.connect(self.view_folder)

        self.ui.titleLabel.setText(self.item_data.display_name)
        self.set_type()
        self.set_additional_info()
        self.set_author()
        self.set_reviews()

        for label, field in self.version_info():
            self.ui.versionLayout.addRow(QLabel(label), QLabel(field))

        self.ui.descriptionLabel.setText(self.item_version.description)

        tech_info = self.technical_info()
        self.ui.techTable.setRowCount(len(tech_info))
        for i, (prop, value) in enumerate(tech_info):
            self.ui.techTable.setItem(i, 0, QTableWidgetItem(prop))
            self.ui.techTable.setItem(i, 1, QTableWidgetItem(value))
        self.ui.techTable.resizeColumnsToContents()
        self.load_thumbnail(self.item_version.thumbnail_url_large)

    def load_thumbnail(self, url: str) -> None:
        request = QNetworkRequest(QUrl(url))
        if (reply := self.network_manager.get(request)) is None:
            return
        reply.finished.connect(lambda: self.handle_thumbnail_response(reply))

    def handle_thumbnail_response(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.thumbnail.loadFromData(reply.readAll())
            ratio = Qt.AspectRatioMode.KeepAspectRatio
            trans_mode = Qt.TransformationMode.SmoothTransformation
            scaled_thumbnail = self.thumbnail.scaled(256, 256, ratio, trans_mode)
            self.ui.thumbnailLabel.setPixmap(scaled_thumbnail)
        else:
            self.ui.thumbnailLabel.setText("Failed to load thumbnail")

        reply.deleteLater()

    def view_folder(self) -> None:
        raise NotImplementedError

    def download_item(self) -> None:
        raise NotImplementedError

    def remove_item_safe(self) -> bool:
        answer = QMessageBox.question(
            self,
            f"Delete {self.item_data.__class__.__name__}",
            f"Are you sure you want to delete this {self.item_data.__class__.__name__}?",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.remove_item()
            return True
        return False

    def remove_item(self) -> None:
        raise NotImplementedError

    def download_or_remove_item(self) -> None:
        if self.is_installed():
            if not self.remove_item_safe():
                return
        else:
            self.download_item()
        self.item_availability_changed.emit()
        self.update_download_button_text()
