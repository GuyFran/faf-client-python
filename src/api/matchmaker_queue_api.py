import logging

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiAccessors import ParsedDataApiResponse
from src.api.models.MatchmakerQueue import MatchmakerQueue

logger = logging.getLogger(__name__)


class MatchmakerQueueApiConnector(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__('/data/matchmakerQueue')

    def convert_parsed(
        self,
        parsed: ParsedDataApiResponse,
    ) -> dict[str, list[MatchmakerQueue]]:
        assert isinstance(parsed["data"], list)
        return {"values": [MatchmakerQueue(**entry) for entry in parsed["data"]]}
