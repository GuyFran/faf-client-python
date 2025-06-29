# TODO: fetch this from API

from enum import Enum
from typing import NamedTuple

# copied from the server code according to which
# this will need be fixed when the database
# gets migrated


class RatingType(Enum):
    GLOBAL = "global"
    LADDER = "ladder_1v1"
    TMM_2v2 = "tmm_2v2"
    TMM_3v3 = "tmm_3v3"
    TMM_4v4 = "tmm_4v4"

    @staticmethod
    def fromMatchmakerQueue(matchmakerQueueName):
        for ratingType in list(RatingType):
            if ratingType.value.replace("_", "") == matchmakerQueueName:
                return ratingType.value
        return RatingType.GLOBAL.value


# this is not from the server code. but it is weird
# that rating types and leaderboard names differ
# from matchmaker queue names


class MatchmakerQueueType(Enum):
    LADDER = "ladder1v1"
    TMM_2v2 = "tmm2v2"
    TMM_3v3 = "tmm3v3"
    TMM_4v4 = "tmm4v4"

    @staticmethod
    def from_rating_type(rating_type: str) -> str:
        for matchmaker_queue in list(MatchmakerQueueType):
            if rating_type.replace("_", "") == matchmaker_queue.value:
                return matchmaker_queue.value
        return MatchmakerQueueType.LADDER.value


class Rating(NamedTuple):
    mean: float
    deviation: float

    def displayed(self) -> float:
        return self.mean - 3 * self.deviation
