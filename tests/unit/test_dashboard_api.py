import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import create_api
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, Base, PaperCombination, PaperRecommendation
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


def test_health_endpoint_returns_service_status(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


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


def test_live_combinations_endpoint_lists_ranked_paper_combinations(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_combination_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/live/combinations")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["rank"] == 1
    assert payload[0]["grade"] == "recommended"
    assert payload[0]["leg_recommendation_ids"] == [1, 2]
    assert payload[0]["risk_flags"] == ["no_current_risk_flags"]
    assert payload[0]["combined_expected_value"] == 0.19


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
    assert payload["output"]["approval_state"] == "approve"
    assert payload["output"]["source_record_ids"] == ["paper_recommendation:1"]


def test_ai_recommendation_review_latest_endpoint_returns_404_when_missing(
    tmp_path: Path,
) -> None:
    database_url = _create_live_api_database(tmp_path)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get("/api/ai/recommendation-review/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "AI recommendation review not found"


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
            kickoff_time="2026-05-19T20:30:00+04:00",
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
                current_odds=2.0,
                expected_value=0.24,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Positive edge is above recommendation threshold.",
            )
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
