from typing import Any

from app.providers.api_football_provider import ApiFootballProvider


def test_api_football_provider_parses_completed_fixture_payloads() -> None:
    provider = _FakeApiFootballProvider(
        {
            "response": [
                {
                    "fixture": {
                        "id": 123,
                        "date": "2026-06-01T18:00:00+00:00",
                        "status": {"short": "FT"},
                    },
                    "league": {"name": "Test League", "season": 2026},
                    "teams": {
                        "home": {"id": 10, "name": "Home FC"},
                        "away": {"id": 20, "name": "Away FC"},
                    },
                    "goals": {"home": 2, "away": 1},
                },
                {
                    "fixture": {
                        "id": 124,
                        "date": "2026-06-02T18:00:00+00:00",
                        "status": {"short": "NS"},
                    },
                    "league": {"name": "Test League", "season": 2026},
                    "teams": {
                        "home": {"id": 10, "name": "Home FC"},
                        "away": {"id": 30, "name": "Future FC"},
                    },
                    "goals": {"home": None, "away": None},
                },
            ]
        }
    )

    fixtures = provider.recent_completed_fixtures(team_id=10, last=2)

    assert len(fixtures) == 1
    assert fixtures[0].provider_fixture_id == 123
    assert fixtures[0].home_team == "Home FC"
    assert fixtures[0].away_team == "Away FC"
    assert fixtures[0].home_score == 2
    assert fixtures[0].away_score == 1
    assert fixtures[0].status_short == "FT"


class _FakeApiFootballProvider(ApiFootballProvider):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(api_key="test", min_interval_seconds=0)
        self.payload = payload

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        assert path == "/fixtures"
        assert params == {"team": "10", "last": "2"}
        return self.payload
