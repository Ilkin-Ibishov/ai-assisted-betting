from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base
from app.db.repositories import MatchRepository
from app.providers.api_football_provider import ApiFootballTeamCandidate
from app.services.external_context_probe_service import (
    ExternalContextProbeRequest,
    ExternalContextProbeService,
)


def test_external_context_probe_reports_missing_api_football_credentials(tmp_path) -> None:
    engine = _engine(tmp_path)

    report = ExternalContextProbeService(engine).probe(ExternalContextProbeRequest())

    assert report["status"] == "missing_credentials"
    assert report["required_env"] == "API_FOOTBALL_KEY"
    assert report["teams_read"] == 0
    engine.dispose()


def test_external_context_probe_matches_unmatched_misli_team_with_history(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(engine)
    provider = _FakeApiFootballProvider(
        search_results={
            "North Carolina FC": [
                ApiFootballTeamCandidate(
                    provider_team_id=101,
                    name="North Carolina FC",
                    country="USA",
                    founded=2006,
                    venue_name="WakeMed Soccer Park",
                )
            ],
            "Salem City FC": [
                ApiFootballTeamCandidate(
                    provider_team_id=202,
                    name="Salem City FC",
                    country="USA",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={101: 5, 202: 4},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=2, minimum_history=3))

    assert report["status"] == "completed"
    assert report["teams_read"] == 2
    assert report["matched_count"] == 2
    assert report["unmatched_count"] == 0
    assert report["teams"][0]["match_status"] == "matched"
    assert report["teams"][0]["top_candidates"][0]["has_minimum_history"] is True
    assert "North Carolina FC" in provider.search_queries
    assert "Salem City FC" in provider.search_queries
    engine.dispose()


def test_external_context_probe_marks_multiple_strong_candidates_ambiguous(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(engine, away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "North Carolina FC": [
                ApiFootballTeamCandidate(
                    provider_team_id=101,
                    name="North Carolina FC",
                    country="USA",
                    founded=None,
                    venue_name=None,
                ),
                ApiFootballTeamCandidate(
                    provider_team_id=102,
                    name="North Carolina FC",
                    country="USA",
                    founded=None,
                    venue_name=None,
                ),
            ],
            "Other Team": [],
        },
        fixture_counts={101: 5, 102: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=1, minimum_history=3))

    assert report["matched_count"] == 0
    assert report["ambiguous_count"] == 1
    assert report["teams"][0]["match_status"] == "ambiguous"
    engine.dispose()


def test_external_context_probe_uses_misli_query_variants(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(engine, home_team="Kolo Kolo", away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "Kolo Kolo": [],
            "Colo Colo": [
                ApiFootballTeamCandidate(
                    provider_team_id=303,
                    name="Colo Colo",
                    country="Chile",
                    founded=1925,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={303: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=1, minimum_history=3))

    assert "Colo Colo" in report["teams"][0]["query_variants"]
    assert report["teams"][0]["top_candidates"][0]["name"] == "Colo Colo"
    assert provider.search_queries[:2] == ["Kolo Kolo", "Colo Colo"]
    engine.dispose()


class _FakeApiFootballProvider:
    def __init__(
        self,
        *,
        search_results: dict[str, list[ApiFootballTeamCandidate]],
        fixture_counts: dict[int, int],
    ) -> None:
        self.search_results = search_results
        self.fixture_counts = fixture_counts
        self.search_queries: list[str] = []

    def search_teams(self, query: str) -> list[ApiFootballTeamCandidate]:
        self.search_queries.append(query)
        return self.search_results.get(query, [])

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        return min(self.fixture_counts.get(team_id, 0), last)


def _engine(tmp_path):
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'context-probe.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    return engine


def _seed_unmatched_misli_match(
    engine,
    *,
    home_team: str = "North Carolina FC",
    away_team: str = "Salem City FC",
) -> None:
    with session_scope(engine) as session:
        MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2847751",
            league="railway-fixture",
            home_team=home_team,
            away_team=away_team,
            kickoff_time="2026-06-14T02:00:00+04:00",
            status="scheduled",
        )
