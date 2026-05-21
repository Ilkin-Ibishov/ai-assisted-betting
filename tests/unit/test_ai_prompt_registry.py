from app.services.ai_prompt_registry import (
    COMPARISON_REPORT_PROMPT_VERSION,
    LIVE_STATUS_PROMPT_VERSION,
    PROVIDER_HEALTH_PROMPT_VERSION,
    build_comparison_report_prompt,
    build_live_status_prompt,
    build_provider_health_prompt,
)


def test_live_status_prompt_declares_safety_and_schema_contract() -> None:
    prompt = build_live_status_prompt(
        {
            "latest_run": {"run_id": "run-1", "status": "failed"},
            "latest_failure": {"run_id": "run-1", "error_summary": "missing kickoff date"},
            "open_paper_bets": 1,
            "settled_paper_bets": 0,
            "runs_count": 1,
            "errors_count": 1,
        }
    )

    assert prompt.version == LIVE_STATUS_PROMPT_VERSION
    assert "advisory" in prompt.system_message.lower()
    assert "real-money" in prompt.system_message.lower()
    assert "source_record_ids" in prompt.response_schema["required"]
    assert prompt.response_schema["properties"]["recommended_next_actions"]["type"] == "array"
    assert prompt.input_payload["latest_run"]["run_id"] == "run-1"


def test_comparison_report_prompt_declares_model_analysis_contract() -> None:
    prompt = build_comparison_report_prompt(
        {
            "report_name": "e0_compare",
            "metadata": {"league": "E0", "season": "2526"},
            "rankings": {"best_roi": {"model": "baseline_heuristic"}},
            "sample_size": {"smallest": 60, "largest": 62},
            "interpretation": "ROI disagrees with calibration winners.",
            "next_experiment": "Increase replay date range.",
        }
    )

    assert prompt.version == COMPARISON_REPORT_PROMPT_VERSION
    assert "calibration" in prompt.system_message.lower()
    assert "real-money" in prompt.system_message.lower()
    assert "source_record_ids" in prompt.response_schema["required"]
    assert prompt.response_schema["properties"]["risk_flags"]["type"] == "array"
    assert prompt.input_payload["report_name"] == "e0_compare"


def test_provider_health_prompt_declares_validation_analysis_contract() -> None:
    prompt = build_provider_health_prompt(
        {
            "provider": "misli_public",
            "runs_count": 2,
            "failed_runs_count": 1,
            "completed_runs_count": 1,
            "latest_failure": {
                "run_id": "failed-run",
                "error_summary": "full kickoff date missing",
            },
            "recent_failures": [],
        }
    )

    assert prompt.version == PROVIDER_HEALTH_PROMPT_VERSION
    assert "provider" in prompt.system_message.lower()
    assert "fail closed" in prompt.system_message.lower()
    assert "real-money" in prompt.system_message.lower()
    assert "source_record_ids" in prompt.response_schema["required"]
    assert prompt.input_payload["provider"] == "misli_public"
