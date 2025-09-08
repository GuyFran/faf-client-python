from typing import Any
from typing import TypedDict

from src.replays.replaydetails.tabs.gamestats_types import GameStats


class ParsedReplayHeader(TypedDict):
    patch: str
    version: str
    mods: dict[str, str]
    scenario_info: dict[str, Any]
    players: dict[int, str]
    observers: dict[int, str]
    armies: dict[int, dict[str, str | float]]
    random_seed: int


class _ConvertedCommands(TypedDict):
    tick: int
    cmd_type: int
    blueprint: str
    upgrades: dict[str, str] | None


class ParsedReplayBody(TypedDict):
    ticks: int
    commands: dict[int, tuple[_ConvertedCommands, ...]]
    points: list[tuple[int, float, float, int, int]]
    chatlines: tuple[tuple[int, str, str, str, int], ...]
    lasttick: dict[int, int]
    chart_data: dict[int, tuple[int, ...]]
    game_stats: GameStats


class ParsedReplay(TypedDict):
    header: ParsedReplayHeader
    body: ParsedReplayBody
