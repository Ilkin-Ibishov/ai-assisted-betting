import json
from pathlib import Path

import pytest

from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService


def test_analyze_comparison_report_rejects_missing_file(tmp_path: Path) -> None:
    report_path = tmp_path / "missing.json"

    with pytest.raises(ComparisonAnalysisError) as exc_info:
        ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert str(report_path) in str(exc_info.value)
    assert "does not exist" in str(exc_info.value)


def test_analyze_comparison_report_requires_top_level_keys(tmp_path: Path) -> None:
    report_path = tmp_path / "comparison.json"
    report_path.write_text(json.dumps({"metadata": {}, "runs": []}), encoding="utf-8")

    with pytest.raises(ComparisonAnalysisError) as exc_info:
        ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert str(report_path) in str(exc_info.value)
    assert "missing required field: rankings" in str(exc_info.value)


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
                        "bookmaker": "B365",
                        "settled_bets": 59,
                        "total_bets": 59,
                        "roi": 0.114068,
                        "profit_loss_units": 6.73,
                        "brier_score": 0.25,
                        "log_loss": 0.70,
                        "roi_rank": 2,
                        "brier_score_rank": 3,
                        "log_loss_rank": 3,
                        "model_config": {"model_name": "baseline_heuristic"},
                    },
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "settled_bets": 62,
                        "total_bets": 62,
                        "roi": 0.022097,
                        "profit_loss_units": 1.37,
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


def test_analyze_comparison_report_formats_winners_and_sample_warning(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "comparison.json"
    _write_comparison_report(report_path)

    output = ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert "Comparison Analysis" in output
    assert f"Report: {report_path}" in output
    assert "League: E0" in output
    assert "Season: 2526" in output
    assert "Models: baseline_heuristic, elo" in output
    assert "Bookmakers: B365, Avg" in output
    assert "Runs: 2" in output
    assert "Best ROI: baseline_heuristic / Avg (0.121333)" in output
    assert "Best Brier score: elo / Avg (0.244022)" in output
    assert "Best log loss: elo / Avg (0.681137)" in output
    assert "Smallest settled sample: 59" in output
    assert "Largest settled sample: 62" in output
    assert "exploratory and should not be trusted as evidence of an edge" in output
