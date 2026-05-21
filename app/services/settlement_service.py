from datetime import UTC, datetime

from sqlalchemy import Engine, select

from app.core.result_settler import ResultSettler
from app.db.engine import session_scope
from app.db.models import Match, OddsSnapshot, PaperBet
from app.db.repositories import DecisionLogRepository
from app.services.prediction_service import StepSummary


class SettlementService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def settle_results(self) -> StepSummary:
        settler = ResultSettler()
        items_read = 0
        items_updated = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            log_repository = DecisionLogRepository(session)
            open_bets = list(session.scalars(select(PaperBet).where(PaperBet.status == "open")))

            for paper_bet in open_bets:
                items_read += 1
                match = session.get(Match, paper_bet.match_id)
                if (
                    match is None
                    or match.status != "completed"
                    or match.home_score is None
                    or match.away_score is None
                ):
                    items_skipped += 1
                    continue

                settlement = settler.settle(
                    market=paper_bet.market,
                    selection=paper_bet.selection,
                    odds_taken=paper_bet.odds_taken,
                    stake_units=paper_bet.stake_units,
                    home_score=match.home_score,
                    away_score=match.away_score,
                )
                closing_odds = _find_closing_odds(session, paper_bet)
                paper_bet.status = settlement.status
                paper_bet.profit_loss_units = settlement.profit_loss_units
                paper_bet.closing_odds = closing_odds
                paper_bet.clv = round(closing_odds - paper_bet.odds_taken, 6)
                paper_bet.settled_at = datetime.now(UTC).isoformat()
                items_updated += 1
                log_repository.add(
                    match_id=paper_bet.match_id,
                    stage="SETTLE_RESULT",
                    level="INFO",
                    message=f"Settled paper bet as {paper_bet.status}",
                )

        return StepSummary(items_read, 0, items_updated, items_skipped, 0)


def _find_closing_odds(session, paper_bet: PaperBet) -> float:
    closing_snapshot = session.scalar(
        select(OddsSnapshot)
        .where(
            OddsSnapshot.match_id == paper_bet.match_id,
            OddsSnapshot.market == paper_bet.market,
            OddsSnapshot.selection == paper_bet.selection,
            OddsSnapshot.is_closing.is_(True),
        )
        .order_by(OddsSnapshot.snapshot_time.desc())
    )
    if closing_snapshot is not None:
        return closing_snapshot.odds_decimal

    latest_snapshot = session.scalar(
        select(OddsSnapshot)
        .where(
            OddsSnapshot.match_id == paper_bet.match_id,
            OddsSnapshot.market == paper_bet.market,
            OddsSnapshot.selection == paper_bet.selection,
        )
        .order_by(OddsSnapshot.snapshot_time.desc())
    )
    return latest_snapshot.odds_decimal if latest_snapshot is not None else paper_bet.odds_taken

