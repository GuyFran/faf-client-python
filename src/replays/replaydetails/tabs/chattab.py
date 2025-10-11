from collections.abc import Generator
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QMenu
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings
from src.replays.replaydetails.helpers import seconds_to_human
from src.replays.replaydetails.replayreader import ReplayParser


class ChatTabUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)

        search_layout = QHBoxLayout()

        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText("Search text...")

        self.clearButton = QPushButton("Clear")

        search_layout.addWidget(self.searchInput)
        search_layout.addWidget(self.clearButton)

        search_layout.addStretch()

        search_layout.addWidget(QLabel("Show messages to: "))

        self.toAllCheckBox = QCheckBox("all")
        self.toAlliesCheckBox = QCheckBox("allies")
        self.toNotifyCheckBox = QCheckBox("notify")

        for btn in (
            self.toAllCheckBox,
            self.toAlliesCheckBox,
            self.toNotifyCheckBox,
        ):
            search_layout.addWidget(btn)
        search_layout.addStretch()

        self.alternateColorsCheckBox = QCheckBox("Alternate row colors")
        search_layout.addWidget(self.alternateColorsCheckBox)
        layout.addLayout(search_layout)

        self.chatTable = QTableWidget()
        self.chatTable.setVerticalScrollMode(self.chatTable.ScrollMode.ScrollPerPixel)
        self.chatTable.setEditTriggers(self.chatTable.EditTrigger.NoEditTriggers)
        self.chatTable.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.chatTable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.chatTable.horizontalHeader().setStretchLastSection(True)
        self.chatTable.setColumnCount(4)
        self.chatTable.setHorizontalHeaderLabels((
            "Time",
            "From",
            "To",
            "Message",
        ))
        layout.addWidget(self.chatTable)


class ChatTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.ui = ChatTabUI()
        self.ui.setupUi(self)
        self.ui.searchInput.textChanged.connect(self.search)
        self.ui.searchInput.returnPressed.connect(self.search_next)
        self.ui.clearButton.clicked.connect(self.ui.searchInput.clear)
        self.ui.chatTable.itemDoubleClicked.connect(self.on_chat_item_double_clicked)
        self.ui.chatTable.itemPressed.connect(self.on_chat_item_clicked)

        self.alternate_row_colors = Settings.get(
            "replaycard.chat/alternate_row_colors",
            default=True,
            type=bool,
        )
        self.ui.alternateColorsCheckBox.setChecked(self.alternate_row_colors)
        self.ui.chatTable.setAlternatingRowColors(self.alternate_row_colors)
        self.ui.alternateColorsCheckBox.checkStateChanged.connect(self.on_row_colors_alternation)

        self.visible_recipients = Settings.get_list(
            "replaycard.chat/visible_recipients",
            default=[True] * 3,
            type=bool,
        )
        self.message_filters = QButtonGroup()
        self.message_filters.setExclusive(False)
        for index, (chbx, visible) in enumerate(
            zip(
                (
                    self.ui.toAllCheckBox,
                    self.ui.toAlliesCheckBox,
                    self.ui.toNotifyCheckBox,
                ),
                self.visible_recipients,
            ),
        ):
            chbx.setChecked(visible)
            self.message_filters.addButton(chbx, index)
        self.message_filters.buttonToggled.connect(self.on_message_filter_changed)

        self._search_index = 0
        self._matching_items: list[QTableWidgetItem] = []

        self.chat_lines: list[tuple[int, str, str, str, int]] = []

    def initialize(self, replay: ReplayParser) -> None:
        self.chat_lines = replay.chatLine
        self.ui.searchInput.clear()
        self.ui.chatTable.clear()
        self.fill_chat()

    def fill_chat(self) -> None:
        self.ui.chatTable.setRowCount(len(self.chat_lines))
        btn_ids = {
            btn.text(): self.message_filters.id(btn)
            for btn in self.message_filters.buttons()
        }
        for row, line in enumerate(self.chat_lines):
            for col, elem in enumerate(line[:-1]):
                if col == 0:
                    text = seconds_to_human(cast(int, elem) // 10)
                else:
                    text = elem
                self.ui.chatTable.setItem(row, col, QTableWidgetItem(text))
                if col == 2:
                    hide = not self.visible_recipients[btn_ids[cast(str, text)]]
                    self.ui.chatTable.setRowHidden(row, hide)

    def _reset_search(self) -> None:
        self.ui.chatTable.setCurrentItem(None)
        self._matching_items.clear()
        self._search_index = 0

    def search(self, text: str) -> None:
        self._reset_search()

        if not text:
            return

        self._matching_items = [
            item for item in
            self.ui.chatTable.findItems(text, Qt.MatchFlag.MatchContains)
            if not self.ui.chatTable.isRowHidden(item.row())
        ]
        if self._matching_items:
            self.ui.chatTable.setCurrentItem(self._matching_items[0])

    def search_next(self) -> None:
        if not self._matching_items:
            if text := self.ui.searchInput.text():
                self.search(text)
            return
        modifiers = QApplication.keyboardModifiers()
        self._search_index += -1 if modifiers == Qt.KeyboardModifier.ShiftModifier else 1
        item = self._matching_items[self._search_index % len(self._matching_items)]
        self.ui.chatTable.setCurrentItem(item)

    def on_message_filter_changed(self, button: QCheckBox) -> None:
        self.visible_recipients[self.message_filters.id(button)] = button.isChecked()
        for row in range(self.ui.chatTable.rowCount()):
            if button.text() == self.chat_lines[row][2]:
                self.ui.chatTable.setRowHidden(row, not button.isChecked())
        self._reset_search()

    def on_row_colors_alternation(self, state: Qt.CheckState) -> None:
        alternate = state == Qt.CheckState.Checked
        self.ui.chatTable.setAlternatingRowColors(alternate)
        self.alternate_row_colors = alternate

    def save_settings(self) -> None:
        Settings.set("replaycard.chat/visible_recipients", self.visible_recipients)
        Settings.set("replaycard.chat/alternate_row_colors", self.alternate_row_colors)

    def on_chat_item_double_clicked(self, chat_item: QTableWidgetItem) -> None:
        if QApplication.mouseButtons() != Qt.MouseButton.LeftButton:
            return
        text_dialog = QDialog(self)
        timing, sender_login, to, *_ = self.chat_lines[chat_item.row()]
        title = f"[{seconds_to_human(timing // 10)}] {sender_login} to {to}"
        text_dialog.setWindowTitle(title)
        layout = QVBoxLayout(text_dialog)
        text_edit = QTextEdit(chat_item.text())
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        text_dialog.exec()
        text_dialog.deleteLater()

    def copy_text_in_selection(self) -> None:
        def _selected_text() -> Generator[str]:
            selection = self.ui.chatTable.selectedItems()
            if not selection:
                return
            for i, table_item in enumerate(selection[:-1]):
                if selection[i + 1].row() > table_item.row():
                    yield f"{table_item.text()}\n"
                else:
                    yield f"{table_item.text()};"
            yield selection[-1].text()

        clip = QApplication.clipboard()
        if clip is not None:
            clip.setText("".join(_selected_text()))

    def on_chat_item_clicked(self, _: QTableWidgetItem) -> None:
        if QApplication.mouseButtons() != Qt.MouseButton.RightButton:
            return
        menu = QMenu(self.ui.chatTable)
        action = QAction("Copy text", menu)
        action.triggered.connect(self.copy_text_in_selection)
        menu.addAction(action)
        menu.popup(QCursor.pos())
