import json

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, Base, PaperCombination, PaperRecommendation
from app.db.repositories import LiveRunRepository, MatchRepository
from app.services.recommendation_quality_service import RecommendationQualityService


def test_quality_report_counts_actionable_watchlist_rejected_and_risk_flags(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'quality.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(engine, started_at="2026-06-03T13:30:00+00:00")
    _seed_recommendation(
        engine,
        source_match_id="match-action",
        grade="recommended",
        status="active",
        expected_value=0.24,
        confidence_score=0.62,
        risk_flags=["no_current_risk_flags"],
        created_at="2026-06-03T13:30:10+00:00",
        latest_snapshot_time="2026-06-03T13:29:30+00:00",
    )
    _seed_recommendation(
        engine,
        source_match_id="match-watch",
        grade="watch",
        status="active",
        expected_value=0.08,
        confidence_score=0.13,
        risk_flags=["low_confidence"],
        created_at="2026-06-03T13:30:11+00:00",
        latest_snapshot_time="2026-06-03T13:29:30+00:00",
    )
    _seed_recommendation(
        engine,
        source_match_id="match-reject",
        grade="reject",
        status="rejected",
        expected_value=-0.04,
        confidence_score=0.13,
        risk_flags=["negative_expected_value", "low_confidence"],
        created_at="2026-06-03T13:30:12+00:00",
        latest_snapshot_time="2026-06-03T13:29:30+00:00",
    )
    _seed_combination(engine, grade="recommended", status="active")
    _seed_ai_review(engine, approval_state="reject")

    report = RecommendationQualityService(database_url).report(now_iso="2026-06-03T13:35:00+00:00")

    assert report["overall_state"] == "actionable_present_ai_rejected"
    assert report["worker"]["latest_run_id"] == 1
    assert report["summary"]["total_recommendations"] == 3
    assert report["summary"]["actionable_count"] == 1
    assert report["summary"]["watchlist_count"] == 1
    assert report["summary"]["rejected_count"] == 1
    assert report["summary"]["created_since_latest_worker"] == 3
    assert report["summary"]["fresh_snapshot_count"] == 3
    assert report["risk_flags"]["low_confidence"] == 2
    assert report["risk_flags"]["negative_expected_value"] == 1
    assert report["distributions"]["expected_value"]["positive"] == 2
    assert report["distributions"]["confidence"]["medium"] == 1
    assert report["top_actionable"][0]["source_match_id"] == "match-action"
    assert report["top_blocked_positive_ev"][0]["source_match_id"] == "match-watch"
    assert report["combinations"]["total"] == 1
    assert report["ai_review"]["approval_state"] == "reject"
    engine.dispose()


def test_quality_report_counts_deduped_fresh_snapshot_rows_after_latest_worker(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'quality-deduped.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(engine, started_at="2026-06-03T14:00:00+00:00")
    _seed_recommendation(
        engine,
        source_match_id="match-deduped",
        grade="recommended",
        status="active",
        expected_value=0.18,
        confidence_score=0.58,
        risk_flags=["no_current_risk_flags"],
        created_at="2026-06-03T13:30:00+00:00",
        latest_snapshot_time="2026-06-03T13:59:30+00:00",
    )

    report = RecommendationQualityService(database_url).report(now_iso="2026-06-03T14:05:00+00:00")

    assert report["summary"]["created_since_latest_worker"] == 0
    assert report["summary"]["fresh_snapshot_count"] == 1
    assert report["summary"]["actionable_count"] == 1
    assert report["overall_state"] == "actionable_present"
    engine.dispose()


def test_quality_report_marks_watchlist_only_when_no_actionable_rows(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'quality-watch.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(engine, started_at="2026-06-03T14:00:00+00:00")
    _seed_recommendation(
        engine,
        source_match_id="match-watch",
        grade="watch",
        status="active",
        expected_value=0.05,
        confidence_score=0.13,
        risk_flags=["low_confidence"],
        created_at="2026-06-03T14:00:10+00:00",
        latest_snapshot_time="2026-06-03T14:00:00+00:00",
    )

    report = RecommendationQualityService(database_url).report(now_iso="2026-06-03T14:05:00+00:00")

    assert report["overall_state"] == "watchlist_only"
    assert report["summary"]["watchlist_count"] == 1
    assert report["summary"]["actionable_count"] == 0
    engine.dispose()


def test_quality_report_marks_all_rejected_when_no_active_positive_rows(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'quality-rejected.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(engine, started_at="2026-06-03T14:00:00+00:00")
    _seed_recommendation(
        engine,
        source_match_id="match-reject",
        grade="reject",
        status="rejected",
        expected_value=-0.05,
        confidence_score=0.13,
        risk_flags=["negative_expected_value"],
        created_at="2026-06-03T14:00:10+00:00",
        latest_snapshot_time="2026-06-03T14:00:00+00:00",
    )

    report = RecommendationQualityService(database_url).report(now_iso="2026-06-03T14:05:00+00:00")

    assert report["overall_state"] == "all_blocked"
    assert report["summary"]["rejected_count"] == 1
    assert report["top_actionable"] == []
    engine.dispose()


def _seed_worker_run(engine, *, started_at: str) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id=f"worker-{started_at}",
            run_type="scheduled_paper_worker",
            provider="misli_public",
            model_name="baseline_heuristic",
        )
        repository.complete(run_id=f"worker-{started_at}", items_read=3, items_created=1)
        run = repository.get_by_run_id(f"worker-{started_at}")
        assert run is not None
        run.started_at = started_at
        run.finished_at = started_at


def _seed_recommendation(
    engine,
    *,
    source_match_id: str,
    grade: str,
    status: str,
    expected_value: float,
    confidence_score: float,
    risk_flags: list[str],
    created_at: str,
    latest_snapshot_time: str,
) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=source_match_id,
            league="Sample Premier",
            home_team=f"Home {source_match_id}",
            away_team=f"Away {source_match_id}",
            kickoff_time="2026-06-03T20:00:00+04:00",
        )
        session.add(
            PaperRecommendation(
                match_id=match.id,
                source_match_id=source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection="HOME",
                latest_snapshot_time=latest_snapshot_time,
                model_name="baseline_heuristic",
                model_version="v0",
                grade=grade,
                status=status,
                model_probability=0.55,
                implied_probability=0.45,
                edge=0.1,
                confidence_score=confidence_score,
                current_odds=2.0,
                expected_value=expected_value,
                risk_flags_json=json.dumps(risk_flags),
                rationale="Seed recommendation",
                created_at=created_at,
            )
        )


def _seed_combination(engine, *, grade: str, status: str) -> None:
    with session_scope(engine) as session:
        session.add(
            PaperCombination(
                leg_recommendation_ids_json="[1]",
                leg_count=1,
                model_name="baseline_heuristic",
                model_version="v0",
                grade=grade,
                status=status,
                rank=1,
                combined_odds=2.0,
                estimated_probability=0.55,
                combined_expected_value=0.1,
                confidence_score=0.62,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Seed combination",
            )
        )


def _seed_ai_review(engine, *, approval_state: str) -> None:
    with session_scope(engine) as session:
        session.add(
            AIAnalysisRun(
                analysis_type="recommendation_review",
                source_type="paper_recommendations",
                source_id="latest",
                input_json="{}",
                output_json=json.dumps(
                    {
                        "approval_state": approval_state,
                        "short_summary": "Reviewed recommendations.",
                        "risk_flags": ["low_confidence_recommendations"],
                    }
                ),
                model_name="deterministic_ai_fallback",
                prompt_version="ai-recommendation-review-v1",
                status="completed",
            )
        )
