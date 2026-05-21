import json
from pathlib import Path

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.migrations import init_db
from app.db.models import AIAnalysisRun
from app.db.repositories import LiveRunRepository
from app.services.ai_analysis_service import AIAnalysisProvider, AIAnalysisService
from app.services.ai_prompt_registry import LiveStatusPrompt


def test_ai_analysis_service_records_deterministic_live_status_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine).analyze_live_status()

    assert analysis.analysis_type == "live_status_summary"
    assert analysis.source_type == "live_status"
    assert analysis.model_name == "deterministic_ai_fallback"
    assert analysis.prompt_version == "ai-live-status-v1"
    assert analysis.status == "completed"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "kickoff date" in output["root_cause"].lower()
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    assert output["source_record_ids"] == ["failed-run"]

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert stored.id == analysis.id
    assert "failed-run" in stored.input_json
    engine.dispose()


def test_ai_analysis_service_records_empty_live_status_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'empty-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_live_status()

    output = json.loads(analysis.output_json)
    assert output["short_summary"] == "No live paper runs have been recorded yet."
    assert output["risk_flags"] == ["no_live_runs"]
    assert output["recommended_next_actions"] == [
        "Run the deterministic live paper dry-run before enabling scheduling."
    ]
    engine.dispose()


def test_ai_analysis_service_uses_injected_provider_metadata(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'provider-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine, provider=RecordingProvider()).analyze_live_status()

    assert analysis.model_name == "custom_provider_model"
    assert analysis.prompt_version == "custom-live-status-v2"
    output = json.loads(analysis.output_json)
    assert output["short_summary"] == "Custom provider summary."
    assert output["source_record_ids"] == ["failed-run"]
    engine.dispose()


def test_ai_analysis_service_fails_closed_on_provider_eval_failure(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'unsafe-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine, provider=UnsafeProvider()).analyze_live_status()

    assert analysis.status == "failed"
    assert analysis.error_summary is not None
    assert "unsafe_real_money_language" in analysis.error_summary
    output = json.loads(analysis.output_json)
    assert output["risk_flags"] == ["ai_eval_failed"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    engine.dispose()


def test_ai_analysis_service_records_comparison_report_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'comparison-ai.sqlite').as_posix()}"
    init_db(database_url)
    report_path = tmp_path / "e0_compare_comparison.json"
    _write_comparison_report(report_path)
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_comparison_report(report_path)

    assert analysis.analysis_type == "model_comparison_summary"
    assert analysis.source_type == "comparison_report"
    assert analysis.source_id == "e0_compare"
    assert analysis.model_name == "deterministic_ai_fallback"
    assert analysis.prompt_version == "ai-comparison-report-v1"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "calibration" in output["root_cause"].lower()
    assert "small_sample_size" in output["risk_flags"]
    assert output["source_record_ids"] == ["e0_compare"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert stored.analysis_type == "model_comparison_summary"
    assert "baseline_heuristic" in stored.input_json
    engine.dispose()


def test_ai_analysis_service_records_provider_health_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'provider-health-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_provider_health_runs(engine)

    analysis = AIAnalysisService(engine).analyze_provider_health("misli_public")

    assert analysis.analysis_type == "provider_health_summary"
    assert analysis.source_type == "live_provider"
    assert analysis.source_id == "misli_public"
    assert analysis.prompt_version == "ai-provider-health-v1"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "Misli" in output["short_summary"]
    assert "provider_datetime_missing" in output["risk_flags"]
    assert output["source_record_ids"] == ["failed-provider-run", "completed-provider-run"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert "failed_runs_count" in stored.input_json
    engine.dispose()


def _seed_failed_misli_run(engine) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="failed-run",
            run_type="collect_odds",
            provider="misli_public",
            league="football",
            season="task48",
        )
        repository.fail(
            run_id="failed-run",
            errors_count=3,
            error_summary="Misli event requires a full kickoff date and time",
            items_read=3,
            items_skipped=3,
        )


def _seed_provider_health_runs(engine) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="completed-provider-run",
            run_type="collect_matches",
            provider="misli_public",
            league="football",
            season="task49",
        )
        repository.complete(
            run_id="completed-provider-run",
            items_read=21,
            items_created=20,
            items_skipped=1,
        )
        repository.start(
            run_id="failed-provider-run",
            run_type="collect_odds",
            provider="misli_public",
            league="football",
            season="task49",
        )
        repository.fail(
            run_id="failed-provider-run",
            errors_count=1,
            error_summary="Misli event requires a full kickoff date and time",
            items_read=21,
            items_created=60,
            items_skipped=1,
        )


def _write_comparison_report(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.12,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.24,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.68,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "settled_bets": 60,
                        "total_bets": 60,
                        "roi": 0.12,
                        "profit_loss_units": 7.2,
                        "brier_score": 0.25,
                        "log_loss": 0.7,
                        "model_config": {"model_name": "baseline_heuristic"},
                    },
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "settled_bets": 62,
                        "total_bets": 62,
                        "roi": 0.02,
                        "profit_loss_units": 1.37,
                        "brier_score": 0.24,
                        "log_loss": 0.68,
                        "model_config": {"model_name": "elo"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


class RecordingProvider(AIAnalysisProvider):
    model_name = "custom_provider_model"

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict:
        assert prompt.version == "ai-live-status-v1"
        return {
            "prompt_version": "custom-live-status-v2",
            "output": {
                "label": "AI-assisted advisory analysis",
                "short_summary": "Custom provider summary.",
                "root_cause": "Custom provider saw a failed run.",
                "risk_flags": ["live_run_failure"],
                "recommended_next_actions": ["Keep analysis paper-only."],
                "confidence": "medium",
                "source_record_ids": ["failed-run"],
            },
        }


class UnsafeProvider(AIAnalysisProvider):
    model_name = "unsafe_provider_model"

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict:
        return {
            "prompt_version": prompt.version,
            "output": {
                "label": "Betting advice",
                "short_summary": "Place a real-money bet now.",
                "root_cause": "Unsupported claim.",
                "risk_flags": [],
                "recommended_next_actions": ["Place real-money stake on the home team."],
                "confidence": "certain",
                "source_record_ids": [],
            },
        }
