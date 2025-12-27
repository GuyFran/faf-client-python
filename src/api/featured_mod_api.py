import logging

from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import ParsedApiResponse
from src.api.models.FeaturedMod import FeaturedMod
from src.api.models.FeaturedModFile import FeaturedModFile

logger = logging.getLogger(__name__)


class FeaturedModApiConnector(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__("/data/featuredMod")

    def convert_parsed(
        self,
        parsed: ParsedApiResponse,
    ) -> dict[str, list[FeaturedMod]]:
        return {"values": [FeaturedMod(**modinfo) for modinfo in parsed["data"]]}

    def request_fmod_by_name(self, technical_name: str) -> None:
        queryDict = {"filter": f"technicalName=={technical_name}"}
        self.reply = self.requestData(queryDict)


class FeaturedModFilesApiConnector(DataApiAccessor):
    main_ready = pyqtSignal(dict)
    mod_ready = pyqtSignal(dict)

    def convert_parsed(
        self,
        parsed: ParsedApiResponse,
    ) -> dict[str, list[FeaturedModFile]]:
        return {"values": [FeaturedModFile(**file) for file in parsed["data"]]}

    def endpoint(self, mod_id: str, version: int | None = None) -> str:
        version_str = str(version) if version else "latest"
        return f"/featuredMods/{mod_id}/files/{version_str}"

    def get_main_files(self, mod_id: str, version: int | None = None) -> None:
        self.get_by_endpoint_converted(self.endpoint(mod_id, version), self.main_ready.emit)

    def get_mod_files(self, mod_id: str, version: int | None = None) -> None:
        self.get_by_endpoint_converted(self.endpoint(mod_id, version), self.mod_ready.emit)
