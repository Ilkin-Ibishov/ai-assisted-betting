import json
import time
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


@dataclass(frozen=True)
class ApiFootballFixture:
    provider_fixture_id: int
    kickoff_time: str
    league_name: str
    league_season: int | None
    home_team_id: int
    away_team_id: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status_short: str
    raw_payload: dict[str, Any]


class ApiFootballProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://v3.football.api-sports.io",
        timeout_seconds: int = 20,
        min_interval_seconds: float = 6.1,
    ) -> None:
        if not api_key:
            raise ValueError("API_FOOTBALL_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self._last_request_at = 0.0

    def search_teams(self, query: str) -> list[ApiFootballTeamCandidate]:
        payload = self._get_json("/teams", {"search": query})
        return [_team_candidate(item) for item in payload.get("response", [])]

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        payload = self._get_json("/fixtures", {"team": str(team_id), "last": str(last)})
        response = payload.get("response", [])
        return len(response) if isinstance(response, list) else 0

    def recent_completed_fixtures(
        self,
        *,
        team_id: int,
        last: int = 5,
    ) -> list[ApiFootballFixture]:
        payload = self._get_json("/fixtures", {"team": str(team_id), "last": str(last)})
        response = payload.get("response", [])
        if not isinstance(response, list):
            return []
        fixtures = [_fixture(item) for item in response]
        return [fixture for fixture in fixtures if fixture is not None]

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        self._pace_requests()
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

    def _pace_requests(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        now = time.monotonic()
        wait_seconds = self.min_interval_seconds - (now - self._last_request_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._last_request_at = time.monotonic()


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


def _fixture(item: dict[str, Any]) -> ApiFootballFixture | None:
    fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    goals = item.get("goals") if isinstance(item.get("goals"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}
    home_goals = goals.get("home")
    away_goals = goals.get("away")
    if not isinstance(home_goals, int) or not isinstance(away_goals, int):
        return None
    status_short = str(status.get("short") or "")
    if status_short not in {"FT", "AET", "PEN"}:
        return None
    provider_fixture_id = int(fixture.get("id") or 0)
    home_team_id = int(home.get("id") or 0)
    away_team_id = int(away.get("id") or 0)
    kickoff_time = str(fixture.get("date") or "")
    home_team = str(home.get("name") or "")
    away_team = str(away.get("name") or "")
    if not provider_fixture_id or not kickoff_time or not home_team_id or not away_team_id:
        return None
    if not home_team or not away_team:
        return None
    return ApiFootballFixture(
        provider_fixture_id=provider_fixture_id,
        kickoff_time=kickoff_time,
        league_name=str(league.get("name") or ""),
        league_season=int(league["season"]) if league.get("season") else None,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team=home_team,
        away_team=away_team,
        home_score=home_goals,
        away_score=away_goals,
        status_short=status_short,
        raw_payload=item,
    )
