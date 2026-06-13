import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ApiFootballTeamCandidate:
    provider_team_id: int
    name: str
    country: str | None
    founded: int | None
    venue_name: str | None


class ApiFootballProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://v3.football.api-sports.io",
        timeout_seconds: int = 20,
    ) -> None:
        if not api_key:
            raise ValueError("API_FOOTBALL_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_teams(self, query: str) -> list[ApiFootballTeamCandidate]:
        payload = self._get_json("/teams", {"search": query})
        return [_team_candidate(item) for item in payload.get("response", [])]

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        payload = self._get_json("/fixtures", {"team": str(team_id), "last": str(last)})
        response = payload.get("response", [])
        return len(response) if isinstance(response, list) else 0

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "x-apisports-key": self.api_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def _team_candidate(item: dict[str, Any]) -> ApiFootballTeamCandidate:
    team = item.get("team") if isinstance(item.get("team"), dict) else {}
    venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
    return ApiFootballTeamCandidate(
        provider_team_id=int(team.get("id") or 0),
        name=str(team.get("name") or ""),
        country=str(team.get("country")) if team.get("country") else None,
        founded=int(team["founded"]) if team.get("founded") else None,
        venue_name=str(venue.get("name")) if venue.get("name") else None,
    )
