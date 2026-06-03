import json
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import Engine, func, select

from app.db.engine import session_scope
from app.db.models import (
    AIAnalysisRun,
    EvaluationRun,
    LiveRun,
    PaperBet,
    PaperCombination,
    PaperRecommendation,
)
from app.services.ai_analysis_evals import evaluate_ai_analysis_output
from app.services.ai_prompt_registry import (
    COMPARISON_REPORT_PROMPT_VERSION,
    LIVE_STATUS_PROMPT_VERSION,
    PROVIDER_HEALTH_PROMPT_VERSION,
    RECOMMENDATION_BACKTEST_PROMPT_VERSION,
    RECOMMENDATION_REVIEW_PROMPT_VERSION,
    ComparisonReportPrompt,
    LiveStatusPrompt,
    ProviderHealthPrompt,
    RecommendationBacktestPrompt,
    RecommendationReviewPrompt,
    build_comparison_report_prompt,
    build_live_status_prompt,
    build_provider_health_prompt,
    build_recommendation_backtest_prompt,
    build_recommendation_review_prompt,
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

    def analyze_recommendation_review(self, prompt: RecommendationReviewPrompt) -> dict[str, Any]:
        pass

    def analyze_recommendation_backtest(
        self,
        prompt: RecommendationBacktestPrompt,
    ) -> dict[str, Any]:
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

    def analyze_recommendation_review(self, prompt: RecommendationReviewPrompt) -> dict[str, Any]:
        return {
            "prompt_version": prompt.version,
            "output": _recommendation_review_output(prompt.input_payload),
        }

    def analyze_recommendation_backtest(
        self,
        prompt: RecommendationBacktestPrompt,
    ) -> dict[str, Any]:
        return {
            "prompt_version": prompt.version,
            "output": _recommendation_backtest_output(prompt.input_payload),
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

    def analyze_recommendation_review(self, *, limit: int = 50) -> AIAnalysisRun:
        input_payload = _recommendation_review_input(self.engine, limit=limit)
        if not input_payload["paper_recommendations"] and not input_payload["paper_combinations"]:
            output_payload = _missing_recommendation_review_output()
            with session_scope(self.engine) as session:
                analysis = AIAnalysisRun(
                    analysis_type="recommendation_review",
                    source_type="paper_recommendations",
                    source_id="empty",
                    input_json=json.dumps(input_payload, sort_keys=True),
                    output_json=json.dumps(output_payload, sort_keys=True),
                    model_name=self.provider.model_name,
                    prompt_version=RECOMMENDATION_REVIEW_PROMPT_VERSION,
                    status="failed",
                    error_summary="recommendation_inputs_missing",
                )
                session.add(analysis)
                session.flush()
                return analysis

        provider_result = self.provider.analyze_recommendation_review(
            build_recommendation_review_prompt(input_payload)
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
                analysis_type="recommendation_review",
                source_type="paper_recommendations",
                source_id="latest",
                input_json=json.dumps(input_payload, sort_keys=True),
                output_json=json.dumps(output_payload, sort_keys=True),
                model_name=self.provider.model_name,
                prompt_version=str(
                    provider_result.get(
                        "prompt_version",
                        RECOMMENDATION_REVIEW_PROMPT_VERSION,
                    )
                ),
                status=status,
                error_summary=error_summary,
            )
            session.add(analysis)
            session.flush()
            return analysis

    def analyze_recommendation_backtest_report(self, report_path: Path) -> AIAnalysisRun:
        input_payload = _recommendation_backtest_input(report_path)
        provider_result = self.provider.analyze_recommendation_backtest(
            build_recommendation_backtest_prompt(input_payload)
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
                analysis_type="recommendation_backtest_summary",
                source_type="recommendation_backtest_report",
                source_id=input_payload["report_name"],
                input_json=json.dumps(input_payload, sort_keys=True),
                output_json=json.dumps(output_payload, sort_keys=True),
                model_name=self.provider.model_name,
                prompt_version=str(
                    provider_result.get(
                        "prompt_version",
                        RECOMMENDATION_BACKTEST_PROMPT_VERSION,
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


def _recommendation_backtest_input(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metadata = report["metadata"]
    return {
        "report_name": metadata.get(
            "report_name",
            report_path.name.removesuffix("_recommendation_backtest.json"),
        ),
        "report_path": str(report_path),
        "metadata": metadata,
        "singles": report["singles"],
        "combinations": report["combinations"],
        "edge_buckets": report.get("edge_buckets", {}),
        "market_buckets": report.get("market_buckets", {}),
        "model_provider_splits": report.get("model_provider_splits", {}),
        "threshold_sensitivity": report.get("threshold_sensitivity", []),
    }


def _recommendation_backtest_output(input_payload: dict[str, Any]) -> dict[str, Any]:
    singles = input_payload["singles"]
    combinations = input_payload["combinations"]
    threshold_sensitivity = input_payload["threshold_sensitivity"]
    singles_roi = _metric_value(singles.get("roi"))
    combinations_roi = _metric_value(combinations.get("roi"))
    risk_flags: list[str] = []
    recommended_actions = [
        "Replay a larger historical sample before changing paper recommendation thresholds.",
        "Keep recommendation output advisory and paper-only while monitoring calibration.",
    ]
    if int(singles.get("settled_bets") or 0) < 300:
        risk_flags.append("small_backtest_sample")
    if int(combinations.get("settled_bets") or 0) < 100:
        risk_flags.append("combination_under_sampled")
    if singles_roi is not None and singles_roi < 0:
        risk_flags.append("negative_singles_roi")
    if combinations_roi is not None and combinations_roi < 0:
        risk_flags.append("negative_combination_roi")
    if (
        singles_roi is not None
        and combinations_roi is not None
        and combinations_roi < singles_roi
    ):
        risk_flags.append("combination_underperformance")
        recommended_actions.insert(
            0,
            "Tighten or pause combination ranking until backtests show repeatable lift.",
        )
    if _has_threshold_sensitivity(threshold_sensitivity):
        risk_flags.append("threshold_sensitivity_present")
        recommended_actions.append(
            "Compare stricter edge and confidence thresholds in the next replay batch."
        )
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": (
            f"Recommendation backtest {input_payload['report_name']} reviewed with "
            f"{singles.get('settled_bets', 0)} settled singles at ROI "
            f"{singles.get('roi')} and {combinations.get('settled_bets', 0)} "
            f"settled combinations at ROI {combinations.get('roi')}."
        ),
        "root_cause": (
            "Recommendation and combination rules were evaluated on settled historical "
            "records with threshold-sensitivity and calibration metrics."
        ),
        "risk_flags": risk_flags or ["no_current_risk_flags"],
        "recommended_next_actions": recommended_actions,
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
        failure_summary_lower = failure_summary.lower()
        root_cause = failure_summary or "Recent provider collection failed."
        if "parser drift" in failure_summary_lower:
            risk_flags.append("provider_parser_drift")
            recommended_actions.insert(
                0,
                "Review Misli public selectors and raw snapshot text before scheduling.",
            )
        if "stale" in failure_summary_lower:
            risk_flags.append("provider_stale_snapshot")
            recommended_actions.append(
                "Collect a fresh public snapshot before trusting recommendation inputs.",
            )
        if "low" in failure_summary_lower and "confidence" in failure_summary_lower:
            risk_flags.append("provider_low_extraction_confidence")
            recommended_actions.append(
                "Compare extracted rows with the visible public Misli page before accepting data.",
            )
        if "kickoff date" in failure_summary_lower:
            risk_flags.append("provider_datetime_missing")
            recommended_actions.insert(
                0,
                "Continue resolving Misli date labels and bare times only against trusted "
                "snapshot scraped_at timestamps.",
            )
        if not risk_flags:
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


def _recommendation_review_input(engine: Engine, *, limit: int) -> dict[str, Any]:
    with session_scope(engine) as session:
        recommendations = session.scalars(
            select(PaperRecommendation)
            .order_by(
                PaperRecommendation.latest_snapshot_time.desc(),
                PaperRecommendation.created_at.desc(),
                PaperRecommendation.id.desc(),
            )
            .limit(max(1, min(limit, 200)))
        ).all()
        combinations = session.scalars(
            select(PaperCombination)
            .order_by(PaperCombination.rank.asc(), PaperCombination.id.asc())
            .limit(max(1, min(limit, 200)))
        ).all()
        latest_provider_run = session.scalar(
            select(LiveRun)
            .where(LiveRun.provider == "misli_public")
            .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
            .limit(1)
        )
        latest_evaluation = session.scalar(
            select(EvaluationRun)
            .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
            .limit(1)
        )
    return {
        "paper_recommendations": [
            _recommendation_review_record(item) for item in recommendations
        ],
        "paper_combinations": [_combination_review_record(item) for item in combinations],
        "provider_health": _live_run_input(latest_provider_run),
        "historical_calibration": _evaluation_review_record(latest_evaluation),
    }


def _recommendation_review_record(recommendation: PaperRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "source_match_id": recommendation.source_match_id,
        "bookmaker": recommendation.bookmaker,
        "market": recommendation.market,
        "selection": recommendation.selection,
        "grade": recommendation.grade,
        "status": recommendation.status,
        "model_probability": recommendation.model_probability,
        "implied_probability": recommendation.implied_probability,
        "edge": recommendation.edge,
        "confidence_score": recommendation.confidence_score,
        "current_odds": recommendation.current_odds,
        "expected_value": recommendation.expected_value,
        "risk_flags": json.loads(recommendation.risk_flags_json),
        "rationale": recommendation.rationale,
    }


def _combination_review_record(combination: PaperCombination) -> dict[str, Any]:
    return {
        "id": combination.id,
        "leg_recommendation_ids": json.loads(combination.leg_recommendation_ids_json),
        "leg_count": combination.leg_count,
        "grade": combination.grade,
        "status": combination.status,
        "rank": combination.rank,
        "combined_odds": combination.combined_odds,
        "estimated_probability": combination.estimated_probability,
        "combined_expected_value": combination.combined_expected_value,
        "confidence_score": combination.confidence_score,
        "risk_flags": json.loads(combination.risk_flags_json),
        "rationale": combination.rationale,
    }


def _evaluation_review_record(evaluation: EvaluationRun | None) -> dict[str, Any] | None:
    if evaluation is None:
        return None
    return {
        "id": evaluation.id,
        "model_name": evaluation.model_name,
        "model_version": evaluation.model_version,
        "total_bets": evaluation.total_bets,
        "roi": evaluation.roi,
        "brier_score": evaluation.brier_score,
        "log_loss": evaluation.log_loss,
    }


def _recommendation_review_output(input_payload: dict[str, Any]) -> dict[str, Any]:
    recommendations = input_payload["paper_recommendations"]
    combinations = input_payload["paper_combinations"]
    model_quality = _recommendation_model_quality(recommendations)
    risk_flags: list[str] = []
    concerns: list[str] = []
    next_checks = [
        "Backtest recommendation and combination thresholds before trusting paper strategy.",
        "Keep all outputs advisory and paper-only.",
    ]
    rejected_assumptions = [
        "Recommendation approval does not imply real-money readiness.",
        "Combination ranking does not prove independent leg probabilities.",
    ]

    unsafe_recommendations = [
        item for item in recommendations if item["status"] != "active" or item["grade"] == "reject"
    ]
    low_confidence = [
        item
        for item in recommendations
        if item["confidence_score"] is not None and float(item["confidence_score"]) < 0.65
    ]
    risky_combinations = [
        item
        for item in combinations
        if item["leg_count"] > 1 or item["risk_flags"] != ["no_current_risk_flags"]
    ]
    provider_health = input_payload["provider_health"]
    if provider_health is not None and provider_health["status"] == "failed":
        risk_flags.append("provider_health_warning")
        concerns.append(
            "Latest Misli provider run failed; recommendations need fresh input checks."
        )
    if unsafe_recommendations:
        risk_flags.append("rejected_recommendations_present")
        concerns.append(
            "Rejected or inactive recommendation records are present in the review set."
        )
    if low_confidence:
        risk_flags.append("low_confidence_recommendations")
        concerns.append("Some recommendation legs have confidence below the preferred review band.")
    if model_quality["cold_start_confidence_ceiling"]:
        risk_flags.append("cold_start_confidence_ceiling")
        concerns.append(
            "Positive-EV rows are watchlist-only because the baseline heuristic confidence "
            "is capped by small probability adjustments."
        )
        next_checks.insert(
            0,
            "Calibrate baseline confidence or add richer team-strength inputs before "
            "promoting watchlist rows.",
        )
    if risky_combinations:
        risk_flags.append("combination_correlation_heuristic")
        concerns.append(
            "Multi-leg combinations rely on heuristic independence and exposure assumptions."
        )

    approval_state = "approve"
    if risk_flags:
        approval_state = "caution"
    if "provider_health_warning" in risk_flags or "rejected_recommendations_present" in risk_flags:
        approval_state = "reject"

    source_ids = [
        f"paper_recommendation:{item['id']}" for item in recommendations
    ] + [f"paper_combination:{item['id']}" for item in combinations]
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": (
            f"Reviewed {len(recommendations)} paper recommendations and "
            f"{len(combinations)} paper combinations."
        ),
        "root_cause": (
            "Deterministic recommendation and combination records were reviewed "
            "against risk flags, confidence, provider health, and calibration context."
        ),
        "risk_flags": risk_flags or ["no_current_risk_flags"],
        "recommended_next_actions": next_checks,
        "confidence": "medium" if risk_flags else "high",
        "model_quality": model_quality,
        "source_record_ids": source_ids,
        "approval_state": approval_state,
        "concerns": concerns,
        "confidence_explanation": _recommendation_confidence_explanation(
            recommendations,
            combinations,
            risk_flags,
        ),
        "rejected_assumptions": rejected_assumptions,
        "next_checks": next_checks,
    }


def _recommendation_confidence_explanation(
    recommendations: list[dict[str, Any]],
    combinations: list[dict[str, Any]],
    risk_flags: list[str],
) -> str:
    if risk_flags:
        return (
            "Confidence is limited by active risk flags and by the current heuristic "
            "combination model."
        )
    return (
        f"Confidence is based on {len(recommendations)} deterministic recommendation "
        f"records and {len(combinations)} combination records with no current risk flags."
    )


def _recommendation_model_quality(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    hard_blocking_flags = {
        "negative_expected_value",
        "missing_prediction",
        "stale_odds",
        "missing_outcome",
        "provider_health_warning",
        "edge_below_threshold",
    }
    blocking_flags = hard_blocking_flags | {"low_confidence"}
    confidence_values = [
        float(item["confidence_score"])
        for item in recommendations
        if item["confidence_score"] is not None
    ]
    watchlist = [
        item
        for item in recommendations
        if item["status"] == "active"
        and float(item["expected_value"] or 0) > 0
        and not set(item["risk_flags"]).intersection(hard_blocking_flags)
    ]
    actionable = [
        item
        for item in recommendations
        if item["status"] == "active"
        and item["grade"] in {"recommended", "lean"}
        and float(item["expected_value"] or 0) > 0
        and not set(item["risk_flags"]).intersection(blocking_flags)
    ]
    max_confidence = max(confidence_values) if confidence_values else None
    return {
        "recommendation_count": len(recommendations),
        "watchlist_count": len(watchlist),
        "actionable_count": len(actionable),
        "low_confidence_count": len(
            [
                item
                for item in recommendations
                if item["confidence_score"] is not None
                and float(item["confidence_score"]) < 0.65
            ]
        ),
        "max_confidence_score": round(max_confidence, 6)
        if max_confidence is not None
        else None,
        "cold_start_confidence_ceiling": (
            bool(watchlist)
            and not actionable
            and max_confidence is not None
            and max_confidence < 0.5
        ),
    }


def _metric_value(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _has_threshold_sensitivity(scenarios: list[dict[str, Any]]) -> bool:
    if len(scenarios) < 2:
        return False
    settled_counts = {int(scenario.get("settled_bets") or 0) for scenario in scenarios}
    roi_values = {
        round(float(scenario["roi"]), 6)
        for scenario in scenarios
        if scenario.get("roi") is not None
    }
    return len(settled_counts) > 1 or len(roi_values) > 1


def _missing_recommendation_review_output() -> dict[str, Any]:
    return {
        "label": "AI-assisted advisory analysis",
        "short_summary": "No paper recommendations or combinations are available for review.",
        "root_cause": "The recommendation review cannot run without persisted advisory inputs.",
        "risk_flags": ["recommendation_inputs_missing"],
        "recommended_next_actions": [
            "Run generate-recommendations and generate-combinations before AI review."
        ],
        "confidence": "high",
        "source_record_ids": [],
        "approval_state": "reject",
        "concerns": ["No deterministic recommendation inputs were available."],
        "confidence_explanation": "The review is rejected because no source records exist.",
        "rejected_assumptions": ["No recommendation quality can be inferred without inputs."],
        "next_checks": ["Generate deterministic recommendation inputs first."],
    }


def _failed_eval_output(input_payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    output = {
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
    if "paper_recommendations" in input_payload:
        output.update(
            {
                "approval_state": "reject",
                "concerns": ["AI provider output failed recommendation-review eval gates."],
                "confidence_explanation": (
                    "Deterministic fallback rejected unsafe or unsupported review output."
                ),
                "rejected_assumptions": [
                    "Unsafe AI review output must not be treated as recommendation approval."
                ],
                "next_checks": ["Fix provider output and rerun evals."],
            }
        )
    return output


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
    if "paper_recommendations" in input_payload:
        return [
            f"paper_recommendation:{item['id']}"
            for item in input_payload["paper_recommendations"]
        ] + [
            f"paper_combination:{item['id']}"
            for item in input_payload["paper_combinations"]
        ]
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
