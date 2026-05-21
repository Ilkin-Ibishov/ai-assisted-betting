import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.repositories import DecisionLogRepository, LiveRunRepository, MatchRepository
from app.services.prediction_service import StepSummary


@dataclass(frozen=True)
class LiveResultRequest:
    provider: str
    path: Path
    league: str | None = None
    season: str | None = None


class LiveResultService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def collect_results(self, request: LiveResultRequest) -> StepSummary:
        if request.provider != "manual":
            raise ValueError("Only provider=manual is supported for result collection")

        payload = json.loads(request.path.read_text(encoding="utf-8"))
        run_id = f"collect_results:{request.provider}:{request.path.resolve().as_posix()}"
        items_read = 0
        items_updated = 0
        items_skipped = 0
        errors: list[str] = []

        with session_scope(self.engine) as session:
            live_runs = LiveRunRepository(session)
            matches = MatchRepository(session)
            logs = DecisionLogRepository(session)
            live_runs.start(
                run_id=run_id,
                run_type="collect_results",
                provider=request.provider,
                league=request.league,
                season=request.season,
            )

            for raw_result in payload.get("results", []):
                items_read += 1
                source = str(raw_result.get("source") or "")
                source_match_id = str(raw_result.get("source_match_id") or "")
                match = matches.get_by_source_id(source, source_match_id)
                if match is None:
                    errors.append(f"Missing match for result: {source}/{source_match_id}")
                    items_skipped += 1
                    continue

                home_score = int(raw_result["home_score"])
                away_score = int(raw_result["away_score"])
                result = str(raw_result.get("result") or _result_from_score(home_score, away_score))
                if (
                    match.status == "completed"
                    and match.home_score == home_score
                    and match.away_score == away_score
                    and match.result == result
                ):
                    items_skipped += 1
                    continue

                match.status = "completed"
                match.home_score = home_score
                match.away_score = away_score
                match.result = result
                match.raw_payload_json = json.dumps(raw_result, sort_keys=True, ensure_ascii=False)
                items_updated += 1
                logs.add(
                    match_id=match.id,
                    stage="COLLECT_RESULTS",
                    level="INFO",
                    message="Collected manual live result",
                    input_json=match.raw_payload_json,
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


def _result_from_score(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"
