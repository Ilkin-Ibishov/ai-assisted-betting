from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class ValueDecision:
    decision: str
    expected_value: float | None
    reason: str


class ValueDetector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        *,
        edge: float,
        odds_decimal: float,
        model_probability: float | None = None,
    ) -> ValueDecision:
        if edge < self.settings.min_edge:
            return ValueDecision("SKIP", None, "edge below minimum")
        if odds_decimal < self.settings.min_odds:
            return ValueDecision("SKIP", None, "odds below minimum")
        if odds_decimal > self.settings.max_odds:
            return ValueDecision("SKIP", None, "odds above maximum")

        probability = model_probability if model_probability is not None else edge
        expected_value = probability * (odds_decimal - 1) - (1 - probability)
        if expected_value <= 0:
            return ValueDecision("SKIP", round(expected_value, 6), "expected value not positive")
        return ValueDecision("BET", round(expected_value, 6), "edge and odds passed value rules")
