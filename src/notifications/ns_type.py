from enum import Enum


class NsType(Enum):
    USER_ONLINE = "user_online"
    NEW_GAME = "new_game"
    GAME_FULL = "game_full"
    CUSTOM_GAME_LAUNCHED = "game_launched_custom"
    LADDER_GAME_LAUNCHED = "game_launched_ladder"
    LAUNCHING_LADDER = "launching_ladder"
    UNOFFICIAL_CLIENT = "unofficial_client"
    PARTY_INVITE = "party_invite"
