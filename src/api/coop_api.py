from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiAccessors import ParsedDataApiResponse
from src.api.ApiBase import QueryOptions
from src.api.models.CoopResult import CoopResult
from src.api.models.CoopScenario import CoopScenario


class CoopApiAccessor(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__("/data/coopScenario")

    def request_coop_scenarios(self) -> None:
        self.requestData({"include": "maps"})

    def convert_parsed(
        self,
        parsed: ParsedDataApiResponse,
    ) -> dict[str, list[CoopScenario]]:
        assert isinstance(parsed["data"], list)
        return {"values": [CoopScenario(**scenario) for scenario in parsed["data"]]}


class CoopResultApiAccessor(DataApiAccessor):
    def __init__(self) -> None:
        super().__init__("/data/coopResult")

    def prepare_query_options(self, mission: int) -> QueryOptions:
        return {
            "filter": f"mission=={mission}",
            "include": "game,game.playerStats.player",
            "sort": "duration",
            "page[size]": 1000,
        }

    def extend_filter(self, query_options: QueryOptions, filteroption: str) -> QueryOptions:
        cur_filters = query_options.get("filter", "")
        query_options["filter"] = ";".join((str(cur_filters), filteroption)).removeprefix(";")
        return query_options

    def request_coop_results(self, mission: int, player_count: int) -> None:
        default_query = self.prepare_query_options(mission)
        query = self.extend_filter(default_query, f"playerCount=={player_count}")
        self.requestData(query)

    def request_coop_results_general(self, mission: int) -> None:
        self.requestData(self.prepare_query_options(mission))

    def filter_unique_teams(self, results: list[CoopResult]) -> list[CoopResult]:
        unique_results: list[CoopResult] = []
        unique_teams: set[tuple[str, ...]] = set()
        for result in results:
            assert result.game is not None
            assert result.game.player_stats is not None
            player_ids = [
                player_stat.player.xd
                for player_stat in result.game.player_stats
                if player_stat.player is not None
            ]
            players_tuple = tuple(sorted(player_ids))
            if players_tuple not in unique_teams:
                unique_results.append(result)
            unique_teams.add(players_tuple)
        return unique_results

    def convert_parsed(
        self,
        parsed: ParsedDataApiResponse,
    ) -> dict[str, list[CoopResult]]:
        assert isinstance(parsed["data"], list)
        results = [CoopResult(**result) for result in parsed["data"]]
        distinct = self.filter_unique_teams(results)
        return {"values": distinct}
