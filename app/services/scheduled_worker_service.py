import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from sqlalchemy import Engine, select

from app.config import Settings
from app.db.engine import session_scope
from app.db.models import LiveRun, utc_now_iso
from app.db.repositories import LiveRunRepository
from app.services.ai_analysis_service import AIAnalysisService
from app.services.combination_service import CombinationService
from app.services.daily_paper_journal_service import DailyPaperJournalService
from app.services.live_cycle_service import (
    LivePaperCycleRequest,
    LivePaperCycleService,
    LivePaperCycleSummary,
)
from app.services.misli_result_service import MisliResultService
from app.services.prediction_service import StepSummary
from app.services.recommendation_service import RecommendationService
from app.services.settlement_service import SettlementService

MAX_SNAPSHOT_DOWNLOAD_BYTES = 5_000_000


@dataclass(frozen=True)
class ScheduledPaperWorkerRequest:
    provider: str
    snapshot: Path | None = None
    snapshot_url: str | None = None
    model: str | None = None
    league: str | None = None
    season: str | None = None


@dataclass(frozen=True)
class ScheduledPaperWorkerSummary:
    status: str
    run_id: str | None
    cycle_summary: LivePaperCycleSummary | None
    error_summary: str | None = None
    snapshot_path: Path | None = None
    recommendation_items: int = 0
    combination_items: int = 0
    ai_review_id: int | None = None
    journal_id: int | None = None
    result_summary: StepSummary | None = None
    settlement_summary: StepSummary | None = None

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
        snapshot_path = _snapshot_reference(request)
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
                snapshot_path=snapshot_path,
            )

        try:
            resolved_snapshot = resolve_worker_snapshot(request)
            cycle_summary = LivePaperCycleService(self.engine, self.settings).run(
                LivePaperCycleRequest(
                    provider=request.provider,
                    snapshot=resolved_snapshot,
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
                snapshot_path=snapshot_path,
            )

        recommendation_items = 0
        combination_items = 0
        ai_review_id = None
        journal_id = None
        settlement_summary = None
        result_summary = None
        if cycle_summary.status == "completed":
            recommendation_summary = RecommendationService(self.engine, self.settings).generate()
            recommendation_items = recommendation_summary.items_created
            combination_summary = CombinationService(self.engine).generate()
            combination_items = combination_summary.items_created
            if self.settings.misli_result_fetch_enabled:
                result_summary = MisliResultService(self.engine).collect_due_results(
                    dry_run=self.settings.misli_result_preview_mode,
                )
            if self.settings.scheduled_settlement_enabled:
                settlement_summary = SettlementService(self.engine).settle_results()
            ai_review = AIAnalysisService(self.engine).analyze_recommendation_review()
            ai_review_id = ai_review.id
            journal = DailyPaperJournalService(
                self.engine,
                product_timezone=self.settings.product_timezone,
            ).generate()
            journal_id = int(journal["id"]) if journal.get("id") is not None else None

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
            snapshot_path=resolved_snapshot,
            recommendation_items=recommendation_items,
            combination_items=combination_items,
            ai_review_id=ai_review_id,
            journal_id=journal_id,
            result_summary=result_summary,
            settlement_summary=settlement_summary,
        )


def resolve_worker_snapshot(request: ScheduledPaperWorkerRequest) -> Path:
    if request.snapshot_url:
        return _download_snapshot_url(request.snapshot_url)
    if request.snapshot is not None:
        return request.snapshot
    raise ValueError("Either snapshot or snapshot_url must be provided")


def _download_snapshot_url(snapshot_url: str) -> Path:
    parsed = urlparse(snapshot_url)
    if parsed.scheme != "https":
        raise ValueError("snapshot_url must be an https URL")

    target = Path("data/live-snapshots") / f"scheduled-worker-{utc_now_iso_filename()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    with urlopen(snapshot_url, timeout=30) as response:
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            raise ValueError(f"snapshot_url must return JSON, got content-type {content_type!r}")
        payload = response.read(MAX_SNAPSHOT_DOWNLOAD_BYTES + 1)

    if len(payload) > MAX_SNAPSHOT_DOWNLOAD_BYTES:
        raise ValueError("snapshot_url response is too large")

    parsed_json = json.loads(payload.decode("utf-8"))
    target.write_text(json.dumps(parsed_json, indent=2) + "\n", encoding="utf-8")
    return target


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
    snapshot_ref = _snapshot_reference(request)
    return (
        "scheduled_paper_worker:"
        f"{request.provider}:{model}:{snapshot_ref}:{utc_now_iso()}"
    )


def _snapshot_reference(request: ScheduledPaperWorkerRequest) -> str:
    if request.snapshot_url:
        parsed = urlparse(request.snapshot_url)
        return f"url:{parsed.netloc}{parsed.path}"
    if request.snapshot is not None:
        return request.snapshot.resolve().as_posix()
    return "snapshot:missing"


def utc_now_iso_filename() -> str:
    return utc_now_iso().replace(":", "-").replace("+", "_")


def _provider_source(provider: str) -> str:
    if provider == "misli-public":
        return "misli_public"
    return provider
