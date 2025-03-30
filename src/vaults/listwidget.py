from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Map import Map
from src.api.models.Mod import Mod
from src.vaults.listwidgetui import ListWidgetUI
from src.vaults.starrating import StarRatingWidget
from src.vaults.thumbnailloader import ThumbnailLoader

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class VaultListWidget(QWidget):
    def __init__(self, item_data: Map | Mod, parent: QWidget | None = None) -> None:
        QWidget.__init__(self, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version
        self.thumbnail_loader = ThumbnailLoader()
        self.ui = ListWidgetUI()
        self.ui.setupUi(self)
        self.init_ui()

    def update_visibility(self) -> None:
        old_property = self.ui.titleLabel.property("installed")
        if self.is_installed():
            self.ui.titleLabel.setProperty("installed", "true")
        else:
            self.ui.titleLabel.setProperty("installed", None)
        if old_property != self.ui.titleLabel.property("installed"):
            self.ui.titleLabel.setStyleSheet(STYLESHEET)

    def is_installed(self) -> bool:
        return False

    def check_installed(self) -> None:
        raise NotImplementedError

    def init_ui(self) -> None:
        self.ui.titleLabel.setText(self.item_data.display_name)
        if self.is_installed():
            self.ui.titleLabel.setProperty("installed", "true")
        if self.item_version and self.item_version.thumbnail_url:
            self.ui.thumbnailLabel.setText("Loading...")
            self.thumbnail_loader.load(
                self.item_version.thumbnail_url,
                self.set_thumbnail,
            )
        else:
            self.ui.thumbnailLabel.setText("No image")
        self.ui.versionLabel.setText(f"version {self.item_version.version}")
        self.set_author()
        self.populate_details()

    def set_author(self) -> None:
        raise NotImplementedError

    def grid_elements(self) -> list[QWidget | QLayout]:
        return []

    def populate_details(self) -> None:
        for index, element in enumerate(self.grid_elements()):
            if isinstance(element, QWidget):
                self.ui.detailsLayout.addWidget(element, index // 2, index % 2)
            elif isinstance(element, QLayout):
                self.ui.detailsLayout.addLayout(element, index // 2, index % 2)

    def rating_layout(self) -> QHBoxLayout:
        rating_layout = QHBoxLayout()
        if self.item_data.reviews_summary is not None:
            rating = self.item_data.reviews_summary.average_score
            star_rating = StarRatingWidget(rating=rating, max_rating=5, star_size=10)
            rating_layout.addWidget(star_rating)
            rating_layout.addWidget(QLabel(f"({self.item_data.reviews_summary.num_reviews})"))
        else:
            rating_layout.addWidget(QLabel("<i>No reviews</i>"))
        return rating_layout

    def uploaded_label(self) -> QLabel:
        local_time = util.utctolocal(self.item_version.create_time)
        return QLabel(f"<b>Uploaded:</b> {local_time}")

    def recommended_label(self) -> QLabel:
        label = QLabel("✓ Recommended" if self.item_data.recommended else "")
        label.setProperty("recommended", "true")
        return label

    def set_thumbnail(self, pixmap: QPixmap | None) -> None:
        if pixmap:
            ratio = Qt.AspectRatioMode.KeepAspectRatio
            trans_mode = Qt.TransformationMode.SmoothTransformation
            thumbnail = pixmap.scaled(100, 100, ratio, trans_mode)
            self.ui.thumbnailLabel.setPixmap(thumbnail)
        else:
            self.ui.thumbnailLabel.setText("Error")
