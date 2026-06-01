import json

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, Base, PaperRecommendation
from app.db.repositories import LiveRunRepository, MatchRepository
from app.services.operational_guardrail_service import OperationalGuardrailService


def test_guardrails_warn_on_stale_worker_data(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-stale.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="worker-stale",
        status="completed",
        started_at="2026-05-22T07:00:00+00:00",
        finished_at="2026-05-22T07:01:00+00:00",
    )

    status = OperationalGuardrailService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        worker_fresh_after_minutes=60,
    )

    assert status["overall_status"] == "warning"
    assert _guardrail(status, "worker_freshness")["severity"] == "warning"
    assert _guardrail(status, "worker_freshness")["state"] == "stale"


def test_guardrails_mark_repeated_worker_failures_critical(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-failures.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    for index in range(3):
        _seed_worker_run(
            engine,
            run_id=f"worker-failed-{index}",
            status="failed",
            started_at=f"2026-05-22T08:0{index}:00+00:00",
            finished_at=f"2026-05-22T08:0{index}:30+00:00",
            error_summary="provider parser drift",
        )

    status = OperationalGuardrailService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        repeated_failure_threshold=3,
    )

    assert status["overall_status"] == "critical"
    assert _guardrail(status, "repeated_worker_failures")["severity"] == "critical"
    assert _guardrail(status, "repeated_worker_failures")["observed_value"] == 3


def test_guardrails_mark_unsafe_ai_eval_failure_critical(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-ai.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        session.add(
            AIAnalysisRun(
                analysis_type="recommendation_review",
                source_type="paper_recommendations",
                source_id="latest",
                input_json="{}",
                output_json=json.dumps(
                    {
                        "label": "AI-assisted advisory analysis",
                        "short_summary": "AI analysis failed safety or structure eval gates.",
                        "root_cause": "Provider output did not satisfy eval gates.",
                        "risk_flags": ["ai_eval_failed"],
                        "recommended_next_actions": ["Review provider output."],
                        "confidence": "high",
                        "source_record_ids": [],
                    }
                ),
                model_name="deterministic_ai_fallback",
                prompt_version="ai-recommendation-review-v1",
                status="failed",
                error_summary="unsafe_real_money_language",
            )
        )

    status = OperationalGuardrailService(database_url).status()

    assert status["overall_status"] == "critical"
    assert _guardrail(status, "ai_eval_safety")["severity"] == "critical"
    assert _guardrail(status, "ai_eval_safety")["state"] == "failed"


def test_guardrails_warn_on_empty_recommendation_cycle_after_fresh_worker(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-empty-recs.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="worker-fresh-empty",
        status="completed",
        started_at="2026-05-22T08:30:00+00:00",
        finished_at="2026-05-22T08:31:00+00:00",
    )

    status = OperationalGuardrailService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        worker_fresh_after_minutes=60,
    )

    assert status["overall_status"] == "warning"
    guardrail = _guardrail(status, "recommendation_output")
    assert guardrail["severity"] == "warning"
    assert guardrail["observed_value"] == 0


def test_guardrails_ok_when_worker_ai_and_recommendations_are_healthy(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-ok.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="worker-fresh-recs",
        status="completed",
        started_at="2026-05-22T08:30:00+00:00",
        finished_at="2026-05-22T08:31:00+00:00",
    )
    _seed_recommendation(engine, created_at="2026-05-22T08:32:00+00:00")

    status = OperationalGuardrailService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        worker_fresh_after_minutes=60,
    )

    assert status["overall_status"] == "ok"
    assert all(item["severity"] == "ok" for item in status["guardrails"])


def test_guardrails_count_recommendations_created_during_latest_worker_run(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guardrails-during-worker.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="worker-fresh-during-recs",
        status="completed",
        started_at="2026-05-22T08:30:00+00:00",
        finished_at="2026-05-22T08:31:00+00:00",
    )
    _seed_recommendation(engine, created_at="2026-05-22T08:30:30+00:00")

    status = OperationalGuardrailService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        worker_fresh_after_minutes=60,
    )

    assert status["overall_status"] == "ok"
    assert _guardrail(status, "recommendation_output")["observed_value"] == 1


def _guardrail(status: dict, name: str) -> dict:
    return next(item for item in status["guardrails"] if item["name"] == name)


def _seed_worker_run(
    engine,
    *,
    run_id: str,
    status: str,
    started_at: str,
    finished_at: str,
    error_summary: str | None = None,
) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id=run_id,
            run_type="scheduled_paper_worker",
            provider="misli_public",
            model_name="baseline_heuristic",
        )
        if status == "completed":
            repository.complete(run_id=run_id, items_read=3, items_created=1)
        else:
            repository.fail(
                run_id=run_id,
                errors_count=1,
                error_summary=error_summary or "worker failed",
            )
        live_run = repository.get_by_run_id(run_id)
        assert live_run is not None
        live_run.started_at = started_at
        live_run.finished_at = finished_at


def _seed_recommendation(engine, *, created_at: str) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-22T20:30:00+04:00",
        )
        recommendation = PaperRecommendation(
            match_id=match.id,
            source_match_id=match.source_match_id,
            bookmaker="Misli.az",
            market="1X2",
            selection="HOME",
            latest_snapshot_time=created_at,
            model_name="baseline_heuristic",
            model_version="v0",
            grade="recommended",
            status="active",
            model_probability=0.62,
            implied_probability=0.5,
            edge=0.12,
            confidence_score=0.72,
            current_odds=2.0,
            expected_value=0.24,
            risk_flags_json='["no_current_risk_flags"]',
            rationale="Seed recommendation",
            created_at=created_at,
        )
        session.add(recommendation)
