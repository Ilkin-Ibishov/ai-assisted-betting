import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.request import Request, urlopen

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import Match, ResultFetchJob
from app.db.repositories import (
    DecisionLogRepository,
    LiveRunRepository,
    ResultFetchJobRepository,
)
from app.providers.misli_results import match_misli_result, parse_misli_results_payload
from app.services.prediction_service import StepSummary

MISLI_RESULTS_URL = "https://apivx.misli.az/api/web/v1/statistics/sport/SOCCER/matches/live"
RESULT_NOT_FOUND_MESSAGE = "result not found in Misli response"
UNRESOLVABLE_RESULT_MESSAGE = "result unavailable after repeated Misli lookups"
UNRESOLVABLE_RESULT_LOOKUP_ATTEMPTS = 3
UNRESOLVABLE_RESULT_LOOKUP_AFTER = timedelta(days=2)


class MisliResultService:
    def __init__(
        self,
        engine: Engine,
        *,
        fetcher: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.engine = engine
        self.fetcher = fetcher or fetch_misli_results_payload

    def collect_due_results(
        self,
        *,
        now_iso: str | None = None,
        dry_run: bool = True,
        limit: int = 50,
    ) -> StepSummary:
        now = _parse_iso(now_iso) if now_iso else datetime.now(UTC)
        now_iso_value = now.isoformat()
        run_id = f"collect_results:misli-public:{now_iso_value}:dry_run={str(dry_run).lower()}"
        items_read = 0
        items_updated = 0
        items_skipped = 0
        errors: list[str] = []

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            live_runs.start(run_id=run_id, run_type="collect_results", provider="misli_public")
            _ensure_result_jobs(session, now)
            _retire_unresolvable_result_jobs(session, now)
            due_jobs = ResultFetchJobRepository(session).due(now_iso=now_iso_value, limit=limit)

        try:
            payload = self.fetcher()
            results = parse_misli_results_payload(payload)
        except Exception as exc:
            with session_scope(self.engine) as session:
                live_runs = LiveRunRepository(session)
                due_jobs = ResultFetchJobRepository(session).due(
                    now_iso=now_iso_value,
                    limit=limit,
                )
                for job in due_jobs:
                    job.attempt_count += 1
                    job.status = "failed"
                    job.last_error = str(exc)
                    job.next_attempt_at = _next_backoff(now, job.attempt_count)
                live_runs.fail(
                    run_id=run_id,
                    errors_count=1,
                    error_summary=str(exc),
                )
            return StepSummary(0, 0, 0, 0, 1)

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            logs = DecisionLogRepository(session)
            due_jobs = ResultFetchJobRepository(session).due(now_iso=now_iso_value, limit=limit)
            for job in due_jobs:
                items_read += 1
                match = session.get(Match, job.match_id)
                if match is None:
                    job.attempt_count += 1
                    job.status = "failed"
                    job.last_error = "match not found"
                    job.next_attempt_at = _next_backoff(now, job.attempt_count)
                    errors.append(f"Match not found for result job {job.id}")
                    items_skipped += 1
                    continue

                result = match_misli_result(match, results)
                job.attempt_count += 1
                if result is None:
                    job.status = "pending"
                    job.last_error = RESULT_NOT_FOUND_MESSAGE
                    job.next_attempt_at = _next_pending_attempt(now, match)
                    items_skipped += 1
                    continue

                job.last_result_payload_json = json.dumps(
                    result.raw_payload,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                job.last_error = None
                if result.status != "completed":
                    job.status = (
                        result.status
                        if result.status in {"postponed", "scheduled"}
                        else "pending"
                    )
                    job.next_attempt_at = _next_non_final_attempt(now, match, result.status)
                    items_skipped += 1
                    continue

                if result.home_score is None or result.away_score is None or result.result is None:
                    job.status = "pending"
                    job.last_error = "final result missing score"
                    job.next_attempt_at = _next_pending_attempt(now, match)
                    items_skipped += 1
                    continue

                if dry_run:
                    job.status = "preview_completed"
                    job.next_attempt_at = _next_pending_attempt(now, match)
                    items_skipped += 1
                    continue

                match.status = "completed"
                match.home_score = result.home_score
                match.away_score = result.away_score
                match.result = result.result
                match.raw_payload_json = json.dumps(
                    {
                        "source": "misli_public",
                        "source_match_id": match.source_match_id,
                        "misli_event_id": result.misli_event_id,
                        "home_score": result.home_score,
                        "away_score": result.away_score,
                        "result": result.result,
                        "raw_result": result.raw_payload,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                job.status = "completed"
                job.next_attempt_at = now_iso_value
                items_updated += 1
                logs.add(
                    match_id=match.id,
                    stage="COLLECT_RESULTS",
                    level="INFO",
                    message="Collected Misli public result",
                    input_json=job.last_result_payload_json,
                )

            if errors:
                live_runs.fail(
                    run_id=run_id,
                    errors_count=len(errors),
                    error_summary="\n".join(errors[:5]),
                    items_read=items_read,
                    items_updated=items_updated,
                    items_skipped=items_skipped,
                )
            else:
                live_runs.complete(
                    run_id=run_id,
                    items_read=items_read,
                    items_updated=items_updated,
                    items_skipped=items_skipped,
                )

        return StepSummary(items_read, 0, items_updated, items_skipped, len(errors))


def fetch_misli_results_payload() -> dict[str, Any]:
    request = Request(
        MISLI_RESULTS_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "PaperOddsLab/0.1 public-result-check",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def result_jobs_payload(
    engine: Engine,
    *,
    now_iso: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    now = _parse_iso(now_iso) if now_iso else datetime.now(UTC)
    now_iso_value = now.isoformat()
    with session_scope(engine) as session:
        rows = session.execute(
            select(ResultFetchJob, Match)
            .join(Match, ResultFetchJob.match_id == Match.id)
            .order_by(ResultFetchJob.next_attempt_at.asc(), ResultFetchJob.id.asc())
            .limit(max(1, min(limit, 500)))
        ).all()
        jobs = [_job_payload(job, match, now_iso_value) for job, match in rows]
    return {
        "summary": {
            "total": len(jobs),
            "due": sum(1 for job in jobs if job["is_due"]),
            "completed": sum(1 for job in jobs if job["status"] == "completed"),
            "postponed": sum(1 for job in jobs if job["status"] == "postponed"),
            "failed": sum(1 for job in jobs if job["status"] == "failed"),
            "unresolvable": sum(1 for job in jobs if job["status"] == "unresolvable"),
            "pending": sum(1 for job in jobs if job["status"] in {"pending", "scheduled"}),
        },
        "jobs": jobs,
    }


def _ensure_result_jobs(session, now: datetime) -> None:
    repository = ResultFetchJobRepository(session)
    matches = session.scalars(
        select(Match).where(Match.source == "misli_public", Match.status != "completed")
    ).all()
    for match in matches:
        event_id, detail_url = _misli_metadata(match)
        repository.ensure(
            match_id=match.id,
            source_match_id=match.source_match_id,
            misli_event_id=event_id,
            detail_url=detail_url,
            next_attempt_at=_initial_attempt_at(match, now),
        )


def _retire_unresolvable_result_jobs(session, now: datetime) -> None:
    rows = session.execute(
        select(ResultFetchJob, Match)
        .join(Match, ResultFetchJob.match_id == Match.id)
        .where(
            ResultFetchJob.status.in_(["pending", "failed"]),
            ResultFetchJob.last_error == RESULT_NOT_FOUND_MESSAGE,
            ResultFetchJob.attempt_count >= UNRESOLVABLE_RESULT_LOOKUP_ATTEMPTS,
        )
    ).all()
    for job, match in rows:
        kickoff = _parse_iso(match.kickoff_time)
        if now - kickoff < UNRESOLVABLE_RESULT_LOOKUP_AFTER:
            continue
        job.status = "unresolvable"
        job.last_error = UNRESOLVABLE_RESULT_MESSAGE
        job.next_attempt_at = now.isoformat()


def _misli_metadata(match: Match) -> tuple[str | None, str | None]:
    try:
        raw_payload = json.loads(match.raw_payload_json or "{}")
    except json.JSONDecodeError:
        raw_payload = {}
    event_id = raw_payload.get("event_id")
    if not event_id and match.source_match_id.startswith("misli:football:"):
        event_id = match.source_match_id.rsplit(":", 1)[-1]
    detail_url = raw_payload.get("detail_url")
    return (str(event_id) if event_id else None, str(detail_url) if detail_url else None)


def _initial_attempt_at(match: Match, now: datetime) -> str:
    kickoff = _parse_iso(match.kickoff_time)
    if kickoff > now:
        return (kickoff + timedelta(hours=2)).isoformat()
    return now.isoformat()


def _next_non_final_attempt(now: datetime, match: Match, status: str) -> str:
    if status == "postponed":
        return (now + timedelta(days=1)).isoformat()
    return _next_pending_attempt(now, match)


def _next_pending_attempt(now: datetime, match: Match) -> str:
    kickoff = _parse_iso(match.kickoff_time)
    if kickoff > now:
        return (kickoff + timedelta(hours=2)).isoformat()
    return (now + timedelta(minutes=30)).isoformat()


def _next_backoff(now: datetime, attempt_count: int) -> str:
    hours = min(24, max(1, 2 ** min(attempt_count, 5)))
    return (now + timedelta(hours=hours)).isoformat()


def _job_payload(job: ResultFetchJob, match: Match, now_iso: str) -> dict[str, Any]:
    return {
        "id": job.id,
        "match_id": job.match_id,
        "source_match_id": job.source_match_id,
        "misli_event_id": job.misli_event_id,
        "detail_url": job.detail_url,
        "status": job.status,
        "next_attempt_at": job.next_attempt_at,
        "attempt_count": job.attempt_count,
        "last_error": job.last_error,
        "is_due": job.status not in {"completed", "unresolvable"}
        and job.next_attempt_at <= now_iso,
        "match_label": f"{match.home_team} vs {match.away_team}",
        "kickoff_time": match.kickoff_time,
    }


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
