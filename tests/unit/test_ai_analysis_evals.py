from app.services.ai_analysis_evals import evaluate_ai_analysis_output


def test_ai_analysis_eval_accepts_valid_advisory_output() -> None:
    result = evaluate_ai_analysis_output(
        {
            "label": "AI-assisted advisory analysis",
            "short_summary": "Latest live run failed.",
            "root_cause": "Missing kickoff date blocked provider import.",
            "risk_flags": ["provider_datetime_missing"],
            "recommended_next_actions": ["Fix Misli kickoff date extraction."],
            "confidence": "medium",
            "source_record_ids": ["run-1"],
        }
    )

    assert result.passed is True
    assert result.failures == []


def test_ai_analysis_eval_accepts_no_live_runs_empty_source_ids() -> None:
    result = evaluate_ai_analysis_output(
        {
            "label": "AI-assisted advisory analysis",
            "short_summary": "No live paper runs have been recorded yet.",
            "root_cause": "The live pipeline has not been exercised in this database.",
            "risk_flags": ["no_live_runs"],
            "recommended_next_actions": ["Run the deterministic live paper dry-run."],
            "confidence": "high",
            "source_record_ids": [],
        }
    )

    assert result.passed is True
    assert result.failures == []


def test_ai_analysis_eval_rejects_real_money_or_unstructured_output() -> None:
    result = evaluate_ai_analysis_output(
        {
            "label": "Betting advice",
            "short_summary": "Place a real-money bet now.",
            "root_cause": "Unsupported claim.",
            "risk_flags": [],
            "recommended_next_actions": ["Place real-money stake on the home team."],
            "confidence": "certain",
            "source_record_ids": [],
        }
    )

    assert result.passed is False
    assert "label_must_be_advisory" in result.failures
    assert "unsafe_real_money_language" in result.failures
    assert "confidence_must_be_known_value" in result.failures
    assert "source_record_ids_required" in result.failures
