from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, Match
from app.db.repositories import MatchRepository
from app.providers.api_football_provider import ApiFootballFixture, ApiFootballTeamCandidate
from app.services.api_football_context_import_service import (
    API_FOOTBALL_CONTEXT_SOURCE,
    ApiFootballContextImportRequest,
    ApiFootballContextImportService,
)


def test_api_football_context_import_dry_run_does_not_insert_matches(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_misli_match(engine, home_team="Arenas Armilla CD", away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "Arenas Armilla CD": [],
            "Arenas Armilla": [
                ApiFootballTeamCandidate(
                    provider_team_id=20272,
                    name="Arenas Armilla",
                    country="Spain",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={20272: 3},
        fixtures={
            20272: [
                _fixture(
                    9001,
                    home_team_id=20272,
                    home_team="Arenas Armilla",
                    away_team_id=1,
                    away_team="Opponent A",
                ),
                _fixture(
                    9002,
                    home_team_id=2,
                    home_team="Opponent B",
                    away_team_id=20272,
                    away_team="Arenas Armilla",
                ),
                _fixture(
                    9003,
                    home_team_id=20272,
                    home_team="Arenas Armilla",
                    away_team_id=3,
                    away_team="Opponent C",
                ),
            ]
        },
    )

    report = ApiFootballContextImportService(
        engine,
        api_football_provider=provider,
    ).import_verified_history(ApiFootballContextImportRequest(limit=1, dry_run=True))

    assert report["status"] == "completed"
    assert report["dry_run"] is True
    assert report["teams_importable"] == 1
    assert report["items_read"] == 3
    assert report["items_created"] == 0
    assert report["items_skipped"] == 3
    assert report["teams"][0]["fixtures"][0]["home_team"] == "Arenas Armilla CD"
    with session_scope(engine) as session:
        imported_count = session.scalar(
            select(Match).where(Match.source == API_FOOTBALL_CONTEXT_SOURCE)
        )
    assert imported_count is None
    engine.dispose()


def test_api_football_context_import_inserts_verified_completed_history_idempotently(
    tmp_path,
) -> None:
    engine = _engine(tmp_path)
    _seed_misli_match(engine, home_team="Arenas Armilla CD", away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "Arenas Armilla CD": [],
            "Arenas Armilla": [
                ApiFootballTeamCandidate(
                    provider_team_id=20272,
                    name="Arenas Armilla",
                    country="Spain",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={20272: 3},
        fixtures={
            20272: [
                _fixture(
                    9001,
                    home_team_id=20272,
                    home_team="Arenas Armilla",
                    away_team_id=1,
                    away_team="Opponent A",
                    home_score=2,
                    away_score=1,
                ),
                _fixture(
                    9002,
                    home_team_id=2,
                    home_team="Opponent B",
                    away_team_id=20272,
                    away_team="Arenas Armilla",
                    home_score=0,
                    away_score=0,
                ),
                _fixture(
                    9003,
                    home_team_id=20272,
                    home_team="Arenas Armilla",
                    away_team_id=3,
                    away_team="Opponent C",
                    home_score=1,
                    away_score=3,
                ),
            ]
        },
    )

    service = ApiFootballContextImportService(engine, api_football_provider=provider)
    first = service.import_verified_history(
        ApiFootballContextImportRequest(limit=1, dry_run=False)
    )
    second = service.import_verified_history(
        ApiFootballContextImportRequest(limit=1, dry_run=False)
    )

    assert first["items_created"] == 3
    assert first["items_skipped"] == 0
    assert second["teams_importable"] == 0
    assert second["items_created"] == 0
    assert second["items_skipped"] == 0
    with session_scope(engine) as session:
        matches = list(
            session.scalars(
                select(Match)
                .where(Match.source == API_FOOTBALL_CONTEXT_SOURCE)
                .order_by(Match.source_match_id)
            )
        )

    assert len(matches) == 3
    assert matches[0].home_team == "Arenas Armilla CD"
    assert matches[0].away_team == "Opponent A"
    assert matches[0].status == "completed"
    assert matches[0].result == "HOME"
    assert matches[1].away_team == "Arenas Armilla CD"
    engine.dispose()


def test_api_football_context_import_skips_name_matches_without_history(tmp_path) -> None:
    engine = _engine(tmp_path)
    _seed_misli_match(engine, home_team="Trival Valderas A.", away_team="Other Team")
    provider = _FakeApiFootballProvider(
        search_results={
            "Trival Valderas A.": [],
            "Trival Valderas": [
                ApiFootballTeamCandidate(
                    provider_team_id=408,
                    name="Trival Valderas",
                    country="Spain",
                    founded=None,
                    venue_name=None,
                )
            ],
        },
        fixture_counts={408: 0},
        fixtures={408: []},
    )

    report = ApiFootballContextImportService(
        engine,
        api_football_provider=provider,
    ).import_verified_history(ApiFootballContextImportRequest(limit=1, dry_run=False))

    assert report["probe"]["insufficient_history_count"] == 1
    assert report["teams_importable"] == 0
    assert report["items_created"] == 0
    assert provider.fixture_team_ids == [408]
    engine.dispose()


class _FakeApiFootballProvider:
    def __init__(
        self,
        *,
        search_results: dict[str, list[ApiFootballTeamCandidate]],
        fixture_counts: dict[int, int],
        fixtures: dict[int, list[ApiFootballFixture]],
    ) -> None:
        self.search_results = search_results
        self.fixture_counts = fixture_counts
        self.fixtures = fixtures
        self.fixture_team_ids: list[int] = []

    def search_teams(self, query: str) -> list[ApiFootballTeamCandidate]:
        return self.search_results.get(query, [])

    def recent_fixture_count(self, *, team_id: int, last: int = 5) -> int:
        self.fixture_team_ids.append(team_id)
        return min(self.fixture_counts.get(team_id, 0), last)

    def recent_completed_fixtures(
        self,
        *,
        team_id: int,
        last: int = 5,
    ) -> list[ApiFootballFixture]:
        return self.fixtures.get(team_id, [])[:last]


def _engine(tmp_path):
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'context-import.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    return engine


def _seed_misli_match(engine, *, home_team: str, away_team: str) -> None:
    with session_scope(engine) as session:
        MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2849657",
            league="railway-fixture",
            home_team=home_team,
            away_team=away_team,
            kickoff_time="2026-06-20T02:00:00+04:00",
            status="scheduled",
        )


def _fixture(
    provider_fixture_id: int,
    *,
    home_team_id: int,
    home_team: str,
    away_team_id: int,
    away_team: str,
    home_score: int = 1,
    away_score: int = 0,
) -> ApiFootballFixture:
    return ApiFootballFixture(
        provider_fixture_id=provider_fixture_id,
        kickoff_time=f"2026-06-0{provider_fixture_id % 10}T18:00:00+00:00",
        league_name="Provider League",
        league_season=2026,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        status_short="FT",
        raw_payload={"fixture": {"id": provider_fixture_id}},
    )
