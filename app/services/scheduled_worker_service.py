from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, select

from app.config import Settings
from app.db.engine import session_scope
from app.db.models import LiveRun, utc_now_iso
from app.db.repositories import LiveRunRepository
from app.services.live_cycle_service import (
    LivePaperCycleRequest,
    LivePaperCycleService,
    LivePaperCycleSummary,
)


@dataclass(frozen=True)
class ScheduledPaperWorkerRequest:
    provider: str
    snapshot: Path
    model: str | None = None
    league: str | None = None
    season: str | None = None


@dataclass(frozen=True)
class ScheduledPaperWorkerSummary:
    status: str
    run_id: str | None
    cycle_summary: LivePaperCycleSummary | None
    error_summary: str | None = None

    @property
    def items_read(self) -> int:
        return self.cycle_summary.items_read if self.cycle_summary is not None else 0

    @property
    def items_created(self) -> int:
        return self.cycle_summary.items_created if self.cycle_summary is not None else 0

    @property
    def items_updated(self) -> int:
        return self.cycle_summary.items_updated if self.cycle_summary is not None else 0

    @property
    def items_skipped(self) -> int:
        return self.cycle_summary.items_skipped if self.cycle_summary is not None else 0

    @property
    def errors_count(self) -> int:
        if self.status == "failed" and self.cycle_summary is None:
            return 1
        return self.cycle_summary.errors_count if self.cycle_summary is not None else 0


class ScheduledPaperWorkerService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def run_once(self, request: ScheduledPaperWorkerRequest) -> ScheduledPaperWorkerSummary:
        if _running_worker_exists(self.engine):
            return ScheduledPaperWorkerSummary(
                status="skipped",
                run_id=None,
                cycle_summary=None,
                error_summary="another scheduled_paper_worker run is already running",
            )

        run_id = _run_id(request)
        provider = _provider_source(request.provider)
        with session_scope(self.engine) as session:
            LiveRunRepository(session).start(
                run_id=run_id,
                run_type="scheduled_paper_worker",
                provider=provider,
                league=request.league,
                season=request.season,
                model_name=request.model or self.settings.model_name,
            )

        if not self.settings.live_collection_enabled:
            error_summary = "LIVE_COLLECTION_ENABLED must be true"
            with session_scope(self.engine) as session:
                LiveRunRepository(session).fail(
                    run_id=run_id,
                    errors_count=1,
                    error_summary=error_summary,
                )
            return ScheduledPaperWorkerSummary(
                status="failed",
                run_id=run_id,
                cycle_summary=None,
                error_summary=error_summary,
            )

        try:
            cycle_summary = LivePaperCycleService(self.engine, self.settings).run(
                LivePaperCycleRequest(
                    provider=request.provider,
                    snapshot=request.snapshot,
                    model=request.model,
                    league=request.league,
                    season=request.season,
                )
            )
        except Exception as exc:
            error_summary = str(exc)
            with session_scope(self.engine) as session:
                LiveRunRepository(session).fail(
                    run_id=run_id,
                    errors_count=1,
                    error_summary=error_summary,
                )
            return ScheduledPaperWorkerSummary(
                status="failed",
                run_id=run_id,
                cycle_summary=None,
                error_summary=error_summary,
            )

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            if cycle_summary.status == "failed":
                live_runs.fail(
                    run_id=run_id,
                    errors_count=cycle_summary.errors_count,
                    error_summary="paper cycle failed",
                    items_read=cycle_summary.items_read,
                    items_created=cycle_summary.items_created,
                    items_updated=cycle_summary.items_updated,
                    items_skipped=cycle_summary.items_skipped,
                )
            else:
                live_runs.complete(
                    run_id=run_id,
                    items_read=cycle_summary.items_read,
                    items_created=cycle_summary.items_created,
                    items_updated=cycle_summary.items_updated,
                    items_skipped=cycle_summary.items_skipped,
                )

        return ScheduledPaperWorkerSummary(
            status=cycle_summary.status,
            run_id=run_id,
            cycle_summary=cycle_summary,
            error_summary="paper cycle failed" if cycle_summary.status == "failed" else None,
        )


def _running_worker_exists(engine: Engine) -> bool:
    with session_scope(engine) as session:
        running_id = session.scalar(
            select(LiveRun.id).where(
                LiveRun.run_type == "scheduled_paper_worker",
                LiveRun.status == "running",
            )
        )
        return running_id is not None


def _run_id(request: ScheduledPaperWorkerRequest) -> str:
    model = request.model or "default"
    return (
        "scheduled_paper_worker:"
        f"{request.provider}:{model}:{request.snapshot.resolve().as_posix()}:{utc_now_iso()}"
    )


def _provider_source(provider: str) -> str:
    if provider == "misli-public":
        return "misli_public"
    return provider
