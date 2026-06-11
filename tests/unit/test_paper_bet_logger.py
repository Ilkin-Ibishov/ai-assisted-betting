from app.core.paper_bet_logger import PaperBetLogger


class _Prediction:
    def __init__(self, *, decision: str, confidence_score: float | None) -> None:
        self.decision = decision
        self.confidence_score = confidence_score


class _Match:
    def __init__(self, *, status: str = "scheduled") -> None:
        self.status = status


def test_paper_bet_logger_allows_low_confidence_research_samples() -> None:
    assert PaperBetLogger().should_create(
        prediction=_Prediction(decision="BET", confidence_score=0.133333),
        match=_Match(),
        existing_bet=None,
    )


def test_paper_bet_logger_rejects_tiny_confidence_noise() -> None:
    assert not PaperBetLogger().should_create(
        prediction=_Prediction(decision="BET", confidence_score=0.05),
        match=_Match(),
        existing_bet=None,
    )
