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


def test_external_context_probe_matches_live_suffix_and_transliteration_variants(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(
        engine,
        home_team="Rockdale Illinden U20",
        away_team="Other Team",
    )
    provider = _FakeApiFootballProvider(
        search_results={
            "Rockdale Illinden U20": [],
            "Rockdale Ilinden U20": [
                ApiFootballTeamCandidate(
                    provider_team_id=404,
                    name="Rockdale Ilinden",
                    country="Australia",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={404: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=1, minimum_history=3))

    assert "Rockdale Ilinden U20" in report["teams"][0]["query_variants"]
    assert report["teams"][0]["match_status"] == "matched"
    assert report["teams"][0]["top_candidates"][0]["name"] == "Rockdale Ilinden"
    assert report["teams"][0]["top_candidates"][0]["has_minimum_history"] is True
    engine.dispose()


def test_external_context_probe_uses_live_prefix_and_suffix_search_variants(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(
        engine,
        home_team="CF La Nucia",
        away_team="Trival Valderas A.",
    )
    provider = _FakeApiFootballProvider(
        search_results={
            "CF La Nucia": [],
            "La Nucia": [
                ApiFootballTeamCandidate(
                    provider_team_id=405,
                    name="La Nucia",
                    country="Spain",
                    founded=None,
                    venue_name=None,
                )
            ],
            "Trival Valderas A.": [],
            "Trival Valderas": [
                ApiFootballTeamCandidate(
                    provider_team_id=406,
                    name="Trival Valderas",
                    country="Spain",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={405: 5, 406: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=2, minimum_history=3))

    assert report["matched_count"] == 2
    assert "La Nucia" in report["teams"][0]["query_variants"]
    assert "Trival Valderas" in report["teams"][1]["query_variants"]
    engine.dispose()


def test_external_context_probe_scores_age_suffix_equivalents(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(
        engine,
        home_team="JK Tammeka Tartu U21",
        away_team="Other Team",
    )
    provider = _FakeApiFootballProvider(
        search_results={
            "JK Tammeka Tartu U21": [],
            "Tammeka Tartu U21": [],
            "JK Tammeka Tartu": [
                ApiFootballTeamCandidate(
                    provider_team_id=407,
                    name="Tammeka Tartu U19",
                    country="Estonia",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={407: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(ExternalContextProbeRequest(limit=1, minimum_history=3))

    assert report["teams"][0]["match_status"] == "matched"
    assert report["teams"][0]["top_candidates"][0]["name"] == "Tammeka Tartu U19"
    engine.dispose()


def test_external_context_probe_limits_fixture_history_calls_to_plausible_candidates(
    tmp_path,
) -> None:
    engine = _engine(tmp_path)
    _seed_unmatched_misli_match(engine, home_team="Qingdao Red Lions", away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "Qingdao Red Lions": [
                ApiFootballTeamCandidate(
                    provider_team_id=501,
                    name="Qingdao Red Lions",
                    country="China",
                    founded=None,
                    venue_name=None,
                ),
                ApiFootballTeamCandidate(
                    provider_team_id=502,
                    name="Unrelated City",
                    country="China",
                    founded=None,
                    venue_name=None,
                ),
                ApiFootballTeamCandidate(
                    provider_team_id=503,
                    name="Qingdao Youth",
                    country="China",
                    founded=None,
                    venue_name=None,
                ),
            ],
        },
        fixture_counts={501: 5, 502: 5, 503: 5},
    )

    report = ExternalContextProbeService(
        engine,
        api_football_provider=provider,
    ).probe(
        ExternalContextProbeRequest(
            limit=1,
            minimum_history=3,
            max_history_candidates_per_team=1,
        )
    )

    assert report["teams"][0]["match_status"] == "matched"
    assert provider.fixture_team_ids == [501]
    assert report["teams"][0]["top_candidates"][0]["recent_fixture_count"] == 5
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
        self.fixture_team_ids: list[int] = []

    def search_teams(self, query: str) -> list[ApiFootballTeamCandidate]:
        self.search_queries.append(query)
        return self.search_results.get(query, [])

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        self.fixture_team_ids.append(team_id)
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
            kickoff_time="2026-06-20T02:00:00+04:00",
            status="scheduled",
        )
