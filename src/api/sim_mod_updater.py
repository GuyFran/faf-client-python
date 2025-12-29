import logging

from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import ParsedApiResponse

logger = logging.getLogger(__name__)


class SimModFiles(DataApiAccessor):
    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__('/data/modVersion')
        self.mod_url = ""
        self.wait_loop = QEventLoop()
        self.ready.connect(self.wait_loop.quit)

    def get_url_from_message(self, message: ParsedApiResponse) -> None:
        assert isinstance(message["data"], list)
        try:
            self.mod_url = message["data"][0]["downloadUrl"]
        except IndexError:
            logger.warning("Mod was not found in the vault. Possibly custom and not uploaded")
        self.ready.emit()

    def request_and_get_sim_mod_url_by_id(self, uid: str) -> str:
        query_dict = {"filter": f"uid=={uid}"}
        self.get_by_query_parsed(query_dict, self.get_url_from_message, lambda _: self.ready.emit())
        self.wait_loop.exec()
        return self.mod_url
