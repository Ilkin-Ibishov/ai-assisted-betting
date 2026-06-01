import json
from typing import Any

from sqlalchemy import func, select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, LiveRun, PaperRecommendation
from app.services.worker_monitoring_service import WorkerMonitoringService


class OperationalGuardrailService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def status(
        self,
        *,
        now_iso: str | None = None,
        worker_fresh_after_minutes: int = 90,
        repeated_failure_threshold: int = 3,
    ) -> dict[str, Any]:
        worker_status = WorkerMonitoringService(self.database_url).status(
            fresh_after_minutes=worker_fresh_after_minutes,
            now_iso=now_iso,
        )
        with _guardrail_session(self.database_url) as session:
            latest_ai_failure = _latest_ai_failure(session)
            recommendation_count = _recommendation_count_since_latest_worker(session)
            consecutive_failures = _consecutive_worker_failures(session)
            latest_provider_failure = _latest_provider_failure(session)

        guardrails = [
            _worker_freshness_guardrail(worker_status),
            _repeated_worker_failures_guardrail(
                consecutive_failures,
                repeated_failure_threshold,
            ),
            _provider_data_guardrail(latest_provider_failure),
            _ai_eval_guardrail(latest_ai_failure),
            _recommendation_output_guardrail(worker_status, recommendation_count),
        ]
        return {
            "overall_status": _overall_status(guardrails),
            "guardrails": guardrails,
            "worker_status": worker_status,
        }


def _guardrail_session(database_url: str):
    engine = create_engine_from_url(database_url)

    class GuardrailSession:
        def __enter__(self):
            self.scope = session_scope(engine)
            return self.scope.__enter__()

        def __exit__(self, exc_type, exc, traceback):
            try:
                return self.scope.__exit__(exc_type, exc, traceback)
            finally:
                engine.dispose()

    return GuardrailSession()


def _worker_freshness_guardrail(worker_status: dict[str, Any]) -> dict[str, Any]:
    status = str(worker_status["status"])
    if status == "fresh":
        severity = "ok"
    elif status in {"never_run", "stale", "running"}:
        severity = "warning"
    else:
        severity = "critical"
    return _guardrail(
        name="worker_freshness",
        severity=severity,
        state=status,
        observed_value=worker_status.get("freshness_minutes"),
        remediation=(
            "Check Railway worker cadence, latest worker logs, and DATABASE_URL alignment."
        ),
    )


def _repeated_worker_failures_guardrail(
    consecutive_failures: int,
    repeated_failure_threshold: int,
) -> dict[str, Any]:
    severity = "critical" if consecutive_failures >= repeated_failure_threshold else "ok"
    return _guardrail(
        name="repeated_worker_failures",
        severity=severity,
        state="threshold_exceeded" if severity == "critical" else "within_threshold",
        observed_value=consecutive_failures,
        threshold=repeated_failure_threshold,
        remediation="Inspect scheduled worker logs and provider validation errors.",
    )


def _provider_data_guardrail(latest_failure: LiveRun | None) -> dict[str, Any]:
    if latest_failure is None:
        return _guardrail(
            name="provider_data_quality",
            severity="ok",
            state="no_recent_provider_failure",
            remediation="Continue monitoring provider health and parser drift.",
        )
    summary = (latest_failure.error_summary or "").lower()
    alert_terms = ("parser drift", "stale", "low extraction confidence", "kickoff date")
    severity = "warning" if any(term in summary for term in alert_terms) else "ok"
    return _guardrail(
        name="provider_data_quality",
        severity=severity,
        state="provider_warning" if severity == "warning" else "provider_failure_recorded",
        observed_value=latest_failure.error_summary,
        remediation=(
            "Collect a fresh public snapshot and verify parser confidence before trusting "
            "recommendations."
        ),
    )


def _ai_eval_guardrail(latest_failure: AIAnalysisRun | None) -> dict[str, Any]:
    if latest_failure is None:
        return _guardrail(
            name="ai_eval_safety",
            severity="ok",
            state="no_failed_ai_eval",
            remediation="Keep AI assistance advisory and run evals after prompt/provider changes.",
        )
    return _guardrail(
        name="ai_eval_safety",
        severity="critical",
        state="failed",
        observed_value=latest_failure.error_summary,
        remediation="Review the failed AI analysis output and keep deterministic fallback active.",
    )


def _recommendation_output_guardrail(
    worker_status: dict[str, Any],
    recommendation_count: int,
) -> dict[str, Any]:
    worker_is_fresh = worker_status["status"] == "fresh"
    severity = "warning" if worker_is_fresh and recommendation_count == 0 else "ok"
    return _guardrail(
        name="recommendation_output",
        severity=severity,
        state="empty_after_fresh_worker" if severity == "warning" else "available_or_not_expected",
        observed_value=recommendation_count,
        remediation=(
            "Inspect odds movement, provider health, recommendation thresholds, and AI "
            "review state."
        ),
    )


def _guardrail(
    *,
    name: str,
    severity: str,
    state: str,
    remediation: str,
    observed_value: Any = None,
    threshold: Any = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "severity": severity,
        "state": state,
        "observed_value": observed_value,
        "threshold": threshold,
        "remediation": remediation,
    }


def _overall_status(guardrails: list[dict[str, Any]]) -> str:
    severities = {str(item["severity"]) for item in guardrails}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "warning"
    return "ok"


def _latest_ai_failure(session) -> AIAnalysisRun | None:
    failures = list(
        session.scalars(
            select(AIAnalysisRun)
            .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
            .limit(20)
        )
    )
    for failure in failures:
        if failure.status == "failed" or "ai_eval_failed" in _analysis_risk_flags(failure):
            return failure
    return None


def _analysis_risk_flags(analysis: AIAnalysisRun) -> list[str]:
    try:
        output = json.loads(analysis.output_json)
    except json.JSONDecodeError:
        return ["invalid_ai_output_json"]
    risk_flags = output.get("risk_flags") if isinstance(output, dict) else None
    if not isinstance(risk_flags, list):
        return []
    return [str(flag) for flag in risk_flags]


def _recommendation_count_since_latest_worker(session) -> int:
    latest_worker = session.scalar(
        select(LiveRun)
        .where(LiveRun.run_type == "scheduled_paper_worker")
        .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
        .limit(1)
    )
    query = select(func.count()).select_from(PaperRecommendation)
    if latest_worker is not None:
        query = query.where(PaperRecommendation.created_at >= latest_worker.started_at)
    count = session.scalar(query)
    return int(count or 0)


def _consecutive_worker_failures(session) -> int:
    runs = list(
        session.scalars(
            select(LiveRun)
            .where(LiveRun.run_type == "scheduled_paper_worker")
            .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
            .limit(10)
        )
    )
    failures = 0
    for run in runs:
        if run.status != "failed":
            break
        failures += 1
    return failures


def _latest_provider_failure(session) -> LiveRun | None:
    return session.scalar(
        select(LiveRun)
        .where(
            LiveRun.status == "failed",
            LiveRun.provider == "misli_public",
            LiveRun.run_type.in_(["collect_matches", "collect_odds", "scheduled_paper_worker"]),
        )
        .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
        .limit(1)
    )
