import logging

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import ParsedApiResponse

logger = logging.getLogger(__name__)


class MatchmakerQueueApiConnector(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__('/data/matchmakerQueue')

    def convert_parsed(
        self,
        parsed: ParsedApiResponse,
    ) -> dict[str, list[dict[str, str | int]]]:
        prepared_data = {"values": []}
        for queue in parsed["data"]:
            preparedQueue = {
                "technicalName": queue["technicalName"],
                "ratingType": queue["leaderboard"]["technicalName"],
                "id": queue["id"],
                "leaderboardId": queue["leaderboard"]["id"],
            }
            prepared_data["values"].append(preparedQueue)
        return prepared_data
