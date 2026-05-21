import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.repositories import (
    DecisionLogRepository,
    LiveRunRepository,
    MatchRepository,
    OddsSnapshotRepository,
)
from app.providers.misli_public import MisliPublicEvent, resolve_misli_public_event_date
from app.services.prediction_service import StepSummary

MISLI_PUBLIC_SOURCE = "misli_public"
MISLI_PUBLIC_BOOKMAKER = "Misli.az"


@dataclass(frozen=True)
class LiveCollectionRequest:
    provider: str
    snapshot: Path
    league: str | None = None
    season: str | None = None


class LiveCollectionService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def collect_matches(self, request: LiveCollectionRequest) -> StepSummary:
        _ensure_misli_provider(request.provider)
        payload = _read_snapshot(request.snapshot)
        run_id = _run_id("collect_matches", request)
        items_read = 0
        items_created = 0
        items_skipped = 0
        errors: list[str] = []

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            matches = MatchRepository(session)
            logs = DecisionLogRepository(session)
            live_runs.start(
                run_id=run_id,
                run_type="collect_matches",
                provider=MISLI_PUBLIC_SOURCE,
                league=request.league,
                season=request.season,
            )

            for raw_event in payload.get("events", []):
                items_read += 1
                event = _validate_event(raw_event, errors, payload)
                if event is None:
                    items_skipped += 1
                    continue

                existing = matches.get_by_source_id(MISLI_PUBLIC_SOURCE, event.source_match_id)
                if existing is not None:
                    items_skipped += 1
                    continue

                match = matches.add(
                    source=MISLI_PUBLIC_SOURCE,
                    source_match_id=event.source_match_id,
                    league=request.league or event.league,
                    season=request.season,
                    home_team=event.home_team,
                    away_team=event.away_team,
                    kickoff_time=_kickoff_iso(event.kickoff_date, event.kickoff_time),
                    status="scheduled",
                    raw_payload_json=json.dumps(raw_event, sort_keys=True, ensure_ascii=False),
                )
                items_created += 1
                logs.add(
                    match_id=match.id,
                    stage="COLLECT_MATCHES",
                    level="INFO",
                    message="Imported Misli public match",
                    input_json=match.raw_payload_json,
                )

            _finish_run(
                live_runs,
                run_id=run_id,
                errors=errors,
                items_read=items_read,
                items_created=items_created,
                items_updated=0,
                items_skipped=items_skipped,
            )

        return StepSummary(items_read, items_created, 0, items_skipped, len(errors))

    def collect_odds(self, request: LiveCollectionRequest) -> StepSummary:
        _ensure_misli_provider(request.provider)
        payload = _read_snapshot(request.snapshot)
        run_id = _run_id("collect_odds", request)
        items_read = 0
        items_created = 0
        items_skipped = 0
        errors: list[str] = []
        snapshot_time = str(payload.get("scraped_at") or "")

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            matches = MatchRepository(session)
            odds = OddsSnapshotRepository(session)
            logs = DecisionLogRepository(session)
            live_runs.start(
                run_id=run_id,
                run_type="collect_odds",
                provider=MISLI_PUBLIC_SOURCE,
                league=request.league,
                season=request.season,
            )

            for raw_event in payload.get("events", []):
                items_read += 1
                event = _validate_event(raw_event, errors, payload)
                if event is None:
                    items_skipped += 1
                    continue

                match = matches.get_by_source_id(MISLI_PUBLIC_SOURCE, event.source_match_id)
                if match is None:
                    errors.append(f"Missing imported match for odds: {event.source_match_id}")
                    items_skipped += 1
                    continue

                for raw_odd in event.odds:
                    if raw_odd.market != "1X2":
                        continue
                    if odds.exists_snapshot(
                        match_id=match.id,
                        source=MISLI_PUBLIC_SOURCE,
                        bookmaker=MISLI_PUBLIC_BOOKMAKER,
                        market=raw_odd.market,
                        selection=raw_odd.selection,
                        snapshot_time=snapshot_time,
                    ):
                        items_skipped += 1
                        continue

                    snapshot = odds.add(
                        match_id=match.id,
                        source=MISLI_PUBLIC_SOURCE,
                        bookmaker=MISLI_PUBLIC_BOOKMAKER,
                        market=raw_odd.market,
                        selection=raw_odd.selection,
                        odds_decimal=raw_odd.odds_decimal,
                        implied_probability=1 / raw_odd.odds_decimal,
                        snapshot_time=snapshot_time,
                        raw_payload_json=json.dumps(
                            raw_odd.model_dump(),
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                    )
                    items_created += 1
                    logs.add(
                        match_id=match.id,
                        stage="COLLECT_ODDS",
                        level="INFO",
                        message="Imported Misli public odds snapshot",
                        input_json=snapshot.raw_payload_json,
                    )

            _finish_run(
                live_runs,
                run_id=run_id,
                errors=errors,
                items_read=items_read,
                items_created=items_created,
                items_updated=0,
                items_skipped=items_skipped,
            )

        return StepSummary(items_read, items_created, 0, items_skipped, len(errors))


def _ensure_misli_provider(provider: str) -> None:
    if provider != "misli-public":
        raise ValueError("Only provider=misli-public is supported for manual live collection")


def _read_snapshot(snapshot: Path) -> dict:
    return json.loads(snapshot.read_text(encoding="utf-8"))


def _validate_event(
    raw_event: dict,
    errors: list[str],
    payload: dict,
) -> MisliPublicEvent | None:
    try:
        return MisliPublicEvent.model_validate(
            resolve_misli_public_event_date(raw_event, str(payload.get("scraped_at") or ""))
        )
    except ValidationError as exc:
        errors.append(str(exc))
        return None


def _kickoff_iso(kickoff_date: str, kickoff_time: str) -> str:
    local_datetime = datetime.strptime(
        f"{kickoff_date} {kickoff_time}",
        "%d.%m.%Y %H:%M",
    ).replace(tzinfo=ZoneInfo("Asia/Baku"))
    return local_datetime.isoformat()


def _run_id(run_type: str, request: LiveCollectionRequest) -> str:
    snapshot_name = request.snapshot.resolve().as_posix()
    return f"{run_type}:{request.provider}:{snapshot_name}"


def _finish_run(
    live_runs: LiveRunRepository,
    *,
    run_id: str,
    errors: list[str],
    items_read: int,
    items_created: int,
    items_updated: int,
    items_skipped: int,
) -> None:
    if errors:
        live_runs.fail(
            run_id=run_id,
            errors_count=len(errors),
            error_summary="\n".join(errors[:5]),
            items_read=items_read,
            items_created=items_created,
            items_updated=items_updated,
            items_skipped=items_skipped,
        )
        return

    live_runs.complete(
        run_id=run_id,
        items_read=items_read,
        items_created=items_created,
        items_updated=items_updated,
        items_skipped=items_skipped,
    )
