import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import Match, PaperCombination, PaperRecommendation


@dataclass(frozen=True)
class RecommendationBacktestRequest:
    report_name: str = "recommendation_backtest"
    min_edge: float = 0.0
    min_confidence: float = 0.0
    include_grades: tuple[str, ...] = ("recommended", "lean", "watch")


class RecommendationBacktestService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def backtest(self, request: RecommendationBacktestRequest) -> dict[str, Any]:
        singles, combinations = _load_backtest_inputs(self.engine, request)
        single_bets = [_single_backtest_bet(row) for row in singles]
        single_bets = [bet for bet in single_bets if bet is not None]
        combination_bets = [_combination_backtest_bet(row, single_bets) for row in combinations]
        combination_bets = [bet for bet in combination_bets if bet is not None]

        singles_metrics = _metrics(single_bets)
        combinations_metrics = _metrics(combination_bets)
        return {
            "metadata": {
                "report_type": "recommendation_backtest",
                "report_name": request.report_name,
                "generated_at": datetime.now(UTC).isoformat(),
                "min_edge": request.min_edge,
                "min_confidence": request.min_confidence,
                "include_grades": list(request.include_grades),
            },
            "dashboard_summary": {
                "name": request.report_name,
                "total_settled_bets": (
                    singles_metrics["settled_bets"] + combinations_metrics["settled_bets"]
                ),
                "singles_roi": singles_metrics["roi"],
                "combinations_roi": combinations_metrics["roi"],
            },
            "singles": singles_metrics,
            "combinations": combinations_metrics,
            "edge_buckets": _bucket_metrics(single_bets, _edge_bucket),
            "market_buckets": _bucket_metrics(single_bets, lambda bet: bet["market"]),
            "model_provider_splits": _bucket_metrics(
                single_bets,
                lambda bet: f"{bet['model_name']}/{bet['bookmaker']}",
            ),
            "threshold_sensitivity": _threshold_sensitivity(singles),
        }

    def export(
        self,
        request: RecommendationBacktestRequest,
        *,
        reports_dir: Path = Path("reports"),
    ) -> tuple[Path, Path, dict[str, Any]]:
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_report_name(request.report_name)
        report = self.backtest(request)
        csv_path = reports_dir / f"{safe_name}_recommendation_backtest.csv"
        json_path = reports_dir / f"{safe_name}_recommendation_backtest.json"
        comparison_path = reports_dir / f"{safe_name}_comparison.json"
        _write_summary_csv(csv_path, report)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        comparison_path.write_text(
            json.dumps(_dashboard_comparison_report(report), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return csv_path, json_path, report


def _load_backtest_inputs(
    engine: Engine,
    request: RecommendationBacktestRequest,
) -> tuple[list[tuple[PaperRecommendation, Match]], list[PaperCombination]]:
    with session_scope(engine) as session:
        singles = list(
            session.execute(
                select(PaperRecommendation, Match)
                .join(Match, PaperRecommendation.match_id == Match.id)
                .where(
                    PaperRecommendation.status == "active",
                    PaperRecommendation.grade.in_(request.include_grades),
                    Match.status == "completed",
                )
                .order_by(PaperRecommendation.created_at.asc(), PaperRecommendation.id.asc())
            )
        )
        filtered_singles = [
            (recommendation, match)
            for recommendation, match in singles
            if _passes_thresholds(recommendation, request.min_edge, request.min_confidence)
        ]
        combinations = list(
            session.scalars(
                select(PaperCombination)
                .where(PaperCombination.status == "active")
                .order_by(PaperCombination.rank.asc(), PaperCombination.id.asc())
            )
        )
    return filtered_singles, combinations


def _single_backtest_bet(row: tuple[PaperRecommendation, Match]) -> dict[str, Any] | None:
    recommendation, match = row
    if recommendation.current_odds is None or recommendation.model_probability is None:
        return None
    if match.result not in {"HOME", "DRAW", "AWAY"}:
        return None
    won = recommendation.selection == match.result
    profit_loss = float(recommendation.current_odds) - 1 if won else -1.0
    return {
        "id": recommendation.id,
        "status": "won" if won else "lost",
        "stake_units": 1.0,
        "profit_loss_units": round(profit_loss, 6),
        "odds": float(recommendation.current_odds),
        "model_probability": float(recommendation.model_probability),
        "edge": float(recommendation.edge or 0),
        "market": recommendation.market,
        "bookmaker": recommendation.bookmaker,
        "model_name": recommendation.model_name,
        "grade": recommendation.grade,
        "confidence_score": recommendation.confidence_score,
    }


def _combination_backtest_bet(
    combination: PaperCombination,
    single_bets: list[dict[str, Any]],
) -> dict[str, Any] | None:
    single_by_id = {int(bet["id"]): bet for bet in single_bets}
    leg_ids = [int(value) for value in json.loads(combination.leg_recommendation_ids_json)]
    legs = [single_by_id.get(leg_id) for leg_id in leg_ids]
    if any(leg is None for leg in legs):
        return None
    won = all(leg["status"] == "won" for leg in legs if leg is not None)
    profit_loss = float(combination.combined_odds) - 1 if won else -1.0
    return {
        "id": combination.id,
        "status": "won" if won else "lost",
        "stake_units": 1.0,
        "profit_loss_units": round(profit_loss, 6),
        "odds": float(combination.combined_odds),
        "model_probability": float(combination.estimated_probability),
        "edge": float(combination.combined_expected_value),
        "market": "combination",
        "bookmaker": "mixed",
        "model_name": combination.model_name,
        "grade": combination.grade,
        "confidence_score": combination.confidence_score,
    }


def _metrics(bets: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [bet for bet in bets if bet["status"] in {"won", "lost"}]
    wins = sum(1 for bet in settled if bet["status"] == "won")
    losses = sum(1 for bet in settled if bet["status"] == "lost")
    total_staked = float(len(settled))
    profit_loss = round(sum(float(bet["profit_loss_units"]) for bet in settled), 6)
    return {
        "total_bets": len(bets),
        "settled_bets": len(settled),
        "wins": wins,
        "losses": losses,
        "profit_loss_units": profit_loss,
        "roi": _round_or_none(profit_loss / total_staked if total_staked else None),
        "hit_rate": _round_or_none(wins / len(settled) if settled else None),
        "average_odds": _average([float(bet["odds"]) for bet in bets]),
        "average_edge": _average([float(bet["edge"]) for bet in bets]),
        "brier_score": _average([_brier(bet) for bet in settled]),
        "log_loss": _average([_log_loss(bet) for bet in settled]),
        "max_drawdown_units": _max_drawdown(settled),
    }


def _bucket_metrics(
    bets: list[dict[str, Any]],
    bucket_selector,
) -> dict[str, dict[str, Any]]:
    buckets = sorted({str(bucket_selector(bet)) for bet in bets})
    return {
        bucket: _metrics([bet for bet in bets if str(bucket_selector(bet)) == bucket])
        for bucket in buckets
    }


def _threshold_sensitivity(rows: list[tuple[PaperRecommendation, Match]]) -> list[dict[str, Any]]:
    scenarios = [
        {"min_edge": 0.0, "min_confidence": 0.0},
        {"min_edge": 0.05, "min_confidence": 0.6},
        {"min_edge": 0.1, "min_confidence": 0.7},
    ]
    output = []
    for scenario in scenarios:
        bets = [
            bet
            for row in rows
            if _passes_thresholds(row[0], scenario["min_edge"], scenario["min_confidence"])
            if (bet := _single_backtest_bet(row)) is not None
        ]
        metrics = _metrics(bets)
        output.append({**scenario, **metrics})
    return output


def _passes_thresholds(
    recommendation: PaperRecommendation,
    min_edge: float,
    min_confidence: float,
) -> bool:
    if recommendation.edge is None or recommendation.edge < min_edge:
        return False
    if recommendation.confidence_score is None:
        return min_confidence <= 0
    return recommendation.confidence_score >= min_confidence


def _write_summary_csv(path: Path, report: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "segment",
                "settled_bets",
                "wins",
                "losses",
                "profit_loss_units",
                "roi",
                "hit_rate",
                "max_drawdown_units",
            ],
        )
        writer.writeheader()
        for segment in ("singles", "combinations"):
            row = report[segment]
            writer.writerow(
                {
                    "segment": segment,
                    "settled_bets": row["settled_bets"],
                    "wins": row["wins"],
                    "losses": row["losses"],
                    "profit_loss_units": row["profit_loss_units"],
                    "roi": row["roi"],
                    "hit_rate": row["hit_rate"],
                    "max_drawdown_units": row["max_drawdown_units"],
                }
            )


def _dashboard_comparison_report(report: dict[str, Any]) -> dict[str, Any]:
    runs = [
        _dashboard_run("recommendation_singles", report["singles"]),
        _dashboard_run("recommendation_combinations", report["combinations"]),
    ]
    return {
        "metadata": {
            **report["metadata"],
            "models": [run["model"] for run in runs],
            "bookmakers": ["paper"],
            "league": "recommendation_backtest",
            "season": None,
        },
        "rankings": _dashboard_rankings(runs),
        "runs": runs,
        "recommendation_backtest": report,
    }


def _dashboard_run(model: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "bookmaker": "paper",
        "total_bets": metrics["total_bets"],
        "settled_bets": metrics["settled_bets"],
        "wins": metrics["wins"],
        "losses": metrics["losses"],
        "profit_loss_units": metrics["profit_loss_units"],
        "roi": metrics["roi"],
        "hit_rate": metrics["hit_rate"],
        "average_odds": metrics["average_odds"],
        "average_edge": metrics["average_edge"],
        "brier_score": metrics["brier_score"],
        "log_loss": metrics["log_loss"],
        "max_drawdown_units": metrics["max_drawdown_units"],
    }


def _dashboard_rankings(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    return {
        "best_roi": _best_run(runs, "roi", reverse=True),
        "best_hit_rate": _best_run(runs, "hit_rate", reverse=True),
        "best_brier_score": _best_run(runs, "brier_score", reverse=False),
        "best_log_loss": _best_run(runs, "log_loss", reverse=False),
        "lowest_drawdown": _best_run(runs, "max_drawdown_units", reverse=False),
    }


def _best_run(
    runs: list[dict[str, Any]],
    metric: str,
    *,
    reverse: bool,
) -> dict[str, Any] | None:
    candidates = [run for run in runs if run.get(metric) is not None]
    if not candidates:
        return None
    selected = sorted(candidates, key=lambda run: float(run[metric]), reverse=reverse)[0]
    return {
        "model": selected["model"],
        "bookmaker": selected["bookmaker"],
        "value": selected[metric],
    }


def _edge_bucket(bet: dict[str, Any]) -> str:
    edge = float(bet["edge"])
    if edge < 0.02:
        return "<0.02"
    if edge < 0.05:
        return "0.02-0.05"
    if edge < 0.1:
        return "0.05-0.10"
    return "0.10+"


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _brier(bet: dict[str, Any]) -> float:
    actual = 1 if bet["status"] == "won" else 0
    return (float(bet["model_probability"]) - actual) ** 2


def _log_loss(bet: dict[str, Any]) -> float:
    actual = 1 if bet["status"] == "won" else 0
    probability = max(0.001, min(0.999, float(bet["model_probability"])))
    return -(actual * math.log(probability) + (1 - actual) * math.log(1 - probability))


def _max_drawdown(bets: list[dict[str, Any]]) -> float:
    peak = 0.0
    cumulative = 0.0
    max_drawdown = 0.0
    for bet in bets:
        cumulative += float(bet["profit_loss_units"])
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return round(max_drawdown, 6)


def _safe_report_name(report_name: str) -> str:
    safe_characters = [
        character if character.isalnum() or character in "-_" else "_"
        for character in report_name
    ]
    return "".join(safe_characters).strip("_") or "recommendation_backtest"
