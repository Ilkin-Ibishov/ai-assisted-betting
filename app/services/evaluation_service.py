import json
from datetime import UTC, datetime

from sqlalchemy import Engine, select

from app.config import Settings
from app.core.evaluator import (
    EvaluationReport,
    Evaluator,
    SettledBetForEvaluation,
)
from app.db.engine import session_scope
from app.db.models import PaperBet, Prediction
from app.db.repositories import DecisionLogRepository, EvaluationRunRepository


class EvaluationService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def evaluate(self) -> EvaluationReport:
        start_time = datetime.now(UTC).isoformat()

        with session_scope(self.engine) as session:
            rows = list(
                session.execute(
                    select(PaperBet, Prediction).join(
                        Prediction,
                        PaperBet.prediction_id == Prediction.id,
                    )
                )
            )
            bets = [
                SettledBetForEvaluation(
                    status=paper_bet.status,
                    stake_units=paper_bet.stake_units,
                    odds_taken=paper_bet.odds_taken,
                    profit_loss_units=paper_bet.profit_loss_units or 0,
                    edge=prediction.edge,
                    model_probability=prediction.model_probability,
                )
                for paper_bet, prediction in rows
            ]
            report = Evaluator().evaluate(bets)
            end_time = datetime.now(UTC).isoformat()
            EvaluationRunRepository(session).add(
                run_name="cli_evaluation",
                market=self.settings.default_market,
                model_name=self.settings.model_name,
                model_version=self.settings.model_version,
                start_time=start_time,
                end_time=end_time,
                total_bets=report.total_bets,
                won=report.wins,
                lost=report.losses,
                voided=report.voids,
                profit_loss_units=report.profit_loss_units,
                roi=report.roi or 0,
                hit_rate=report.hit_rate,
                average_odds=report.average_odds,
                average_edge=report.average_edge,
                brier_score=report.brier_score,
                log_loss=report.log_loss,
                report_json=json.dumps(
                    _report_payload(report, self.settings),
                    sort_keys=True,
                ),
            )
            DecisionLogRepository(session).add(
                stage="EVALUATE",
                level="INFO",
                message="Stored evaluation run",
                output_json=json.dumps(_report_payload(report, self.settings), sort_keys=True),
            )
            return report


def format_evaluation_report(report: EvaluationReport) -> str:
    return "\n".join(
        [
            "Evaluation Run",
            "--------------",
            f"Total bets: {report.total_bets}",
            f"Settled bets: {report.settled_bets}",
            f"Wins: {report.wins}",
            f"Losses: {report.losses}",
            f"Voids: {report.voids}",
            f"Hit rate: {_format_optional(report.hit_rate)}",
            f"Total staked: {report.total_staked}",
            f"Profit/Loss: {report.profit_loss_units}",
            f"ROI: {_format_optional(report.roi)}",
            f"Average odds: {_format_optional(report.average_odds)}",
            f"Average edge: {_format_optional(report.average_edge)}",
            f"Brier score: {_format_optional(report.brier_score)}",
            f"Log loss: {_format_optional(report.log_loss)}",
        ]
    )


def _format_optional(value: float | None) -> str:
    return "n/a" if value is None else str(value)


def model_config_from_settings(settings: Settings) -> dict[str, str | float]:
    return {
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "elo_initial_rating": settings.elo_initial_rating,
        "elo_k_factor": settings.elo_k_factor,
        "elo_home_advantage": settings.elo_home_advantage,
    }


def report_payload_from_settings(
    report: EvaluationReport,
    settings: Settings,
) -> dict[str, object]:
    return _report_payload(report, settings)


def _report_payload(report: EvaluationReport, settings: Settings) -> dict[str, object]:
    payload = report.to_dict()
    payload["model_config"] = model_config_from_settings(settings)
    return payload
