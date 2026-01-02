import logging
from collections.abc import Callable
from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict
from typing import cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkReply

from src.api.ApiBase import JsonApiBase
from src.api.ApiBase import QueryOptions
from src.api.ApiBase import _do_nothing

logger = logging.getLogger(__name__)


class ApiAccessor(JsonApiBase):
    def __init__(self, route: str = "") -> None:
        super().__init__(route)
        self.host_config_key = "api"


class UserApiAccessor(JsonApiBase):
    def __init__(self, route: str = "") -> None:
        super().__init__(route)
        self.host_config_key = "user_api"


class DataApiResourceObject(TypedDict):
    id: str
    type: str
    attributes: NotRequired[dict[str, Any]]
    relationships: NotRequired[dict[str, DataApiResponse]]


class DataApiResponse(TypedDict):
    data: DataApiResourceObject | list[DataApiResourceObject]
    included: NotRequired[list[DataApiResourceObject]]
    meta: NotRequired[dict[Literal["page"], dict[str, int]]]


class ParsedDataApiResponse(TypedDict):
    data: dict[str, Any] | list[dict[str, Any]]
    meta: NotRequired[dict[Literal["page"], dict[str, int]]]


class DataApiAccessor(ApiAccessor):
    data_ready = pyqtSignal(dict)

    def _handler_parsed(
        self,
        handler: Callable[[ParsedDataApiResponse], Any],
    ) -> Callable[[dict[str, Any]], None]:
        def handle(response: dict[str, Any]) -> None:
            handler(self.parse_message(cast(DataApiResponse, response)))
        return handle

    def get_parsed(
        self,
        query_or_path: QueryOptions | str,
        response_handler: Callable[[ParsedDataApiResponse], None],
        error_handler: Callable[[QNetworkReply], None] = _do_nothing,
    ) -> QNetworkReply:
        return self.get(
            query_or_path,
            self._handler_parsed(response_handler),
            error_handler,
        )

    def post_and_parse(
        self,
        endpoint: str,
        data: QByteArray,
        response_handler: Callable[[ParsedDataApiResponse], None] = _do_nothing,
        error_handler: Callable[[QNetworkReply], None] = _do_nothing,
    ) -> QNetworkReply:
        return self.post(
            endpoint,
            data,
            self._handler_parsed(response_handler),
            error_handler,
        )

    def _handler_converted(
        self,
        handler: Callable[[dict[str, Any]], None],
    ) -> Callable[[dict[str, Any]], None]:
        def handle(response: dict[str, Any]) -> None:
            handler(self.convert_parsed(self.parse_message(cast(DataApiResponse, response))))
        return handle

    def get_converted(
        self,
        query_or_path: QueryOptions | str,
        response_handler: Callable[[dict[str, Any]], None],
        error_handler: Callable[[QNetworkReply], None] = _do_nothing,
    ) -> QNetworkReply:
        return self.get(
            query_or_path,
            self._handler_converted(response_handler),
            error_handler,
        )

    def parse_message(self, message: DataApiResponse) -> ParsedDataApiResponse:
        included = self.parseIncluded(message)
        result: ParsedDataApiResponse = {"data": {}}
        result["data"] = self.parse_data(message, included)
        result["meta"] = self.parse_meta(message)
        return result

    def parseIncluded(self, message: DataApiResponse) -> dict[str, Any]:
        result: dict[str, Any] = {}
        relationships: list[tuple[str, str, str, DataApiResponse]] = []
        if "included" in message:
            for inc_item in message["included"]:
                if not inc_item["type"] in result:
                    result[inc_item["type"]] = {}
                if "attributes" in inc_item:
                    type_ = inc_item["type"]
                    id_ = inc_item["id"]
                    result[type_][id_] = inc_item["attributes"]
                if "relationships" in inc_item:
                    for key, value in inc_item["relationships"].items():
                        relationships.append((
                            inc_item["type"], inc_item["id"], key, value,
                        ))
            message.pop('included')
        # resolve relationships
        for r in relationships:
            result[r[0]][r[1]][r[2]] = self.parse_data(r[3], result)
        return result

    def parse_data(
        self,
        message: DataApiResponse,
        included: dict[str, Any],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        data = message["data"]
        if isinstance(data, list):
            return [self.parse_single(entry, included) for entry in data]
        else:
            return self.parse_single(data, included)

    def parse_single(
        self,
        data: DataApiResourceObject,
        included: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            if (
                data["type"] in included
                and data["id"] in included[data["type"]]
            ):
                result = included[data["type"]][data["id"]]
            result["id"] = data["id"]
            if "type" not in result:
                result["type"] = data["type"]
            if "attributes" in data:
                for key, value in data["attributes"].items():
                    result[key] = value
            if "relationships" in data:
                for key, value in data["relationships"].items():
                    result[key] = self.parse_data(value, included)
        except Exception as e:
            logger.error("Erorr parsing %s: %s", data, e)
        return result

    def parse_meta(self, message: DataApiResponse) -> dict[Literal["page"], dict[str, int]]:
        if "meta" in message:
            return message["meta"]
        return {"page": {}}

    def requestData(
        self,
        query_dict: QueryOptions | None = None,
        error_handler: Callable[[QNetworkReply], None] | None = None,
    ) -> QNetworkReply:
        query_dict = query_dict or {}
        if error_handler is None:
            return self.get_converted(query_dict, self.data_ready.emit)
        else:
            return self.get_converted(query_dict, self.data_ready.emit, error_handler)

    def convert_parsed(self, parsed: ParsedDataApiResponse) -> dict[str, Any]:
        raise NotImplementedError
