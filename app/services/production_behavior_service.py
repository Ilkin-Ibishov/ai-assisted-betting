import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, LiveSnapshot, PaperJournalEntry, PaperRecommendation
from app.services.worker_monitoring_service import WorkerMonitoringService


class ProductionBehaviorService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def status(
        self,
        *,
        now_iso: str | None = None,
        fresh_after_minutes: int = 90,
    ) -> dict[str, Any]:
        worker = WorkerMonitoringService(self.database_url).status(
            fresh_after_minutes=fresh_after_minutes,
            now_iso=now_iso,
        )
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                worker_started_at = _latest_worker_started_at(worker)
                stages = {
                    "worker": _worker_stage(worker),
                    "snapshot": _snapshot_stage(
                        _latest_snapshot(session),
                        now_iso=now_iso,
                        fresh_after_minutes=fresh_after_minutes,
                    ),
                    "recommendations": _recommendation_stage(session, worker_started_at),
                    "ai_review": _analysis_stage(
                        _latest_analysis(session, "recommendation_review"),
                        worker_started_at=worker_started_at,
                    ),
                    "threshold_review": _analysis_stage(
                        _latest_analysis(session, "recommendation_backtest_summary"),
                        worker_started_at=worker_started_at,
                    ),
                    "journal": _journal_stage(_latest_journal(session), worker_started_at),
                }
        finally:
            engine.dispose()

        attention_required = [
            name
            for name, stage in stages.items()
            if stage["severity"] in {"warning", "critical"}
        ]
        return {
            "overall_status": _overall_status(stages),
            "healthy": not attention_required,
            "attention_required": attention_required,
            "fresh_after_minutes": fresh_after_minutes,
            "stages": stages,
        }


def _worker_stage(worker: dict[str, Any]) -> dict[str, Any]:
    status = str(worker["status"])
    severity = "ok" if status == "fresh" else "critical" if status == "failed" else "warning"
    return {
        "status": status,
        "severity": severity,
        "freshness_minutes": worker.get("freshness_minutes"),
        "latest_run": worker.get("latest_worker_run"),
    }


def _snapshot_stage(
    snapshot: LiveSnapshot | None,
    *,
    now_iso: str | None,
    fresh_after_minutes: int,
) -> dict[str, Any]:
    if snapshot is None:
        return {"status": "missing", "severity": "warning", "event_count": 0}
    freshness_minutes = _minutes_since(snapshot.created_at, now_iso or _utc_now_iso())
    is_empty = snapshot.event_count <= 0
    is_stale = freshness_minutes is None or freshness_minutes > fresh_after_minutes
    status = "empty" if is_empty else "stale" if is_stale else "fresh"
    return {
        "status": status,
        "severity": "ok" if status == "fresh" else "warning",
        "freshness_minutes": freshness_minutes,
        "event_count": snapshot.event_count,
        "created_at": snapshot.created_at,
        "source_url": snapshot.source_url,
    }


def _recommendation_stage(session, worker_started_at: str | None) -> dict[str, Any]:
    query = select(func.count()).select_from(PaperRecommendation)
    if worker_started_at is not None:
        query = query.where(PaperRecommendation.created_at >= worker_started_at)
    count = int(session.scalar(query) or 0)
    return {
        "status": "available" if count > 0 else "empty",
        "severity": "ok" if count > 0 else "warning",
        "count": count,
        "since": worker_started_at,
    }


def _analysis_stage(
    analysis: AIAnalysisRun | None,
    *,
    worker_started_at: str | None,
) -> dict[str, Any]:
    if analysis is None:
        return {"status": "missing", "severity": "warning", "id": None}
    stale_for_worker = (
        worker_started_at is not None
        and _parse_iso(analysis.created_at) < _parse_iso(worker_started_at)
    )
    if analysis.status == "failed":
        status = "failed"
        severity = "critical"
    elif stale_for_worker:
        status = "stale"
        severity = "warning"
    else:
        status = "fresh"
        severity = "ok"
    return {
        "status": status,
        "severity": severity,
        "id": analysis.id,
        "analysis_type": analysis.analysis_type,
        "created_at": analysis.created_at,
        "error_summary": analysis.error_summary,
    }


def _journal_stage(
    journal: PaperJournalEntry | None,
    worker_started_at: str | None,
) -> dict[str, Any]:
    if journal is None:
        return {"status": "missing", "severity": "warning", "id": None}
    stale_for_worker = (
        worker_started_at is not None
        and _parse_iso(journal.updated_at) < _parse_iso(worker_started_at)
    )
    payload = _json_object(journal.summary_json)
    threshold_review = payload.get("threshold_review") if isinstance(payload, dict) else None
    threshold_decision = (
        threshold_review.get("overall_decision")
        if isinstance(threshold_review, dict)
        else "missing"
    )
    status = "stale" if stale_for_worker else "fresh"
    severity = "warning" if stale_for_worker or threshold_decision == "missing" else "ok"
    return {
        "status": status,
        "severity": severity,
        "id": journal.id,
        "journal_date": journal.journal_date,
        "decision_state": journal.decision_state,
        "updated_at": journal.updated_at,
        "threshold_overall_decision": threshold_decision,
        "source_ids": _json_list(journal.source_ids_json),
    }


def _latest_worker_started_at(worker: dict[str, Any]) -> str | None:
    latest = worker.get("latest_worker_run")
    if not isinstance(latest, dict):
        return None
    started_at = latest.get("started_at")
    return started_at if isinstance(started_at, str) else None


def _latest_snapshot(session) -> LiveSnapshot | None:
    return session.scalar(
        select(LiveSnapshot)
        .where(LiveSnapshot.provider == "misli_public")
        .order_by(LiveSnapshot.created_at.desc(), LiveSnapshot.id.desc())
        .limit(1)
    )


def _latest_analysis(session, analysis_type: str) -> AIAnalysisRun | None:
    return session.scalar(
        select(AIAnalysisRun)
        .where(AIAnalysisRun.analysis_type == analysis_type)
        .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
        .limit(1)
    )


def _latest_journal(session) -> PaperJournalEntry | None:
    return session.scalar(
        select(PaperJournalEntry)
        .order_by(PaperJournalEntry.updated_at.desc(), PaperJournalEntry.id.desc())
        .limit(1)
    )


def _overall_status(stages: dict[str, dict[str, Any]]) -> str:
    severities = {stage["severity"] for stage in stages.values()}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "warning"
    return "ok"


def _minutes_since(reference_iso: str | None, now_iso: str) -> int | None:
    if reference_iso is None:
        return None
    return max(0, int((_parse_iso(now_iso) - _parse_iso(reference_iso)).total_seconds() // 60))


def _parse_iso(value: str) -> datetime:
    if len(value) >= 6 and value[-6] == " " and value[-5:].count(":") == 1:
        value = f"{value[:-6]}+{value[-5:]}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str) -> list[Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []
