import logging
from typing import Any

from PyQt6 import QtCore

from src.api.ApiBase import JsonApiBase

logger = logging.getLogger(__name__)

# FIXME: Make setting
WPAPI_ROOT = "/wp-json/wp/v2/posts?per_page={perpage}&page={page}&_embed=1"


class WPAPI(QtCore.QObject):
    newsDone = QtCore.pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.api = JsonApiBase()
        self.api.host_config_key = "news/host"

    def process_news(self, news: list[dict[str, Any]]) -> None:
        try:
            posts = [
                {
                    'title': post.get('title', {}).get('rendered'),
                    'body': post.get('content', {}).get('rendered'),
                    'date': post.get('date'),
                    'excerpt': post.get('excerpt', {}).get('rendered'),
                    'author': post.get('_embedded', {}).get('author'),
                    'link': post.get('link'),
                    'external_link': post.get('newshub_externalLinkUrl', ''),
                    'img_url': (
                        post.get('_embedded', {})
                        .get('wp:featuredmedia', [{}])[0]
                        .get('source_url', "")
                    ),
                } for post in news
            ]

            self.newsDone.emit(posts)
        except Exception:
            logger.exception("Error handling wp data")

    def download(self, page: int = 1, perpage: int = 10) -> None:
        path = WPAPI_ROOT.format(page=page, perpage=perpage)
        # news api returns list of json objects instead of json object
        # but JsonApiBase class is convenient, so we just smash ignore for now
        self.api.get(path, self.process_news)  # type: ignore[arg-type]
