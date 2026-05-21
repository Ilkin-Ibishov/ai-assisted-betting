import json
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import Engine, func, select

from app.db.engine import session_scope
from app.db.models import AIAnalysisRun, LiveRun, PaperBet
from app.services.ai_analysis_evals import evaluate_ai_analysis_output
from app.services.ai_prompt_registry import (
    COMPARISON_REPORT_PROMPT_VERSION,
    LIVE_STATUS_PROMPT_VERSION,
    PROVIDER_HEALTH_PROMPT_VERSION,
    ComparisonReportPrompt,
    LiveStatusPrompt,
    ProviderHealthPrompt,
    build_comparison_report_prompt,
    build_live_status_prompt,
    build_provider_health_prompt,
)
from app.services.analysis_service import ComparisonAnalysisService

DETERMINISTIC_AI_MODEL = "deterministic_ai_fallback"


class AIAnalysisProvider(Protocol):
    model_name: str

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict[str, Any]:
        pass

    def analyze_comparison_report(self, prompt: ComparisonReportPrompt) -> dict[str, Any]:
        pass

    def analyze_provider_health(self, prompt: ProviderHealthPrompt) -> dict[str, Any]:
        pass


class DeterministicAIAnalysisProvider:
    model_name = DETERMINISTIC_AI_MODEL

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict[str, Any]:
        return {
            "prompt_version": prompt.version,
            "output": _live_status_output(prompt.input_payload),
        }

    def analyze_comparison_report(self, prompt: ComparisonReportPrompt) -> dict[str, Any]:
        return {
            "prompt_version": prompt.version,
            "output": _comparison_report_output(prompt.input_payload),
        }

    def analyze_provider_health(self, prompt: ProviderHealthPrompt) -> dict[str, Any]:
        return {
            "prompt_version": prompt.version,
            "output": _provider_health_output(prompt.input_payload),
        }


class AIAnalysisService:
    def __init__(self, engine: Engine, provider: AIAnalysisProvider | None = None) -> None:
        self.engine = engine
        self.provider = provider or DeterministicAIAnalysisProvider()

    def analyze_live_status(self) -> AIAnalysisRun:
        with session_scope(self.engine) as session:
            latest_run = session.scalar(_ordered_live_runs().limit(1))
            latest_failure = session.scalar(
                _ordered_live_runs().where(LiveRun.status == "failed").limit(1)
            )
            open_bets = _paper_bet_count(session, ["open"])
            settled_bets = _paper_bet_count(session, ["won", "lost", "void"])
            runs_count = int(session.scalar(select(func.count()).select_from(LiveRun)) or 0)
            errors_count = int(
                session.scalar(select(func.coalesce(func.sum(LiveRun.errors_count), 0))) or 0
            )
            input_payload = {
                "latest_run": _live_run_input(latest_run),
                "latest_failure": _live_run_input(latest_failure),
                "open_paper_bets": open_bets,
                "settled_paper_bets": settled_bets,
                "runs_count": runs_count,
                "errors_count": errors_count,
            }
            provider_result = self.provider.analyze_live_status(
                build_live_status_prompt(input_payload)
            )
            output_payload = provider_result["output"]
            eval_result = evaluate_ai_analysis_output(output_payload)
            status = "completed"
            error_summary = None
            if not eval_result.passed:
                status = "failed"
                error_summary = ", ".join(eval_result.failures)
                output_payload = _failed_eval_output(input_payload, eval_result.failures)
            analysis = AIAnalysisRun(
                analysis_type="live_status_summary",
                source_type="live_status",
                source_id=latest_run.run_id if latest_run is not None else "empty",
                input_json=json.dumps(input_payload, sort_keys=True),
                output_json=json.dumps(output_payload, sort_keys=True),
                model_name=self.provider.model_name,
                prompt_version=str(
                    provider_result.get("prompt_version", LIVE_STATUS_PROMPT_VERSION)
                ),
                status=status,
                error_summary=error_summary,
            )
            session.add(analysis)
            session.flush()
            return analysis

    def analyze_provider_health(self, provider: str) -> AIAnalysisRun:
        input_payload = _provider_health_input(self.engine, provider)
        provider_result = self.provider.analyze_provider_health(
            build_provider_health_prompt(input_payload)
        )
        output_payload = provider_result["output"]
        eval_result = evaluate_ai_analysis_output(output_payload)
        status = "completed"
        error_summary = None
        if not eval_result.passed:
            status = "failed"
            error_summary = ", ".join(eval_result.failures)
            output_payload = _failed_eval_output(input_payload, eval_result.failures)
        with session_scope(self.engine) as session:
            analysis = AIAnalysisRun(
                analysis_type="provider_health_summary",
                source_type="live_provider",
                source_id=provider,
                input_json=json.dumps(input_payload, sort_keys=True),
                output_json=json.dumps(output_payload, sort_keys=True),
                model_name=self.provider.model_name,
                prompt_version=str(
                    provider_result.get("prompt_version", PROVIDER_HEALTH_PROMPT_VERSION)
                ),
                status=status,
                error_summary=error_summary,
            )
            session.add(analysis)
            session.flush()
            return analysis

    def analyze_comparison_report(self, report_path: Path) -> AIAnalysisRun:
        input_payload = _comparison_report_input(report_path)
        provider_result = self.provider.analyze_comparison_report(
            build_comparison_report_prompt(input_payload)
        )
        output_payload = provider_result["output"]
        eval_result = evaluate_ai_analysis_output(output_payload)
        status = "completed"
        error_summary = None
        if not eval_result.passed:
            status = "failed"
            error_summary = ", ".join(eval_result.failures)
            output_payload = _failed_eval_output(input_payload, eval_result.failures)
        with session_scope(self.engine) as session:
            analysis = AIAnalysisRun(
                analysis_type="model_comparison_summary",
                source_type="comparison_report",
                source_id=input_payload["report_name"],
                input_json=json.dumps(input_payload, sort_keys=True),
                output_json=json.dumps(output_payload, sort_keys=True),
                model_name=self.provider.model_name,
                prompt_version=str(
                    provider_result.get(
                        "prompt_version",
                        COMPARISON_REPORT_PROMPT_VERSION,
                    )
                ),
                status=status,
                error_summary=error_summary,
            )
            session.add(analysis)
            session.flush()
            return analysis


def _ordered_live_runs():
    return select(LiveRun).order_by(LiveRun.started_at.desc(), LiveRun.id.desc())


def _paper_bet_count(session, statuses: list[str]) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(PaperBet).where(PaperBet.status.in_(statuses))
        )
        or 0
    )


def _live_run_input(live_run: LiveRun | None) -> dict[str, Any] | None:
    if live_run is None:
        return None
    return {
        "run_id": live_run.run_id,
        "run_type": live_run.run_type,
        "provider": live_run.provider,
        "league": live_run.league,
        "season": live_run.season,
        "status": live_run.status,
        "items_read": live_run.items_read,
        "items_created": live_run.items_created,
        "items_updated": live_run.items_updated,
        "items_skipped": live_run.items_skipped,
        "errors_count": live_run.errors_count,
        "error_summary": live_run.error_summary,
    }


def _live_status_output(input_payload: dict[str, Any]) -> dict[str, Any]:
    latest_run = input_payload["latest_run"]
    latest_failure = input_payload["latest_failure"]
    if latest_run is None:
        return {
            "label": "AI-assisted advisory analysis",
            "short_summary": "No live paper runs have been recorded yet.",
            "root_cause": "The live pipeline has not been exercised in this database.",
            "risk_flags": ["no_live_runs"],
            "recommended_next_actions": [
                "Run the deterministic live paper dry-run before enabling scheduling."
            ],
            "confidence": "high",
            "source_record_ids": [],
        }

    risk_flags: list[str] = []
    recommended_actions = [
        "Keep AI assistance advisory and preserve deterministic paper-bet risk gates."
    ]
    root_cause = "Latest live run completed without recorded errors."
    if latest_failure is not None:
        failure_summary = str(latest_failure.get("error_summary") or "")
        if "kickoff date" in failure_summary.lower():
            root_cause = (
                "The latest provider failure is caused by missing full kickoff dates in "
                "public Misli snapshot rows."
            )
            risk_flags.append("provider_datetime_missing")
            recommended_actions.insert(
                0,
                "Resolve Misli kickoff date extraction before treating real Misli import as ready.",
            )
        else:
            root_cause = failure_summary or "A provider or live-run failure was recorded."
            risk_flags.append("live_run_failure")

    if int(input_payload["open_paper_bets"]) > 0:
        risk_flags.append("open_paper_bets")
        recommended_actions.append("Collect results and settle open paper bets on a fixed cadence.")

    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": _short_summary(input_payload),
        "root_cause": root_cause,
        "risk_flags": risk_flags or ["no_current_risk_flags"],
        "recommended_next_actions": recommended_actions,
        "confidence": "medium" if risk_flags else "high",
        "source_record_ids": _source_record_ids(latest_run, latest_failure),
    }


def _comparison_report_input(report_path: Path) -> dict[str, Any]:
    analysis = ComparisonAnalysisService().analyze_comparison_data(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "report_name": report_path.name.removesuffix("_comparison.json"),
        "report_path": str(report_path),
        "metadata": report["metadata"],
        "rankings": report["rankings"],
        "runs": report["runs"],
        "sample_size": analysis["sample_size"],
        "interpretation": analysis["interpretation"],
        "next_experiment": analysis["next_experiment"],
    }


def _comparison_report_output(input_payload: dict[str, Any]) -> dict[str, Any]:
    sample_size = input_payload["sample_size"]
    rankings = input_payload["rankings"]
    risk_flags: list[str] = []
    smallest = int(sample_size["smallest"])
    if smallest < 300:
        risk_flags.append("small_sample_size")
    if _winner_pair(rankings.get("best_roi")) != _winner_pair(
        rankings.get("best_brier_score")
    ):
        risk_flags.append("roi_calibration_disagreement")
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": (
            f"Comparison {input_payload['report_name']} reviewed across "
            f"{len(input_payload['runs'])} model/bookmaker runs."
        ),
        "root_cause": input_payload["interpretation"],
        "risk_flags": risk_flags or ["no_current_risk_flags"],
        "recommended_next_actions": [
            input_payload["next_experiment"],
            "Keep conclusions paper-only until larger replay samples confirm calibration.",
        ],
        "confidence": "medium" if risk_flags else "high",
        "source_record_ids": [input_payload["report_name"]],
    }


def _provider_health_input(engine: Engine, provider: str) -> dict[str, Any]:
    with session_scope(engine) as session:
        runs = list(
            session.scalars(
                select(LiveRun)
                .where(LiveRun.provider == provider)
                .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
                .limit(20)
            )
        )
    failures = [run for run in runs if run.status == "failed"]
    completed = [run for run in runs if run.status == "completed"]
    return {
        "provider": provider,
        "runs_count": len(runs),
        "failed_runs_count": len(failures),
        "completed_runs_count": len(completed),
        "latest_failure": _live_run_input(failures[0]) if failures else None,
        "recent_failures": [_live_run_input(run) for run in failures[:5]],
        "recent_runs": [_live_run_input(run) for run in runs[:10]],
    }


def _provider_health_output(input_payload: dict[str, Any]) -> dict[str, Any]:
    provider = input_payload["provider"]
    latest_failure = input_payload["latest_failure"]
    risk_flags: list[str] = []
    recommended_actions = [
        "Keep provider imports fail-closed when datetime or market confidence is insufficient."
    ]
    root_cause = "No recent provider failures were found."
    if latest_failure is not None:
        failure_summary = str(latest_failure.get("error_summary") or "")
        root_cause = failure_summary or "Recent provider collection failed."
        if "kickoff date" in failure_summary.lower():
            risk_flags.append("provider_datetime_missing")
            recommended_actions.insert(
                0,
                "Continue resolving only high-confidence Misli date labels and reject bare times.",
            )
        else:
            risk_flags.append("provider_validation_failure")
            recommended_actions.insert(0, "Review recent provider validation errors.")
    if input_payload["failed_runs_count"] > 0:
        risk_flags.append("provider_failures_present")
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": (
            f"Misli provider health reviewed with {input_payload['completed_runs_count']} "
            f"completed and {input_payload['failed_runs_count']} failed recent runs."
            if provider == "misli_public"
            else (
                f"Provider {provider} health reviewed with "
                f"{input_payload['completed_runs_count']} completed and "
                f"{input_payload['failed_runs_count']} failed recent runs."
            )
        ),
        "root_cause": root_cause,
        "risk_flags": risk_flags or ["no_current_risk_flags"],
        "recommended_next_actions": recommended_actions,
        "confidence": "medium" if risk_flags else "high",
        "source_record_ids": [
            run["run_id"] for run in input_payload["recent_runs"] if run is not None
        ],
    }


def _failed_eval_output(input_payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": "AI analysis failed safety or structure eval gates.",
        "root_cause": "Provider output did not satisfy AI advisory validation rules.",
        "risk_flags": ["ai_eval_failed"],
        "recommended_next_actions": [
            "Review provider output and keep deterministic fallback active until evals pass."
        ],
        "confidence": "high",
        "source_record_ids": _source_record_ids_from_input(input_payload),
        "eval_failures": failures,
    }


def _short_summary(input_payload: dict[str, Any]) -> str:
    latest_run = input_payload["latest_run"]
    if latest_run is None:
        return "No live paper runs have been recorded yet."
    return (
        f"Latest live run is {latest_run['status']} with "
        f"{input_payload['open_paper_bets']} open and "
        f"{input_payload['settled_paper_bets']} settled paper bets."
    )


def _source_record_ids(
    latest_run: dict[str, Any],
    latest_failure: dict[str, Any] | None,
) -> list[str]:
    ids = [latest_run["run_id"]]
    if latest_failure is not None and latest_failure["run_id"] not in ids:
        ids.append(latest_failure["run_id"])
    return ids


def _source_record_ids_from_input(input_payload: dict[str, Any]) -> list[str]:
    if "report_name" in input_payload:
        return [input_payload["report_name"]]
    if "recent_runs" in input_payload:
        return [run["run_id"] for run in input_payload["recent_runs"] if run is not None]
    latest_run = input_payload["latest_run"]
    if latest_run is None:
        return []
    return _source_record_ids(latest_run, input_payload["latest_failure"])


def _winner_pair(winner: Any) -> tuple[object, object] | None:
    if not isinstance(winner, dict):
        return None
    return winner.get("model"), winner.get("bookmaker")
