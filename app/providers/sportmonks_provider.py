import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SportmonksTeamCandidate:
    provider_team_id: int
    name: str
    country: str | None
    founded: int | None
    venue_name: str | None


class SportmonksProvider:
    def __init__(
        self,
        *,
        api_token: str,
        base_url: str = "https://api.sportmonks.com/v3/football",
        timeout_seconds: int = 20,
    ) -> None:
        if not api_token:
            raise ValueError("SPORTMONKS_API_TOKEN is required")
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search_teams(self, query: str) -> list[SportmonksTeamCandidate]:
        payload = self._get_json("/teams/search/" + quote(query), {})
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return []
        return [_team_candidate(item) for item in rows]

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        payload = self._get_json(
            f"/fixtures/between/2000-01-01/2100-01-01/{team_id}",
            {"include": "scores", "per_page": str(max(1, min(last, 50)))},
        )
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return 0
        return min(
            last,
            sum(1 for item in rows if _is_completed_fixture(item)),
        )

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = {**params, "api_token": self.api_token}
        url = f"{self.base_url}{path}?{urlencode(query)}"
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def _team_candidate(item: dict[str, Any]) -> SportmonksTeamCandidate:
    return SportmonksTeamCandidate(
        provider_team_id=int(item.get("id") or 0),
        name=str(item.get("name") or ""),
        country=_country_name(item),
        founded=int(item["founded"]) if item.get("founded") else None,
        venue_name=_venue_name(item),
    )


def _country_name(item: dict[str, Any]) -> str | None:
    country = item.get("country") if isinstance(item.get("country"), dict) else None
    if country and country.get("name"):
        return str(country["name"])
    return str(item["country_name"]) if item.get("country_name") else None


def _venue_name(item: dict[str, Any]) -> str | None:
    venue = item.get("venue") if isinstance(item.get("venue"), dict) else None
    if venue and venue.get("name"):
        return str(venue["name"])
    return str(item["venue_name"]) if item.get("venue_name") else None


def _is_completed_fixture(item: dict[str, Any]) -> bool:
    state = item.get("state") if isinstance(item.get("state"), dict) else {}
    state_name = str(state.get("name") or item.get("state_name") or "").lower()
    if state_name in {"finished", "after extra time", "after penalties"}:
        return True
    state_short = str(state.get("short_name") or item.get("state_short_name") or "").upper()
    return state_short in {"FT", "AET", "FT_PEN"}
