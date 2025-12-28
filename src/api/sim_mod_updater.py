import logging

from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import DataApiAccessor

logger = logging.getLogger(__name__)


class SimModFiles(DataApiAccessor):
    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__('/data/modVersion')
        self.mod_url = ""
        self.wait_loop = QEventLoop()
        self.ready.connect(self.wait_loop.quit)

    def get_url_from_message(self, message: dict) -> str:
        self.mod_url = message["data"][0]["downloadUrl"]
        self.ready.emit()

    def request_and_get_sim_mod_url_by_id(self, uid: str) -> str:
        query_dict = {"filter": f"uid=={uid}"}
        self.get_by_query_parsed(query_dict, self.get_url_from_message, lambda _: self.ready.emit())
        self.wait_loop.exec()
        return self.mod_url
