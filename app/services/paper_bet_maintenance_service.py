from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import Match, PaperBet, Prediction
from app.db.repositories import DecisionLogRepository


@dataclass(frozen=True)
class UnsafePaperBetCleanupSummary:
    items_read: int
    items_created: int
    items_updated: int
    items_skipped: int
    errors_count: int
    unsafe_count: int
    risk_flag_counts: dict[str, int]
    dry_run: bool


class PaperBetMaintenanceService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def void_unsafe_open_bets(
        self,
        *,
        dry_run: bool = True,
        now: datetime | None = None,
        min_confidence: float = 0.5,
    ) -> UnsafePaperBetCleanupSummary:
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        items_read = 0
        items_updated = 0
        items_skipped = 0
        unsafe_count = 0
        risk_flag_counts: Counter[str] = Counter()

        with session_scope(self.engine) as session:
            log_repository = DecisionLogRepository(session)
            rows = session.execute(
                select(PaperBet, Prediction, Match)
                .join(Prediction, PaperBet.prediction_id == Prediction.id)
                .join(Match, PaperBet.match_id == Match.id)
                .where(PaperBet.status == "open")
                .order_by(PaperBet.created_at.desc(), PaperBet.id.desc())
            ).all()

            for paper_bet, prediction, match in rows:
                items_read += 1
                risk_flags = _unsafe_open_bet_flags(
                    paper_bet,
                    prediction,
                    match,
                    now=current_time,
                    min_confidence=min_confidence,
                )
                if not risk_flags:
                    items_skipped += 1
                    continue

                unsafe_count += 1
                risk_flag_counts.update(risk_flags)
                if dry_run:
                    continue

                paper_bet.status = "void"
                paper_bet.profit_loss_units = 0.0
                paper_bet.settled_at = current_time.isoformat()
                items_updated += 1
                log_repository.add(
                    match_id=paper_bet.match_id,
                    stage="VOID_UNSAFE_PAPER_BET",
                    level="WARNING",
                    message=f"Voided unsafe open paper bet: {', '.join(risk_flags)}",
                )

        return UnsafePaperBetCleanupSummary(
            items_read=items_read,
            items_created=0,
            items_updated=items_updated,
            items_skipped=items_skipped,
            errors_count=0,
            unsafe_count=unsafe_count,
            risk_flag_counts=dict(sorted(risk_flag_counts.items())),
            dry_run=dry_run,
        )


def _unsafe_open_bet_flags(
    paper_bet: PaperBet,
    prediction: Prediction,
    match: Match,
    *,
    now: datetime,
    min_confidence: float,
) -> list[str]:
    risk_flags: list[str] = []
    if paper_bet.expected_value <= 0:
        risk_flags.append("negative_expected_value")
    if prediction.confidence_score is not None and prediction.confidence_score < min_confidence:
        risk_flags.append("low_confidence")
    kickoff_time = _parse_iso_datetime(match.kickoff_time)
    if kickoff_time is not None and kickoff_time <= now:
        risk_flags.append("past_kickoff_open")
    return risk_flags


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
