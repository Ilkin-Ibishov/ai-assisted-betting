from typing import Any

from app.providers.sportmonks_provider import SportmonksProvider


def test_sportmonks_provider_parses_team_search_payload() -> None:
    provider = _FakeSportmonksProvider(
        {
            "data": [
                {
                    "id": 42,
                    "name": "Real Noroeste",
                    "country": {"name": "Brazil"},
                    "founded": 2008,
                    "venue": {"name": "Estadio Test"},
                }
            ]
        }
    )

    teams = provider.search_teams("Real Noroeste")

    assert len(teams) == 1
    assert teams[0].provider_team_id == 42
    assert teams[0].name == "Real Noroeste"
    assert teams[0].country == "Brazil"
    assert teams[0].founded == 2008
    assert teams[0].venue_name == "Estadio Test"


def test_sportmonks_provider_counts_completed_fixtures_only() -> None:
    provider = _FakeSportmonksProvider(
        {
            "data": [
                {"id": 1, "state": {"name": "Finished", "short_name": "FT"}},
                {"id": 2, "state": {"name": "Not Started", "short_name": "NS"}},
                {"id": 3, "state": {"name": "After Penalties", "short_name": "FT_PEN"}},
            ]
        }
    )

    count = provider.recent_fixture_count(team_id=42, last=5)

    assert count == 2


class _FakeSportmonksProvider(SportmonksProvider):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(api_token="test")
        self.payload = payload

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self.payload
