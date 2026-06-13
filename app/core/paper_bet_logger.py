from app.db.models import Match, PaperBet, Prediction

# Paper bets are research records, not real staking instructions. The gate now
# follows recommendation governance so watchlist-only low-confidence cold-start
# rows do not become paper-bet samples.
MIN_PAPER_BET_CONFIDENCE = 0.5


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
