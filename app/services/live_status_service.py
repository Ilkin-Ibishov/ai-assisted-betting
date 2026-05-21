from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import LiveRun, PaperBet


class LiveStatusService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def status(self) -> dict[str, Any]:
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                return {
                    "latest_run": _live_run_payload(_latest_run(session)),
                    "latest_success": _live_run_payload(_latest_run(session, status="completed")),
                    "latest_failure": _live_run_payload(_latest_run(session, status="failed")),
                    "open_paper_bets": _paper_bet_count(session, statuses=["open"]),
                    "settled_paper_bets": _paper_bet_count(
                        session,
                        statuses=["won", "lost", "void"],
                    ),
                    "runs_count": _live_run_count(session),
                    "errors_count": _live_run_error_count(session),
                }
        finally:
            engine.dispose()

    def recent_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                runs = session.scalars(
                    _ordered_live_run_query().limit(max(1, min(limit, 100)))
                ).all()
                return [_live_run_payload(run) for run in runs if run is not None]
        finally:
            engine.dispose()

    def run(self, run_id: str) -> dict[str, Any] | None:
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                live_run = session.scalar(select(LiveRun).where(LiveRun.run_id == run_id))
                return _live_run_payload(live_run)
        finally:
            engine.dispose()


def _latest_run(session: Session, *, status: str | None = None) -> LiveRun | None:
    query = _ordered_live_run_query()
    if status is not None:
        query = query.where(LiveRun.status == status)
    return session.scalar(query.limit(1))


def _ordered_live_run_query():
    return select(LiveRun).order_by(LiveRun.started_at.desc(), LiveRun.id.desc())


def _paper_bet_count(session: Session, *, statuses: list[str]) -> int:
    count = session.scalar(
        select(func.count()).select_from(PaperBet).where(PaperBet.status.in_(statuses))
    )
    return int(count or 0)


def _live_run_count(session: Session) -> int:
    count = session.scalar(select(func.count()).select_from(LiveRun))
    return int(count or 0)


def _live_run_error_count(session: Session) -> int:
    count = session.scalar(select(func.coalesce(func.sum(LiveRun.errors_count), 0)))
    return int(count or 0)


def _live_run_payload(live_run: LiveRun | None) -> dict[str, Any] | None:
    if live_run is None:
        return None
    return {
        "id": live_run.id,
        "run_id": live_run.run_id,
        "run_type": live_run.run_type,
        "provider": live_run.provider,
        "league": live_run.league,
        "season": live_run.season,
        "status": live_run.status,
        "started_at": live_run.started_at,
        "finished_at": live_run.finished_at,
        "items_read": live_run.items_read,
        "items_created": live_run.items_created,
        "items_updated": live_run.items_updated,
        "items_skipped": live_run.items_skipped,
        "errors_count": live_run.errors_count,
        "error_summary": live_run.error_summary,
        "model_name": live_run.model_name,
        "created_at": live_run.created_at,
    }
