from app.db.models import Match, PaperBet, Prediction

# Paper bets are research records, not real staking instructions. Keep the
# confidence gate above neutral cold noise while allowing positive-EV candidates
# to create enough paper samples for settlement and threshold learning.
MIN_PAPER_BET_CONFIDENCE = 0.1


class PaperBetLogger:
    def should_create(
        self,
        *,
        prediction: Prediction,
        match: Match,
        existing_bet: PaperBet | None,
    ) -> bool:
        return (
            prediction.decision == "BET"
            and match.status != "completed"
            and existing_bet is None
            and _confidence_is_sufficient(prediction.confidence_score)
        )


def _confidence_is_sufficient(confidence_score: float | None) -> bool:
    return confidence_score is None or confidence_score >= MIN_PAPER_BET_CONFIDENCE
