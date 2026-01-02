import logging

from PyQt6.QtCore import pyqtSignal

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiAccessors import ParsedDataApiResponse
from src.api.ApiBase import QueryOptions
from src.api.models.Player import Clan
from src.api.models.Player import ClanMembership
from src.api.models.Player import Player

logger = logging.getLogger(__name__)


class PlayerApiConnector(DataApiAccessor):
    alias_info = pyqtSignal(dict)
    player_ready = pyqtSignal(Player)

    def __init__(self) -> None:
        super().__init__('/data/player')

    def requestDataForAliasViewer(self, nameToFind: str) -> None:
        query: QueryOptions = {
            'include': 'names',
            'filter': '(login=="{name}",names.name=="{name}")'.format(
                name=nameToFind,
            ),
            'fields[player]': 'login,names',
            'fields[nameRecord]': 'name,changeTime,player',
        }
        self.get_parsed(query, self.alias_info.emit)

    def request_player(self, player_id: str) -> None:
        query: QueryOptions = {
            "include": "avatarAssignments.avatar,names,clanMembership.clan.memberships.player",
            "filter": f"id=={player_id}",
        }
        self.get_parsed(query, self.handle_player)

    def handle_player(self, message: ParsedDataApiResponse) -> None:
        player_dict, = message["data"]
        assert isinstance(player_dict, dict)
        player = Player(**player_dict)
        if "clan" in player_dict["clanMembership"]:
            clan = Clan(**player_dict["clanMembership"]["clan"])
            clan_membership = ClanMembership(**player_dict["clanMembership"])
            clan_membership.custom_clan = clan
            player.custom_clan_membership = clan_membership
        self.player_ready.emit(player)
