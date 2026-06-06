import json

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import (
    AIAnalysisRun,
    Base,
    LiveSnapshot,
    Match,
    PaperJournalEntry,
    PaperRecommendation,
)
from app.db.repositories import LiveRunRepository
from app.services.production_behavior_service import ProductionBehaviorService


def test_production_behavior_reports_complete_fresh_loop(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'behavior-complete.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_completed_worker(engine)
    _seed_snapshot(engine)
    _seed_recommendation(engine)
    _seed_ai_review(engine, analysis_type="recommendation_review", analysis_id="review")
    threshold_review = _seed_ai_review(
        engine,
        analysis_type="recommendation_backtest_summary",
        analysis_id="threshold",
        output={"threshold_advice": {"overall_decision": "fail_closed"}},
    )
    _seed_journal(engine, source_ids=[f"ai_analysis:{threshold_review.id}"])

    status = ProductionBehaviorService(database_url).status(
        now_iso="2026-06-06T10:30:00+00:00",
        fresh_after_minutes=90,
    )

    assert status["overall_status"] == "ok"
    assert status["stages"]["worker"]["status"] == "fresh"
    assert status["stages"]["snapshot"]["status"] == "fresh"
    assert status["stages"]["recommendations"]["status"] == "available"
    assert status["stages"]["ai_review"]["status"] == "fresh"
    assert status["stages"]["threshold_review"]["status"] == "fresh"
    assert status["stages"]["journal"]["status"] == "fresh"
    assert status["stages"]["journal"]["threshold_overall_decision"] == "fail_closed"


def test_production_behavior_warns_when_threshold_review_missing(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'behavior-missing-threshold.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_completed_worker(engine)
    _seed_snapshot(engine)
    _seed_recommendation(engine)
    _seed_ai_review(engine, analysis_type="recommendation_review", analysis_id="review")
    _seed_journal(engine, source_ids=["ai_analysis:1"], threshold_decision="missing")

    status = ProductionBehaviorService(database_url).status(
        now_iso="2026-06-06T10:30:00+00:00",
        fresh_after_minutes=90,
    )

    assert status["overall_status"] == "warning"
    assert status["stages"]["threshold_review"]["status"] == "missing"
    assert status["stages"]["journal"]["threshold_overall_decision"] == "missing"
    assert "threshold_review" in status["attention_required"]


def _seed_completed_worker(engine) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="scheduled-worker-behavior",
            run_type="scheduled_paper_worker",
            provider="misli_public",
            model_name="baseline_heuristic",
        )
        run = repository.get_by_run_id("scheduled-worker-behavior")
        assert run is not None
        run.started_at = "2026-06-06T10:00:00+00:00"
        repository.complete(run_id="scheduled-worker-behavior", items_read=10, items_created=3)
        run = repository.get_by_run_id("scheduled-worker-behavior")
        assert run is not None
        run.started_at = "2026-06-06T10:00:00+00:00"
        run.finished_at = "2026-06-06T10:01:00+00:00"


def _seed_snapshot(engine) -> None:
    with session_scope(engine) as session:
        session.add(
            LiveSnapshot(
                provider="misli_public",
                snapshot_hash="snapshot-hash",
                source_url="https://example.com/misli",
                event_count=12,
                payload_json=json.dumps({"events": []}),
                created_at="2026-06-06T10:02:00+00:00",
            )
        )


def _seed_recommendation(engine) -> None:
    with session_scope(engine) as session:
        match = Match(
            source="misli_public",
            source_match_id="misli:football:behavior",
            league="Behavior League",
            home_team="Home",
            away_team="Away",
            kickoff_time="2026-06-06T12:00:00+04:00",
            status="scheduled",
        )
        session.add(match)
        session.flush()
        session.add(
            PaperRecommendation(
                match_id=match.id,
                prediction_id=None,
                source_run_id="scheduled-worker-behavior",
                source_match_id="misli:football:behavior",
                bookmaker="misli",
                market="1X2",
                selection="HOME",
                latest_snapshot_time="2026-06-06T10:02:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade="watch",
                status="active",
                model_probability=0.5,
                implied_probability=0.45,
                edge=0.05,
                confidence_score=0.4,
                model_confidence_score=0.4,
                recommendation_confidence_score=0.4,
                confidence_adjustment_reason=None,
                current_odds=2.2,
                expected_value=0.1,
                risk_flags_json="[]",
                rationale="seed behavior recommendation",
                created_at="2026-06-06T10:03:00+00:00",
            )
        )


def _seed_ai_review(
    engine,
    *,
    analysis_type: str,
    analysis_id: str,
    output: dict | None = None,
) -> AIAnalysisRun:
    payload = output or {"approval_state": "reject", "risk_flags": []}
    with session_scope(engine) as session:
        analysis = AIAnalysisRun(
            analysis_type=analysis_type,
            source_type="scheduled_worker",
            source_id=analysis_id,
            input_json="{}",
            output_json=json.dumps(payload),
            model_name="deterministic_ai_fallback",
            prompt_version="pytest",
            status="completed",
            created_at="2026-06-06T10:04:00+00:00",
        )
        session.add(analysis)
        session.flush()
        session.refresh(analysis)
        analysis_id_value = analysis.id
    with session_scope(engine) as session:
        loaded = session.get(AIAnalysisRun, analysis_id_value)
        assert loaded is not None
        return loaded


def _seed_journal(
    engine,
    *,
    source_ids: list[str],
    threshold_decision: str = "fail_closed",
) -> None:
    with session_scope(engine) as session:
        session.add(
            PaperJournalEntry(
                journal_date="2026-06-06",
                decision_state="no_candidates",
                summary_json=json.dumps(
                    {
                        "threshold_review": {
                            "overall_decision": threshold_decision,
                            "risk_flags": [],
                        }
                    }
                ),
                source_ids_json=json.dumps(source_ids),
                created_at="2026-06-06T10:05:00+00:00",
                updated_at="2026-06-06T10:05:00+00:00",
            )
        )
