from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.MapVersion import MapVersion
from src.api.models.Player import Player


class MapVersionReview(AbstractEntity):
    score:       int
    text:        str

    player:      Player | None     = Field(None)
    version:     MapVersion | None = Field(alias="mapVersion")
