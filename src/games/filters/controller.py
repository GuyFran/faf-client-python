from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton

from src.config import Settings
from src.games.filters.sortfiltermodel import CustomGameFilterModel


class GamesSortFilterController:
    apply_custom_filters = Settings.persisted_property(
        "play/applyCustomFilters",
        default_value=False,
        type=bool,
    )
    hide_private_games = Settings.persisted_property(
        "play/hidePrivateGames",
        default_value=False,
        type=bool,
    )
    hide_modded_games = Settings.persisted_property(
        "play/hideModdedGames",
        default_value=False,
        type=bool,
    )
    sort_games_index = Settings.persisted_property(
        "play/sortGames",
        default_value=0,
        type=int,
    )

    def __init__(
            self,
            game_filter_model: CustomGameFilterModel,
            games_shown: QLabel,
            apply_filters: QCheckBox,
            hide_private: QCheckBox,
            hide_modded: QCheckBox,
            filter_button: QPushButton,
            sort_combobox: QComboBox,
    ) -> None:
        self.gamesShownCountLabel = games_shown
        self.applyFiltersCheckBox = apply_filters
        self.hidePrivateGamesCheckBox = hide_private
        self.hideModdedGamesCheckBox = hide_modded
        self.sortGamesComboBox = sort_combobox

        self.game_filter_model = game_filter_model

        self.applyFiltersCheckBox.checkStateChanged.connect(self.toggle_filters)
        self.applyFiltersCheckBox.setChecked(self.apply_custom_filters)
        self.hidePrivateGamesCheckBox.checkStateChanged.connect(self.toggle_private_games)
        self.hidePrivateGamesCheckBox.setChecked(self.hide_private_games)
        self.hideModdedGamesCheckBox.checkStateChanged.connect(self.toggle_modded_games)
        self.hideModdedGamesCheckBox.setChecked(self.hide_modded_games)

        self.game_model = self.game_filter_model.sourceModel()
        self.game_model.dataChanged.connect(self.on_games_count_changed)

        self.manageGameFiltersButton = filter_button
        self.manageGameFiltersButton.clicked.connect(self.game_filter_model.manage_filters)

        self.sortGamesComboBox.addItems([
            "By Players",
            "By avg. Player Rating",
            "By Map",
            "By Host",
            "By Age",
        ])
        self.sortGamesComboBox.currentIndexChanged.connect(self.on_sort_games_combo_changed)

        if self.sort_games_index in self.game_filter_model.SortType:
            safe_sort_index = self.sort_games_index
        else:
            safe_sort_index = 0

        if self.sortGamesComboBox.currentIndex() == safe_sort_index:
            self.on_sort_games_combo_changed(safe_sort_index)
        else:
            self.sortGamesComboBox.setCurrentIndex(safe_sort_index)

    def on_games_count_changed(self) -> None:
        shown = self.game_filter_model.rowCount()
        total = self.game_filter_model.total_games()
        self.gamesShownCountLabel.setText(f"Games shown: {shown}/{total}")

    def toggle_filters(self, state: Qt.CheckState) -> None:
        self.apply_custom_filters = state == Qt.CheckState.Checked
        self.game_filter_model.apply_custom_filters = state == Qt.CheckState.Checked
        self.on_games_count_changed()

    def toggle_private_games(self, state: Qt.CheckState) -> None:
        self.hide_private_games = state == Qt.CheckState.Checked
        self.game_filter_model.hide_private_games = state == Qt.CheckState.Checked
        self.on_games_count_changed()

    def toggle_modded_games(self, state: Qt.CheckState) -> None:
        self.hide_modded_games = state == Qt.CheckState.Checked
        self.game_filter_model.hide_modded_games = state == Qt.CheckState.Checked
        self.on_games_count_changed()

    def on_sort_games_combo_changed(self, index: int) -> None:
        self.sort_games_index = index
        self.game_filter_model.sort_type = self.game_filter_model.SortType(index)
