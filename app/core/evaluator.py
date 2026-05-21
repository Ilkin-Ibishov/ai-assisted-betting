import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SettledBetForEvaluation:
    status: str
    stake_units: float
    odds_taken: float
    profit_loss_units: float
    edge: float
    model_probability: float


@dataclass(frozen=True)
class EvaluationReport:
    total_bets: int
    settled_bets: int
    wins: int
    losses: int
    voids: int
    total_staked: float
    profit_loss_units: float
    roi: float | None
    hit_rate: float | None
    average_odds: float | None
    average_edge: float | None
    brier_score: float | None
    log_loss: float | None
    probability_buckets: dict[str, dict[str, int | float | None]]
    odds_buckets: dict[str, dict[str, int | float | None]]
    edge_buckets: dict[str, dict[str, int | float | None]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Evaluator:
    def evaluate(self, bets: list[SettledBetForEvaluation]) -> EvaluationReport:
        settled_bets = [bet for bet in bets if bet.status in {"won", "lost", "void"}]
        wins = sum(1 for bet in settled_bets if bet.status == "won")
        losses = sum(1 for bet in settled_bets if bet.status == "lost")
        voids = sum(1 for bet in settled_bets if bet.status == "void")
        total_staked = sum(bet.stake_units for bet in settled_bets)
        profit_loss_units = round(sum(bet.profit_loss_units for bet in settled_bets), 6)
        non_void_settled = [bet for bet in settled_bets if bet.status != "void"]

        return EvaluationReport(
            total_bets=len(bets),
            settled_bets=len(settled_bets),
            wins=wins,
            losses=losses,
            voids=voids,
            total_staked=round(total_staked, 6),
            profit_loss_units=profit_loss_units,
            roi=_round_or_none(profit_loss_units / total_staked if total_staked else None),
            hit_rate=_round_or_none(wins / len(non_void_settled) if non_void_settled else None),
            average_odds=_average([bet.odds_taken for bet in bets]),
            average_edge=_average([bet.edge for bet in bets]),
            brier_score=_average([_brier(bet) for bet in non_void_settled]),
            log_loss=_average([_log_loss(bet) for bet in non_void_settled]),
            probability_buckets=_bucket_report(
                bets,
                lambda bet: _probability_bucket(bet.model_probability),
                PROBABILITY_BUCKET_LABELS,
            ),
            odds_buckets=_bucket_report(
                bets,
                lambda bet: _odds_bucket(bet.odds_taken),
                ODDS_BUCKET_LABELS,
            ),
            edge_buckets=_bucket_report(
                bets,
                lambda bet: _edge_bucket(bet.edge),
                EDGE_BUCKET_LABELS,
            ),
        )


PROBABILITY_BUCKET_LABELS = [
    "0.00-0.10",
    "0.10-0.20",
    "0.20-0.30",
    "0.30-0.40",
    "0.40-0.50",
    "0.50-0.60",
    "0.60-0.70",
    "0.70-0.80",
    "0.80-0.90",
    "0.90-1.00",
]

ODDS_BUCKET_LABELS = [
    "1.00-1.50",
    "1.51-2.00",
    "2.01-2.50",
    "2.51-3.00",
    "3.01-3.50",
    "3.51+",
]

EDGE_BUCKET_LABELS = [
    "<0.02",
    "0.02-0.04",
    "0.04-0.06",
    "0.06-0.08",
    "0.08+",
]


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _brier(bet: SettledBetForEvaluation) -> float:
    actual = 1 if bet.status == "won" else 0
    return (bet.model_probability - actual) ** 2


def _log_loss(bet: SettledBetForEvaluation) -> float:
    actual = 1 if bet.status == "won" else 0
    probability = max(0.001, min(0.999, bet.model_probability))
    return -(actual * math.log(probability) + (1 - actual) * math.log(1 - probability))


def _bucket_report(
    bets: list[SettledBetForEvaluation],
    bucket_selector,
    labels: list[str],
) -> dict[str, dict[str, int | float | None]]:
    return {
        label: _bucket_metrics([bet for bet in bets if bucket_selector(bet) == label])
        for label in labels
    }


def _bucket_metrics(bets: list[SettledBetForEvaluation]) -> dict[str, int | float | None]:
    wins = sum(1 for bet in bets if bet.status == "won")
    losses = sum(1 for bet in bets if bet.status == "lost")
    voids = sum(1 for bet in bets if bet.status == "void")
    total_staked = sum(bet.stake_units for bet in bets if bet.status in {"won", "lost", "void"})
    profit_loss_units = round(sum(bet.profit_loss_units for bet in bets), 6)
    return {
        "bets": len(bets),
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "profit_loss_units": profit_loss_units,
        "roi": _round_or_none(profit_loss_units / total_staked if total_staked else None),
        "average_odds": _average([bet.odds_taken for bet in bets]),
        "average_edge": _average([bet.edge for bet in bets]),
        "brier_score": _average(
            [_brier(bet) for bet in bets if bet.status in {"won", "lost"}]
        ),
    }


def _probability_bucket(probability: float) -> str:
    if probability >= 0.9:
        return "0.90-1.00"
    index = max(0, int(probability * 10))
    return PROBABILITY_BUCKET_LABELS[index]


def _odds_bucket(odds: float) -> str:
    if odds <= 1.5:
        return "1.00-1.50"
    if odds <= 2.0:
        return "1.51-2.00"
    if odds <= 2.5:
        return "2.01-2.50"
    if odds <= 3.0:
        return "2.51-3.00"
    if odds <= 3.5:
        return "3.01-3.50"
    return "3.51+"


def _edge_bucket(edge: float) -> str:
    if edge < 0.02:
        return "<0.02"
    if edge < 0.04:
        return "0.02-0.04"
    if edge < 0.06:
        return "0.04-0.06"
    if edge < 0.08:
        return "0.06-0.08"
    return "0.08+"
