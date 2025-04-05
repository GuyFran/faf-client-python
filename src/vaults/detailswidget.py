from __future__ import annotations

from operator import attrgetter

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.api.models.MapVersionReview import MapVersionReview
from src.api.models.Mod import Mod
from src.api.models.ModVersionReview import ModVersionReview
from src.api.vaults_api import ReviewsApiConnector
from src.downloadManager import DownloadRequest
from src.downloadManager import ImageDownloader
from src.vaults.detailswidgetui import DetailsWidgetUI
from src.vaults.reviewwidget import CommentWidget
from src.vaults.reviewwidget import RatingBarWidget
from src.vaults.reviewwidget import RatingDistribution

STYLESHEET = util.THEME.readstylesheet("client/client.css")

type VersionReview = MapVersionReview | ModVersionReview


def convert_review(dto_cls: type[Map | Mod], dto: dict) -> VersionReview:
    if dto_cls == Map:
        return MapVersionReview(**dto)
    elif dto_cls == Mod:
        return ModVersionReview(**dto)
    raise ValueError(f"Unexpected dto_cls: {dto_cls}")


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
        self.item_type_name = type(item_data).__name__

        self.image_downloader = ImageDownloader(image_cache_dir)
        self.image_dl_request = DownloadRequest()
        self.image_dl_request.done.connect(self.on_image_downloaded)

        self.reviews_api = ReviewsApiConnector()
        self.reviews_api.data_ready.connect(self.on_reviews_data)

        self.ui = DetailsWidgetUI()
        self.ui.setupUi(self)
        self.init_ui()

    def is_installed(self) -> bool:
        return False

    def set_author(self) -> None:
        self.ui.authorLayout.addWidget(QLabel("Unknown Author"))

    def set_reviews_summary(self) -> None:
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
                self.ui.reviewsForm.addRow(QLabel(label), QLabel(field))
            view_reviews_btn = QPushButton("View All Reviews")
            view_reviews_btn.clicked.connect(lambda: self.ui.tabs.setCurrentIndex(2))
            self.ui.reviewsLayout.addWidget(view_reviews_btn)
        else:
            self.ui.reviewsLayout.addWidget(QLabel("No reviews available"))

    def version_info(self) -> list[tuple[str, str]]:
        raise NotImplementedError

    def technical_info(self) -> list[tuple[str, str]]:
        name = self.item_type_name
        return [
            (f"{name} created", util.utctolocal(self.item_data.create_time)),
            (f"{name} updated", util.utctolocal(self.item_data.update_time)),
            (f"{name}Version created", util.utctolocal(self.item_version.create_time)),
            (f"{name}Version updated", util.utctolocal(self.item_version.update_time)),
        ]

    def set_type(self) -> None:
        raise NotImplementedError

    def set_additional_info(self) -> None:
        raise NotImplementedError

    def update_buttons_layout(self) -> None:
        self.ui.downloadButton.setVisible(not self.is_installed())
        self.ui.removeButton.setVisible(self.is_installed())

    def configure_buttons(self) -> None:
        self.ui.downloadButton.setText(f"Download {self.item_type_name}")
        self.ui.removeButton.setText(f"Remove {self.item_type_name}")
        self.update_buttons_layout()
        self.ui.downloadButton.clicked.connect(self.download_and_change_availability)
        self.ui.removeButton.clicked.connect(self.remove_and_change_availability)

    def init_ui(self) -> None:
        self.configure_buttons()

        self.ui.viewFolderButton.clicked.connect(self.view_folder)
        self.ui.tabs.currentChanged.connect(self.on_tab_changed)

        self.ui.titleLabel.setText(self.item_data.display_name)
        self.set_type()
        self.set_additional_info()
        self.set_author()
        self.set_reviews_summary()

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
            f"Delete {self.item_type_name}",
            f"Are you sure you want to delete this {self.item_type_name}?",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.remove_item()
            return True
        return False

    def remove_item(self) -> None:
        raise NotImplementedError

    def download_and_change_availability(self) -> None:
        self.download_item()
        self.on_availability_changed()

    def remove_and_change_availability(self) -> None:
        if not self.remove_item_safe():
            return
        self.on_availability_changed()

    def on_availability_changed(self) -> None:
        self.item_availability_changed.emit()
        self.update_buttons_layout()

    def on_reviews_data(self, message: dict) -> None:
        map_info = message["data"]

        reviews = []
        for version in map_info["versions"]:
            for review_dct in version["reviews"]:
                if review_dct["text"] is None:
                    review_dct["text"] = ""
                review = convert_review(type(self.item_data), review_dct)
                reviews.append(review)
        reviews.sort(key=attrgetter("create_time"), reverse=True)
        self.set_reviews_and_comments(reviews)

    def set_reviews_and_comments(self, reviews: list[VersionReview]) -> None:
        rating_distribution = RatingDistribution(reviews)
        self.ui.detailedReviews.ratingBarsLayout.addWidget(RatingBarWidget(rating_distribution))
        for review in reviews:
            comment_widget = CommentWidget(review)
            self.ui.detailedReviews.commentsContainer.addWidget(comment_widget)
        self.ui.detailedReviews.commentsContainer.addStretch()

        self.ui.detailedReviews.show_reviews()

    def show_comments(self) -> None:
        self.reviews_api.request_data({"filter": f"id=={self.item_data.xd}"})

    def on_tab_changed(self, index: int) -> None:
        if index != 2:
            return

        if self.item_data.reviews_summary is None:
            self.ui.detailedReviews.show_no_reviews()
        elif self.ui.detailedReviews.commentsContainer.count() == 0:
            self.ui.detailedReviews.show_loading()
            self.reviews_api.request_reviews(self.item_data)
