from PyQt6.QtWidgets import QTextEdit

from src.replays.replaydetails.replayreader import ReplayParser


class ChatTab(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)

    def initialize(self, replay: ReplayParser) -> None:
        self.setText(replay.get_chat())
