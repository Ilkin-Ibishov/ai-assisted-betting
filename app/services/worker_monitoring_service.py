from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import LiveRun, utc_now_iso
from app.services.live_status_service import live_run_payload


class WorkerMonitoringService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def status(
        self,
        *,
        fresh_after_minutes: int = 90,
        now_iso: str | None = None,
    ) -> dict[str, Any]:
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                latest_worker = session.scalar(
                    select(LiveRun)
                    .where(LiveRun.run_type == "scheduled_paper_worker")
                    .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
                    .limit(1)
                )
                payload = live_run_payload(latest_worker)
                if latest_worker is None:
                    return _status_payload(
                        status="never_run",
                        healthy=False,
                        latest_worker_run=None,
                        freshness_minutes=None,
                        fresh_after_minutes=fresh_after_minutes,
                    )
                freshness_minutes = _freshness_minutes(latest_worker, now_iso or utc_now_iso())
                return _status_payload(
                    status=_worker_status(latest_worker, freshness_minutes, fresh_after_minutes),
                    healthy=_worker_healthy(
                        latest_worker,
                        freshness_minutes,
                        fresh_after_minutes,
                    ),
                    latest_worker_run=payload,
                    freshness_minutes=freshness_minutes,
                    fresh_after_minutes=fresh_after_minutes,
                )
        finally:
            engine.dispose()


def _status_payload(
    *,
    status: str,
    healthy: bool,
    latest_worker_run: dict[str, Any] | None,
    freshness_minutes: int | None,
    fresh_after_minutes: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "healthy": healthy,
        "latest_worker_run": latest_worker_run,
        "freshness_minutes": freshness_minutes,
        "fresh_after_minutes": fresh_after_minutes,
    }


def _worker_status(
    live_run: LiveRun,
    freshness_minutes: int | None,
    fresh_after_minutes: int,
) -> str:
    if live_run.status == "running":
        return "running"
    if live_run.status == "failed":
        return "failed"
    if live_run.status != "completed":
        return live_run.status
    if freshness_minutes is None or freshness_minutes > fresh_after_minutes:
        return "stale"
    return "fresh"


def _worker_healthy(
    live_run: LiveRun,
    freshness_minutes: int | None,
    fresh_after_minutes: int,
) -> bool:
    return (
        live_run.status == "completed"
        and freshness_minutes is not None
        and freshness_minutes <= fresh_after_minutes
    )


def _freshness_minutes(live_run: LiveRun, now_iso: str) -> int | None:
    reference_iso = live_run.finished_at or live_run.started_at
    if reference_iso is None:
        return None
    reference = _parse_iso(reference_iso)
    now = _parse_iso(now_iso)
    return max(0, int((now - reference).total_seconds() // 60))


def _parse_iso(value: str) -> datetime:
    if len(value) >= 6 and value[-6] == " " and value[-5:].count(":") == 1:
        value = f"{value[:-6]}+{value[-5:]}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
