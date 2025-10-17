from __future__ import annotations

from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem

from src.api.models.Map import Map
from src.api.models.Mod import Mod


class VaultListItem[T: Map | Mod](QListWidgetItem):
    def __init__(self, parent: QListWidget, item_data: T) -> None:
        QListWidgetItem.__init__(self, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

    def should_be_visible(self) -> bool:
        return True

    def on_sort_type_changed(self, index: int) -> None:
        raise NotImplementedError

    def on_display_type_changed(self, index: int) -> None:
        raise NotImplementedError

    def set_display_type(self, index: int) -> None:
        raise NotImplementedError

    def _less_than(self, other: VaultListItem) -> bool:
        return True

    def should_be_hidden(self) -> bool:
        return not self.should_be_visible()

    def update_visibility(self) -> None:
        self.setHidden(self.should_be_hidden())

    def __ge__(self, other: QListWidgetItem) -> bool:
        return not self.__lt__(other)

    def __lt__(self, other: QListWidgetItem) -> bool:
        if not isinstance(other, VaultListItem):
            return QListWidgetItem.__lt__(self, other)
        return self._less_than(other)

    def _lt_date(self, other: VaultListItem) -> bool:
        if self.item_version.create_time == other.item_version.create_time:
            if self.item_version.update_time == other.item_version.update_time:
                return self._lt_alphabetical(other)
            return self.item_version.update_time < other.item_version.update_time
        return self.item_version.create_time < other.item_version.create_time

    def _lt_alphabetical(self, other: VaultListItem) -> bool:
        return self.item_data.display_name.lower() > other.item_data.display_name.lower()

    def _lt_rating(self, other: VaultListItem) -> bool:
        review = self.item_data.reviews_summary
        other_review = other.item_data.reviews_summary

        if review is None:
            return other_review is not None
        if other_review is None:
            return review is None

        if review.average_score == other_review.average_score:
            if review.num_reviews == other_review.num_reviews:
                return self._lt_alphabetical(other)
            return review.num_reviews < other_review.num_reviews

        return review.average_score < other_review.average_score
