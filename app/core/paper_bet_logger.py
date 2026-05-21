from app.db.models import Match, PaperBet, Prediction


class PaperBetLogger:
    def should_create(
        self,
        *,
        prediction: Prediction,
        match: Match,
        existing_bet: PaperBet | None,
    ) -> bool:
        return prediction.decision == "BET" and match.status != "completed" and existing_bet is None
