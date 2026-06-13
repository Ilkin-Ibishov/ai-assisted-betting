from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base
from app.db.repositories import MatchRepository
from app.services.feature_enrichment_audit_service import FeatureEnrichmentAuditService


def test_feature_enrichment_audit_reports_full_and_unmatched_coverage(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-audit.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_completed_history(engine)
    with session_scope(engine) as session:
        repository = MatchRepository(session)
        repository.add(
            source="misli_public",
            source_match_id="misli:football:covered",
            league="Azerbaijan Premier",
            home_team="Qarabag Agdam",
            away_team="Sabah FK",
            kickoff_time="2026-06-10T20:00:00+04:00",
            status="scheduled",
        )
        repository.add(
            source="misli_public",
            source_match_id="misli:football:cold",
            league="Azerbaijan Premier",
            home_team="Unknown Home",
            away_team="Unknown Away",
            kickoff_time="2026-06-10T22:00:00+04:00",
            status="scheduled",
        )

    report = FeatureEnrichmentAuditService(engine).report(
        now_iso="2026-06-09T00:00:00+00:00",
        source=None,
        source_match_id_prefix=None,
    )

    assert report["scheduled_matches"] == 2
    assert report["source"] is None
    assert report["source_match_id_prefix"] is None
    assert report["include_past"] is False
    assert report["full_enriched_candidates"] == 1
    assert report["cold_start_candidates"] == 1
    assert report["team_coverage"] == {
        "total_team_slots": 4,
        "matched_team_slots": 2,
        "unmatched_team_slots": 2,
    }
    assert {team["team"] for team in report["unmatched_teams"]} == {
        "Unknown Home",
        "Unknown Away",
    }
    covered_match = next(
        match for match in report["matches"] if match["source_match_id"] == "misli:football:covered"
    )
    assert covered_match["enrichment_tier"] == "full_enriched"
    assert covered_match["home"]["history_sources"] == ["football-data"]
    engine.dispose()


def test_feature_enrichment_audit_excludes_past_scheduled_rows_by_default(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-audit-past.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:old",
            league="Sample Premier",
            home_team="Old Home",
            away_team="Old Away",
            kickoff_time="2026-06-01T20:00:00+04:00",
            status="scheduled",
        )

    current_report = FeatureEnrichmentAuditService(engine).report(
        now_iso="2026-06-09T00:00:00+00:00"
    )
    historical_report = FeatureEnrichmentAuditService(engine).report(
        now_iso="2026-06-09T00:00:00+00:00",
        include_past=True,
    )

    assert current_report["scheduled_matches"] == 0
    assert historical_report["scheduled_matches"] == 1
    engine.dispose()


def test_feature_enrichment_audit_limits_after_excluding_past_rows(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-audit-limit.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        repository = MatchRepository(session)
        repository.add(
            source="misli_public",
            source_match_id="misli:football:old",
            league="Sample Premier",
            home_team="Old Home",
            away_team="Old Away",
            kickoff_time="2026-06-01T20:00:00+04:00",
            status="scheduled",
        )
        repository.add(
            source="misli_public",
            source_match_id="misli:football:future",
            league="Sample Premier",
            home_team="Future Home",
            away_team="Future Away",
            kickoff_time="2026-06-10T20:00:00+04:00",
            status="scheduled",
        )

    report = FeatureEnrichmentAuditService(engine).report(
        limit=1,
        now_iso="2026-06-09T00:00:00+00:00",
    )

    assert report["scheduled_matches"] == 1
    assert report["matches"][0]["source_match_id"] == "misli:football:future"
    engine.dispose()


def test_feature_enrichment_audit_defaults_to_misli_source(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-audit-source.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        repository = MatchRepository(session)
        repository.add(
            source="sample",
            source_match_id="sample-future",
            league="Sample Premier",
            home_team="Sample Home",
            away_team="Sample Away",
            kickoff_time="2026-06-10T20:00:00+04:00",
            status="scheduled",
        )
        repository.add(
            source="misli_public",
            source_match_id="misli:football:future",
            league="Sample Premier",
            home_team="Misli Home",
            away_team="Misli Away",
            kickoff_time="2026-06-10T21:00:00+04:00",
            status="scheduled",
        )

    report = FeatureEnrichmentAuditService(engine).report(
        now_iso="2026-06-09T00:00:00+00:00",
    )

    assert report["source"] == "misli_public"
    assert report["scheduled_matches"] == 1
    assert report["matches"][0]["source_match_id"] == "misli:football:future"
    engine.dispose()


def test_feature_enrichment_audit_defaults_to_real_misli_id_prefix(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-audit-prefix.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        repository = MatchRepository(session)
        repository.add(
            source="misli_public",
            source_match_id="task45-001",
            league="Sample Premier",
            home_team="Fixture Home",
            away_team="Fixture Away",
            kickoff_time="2026-06-10T20:00:00+04:00",
            status="scheduled",
        )
        repository.add(
            source="misli_public",
            source_match_id="misli:football:future",
            league="Sample Premier",
            home_team="Misli Home",
            away_team="Misli Away",
            kickoff_time="2026-06-10T21:00:00+04:00",
            status="scheduled",
        )

    report = FeatureEnrichmentAuditService(engine).report(
        now_iso="2026-06-09T00:00:00+00:00",
    )

    assert report["source_match_id_prefix"] == "misli:football:"
    assert report["scheduled_matches"] == 1
    assert report["matches"][0]["source_match_id"] == "misli:football:future"
    engine.dispose()


def _seed_completed_history(engine) -> None:
    with session_scope(engine) as session:
        repository = MatchRepository(session)
        for index, kickoff_time in enumerate(
            [
                "2026-06-08T20:00:00+04:00",
                "2026-06-04T20:00:00+04:00",
                "2026-06-01T20:00:00+04:00",
            ],
            start=1,
        ):
            repository.add(
                source="football-data",
                source_match_id=f"fd-home-{index}",
                league="Azerbaijan Premier",
                home_team="Qarabağ Ağdam",
                away_team=f"Home Opponent {index}",
                kickoff_time=kickoff_time,
                status="completed",
                home_score=2,
                away_score=0,
                result="HOME",
            )
            repository.add(
                source="football-data",
                source_match_id=f"fd-away-{index}",
                league="Azerbaijan Premier",
                home_team="Sabah F.K.",
                away_team=f"Away Opponent {index}",
                kickoff_time=kickoff_time,
                status="completed",
                home_score=1,
                away_score=1,
                result="DRAW",
            )
