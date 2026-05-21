import json
from pathlib import Path
from typing import Any


class ComparisonAnalysisError(ValueError):
    pass


class ComparisonAnalysisService:
    def analyze_comparison_data(self, report_path: Path) -> dict[str, Any]:
        report = self._load_report(report_path)
        self._validate_report(report_path, report)
        metadata = report["metadata"]
        rankings = report["rankings"]
        runs = report["runs"]
        settled_counts = [int(run.get("settled_bets") or 0) for run in runs]
        min_settled = min(settled_counts)
        max_settled = max(settled_counts)
        interpretation = _interpret_winners(rankings)
        next_experiment = _next_experiment(settled_counts)
        warning = _sample_size_warning(settled_counts)
        text = _format_analysis_text(
            report_path=report_path,
            metadata=metadata,
            rankings=rankings,
            runs=runs,
            min_settled=min_settled,
            max_settled=max_settled,
            warning=warning,
            interpretation=interpretation,
            next_experiment=next_experiment,
        )
        return {
            "text": text,
            "sample_size": {
                "smallest": min_settled,
                "largest": max_settled,
                "warning": warning,
            },
            "interpretation": interpretation,
            "next_experiment": next_experiment,
        }

    def analyze_comparison_report(self, report_path: Path) -> str:
        return str(self.analyze_comparison_data(report_path)["text"])

    def _load_report(self, report_path: Path) -> dict[str, Any]:
        if not report_path.exists():
            raise ComparisonAnalysisError(f"{report_path} does not exist")
        try:
            loaded = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ComparisonAnalysisError(f"{report_path} is not valid JSON") from exc
        if not isinstance(loaded, dict):
            raise ComparisonAnalysisError(f"{report_path} must contain a JSON object")
        return loaded

    def _validate_report(self, report_path: Path, report: dict[str, Any]) -> None:
        for field in ["metadata", "rankings", "runs"]:
            if field not in report:
                raise ComparisonAnalysisError(
                    f"{report_path} missing required field: {field}"
                )
        if not isinstance(report["runs"], list) or not report["runs"]:
            raise ComparisonAnalysisError(f"{report_path} runs must be a non-empty list")


def _format_winner(winner: Any) -> str:
    if not isinstance(winner, dict):
        return "n/a"
    return f"{winner.get('model')} / {winner.get('bookmaker')} ({winner.get('value')})"


def _format_analysis_text(
    *,
    report_path: Path,
    metadata: dict[str, Any],
    rankings: dict[str, Any],
    runs: list[dict[str, Any]],
    min_settled: int,
    max_settled: int,
    warning: str,
    interpretation: str,
    next_experiment: str,
) -> str:
    return "\n".join(
        [
            "Comparison Analysis",
            "-------------------",
            f"Report: {report_path}",
            f"League: {metadata.get('league')}",
            f"Season: {metadata.get('season')}",
            f"Models: {', '.join(metadata.get('models', []))}",
            f"Bookmakers: {', '.join(metadata.get('bookmakers', []))}",
            f"Runs: {len(runs)}",
            "",
            "Winners",
            "-------",
            f"Best ROI: {_format_winner(rankings.get('best_roi'))}",
            f"Best Brier score: {_format_winner(rankings.get('best_brier_score'))}",
            f"Best log loss: {_format_winner(rankings.get('best_log_loss'))}",
            "",
            "Sample Size",
            "-----------",
            f"Smallest settled sample: {min_settled}",
            f"Largest settled sample: {max_settled}",
            f"Warning: {warning}",
            "",
            "Interpretation",
            "--------------",
            interpretation,
            "",
            "Next Experiment",
            "---------------",
            next_experiment,
        ]
    )


def _sample_size_warning(settled_counts: list[int]) -> str:
    if all(count < 300 for count in settled_counts):
        return "Result is exploratory and should not be trusted as evidence of an edge."
    if any(300 <= count < 500 for count in settled_counts):
        return "Result is directionally useful but still not conclusive."
    return "Sample is large enough for stronger comparison, but not proof of future profit."


def _winner_pair(winner: Any) -> tuple[object, object] | None:
    if not isinstance(winner, dict):
        return None
    return winner.get("model"), winner.get("bookmaker")


def _interpret_winners(rankings: dict[str, Any]) -> str:
    roi = _winner_pair(rankings.get("best_roi"))
    brier = _winner_pair(rankings.get("best_brier_score"))
    log_loss = _winner_pair(rankings.get("best_log_loss"))
    if (
        roi is not None
        and brier is not None
        and log_loss is not None
        and roi != brier
        and roi != log_loss
    ):
        return (
            "Best ROI disagrees with calibration winners; treat ROI as exploratory "
            "until sample size improves."
        )
    if brier is not None and brier == log_loss:
        return "Brier score and log loss agree on the strongest calibration run."
    return "Winners are mixed; compare larger samples before drawing conclusions."


def _next_experiment(settled_counts: list[int]) -> str:
    if any(count < 300 for count in settled_counts):
        return "Increase the replay date range or add leagues before drawing stronger conclusions."
    return "Compare additional bookmakers or model settings to test whether the result persists."
