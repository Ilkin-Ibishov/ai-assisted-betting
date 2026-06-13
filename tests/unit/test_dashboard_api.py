import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import create_api
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import (
    AIAnalysisRun,
    Base,
    LiveSnapshot,
    PaperCombination,
    PaperJournalEntry,
    PaperRecommendation,
    ResultFetchJob,
    ThresholdPolicyRun,
)
from app.db.repositories import (
    LiveRunRepository,
    MatchRepository,
    OddsSnapshotRepository,
    PaperBetRepository,
    PredictionRepository,
)
from app.services.ai_analysis_service import AIAnalysisService


def _write_comparison_report(
    reports_dir: Path,
    name: str,
    *,
    generated_at: str | None = None,
) -> Path:
    report_path = reports_dir / f"{name}_comparison.json"
    metadata = {
        "league": "E0",
        "season": "2526",
        "models": ["baseline_heuristic", "elo"],
        "bookmakers": ["B365", "Avg"],
        "parallel_workers": 2,
    }
    if generated_at is not None:
        metadata["generated_at"] = generated_at
    report_path.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.121333,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.244022,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.681137,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "total_bets": 60,
                        "settled_bets": 60,
                        "wins": 20,
                        "losses": 40,
                        "roi": 0.121333,
                        "profit_loss_units": 7.28,
                        "average_odds": 2.45,
                        "average_edge": 0.04,
                        "brier_score": 0.25,
                        "log_loss": 0.70,
                        "roi_rank": 1,
                        "brier_score_rank": 2,
                        "log_loss_rank": 2,
                        "model_config": {"model_name": "baseline_heuristic"},
                    },
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "total_bets": 62,
                        "settled_bets": 62,
                        "wins": 19,
                        "losses": 43,
                        "roi": 0.022097,
                        "profit_loss_units": 1.37,
                        "average_odds": 2.39,
                        "average_edge": 0.03,
                        "brier_score": 0.244022,
                        "log_loss": 0.681137,
                        "roi_rank": 4,
                        "brier_score_rank": 1,
                        "log_loss_rank": 1,
                        "model_config": {"model_name": "elo"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return report_path


def test_comparison_report_list_returns_dashboard_report_summaries(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_comparison_report(reports_dir, "e0_compare")
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons")

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "name": "e0_compare",
            "filename": "e0_compare_comparison.json",
            "league": "E0",
            "season": "2526",
            "models": ["baseline_heuristic", "elo"],
            "bookmakers": ["B365", "Avg"],
            "runs": 2,
            "modified_at": payload[0]["modified_at"],
            "total_settled_bets": 122,
            "best_roi": 0.121333,
            "best_brier_score": 0.244022,
            "best_log_loss": 0.681137,
            "sample_size_smallest": 60,
            "sample_size_largest": 62,
        }
    ]
    assert payload[0]["modified_at"].endswith("+00:00")


def test_api_cors_allows_railway_dashboard_origin(tmp_path: Path) -> None:
    client = TestClient(create_api(reports_dir=tmp_path))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://paper-dashboard-production.up.railway.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://paper-dashboard-production.up.railway.app"
    )


def test_health_endpoint_returns_service_status(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_favicon_endpoint_avoids_browser_probe_404s(tmp_path: Path) -> None:
    client = TestClient(create_api(reports_dir=tmp_path / "reports"))

    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_comparison_report_list_prefers_generated_at_for_modified_at(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_comparison_report(
        reports_dir,
        "e0_compare",
        generated_at="2026-05-18T20:24:46.522781+00:00",
    )
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons")

    assert response.status_code == 200
    assert response.json()[0]["modified_at"] == "2026-05-18T20:24:46.522781+00:00"


def test_comparison_report_list_hides_pytest_reports_unless_requested(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_comparison_report(reports_dir, "e0_compare")
    _write_comparison_report(reports_dir, "pytest_compare")
    client = TestClient(create_api(reports_dir=reports_dir))

    default_response = client.get("/api/reports/comparisons")
    debug_response = client.get("/api/reports/comparisons?include_test_reports=true")

    assert default_response.status_code == 200
    assert [report["name"] for report in default_response.json()] == ["e0_compare"]
    assert debug_response.status_code == 200
    assert [report["name"] for report in debug_response.json()] == [
        "e0_compare",
        "pytest_compare",
    ]


def test_comparison_detail_returns_report_with_structured_analysis(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_comparison_report(reports_dir, "e0_compare")
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons/e0_compare")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["league"] == "E0"
    assert payload["rankings"]["best_roi"]["model"] == "baseline_heuristic"
    assert len(payload["runs"]) == 2
    assert payload["analysis"]["sample_size"]["smallest"] == 60
    assert payload["analysis"]["sample_size"]["largest"] == 62
    assert "exploratory" in payload["analysis"]["sample_size"]["warning"]
    assert payload["analysis"]["next_experiment"].startswith("Increase the replay")


def test_comparison_detail_returns_legacy_report_when_analysis_is_unavailable(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "legacy_compare_comparison.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {"league": "E0"},
                "runs": [
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "settled_bets": 10,
                        "roi": 0.05,
                        "brier_score": 0.22,
                        "log_loss": 0.63,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons/legacy_compare")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["league"] == "E0"
    assert payload["runs"][0]["model"] == "elo"
    assert "analysis" not in payload
    assert "missing required field: rankings" in payload["analysis_error"]


def test_comparison_analysis_endpoint_returns_analysis_only(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_comparison_report(reports_dir, "e0_compare")
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons/e0_compare/analysis")

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"].startswith("Comparison Analysis")
    assert payload["sample_size"]["smallest"] == 60


def test_unknown_comparison_report_returns_404(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    client = TestClient(create_api(reports_dir=reports_dir))

    response = client.get("/api/reports/comparisons/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "comparison report not found: missing"


def test_live_status_endpoint_returns_empty_state(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/status")

    assert response.status_code == 200
    assert response.json() == {
        "latest_run": None,
        "latest_success": None,
        "latest_failure": None,
        "open_paper_bets": 0,
        "settled_paper_bets": 0,
        "runs_count": 0,
        "errors_count": 0,
    }


def test_live_enrichment_audit_endpoint_reports_unmatched_teams(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:cold",
            league="Sample Premier",
            home_team="Unknown Home",
            away_team="Unknown Away",
            kickoff_time="2026-06-10T20:00:00+04:00",
            status="scheduled",
        )
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/enrichment-audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled_matches"] == 1
    assert payload["cold_start_candidates"] == 1
    assert payload["team_coverage"]["unmatched_team_slots"] == 2
    assert {team["team"] for team in payload["unmatched_teams"]} == {
        "Unknown Home",
        "Unknown Away",
    }


def test_worker_status_endpoint_returns_latest_worker_freshness(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="scheduled-worker-api",
            run_type="scheduled_paper_worker",
            provider="misli_public",
        )
        repository.complete(run_id="scheduled-worker-api", items_read=3, items_created=1)
        live_run = repository.get_by_run_id("scheduled-worker-api")
        assert live_run is not None
        live_run.started_at = "2026-05-22T08:30:00+00:00"
        live_run.finished_at = "2026-05-22T08:31:00+00:00"
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/worker-status?fresh_after_minutes=60&now=2026-05-22T09:00:00+00:00"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fresh"
    assert payload["healthy"] is True
    assert payload["freshness_minutes"] == 29
    assert payload["latest_worker_run"]["run_id"] == "scheduled-worker-api"


def test_operational_guardrails_endpoint_reports_critical_ai_failure(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
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
                        "short_summary": "AI eval failed.",
                        "root_cause": "Unsafe output.",
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
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/operations/guardrails")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] == "critical"
    assert any(
        item["name"] == "ai_eval_safety" and item["severity"] == "critical"
        for item in payload["guardrails"]
    )


def test_production_behavior_endpoint_reports_complete_loop(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="scheduled-worker-behavior-api",
            run_type="scheduled_paper_worker",
            provider="misli_public",
        )
        worker = repository.get_by_run_id("scheduled-worker-behavior-api")
        assert worker is not None
        worker.started_at = "2026-06-06T10:00:00+00:00"
        repository.complete(run_id="scheduled-worker-behavior-api", items_read=10, items_created=3)
        worker = repository.get_by_run_id("scheduled-worker-behavior-api")
        assert worker is not None
        worker.started_at = "2026-06-06T10:00:00+00:00"
        worker.finished_at = "2026-06-06T10:01:00+00:00"
        session.add(
            LiveSnapshot(
                provider="misli_public",
                snapshot_hash="api-behavior-snapshot",
                source_url="https://example.com/misli",
                event_count=8,
                payload_json="{}",
                created_at="2026-06-06T10:02:00+00:00",
            )
        )
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:behavior-api",
            league="Behavior League",
            home_team="Home",
            away_team="Away",
            kickoff_time="2026-06-06T12:00:00+04:00",
            status="scheduled",
        )
        session.add(
            PaperRecommendation(
                match_id=match.id,
                prediction_id=None,
                source_run_id="scheduled-worker-behavior-api",
                source_match_id=match.source_match_id,
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
        threshold = AIAnalysisRun(
            analysis_type="recommendation_backtest_summary",
            source_type="scheduled_worker",
            source_id="threshold",
            input_json="{}",
            output_json=json.dumps({"threshold_advice": {"overall_decision": "fail_closed"}}),
            model_name="deterministic_ai_fallback",
            prompt_version="pytest",
            status="completed",
            created_at="2026-06-06T10:04:00+00:00",
        )
        session.add_all(
            [
                AIAnalysisRun(
                    analysis_type="recommendation_review",
                    source_type="scheduled_worker",
                    source_id="review",
                    input_json="{}",
                    output_json=json.dumps({"approval_state": "reject", "risk_flags": []}),
                    model_name="deterministic_ai_fallback",
                    prompt_version="pytest",
                    status="completed",
                    created_at="2026-06-06T10:04:00+00:00",
                ),
                threshold,
            ]
        )
        session.flush()
        session.add(
            PaperJournalEntry(
                journal_date="2026-06-06",
                decision_state="no_candidates",
                summary_json=json.dumps(
                    {"threshold_review": {"overall_decision": "fail_closed"}}
                ),
                source_ids_json=json.dumps([f"ai_analysis:{threshold.id}"]),
                created_at="2026-06-06T10:05:00+00:00",
                updated_at="2026-06-06T10:05:00+00:00",
            )
        )
        session.add(
            ThresholdPolicyRun(
                state="applied",
                decision="tighten",
                active=True,
                source_backtest_id=None,
                source_backtest_name="pytest_threshold_policy",
                sample_size=350,
                roi=-0.1,
                hit_rate=0.4,
                brier_score=0.3,
                log_loss=0.8,
                max_drawdown_units=-18.0,
                policy_values_json=json.dumps({"min_edge": 0.1}),
                rollback_policy_values_json=json.dumps({"min_edge": 0.07}),
                evidence_json=json.dumps({"sample_size": 350}),
                rationale="Applied test threshold policy.",
                risk_flags_json=json.dumps(["negative_singles_roi"]),
                applied_at="2026-06-06T10:04:30+00:00",
                created_at="2026-06-06T10:04:30+00:00",
                updated_at="2026-06-06T10:04:30+00:00",
            )
        )
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/operations/behavior?fresh_after_minutes=90&now=2026-06-06T10:30:00+00:00"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] == "ok"
    assert payload["stages"]["threshold_review"]["status"] == "fresh"
    assert payload["stages"]["threshold_policy"]["status"] == "applied"
    assert payload["stages"]["journal"]["threshold_overall_decision"] == "fail_closed"


def test_live_status_endpoint_returns_latest_success_failure_and_bet_counts(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_run"]["run_id"] == "failed-run"
    assert payload["latest_run"]["status"] == "failed"
    assert payload["latest_success"]["run_id"] == "completed-run"
    assert payload["latest_failure"]["run_id"] == "failed-run"
    assert payload["open_paper_bets"] == 1
    assert payload["settled_paper_bets"] == 1
    assert payload["runs_count"] == 2
    assert payload["errors_count"] == 2


def test_live_runs_endpoint_lists_recent_runs(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/runs")

    assert response.status_code == 200
    payload = response.json()
    assert [run["run_id"] for run in payload] == ["failed-run", "completed-run"]
    assert payload[0]["error_summary"] == "Missing match"


def test_live_run_detail_endpoint_returns_run_by_id(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/runs/completed-run")

    assert response.status_code == 200
    assert response.json()["run_id"] == "completed-run"
    assert response.json()["items_created"] == 3


def test_unknown_live_run_returns_404(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/runs/missing-run")

    assert response.status_code == 404
    assert response.json()["detail"] == "live run not found: missing-run"


def test_live_odds_movement_endpoint_returns_recent_movement(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_odds_movement_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/odds-movement?stale_after_minutes=100000")

    assert response.status_code == 200
    payload = response.json()
    by_selection = {item["selection"]: item for item in payload}
    assert by_selection["HOME"]["movement_direction"] == "up"
    assert by_selection["HOME"]["current_odds"] == 2.3
    assert by_selection["DRAW"]["movement_direction"] == "stable"
    assert by_selection["AWAY"]["movement_direction"] == "down"


def test_live_recommendations_endpoint_lists_persisted_recommendations(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_recommendation_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/recommendations")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["grade"] == "recommended"
    assert payload[0]["risk_flags"] == ["no_current_risk_flags"]
    assert payload[0]["source_match_id"] == "misli:football:2816300"
    assert payload[0]["model_confidence_score"] == 0.42
    assert payload[0]["recommendation_confidence_score"] == 0.72
    assert payload[0]["confidence_adjustment_reason"] == "high_ev_confidence_calibration"


def test_live_recommendations_endpoint_prefers_fresh_snapshot_over_refreshed_stale_row(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_mixed_freshness_recommendation_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/recommendations?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert [item["source_match_id"] for item in payload] == [
        "misli:football:fresh",
        "misli:football:stale",
    ]
    assert payload[0]["latest_snapshot_time"] == "2026-06-02T17:02:32+00:00"
    assert "stale_odds" not in payload[0]["risk_flags"]


def test_live_recommendation_quality_endpoint_reports_cycle_summary(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_recommendation_database(database_url)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/recommendation-quality",
        params={"now": "2026-05-18T08:05:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_recommendations"] >= 1
    assert payload["summary"]["actionable_count"] >= 1
    assert payload["top_actionable"][0]["grade"] == "recommended"
    assert "expected_value" in payload["distributions"]


def test_live_bet_ledger_endpoint_returns_default_fresh_rows(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_recommendation_database(database_url)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "status": "fresh",
            "date_range": "next_7_days",
            "now": "2026-05-18T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "rows" in payload
    assert payload["summary"]["fresh_count"] >= 1
    assert {row["state"] for row in payload["rows"]} == {"fresh"}
    assert {"model_probability", "implied_probability", "edge", "paper_profit_loss"}.issubset(
        payload["rows"][0].keys()
    )


def test_live_bet_ledger_endpoint_can_show_resulted_rows(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "status": "resulted",
            "date_range": "all",
            "now": "2026-06-20T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["resulted_count"] == 1
    assert payload["rows"][0]["outcome"] == "won"


def test_live_bet_ledger_endpoint_preserves_supplied_timezone_date_for_today(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="sample",
            source_match_id="match-local-today",
            league="Sample Premier",
            home_team="Local Morning",
            away_team="UTC Evening",
            kickoff_time="2026-05-29T20:30:00+04:00",
        )
        prediction = PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.55,
            bookmaker_probability=0.50,
            edge=0.05,
            confidence_score=None,
            decision="BET",
            reason="seed local-date paper bet",
        )
        PaperBetRepository(session).add(
            prediction_id=prediction.id,
            match_id=match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.0,
            stake_units=1.0,
            expected_value=0.1,
            status="open",
        )
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "status": "fresh",
            "date_range": "today",
            "now": "2026-05-29T00:30:00+04:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [row["source_match_id"] for row in payload["rows"]] == ["match-local-today"]


def test_live_bet_ledger_endpoint_rejects_invalid_status(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/bet-ledger", params={"status": "bogus"})

    assert response.status_code == 422


def test_live_bet_ledger_endpoint_rejects_invalid_date_range(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/bet-ledger", params={"date_range": "someday"})

    assert response.status_code == 422


def test_live_bet_ledger_endpoint_rejects_invalid_now(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/bet-ledger", params={"now": "not-a-date"})

    assert response.status_code == 422


def test_live_bet_ledger_endpoint_rejects_invalid_custom_from_date(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(
        create_api(reports_dir=tmp_path / "reports", database_url=database_url),
        raise_server_exceptions=False,
    )

    response = client.get(
        "/api/live/bet-ledger",
        params={"date_range": "custom", "from_date": "bad"},
    )

    assert response.status_code == 422


def test_live_bet_ledger_endpoint_rejects_invalid_custom_to_date(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(
        create_api(reports_dir=tmp_path / "reports", database_url=database_url),
        raise_server_exceptions=False,
    )

    response = client.get(
        "/api/live/bet-ledger",
        params={"date_range": "custom", "to_date": "bad"},
    )

    assert response.status_code == 422


def test_live_bet_ledger_endpoint_rejects_inverted_custom_date_range(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(
        create_api(reports_dir=tmp_path / "reports", database_url=database_url),
        raise_server_exceptions=False,
    )

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "date_range": "custom",
            "from_date": "2026-05-30",
            "to_date": "2026-05-29",
        },
    )

    assert response.status_code == 422


def test_live_paper_bets_endpoint_lists_open_bets_with_match_context(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/paper-bets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["status"] == "open"
    assert payload[0]["source_match_id"] == "match-001"
    assert payload[0]["match_label"] == "Northbridge FC vs Metro United"
    assert payload[0]["selection"] == "HOME"
    assert payload[0]["odds_taken"] == 2.0
    assert payload[0]["model_probability"] == 0.55
    assert payload[0]["risk_flags"] == ["no_current_risk_flags"]
    assert payload[0]["is_valid_open"] is True
    assert payload[1]["status"] == "won"


def test_live_paper_bets_endpoint_flags_unsafe_open_bets(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="sample",
            source_match_id="match-risky",
            league="Sample Premier",
            home_team="Old Town",
            away_team="Low Edge City",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        prediction = PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.40,
            bookmaker_probability=0.32,
            edge=0.08,
            confidence_score=0.35,
            decision="BET",
            reason="legacy unsafe paper bet",
        )
        PaperBetRepository(session).add(
            prediction_id=prediction.id,
            match_id=match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.2,
            stake_units=1.0,
            expected_value=-0.12,
            status="open",
        )
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/paper-bets")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["is_valid_open"] is False
    assert payload[0]["risk_flags"] == [
        "negative_expected_value",
        "low_confidence",
        "past_kickoff_open",
    ]


def test_live_result_jobs_endpoint_reports_pipeline_health(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        session.add(
            ResultFetchJob(
                match_id=match.id,
                source_match_id=match.source_match_id,
                misli_event_id="2816300",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                status="pending",
                next_attempt_at="2026-05-20T01:00:00+04:00",
                attempt_count=2,
                last_error="result not final",
            )
        )
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/result-jobs",
        params={"now": "2026-05-20T02:00:00+04:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "total": 1,
        "due": 1,
        "completed": 0,
        "postponed": 0,
        "failed": 0,
        "unresolvable": 0,
        "retention_miss": 0,
        "missing_score": 0,
        "pending": 1,
    }
    assert payload["jobs"][0]["source_match_id"] == "misli:football:2816300"
    assert payload["jobs"][0]["match_label"] == "Forest City vs Eastport Athletic"
    assert payload["jobs"][0]["diagnostic_reason"] is None


def test_live_combinations_endpoint_lists_ranked_paper_combinations(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_combination_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/combinations")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["rank"] == 1
    assert payload[0]["grade"] == "recommended"
    assert payload[0]["decision_weight"] == "experimental"
    assert payload[0]["leg_recommendation_ids"] == [1, 2]
    assert payload[0]["risk_flags"] == ["experimental_combination"]
    assert payload[0]["combined_expected_value"] == 0.19


def test_live_snapshot_endpoint_stores_and_serves_latest_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNAPSHOT_INGEST_TOKEN", "test-token")
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))
    snapshot = _valid_snapshot_payload()

    post_response = client.post(
        "/api/live/snapshots/latest/misli-public",
        headers={"Authorization": "Bearer test-token"},
        json=snapshot,
    )
    get_response = client.get("/api/live/snapshots/latest/misli-public")

    assert post_response.status_code == 200
    assert post_response.json()["provider"] == "misli_public"
    assert post_response.json()["event_count"] == 1
    assert get_response.status_code == 200
    assert get_response.json() == snapshot


def test_live_snapshot_post_requires_configured_bearer_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SNAPSHOT_INGEST_TOKEN", raising=False)
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    disabled_response = client.post(
        "/api/live/snapshots/latest/misli-public",
        headers={"Authorization": "Bearer test-token"},
        json=_valid_snapshot_payload(),
    )

    monkeypatch.setenv("SNAPSHOT_INGEST_TOKEN", "test-token")
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))
    invalid_response = client.post(
        "/api/live/snapshots/latest/misli-public",
        headers={"Authorization": "Bearer wrong-token"},
        json=_valid_snapshot_payload(),
    )

    assert disabled_response.status_code == 403
    assert invalid_response.status_code == 401


def test_admin_void_unsafe_paper_bets_requires_token_and_executes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNAPSHOT_INGEST_TOKEN", "test-token")
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    engine = create_engine_from_url(database_url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE paper_bets SET expected_value = -0.01"))
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    unauthorized = client.post("/api/admin/paper-bets/void-unsafe?dry_run=false")
    dry_run = client.post(
        "/api/admin/paper-bets/void-unsafe",
        headers={"Authorization": "Bearer test-token"},
    )
    execute = client.post(
        "/api/admin/paper-bets/void-unsafe?dry_run=false",
        headers={"Authorization": "Bearer test-token"},
    )

    assert unauthorized.status_code == 401
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    assert dry_run.json()["unsafe_count"] == 1
    assert dry_run.json()["risk_flag_counts"]["negative_expected_value"] == 1
    assert dry_run.json()["items_updated"] == 0
    assert execute.status_code == 200
    assert execute.json()["dry_run"] is False
    assert execute.json()["items_updated"] == 1
    engine = create_engine_from_url(database_url)
    with engine.connect() as connection:
        open_count = connection.execute(
            text("SELECT count(*) FROM paper_bets WHERE status = 'open'")
        ).scalar_one()
        void_count = connection.execute(
            text("SELECT count(*) FROM paper_bets WHERE status = 'void'")
        ).scalar_one()
    engine.dispose()
    assert open_count == 0
    assert void_count == 1


def test_ai_analysis_latest_endpoint_returns_latest_advisory(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    engine = create_engine_from_url(database_url)
    AIAnalysisService(engine).analyze_live_status()
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/analysis/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_type"] == "live_status_summary"
    assert payload["model_name"] == "deterministic_ai_fallback"
    assert payload["output"]["label"] == "AI-assisted advisory analysis"
    assert "failed-run" in payload["output"]["source_record_ids"]


def test_ai_recommendation_review_latest_endpoint_returns_latest_review(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_recommendation_database(database_url)
    engine = create_engine_from_url(database_url)
    AIAnalysisService(engine).analyze_recommendation_review()
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/recommendation-review/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_type"] == "recommendation_review"
    assert payload["output"]["approval_state"] == "caution"
    assert "confidence_calibrated_recommendations" in payload["output"]["risk_flags"]
    assert payload["output"]["source_record_ids"] == ["paper_recommendation:1"]


def test_ai_recommendation_review_latest_endpoint_returns_404_when_missing(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/recommendation-review/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "AI recommendation review not found"


def test_live_daily_journal_latest_endpoint_returns_latest(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        session.add(
            PaperJournalEntry(
                journal_date="2026-06-04",
                decision_state="candidate_ready",
                summary_json=json.dumps(
                    {
                        "journal_date": "2026-06-04",
                        "decision_state": "candidate_ready",
                        "summary": {"candidate_count": 1},
                        "quality_snapshot": {"overall_state": "actionable_present"},
                        "ai_review": {"approval_state": "approve"},
                        "settled_since_previous_journal": [],
                        "open_paper_bets": [],
                        "source_ids": ["paper_recommendation:1"],
                    }
                ),
                source_ids_json='["paper_recommendation:1"]',
                created_at="2026-06-04T10:00:00+00:00",
                updated_at="2026-06-04T10:00:00+00:00",
            )
        )
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/daily-journal/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["journal_date"] == "2026-06-04"
    assert payload["decision_state"] == "candidate_ready"
    assert payload["summary"]["candidate_count"] == 1
    assert payload["source_ids"] == ["paper_recommendation:1"]


def test_live_daily_journal_latest_endpoint_returns_404_when_missing(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/daily-journal/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "daily journal entry not found"


def test_ai_analysis_runs_endpoint_lists_recent_advisories(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    engine = create_engine_from_url(database_url)
    first = AIAnalysisService(engine).analyze_live_status()
    second = AIAnalysisService(engine).analyze_live_status()
    engine.dispose()
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/analysis/runs")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [second.id, first.id]
    assert payload[0]["output"]["label"] == "AI-assisted advisory analysis"


def test_ai_analysis_detail_endpoint_returns_404_for_missing_run(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/analysis/runs/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "AI analysis run not found: 999"


def _create_live_api_database(tmp_path: Path) -> str:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(exist_ok=True)
    database_url = f"sqlite:///{(tmp_path / 'api.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return database_url


def _seed_live_status_database(database_url: str) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        live_runs = LiveRunRepository(session)
        completed = live_runs.start(
            run_id="completed-run",
            run_type="collect_odds",
            provider="misli_public",
        )
        completed.started_at = "2026-05-19T10:00:00+00:00"
        live_runs.complete(
            run_id="completed-run",
            items_read=3,
            items_created=3,
        ).finished_at = "2026-05-19T10:01:00+00:00"
        failed = live_runs.start(
            run_id="failed-run",
            run_type="collect_results",
            provider="manual",
        )
        failed.started_at = "2026-05-19T11:00:00+00:00"
        live_runs.fail(
            run_id="failed-run",
            errors_count=2,
            error_summary="Missing match",
            items_read=2,
            items_skipped=2,
        ).finished_at = "2026-05-19T11:01:00+00:00"

        match = MatchRepository(session).add(
            source="sample",
            source_match_id="match-001",
            league="Sample Premier",
            home_team="Northbridge FC",
            away_team="Metro United",
            kickoff_time="2026-06-19T20:30:00+04:00",
        )
        predictions = PredictionRepository(session)
        home_prediction = predictions.add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.55,
            bookmaker_probability=0.50,
            edge=0.05,
            confidence_score=None,
            decision="BET",
            reason="seed open paper bet",
        )
        away_prediction = predictions.add(
            match_id=match.id,
            market="1X2",
            selection="AWAY",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.45,
            bookmaker_probability=0.40,
            edge=0.05,
            confidence_score=None,
            decision="BET",
            reason="seed settled paper bet",
        )
        PaperBetRepository(session).add(
            prediction_id=home_prediction.id,
            match_id=match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.0,
            stake_units=1.0,
            expected_value=0.1,
            status="open",
        )
        PaperBetRepository(session).add(
            prediction_id=away_prediction.id,
            match_id=match.id,
            market="1X2",
            selection="AWAY",
            odds_taken=2.5,
            stake_units=1.0,
            expected_value=0.2,
            status="won",
        )
    engine.dispose()


def _seed_odds_movement_database(database_url: str) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        odds = OddsSnapshotRepository(session)
        for selection, value in (("HOME", 2.1), ("DRAW", 3.1), ("AWAY", 3.0)):
            odds.add(
                match_id=match.id,
                source="misli_public",
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                odds_decimal=value,
                implied_probability=1 / value,
                snapshot_time="2026-05-19T11:00:00+00:00",
            )
        for selection, value in (("HOME", 2.3), ("DRAW", 3.1), ("AWAY", 2.8)):
            odds.add(
                match_id=match.id,
                source="misli_public",
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                odds_decimal=value,
                implied_probability=1 / value,
                snapshot_time="2026-05-19T12:00:00+00:00",
            )
    engine.dispose()


def _seed_recommendation_database(database_url: str) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        session.add(
            PaperRecommendation(
                match_id=match.id,
                source_match_id=match.source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection="HOME",
                latest_snapshot_time="2026-05-19T12:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade="recommended",
                status="active",
                model_probability=0.62,
                implied_probability=0.5,
                edge=0.12,
                confidence_score=0.72,
                model_confidence_score=0.42,
                recommendation_confidence_score=0.72,
                confidence_adjustment_reason="high_ev_confidence_calibration",
                current_odds=2.0,
                expected_value=0.24,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Positive edge is above recommendation threshold.",
            )
        )
    engine.dispose()


def _seed_mixed_freshness_recommendation_database(database_url: str) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        stale_match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:stale",
            league="Sample Premier",
            home_team="Old Home",
            away_team="Old Away",
            kickoff_time="2026-06-03T20:30:00+04:00",
        )
        fresh_match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:fresh",
            league="Sample Premier",
            home_team="Fresh Home",
            away_team="Fresh Away",
            kickoff_time="2026-06-03T22:30:00+04:00",
        )
        session.add_all(
            [
                PaperRecommendation(
                    match_id=fresh_match.id,
                    source_match_id=fresh_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-02T17:02:32+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="watch",
                    status="active",
                    model_probability=0.58,
                    implied_probability=0.5,
                    edge=0.08,
                    confidence_score=0.42,
                    current_odds=2.0,
                    expected_value=0.16,
                    risk_flags_json='["low_confidence"]',
                    rationale="Positive edge exists, but confidence is low.",
                    created_at="2026-06-02T17:02:33+00:00",
                ),
                PaperRecommendation(
                    match_id=stale_match.id,
                    source_match_id=stale_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-05-31T19:02:16+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="reject",
                    status="rejected",
                    model_probability=0.62,
                    implied_probability=0.5,
                    edge=0.12,
                    confidence_score=0.72,
                    current_odds=2.0,
                    expected_value=0.24,
                    risk_flags_json='["stale_odds"]',
                    rationale="Rejected because live odds/provider state is not healthy enough.",
                    created_at="2026-06-02T17:05:00+00:00",
                ),
            ]
        )
    engine.dispose()


def _seed_combination_database(database_url: str) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        recommendations = []
        for selection in ("HOME", "AWAY"):
            recommendation = PaperRecommendation(
                match_id=match.id,
                source_match_id=f"misli:football:2816300:{selection}",
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                latest_snapshot_time="2026-05-19T12:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade="recommended",
                status="active",
                model_probability=0.6,
                implied_probability=0.5,
                edge=0.1,
                confidence_score=0.7,
                current_odds=2.0,
                expected_value=0.2,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Seed recommendation",
            )
            session.add(recommendation)
            session.flush()
            recommendations.append(recommendation)
        session.add(
            PaperCombination(
                leg_recommendation_ids_json=json.dumps([item.id for item in recommendations]),
                leg_count=2,
                model_name="baseline_heuristic",
                model_version="v0",
                grade="recommended",
                status="active",
                rank=1,
                combined_odds=3.8,
                estimated_probability=0.313,
                combined_expected_value=0.19,
                confidence_score=0.7,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Seed combination",
            )
        )
    engine.dispose()


def _valid_snapshot_payload() -> dict:
    return {
        "source": "misli_public",
        "page_url": "https://www.misli.az/idman-novleri/futbol",
        "scraped_at": "2026-05-24T17:30:00.000Z",
        "event_count": 1,
        "events": [
            {
                "source": "misli_public",
                "sport": "football",
                "event_id": "2816300",
                "source_match_id": "misli:football:2816300",
                "home_team": "Forest City",
                "away_team": "Eastport Athletic",
                "kickoff_date": "24.05.2026",
                "kickoff_time": "20:30",
                "league": "Sample Premier",
                "odds": [
                    {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                    {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                ],
            }
        ],
    }
