import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine

from app.config import Settings
from app.db.engine import session_scope
from app.db.repositories import LiveRunRepository, MatchRepository
from app.providers.misli_public import MisliPublicEvent, resolve_misli_public_event_date
from app.services.live_collection_service import (
    LiveCollectionRequest,
    LiveCollectionService,
)
from app.services.prediction_service import PredictionService, StepSummary


@dataclass(frozen=True)
class LivePaperCycleRequest:
    provider: str
    snapshot: Path
    model: str | None = None
    league: str | None = None
    season: str | None = None


@dataclass(frozen=True)
class LivePaperCycleSummary:
    status: str
    collect_matches: StepSummary
    collect_odds: StepSummary
    generate_features: StepSummary
    generate_predictions: StepSummary
    write_paper_bets: StepSummary

    @property
    def items_read(self) -> int:
        return sum(summary.items_read for summary in self._stage_summaries())

    @property
    def items_created(self) -> int:
        return sum(summary.items_created for summary in self._stage_summaries())

    @property
    def items_updated(self) -> int:
        return sum(summary.items_updated for summary in self._stage_summaries())

    @property
    def items_skipped(self) -> int:
        return sum(summary.items_skipped for summary in self._stage_summaries())

    @property
    def errors_count(self) -> int:
        return sum(summary.errors_count for summary in self._stage_summaries())

    def _stage_summaries(self) -> tuple[StepSummary, ...]:
        return (
            self.collect_matches,
            self.collect_odds,
            self.generate_features,
            self.generate_predictions,
            self.write_paper_bets,
        )


class LivePaperCycleService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def run(self, request: LivePaperCycleRequest) -> LivePaperCycleSummary:
        run_id = _run_id(request)
        cycle_settings = (
            self.settings
            if request.model is None
            else self.settings.__class__(**{**self.settings.__dict__, "model_name": request.model})
        )
        with session_scope(self.engine) as session:
            LiveRunRepository(session).start(
                run_id=run_id,
                run_type="run_live_paper_cycle",
                provider=_provider_source(request.provider),
                league=request.league,
                season=request.season,
                model_name=cycle_settings.model_name,
            )

        collection_request = LiveCollectionRequest(
            provider=request.provider,
            snapshot=request.snapshot,
            league=request.league,
            season=request.season,
        )
        collection = LiveCollectionService(self.engine)
        predictions = PredictionService(self.engine, cycle_settings)

        collect_matches = collection.collect_matches(collection_request)
        collect_odds = collection.collect_odds(collection_request)
        scoped_match_ids = _snapshot_match_ids(self.engine, request)
        generate_features = predictions.generate_features_for_matches(
            scoped_match_ids,
            allow_cold_start_features=True,
        )
        generate_predictions = predictions.generate_predictions_for_matches(scoped_match_ids)
        write_paper_bets = predictions.write_paper_bets_for_matches(scoped_match_ids)

        summary = LivePaperCycleSummary(
            status="failed"
            if collect_matches.errors_count
            or collect_odds.errors_count
            or generate_features.errors_count
            or generate_predictions.errors_count
            or write_paper_bets.errors_count
            else "completed",
            collect_matches=collect_matches,
            collect_odds=collect_odds,
            generate_features=generate_features,
            generate_predictions=generate_predictions,
            write_paper_bets=write_paper_bets,
        )

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            if summary.status == "failed":
                live_runs.fail(
                    run_id=run_id,
                    errors_count=summary.errors_count,
                    error_summary=_error_summary(summary),
                    items_read=summary.items_read,
                    items_created=summary.items_created,
                    items_updated=summary.items_updated,
                    items_skipped=summary.items_skipped,
                )
            else:
                live_runs.complete(
                    run_id=run_id,
                    items_read=summary.items_read,
                    items_created=summary.items_created,
                    items_updated=summary.items_updated,
                    items_skipped=summary.items_skipped,
                )

        return summary


def _run_id(request: LivePaperCycleRequest) -> str:
    snapshot_name = request.snapshot.resolve().as_posix()
    model = request.model or "default"
    return f"run_live_paper_cycle:{request.provider}:{model}:{snapshot_name}"


def _provider_source(provider: str) -> str:
    if provider == "misli-public":
        return "misli_public"
    return provider


def _snapshot_match_ids(engine: Engine, request: LivePaperCycleRequest) -> set[int]:
    payload = json.loads(request.snapshot.read_text(encoding="utf-8"))
    source = _provider_source(request.provider)
    scraped_at = str(payload.get("scraped_at") or "")
    source_match_ids = {
        event.source_match_id
        for raw_event in payload.get("events", [])
        if (event := _valid_snapshot_event(raw_event, scraped_at)) is not None
    }
    if not source_match_ids:
        return set()
    with session_scope(engine) as session:
        matches = MatchRepository(session)
        return {
            match.id
            for source_match_id in source_match_ids
            if (match := matches.get_by_source_id(source, source_match_id)) is not None
        }


def _valid_snapshot_event(raw_event: dict, scraped_at: str) -> MisliPublicEvent | None:
    try:
        return MisliPublicEvent.model_validate(
            resolve_misli_public_event_date(raw_event, scraped_at)
        )
    except ValueError:
        return None


def _error_summary(summary: LivePaperCycleSummary) -> str:
    parts = []
    if summary.collect_matches.errors_count:
        parts.append(f"collect_matches errors={summary.collect_matches.errors_count}")
    if summary.collect_odds.errors_count:
        parts.append(f"collect_odds errors={summary.collect_odds.errors_count}")
    if summary.generate_features.errors_count:
        parts.append(f"generate_features errors={summary.generate_features.errors_count}")
    if summary.generate_predictions.errors_count:
        parts.append(f"generate_predictions errors={summary.generate_predictions.errors_count}")
    if summary.write_paper_bets.errors_count:
        parts.append(f"write_paper_bets errors={summary.write_paper_bets.errors_count}")
    return "; ".join(parts)
