import json

from sqlalchemy import select

from app.config import Settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, LiveRun, PaperRecommendation
from app.db.repositories import (
    LiveRunRepository,
    MatchRepository,
    OddsSnapshotRepository,
    PredictionRepository,
)
from app.services.recommendation_service import RecommendationService


def test_recommendation_service_persists_recommended_positive_edge(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.72)

    summary = RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    assert summary.items_read == 1
    assert summary.items_created == 1
    assert summary.errors_count == 0
    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "recommended"
    assert recommendation.status == "active"
    assert recommendation.edge == 0.12
    assert recommendation.expected_value > 0
    assert json.loads(recommendation.risk_flags_json) == ["no_current_risk_flags"]
    assert "Positive edge" in recommendation.rationale


def test_recommendation_service_rejects_negative_edge_without_silently_omitting(
    tmp_path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=-0.02, confidence=0.8)

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "edge_below_threshold" in json.loads(recommendation.risk_flags_json)
    assert "below threshold" in recommendation.rationale


def test_recommendation_service_rejects_stale_odds(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.8, snapshot_time="2026-05-19T10:00:00+00:00")

    RecommendationService(engine, _settings()).generate(stale_after_minutes=30)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "stale_odds" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_marks_low_confidence_candidate_as_watch(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.3)

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "watch"
    assert "low_confidence" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_rejects_when_provider_health_is_unhealthy(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.8)
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="failed-provider",
            run_type="collect_odds",
            provider="misli_public",
        )
        repository.fail(
            run_id="failed-provider",
            errors_count=1,
            error_summary="Misli snapshot contains no events; possible Misli parser drift",
        )

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))
        provider_run = session.scalar(select(LiveRun).where(LiveRun.run_id == "failed-provider"))

    assert provider_run is not None
    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "provider_health_warning" in json.loads(recommendation.risk_flags_json)


def _seed_candidate(
    engine,
    *,
    edge: float,
    confidence: float,
    snapshot_time: str = "2026-05-19T12:00:00+00:00",
) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        odds_decimal = 2.0
        OddsSnapshotRepository(session).add(
            match_id=match.id,
            source="misli_public",
            bookmaker="Misli.az",
            market="1X2",
            selection="HOME",
            odds_decimal=odds_decimal,
            implied_probability=1 / odds_decimal,
            snapshot_time=snapshot_time,
        )
        PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=(1 / odds_decimal) + edge,
            bookmaker_probability=1 / odds_decimal,
            edge=edge,
            confidence_score=confidence,
            decision="PENDING",
            reason="seed prediction",
        )


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        default_sport="football",
        default_market="1X2",
        default_stake_units=1.0,
        min_edge=0.07,
        min_odds=1.7,
        max_odds=3.5,
        feature_version="v0_baseline",
        model_name="baseline_heuristic",
        model_version="v0",
        elo_initial_rating=1500,
        elo_k_factor=20,
        elo_home_advantage=65,
        log_level="INFO",
        live_collection_enabled=True,
    )
