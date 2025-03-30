from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.api.models.Mod import Mod
from src.downloadManager import DownloadRequest
from src.downloadManager import ImageDownloader
from src.vaults.detailswidgetui import DetailsWidgetUI

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class DetailsWidget(QWidget):
    item_availability_changed = pyqtSignal()

    def __init__(
            self,
            item_data: Map | Mod,
            image_cache_dir: str,
            parent: QWidget | None = None,
    ) -> None:
        QWidget.__init__(self, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

        self.image_downloader = ImageDownloader(image_cache_dir)
        self.image_dl_request = DownloadRequest()
        self.image_dl_request.done.connect(self.on_image_downloaded)

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
        self.update_thumbnail()

    def get_thumbnail(self) -> QPixmap:
        url = QUrl(self.item_version.thumbnail_url_large)
        if self.image_downloader.image_exists(url):
            return QPixmap(self.image_downloader.image_path(url))
        return QPixmap()

    def update_thumbnail(self) -> None:
        if (thumbnail := self.get_thumbnail()).isNull():
            self.load_thumbnail()
        else:
            self.set_thumbnail(thumbnail)

    def load_thumbnail(self) -> None:
        self.ui.thumbnailLabel.setText("Loading thumbnail...")
        self.image_downloader.download_image(
            self.item_version.thumbnail_url_large,
            self.image_dl_request,
        )

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.ui.thumbnailLabel.setText("Failed to load thumbnail")
            return
        ratio = Qt.AspectRatioMode.KeepAspectRatio
        trans_mode = Qt.TransformationMode.SmoothTransformation
        scaled_thumbnail = pixmap.scaled(256, 256, ratio, trans_mode)
        self.ui.thumbnailLabel.setPixmap(scaled_thumbnail)

    def on_image_downloaded(self, _: str, pixmap: QPixmap) -> None:
        self.set_thumbnail(pixmap)

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
