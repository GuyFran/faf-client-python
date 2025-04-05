from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtWidgets import QSpacerItem
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget


class ListWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        self.mainLayout = QHBoxLayout(widget)
        self.mainLayout.setContentsMargins(5, 5, 5, 5)

        self.thumbnailLabel = QLabel()
        self.thumbnailLabel.setFixedSize(100, 100)
        self.thumbnailLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnailLabel.setObjectName("vaultThumbnail")

        self.mainLayout.addWidget(self.thumbnailLabel)

        self.infoLayout = QVBoxLayout()
        self.infoLayout.setSpacing(0)

        self.titleLabel = QLabel()
        self.titleLabel.setObjectName("vaultListItemTitle")
        self.titleLabel.setProperty("titleLabel", "true")
        self.infoLayout.addWidget(self.titleLabel)

        self.versionLabel = QLabel()
        self.infoLayout.addWidget(self.versionLabel)
        self.authorLabel = QLabel()
        self.infoLayout.addWidget(self.authorLabel)
        self.infoLayout.addStretch()

        self.detailsLayout = QGridLayout()
        self.detailsLayout.setHorizontalSpacing(20)
        spacer = QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.detailsLayout.addItem(spacer, 0, 2)
        self.infoLayout.addLayout(self.detailsLayout)
        self.mainLayout.addLayout(self.infoLayout, 1)
