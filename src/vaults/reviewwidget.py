from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.api.models.MapVersionReview import MapVersionReview
from src.api.models.ModVersionReview import ModVersionReview
from src.util import utctolocal
from src.vaults.starrating import StarRatingWidget

type VersionReview = MapVersionReview | ModVersionReview


class RatingDistribution:
    def __init__(self, reviews: list[VersionReview]) -> None:
        self.num_reviews = len(reviews)
        self.counts = Counter(review.score for review in reviews)

    def get_percentage(self, score: int) -> float:
        if self.num_reviews == 0:
            return 0
        return (self.counts[score] / self.num_reviews) * 100

    def get_count(self, score: int) -> int:
        return self.counts[score]

    def total_score(self) -> int:
        return sum(self.counts[score] * score for score in range(1, 6))

    def average_score(self) -> float:
        if self.num_reviews == 0:
            return 0.0
        return self.total_score() / self.num_reviews


class CommentWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        header_layout = QVBoxLayout()
        additional_info_layout = QHBoxLayout()

        self.nameLabel = QLabel()
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        self.nameLabel.setFont(name_font)
        header_layout.addWidget(self.nameLabel)

        self.dateLabel = QLabel()
        self.dateLabel.setFixedWidth(200)

        self.versionLabel = QLabel()

        self.scoreLabel = QLabel()
        self.scoreLabel.setObjectName("starLabel")

        additional_info_layout.addWidget(self.dateLabel)
        additional_info_layout.addWidget(self.versionLabel)
        additional_info_layout.addWidget(self.scoreLabel)
        additional_info_layout.addStretch()
        header_layout.addLayout(additional_info_layout)
        layout.addLayout(header_layout)

        self.reviewText = QTextEdit()
        self.reviewText.setObjectName("reviewText")
        self.reviewText.setReadOnly(True)
        self.reviewText.setMaximumHeight(100)
        layout.addWidget(self.reviewText)

        widget.setLayout(layout)


class CommentWidget(QWidget):
    def __init__(self, review: VersionReview, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.review = review
        self.ui = CommentWidgetUI()
        self.ui.setupUi(self)
        self.fill_ui()

    def fill_ui(self) -> None:
        self.ui.nameLabel.setText(self.review.player.login if self.review.player else "Anonymous")
        self.ui.dateLabel.setText(utctolocal(self.review.create_time, "MMMM dd, yyyy hh:mm"))
        assert self.review.version is not None
        self.ui.versionLabel.setText(f"version {self.review.version.version}")
        self.ui.scoreLabel.setText(self.get_star_rating())
        self.ui.reviewText.setText(self.review.text)

    def get_star_rating(self) -> str:
        full_stars = "★" * self.review.score
        empty_stars = "☆" * (5 - self.review.score)
        return f"{full_stars}{empty_stars} ({self.review.score}/5)"


class RatingBarWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        self.bars: dict[int, tuple[QProgressBar, QLabel]] = {}

        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        self.summaryLayout = QVBoxLayout()
        self.summaryLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.averageLabel = QLabel()
        self.averageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.averageLabel.setObjectName("averageReviewRatingLabel")
        self.summaryLayout.addWidget(self.averageLabel)

        self.reviewsCountLabel = QLabel()
        self.reviewsCountLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reviewsCountLabel.setObjectName("reviewRatingCountLabel")
        self.summaryLayout.addWidget(self.reviewsCountLabel)

        main_layout.addLayout(self.summaryLayout, stretch=1)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        title_label = QLabel("Rating Distribution")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        right_layout.addWidget(title_label)

        for score in range(5, 0, -1):
            row_layout = QHBoxLayout()

            star_label = QLabel(f"{score} {'★' if score == 1 else '★' * score}")
            star_label.setFixedWidth(80)
            row_layout.addWidget(star_label)

            progress_bar = QProgressBar()
            progress_bar.setObjectName("reviewRatingProgressBar")
            progress_bar.setRange(0, 100)

            color_map = {
                5: "#4CAF50",
                4: "#8BC34A",
                3: "#FFEB3B",
                2: "#FF9800",
                1: "#F44336",
            }

            progress_bar.setStyleSheet(f"""
                QProgressBar::chunk {{
                    background-color: {color_map[score]};
                }}
            """)

            row_layout.addWidget(progress_bar, 7)

            count_label = QLabel()
            count_label.setFixedWidth(40)
            count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(count_label)
            self.bars[score] = (progress_bar, count_label)

            right_layout.addLayout(row_layout)

        main_layout.addLayout(right_layout, stretch=3)


class RatingBarWidget(QWidget):
    def __init__(self, distribution: RatingDistribution, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.distribution = distribution
        self.ui = RatingBarWidgetUI()
        self.ui.setupUi(self)
        self.fill_ui()

    def fill_ui(self) -> None:
        average = self.distribution.average_score()
        self.ui.averageLabel.setText(f"{average:.1f}")
        self.ui.reviewsCountLabel.setText(f"{self.distribution.num_reviews} reviews")
        star_rating = StarRatingWidget(
            rating=average,
            max_rating=5,
            star_size=20,
            star_color_filled=QColor("#4CAF50"),
        )
        self.ui.summaryLayout.insertWidget(1, star_rating)

        for score, (bar, count) in self.ui.bars.items():
            bar.setValue(int(self.distribution.get_percentage(score)))
            count.setText(f"{self.distribution.get_count(score)}")
