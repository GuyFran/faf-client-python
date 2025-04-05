from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.ModVersion import ModVersion
from src.api.models.Player import Player


class ModVersionReview(AbstractEntity):
    score:       int
    text:        str

    player:      Player | None     = Field(None)
    version:     ModVersion | None = Field(alias="modVersion")
