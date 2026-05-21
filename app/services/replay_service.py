import csv
import json
from pathlib import Path

from sqlalchemy import Engine, select

from app.config import Settings
from app.db.engine import session_scope
from app.db.migrations import init_db
from app.db.models import Match, PaperBet, Prediction
from app.services.evaluation_service import (
    EvaluationService,
    format_evaluation_report,
    report_payload_from_settings,
)
from app.services.football_data_service import FootballDataImportRequest, FootballDataImportService
from app.services.prediction_service import PredictionService
from app.services.settlement_service import SettlementService


class ReplayService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def replay_football_data(
        self,
        *,
        league: str,
        season: str,
        bookmaker: str = "B365",
        path: Path | None = None,
        url: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        min_history: int = 3,
        report_name: str | None = None,
    ) -> str:
        init_db(self.settings.database_url)
        FootballDataImportService(self.engine).import_csv(
            FootballDataImportRequest(
                league=league,
                season=season,
                bookmaker=bookmaker,
                path=path,
                url=url,
            )
        )
        self._prepare_completed_matches_as_replay_candidates(
            from_date=from_date,
            to_date=to_date,
            min_history=min_history,
        )

        prediction_service = PredictionService(self.engine, self.settings)
        feature_summary = prediction_service.generate_features()
        prediction_summary = prediction_service.generate_predictions()
        paper_bet_summary = prediction_service.write_paper_bets()

        self._restore_replay_results()
        settlement_summary = SettlementService(self.engine).settle_results()
        report = EvaluationService(self.engine, self.settings).evaluate()
        report_lines = []
        if report_name is not None:
            bets_path, summary_path = self._export_reports(
                report_name,
                report_payload_from_settings(report, self.settings),
            )
            report_lines = [f"bets_report={bets_path}", f"summary_report={summary_path}"]

        return "\n".join(
            [
                "replay-football-data: started",
                f"features_created={feature_summary.items_created}",
                f"predictions_created={prediction_summary.items_created}",
                f"paper_bets_created={paper_bet_summary.items_created}",
                f"paper_bets_settled={settlement_summary.items_updated}",
                *report_lines,
                "replay-football-data: finished",
                format_evaluation_report(report),
            ]
        )

    def _prepare_completed_matches_as_replay_candidates(
        self,
        *,
        from_date: str | None,
        to_date: str | None,
        min_history: int,
    ) -> None:
        with session_scope(self.engine) as session:
            completed_matches = list(
                session.scalars(
                    select(Match)
                    .where(
                        Match.source == "football-data",
                        Match.status == "completed",
                    )
                    .order_by(Match.kickoff_time)
                )
            )
            for match in completed_matches:
                if not _is_inside_date_window(match.kickoff_time, from_date, to_date):
                    continue
                if not _has_minimum_prior_history(match, completed_matches, min_history):
                    continue
                match.raw_payload_json = _append_replay_scores(
                    match.raw_payload_json,
                    home_score=match.home_score,
                    away_score=match.away_score,
                    result=match.result,
                )
                match.status = "scheduled"
                match.home_score = None
                match.away_score = None
                match.result = None

    def _restore_replay_results(self) -> None:
        with session_scope(self.engine) as session:
            replay_matches = list(
                session.scalars(
                    select(Match)
                    .where(
                        Match.source == "football-data",
                        Match.status == "scheduled",
                    )
                    .order_by(Match.kickoff_time)
                )
            )
            for match in replay_matches:
                if match.raw_payload_json is None:
                    continue
                home_score, away_score, result = _extract_replay_scores(match.raw_payload_json)
                if home_score is None or away_score is None:
                    continue
                match.status = "completed"
                match.home_score = home_score
                match.away_score = away_score
                match.result = result

    def _export_reports(
        self,
        report_name: str,
        summary: dict[str, int | float | None],
    ) -> tuple[str, str]:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_report_name(report_name)
        bets_path = reports_dir / f"{safe_name}_bets.csv"
        summary_path = reports_dir / f"{safe_name}_summary.json"

        with session_scope(self.engine) as session:
            rows = list(
                session.execute(
                    select(PaperBet, Prediction, Match)
                    .join(Prediction, PaperBet.prediction_id == Prediction.id)
                    .join(Match, PaperBet.match_id == Match.id)
                    .order_by(Match.kickoff_time, PaperBet.id)
                )
            )

        with bets_path.open("w", encoding="utf-8", newline="") as csv_file:
            fieldnames = [
                "paper_bet_id",
                "match_id",
                "kickoff_time",
                "league",
                "home_team",
                "away_team",
                "market",
                "selection",
                "odds_taken",
                "stake_units",
                "expected_value",
                "status",
                "profit_loss_units",
                "model_probability",
                "bookmaker_probability",
                "edge",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for paper_bet, prediction, match in rows:
                writer.writerow(
                    {
                        "paper_bet_id": paper_bet.id,
                        "match_id": match.id,
                        "kickoff_time": match.kickoff_time,
                        "league": match.league,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "market": paper_bet.market,
                        "selection": paper_bet.selection,
                        "odds_taken": paper_bet.odds_taken,
                        "stake_units": paper_bet.stake_units,
                        "expected_value": paper_bet.expected_value,
                        "status": paper_bet.status,
                        "profit_loss_units": paper_bet.profit_loss_units,
                        "model_probability": prediction.model_probability,
                        "bookmaker_probability": prediction.bookmaker_probability,
                        "edge": prediction.edge,
                    }
                )

        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return bets_path.as_posix(), summary_path.as_posix()


def _append_replay_scores(
    raw_payload_json: str | None,
    *,
    home_score: int | None,
    away_score: int | None,
    result: str | None,
) -> str:
    import json

    payload = json.loads(raw_payload_json or "{}")
    payload["_replay_home_score"] = home_score
    payload["_replay_away_score"] = away_score
    payload["_replay_result"] = result
    return json.dumps(payload, sort_keys=True)


def _extract_replay_scores(raw_payload_json: str) -> tuple[int | None, int | None, str | None]:
    import json

    payload = json.loads(raw_payload_json)
    return (
        payload.get("_replay_home_score"),
        payload.get("_replay_away_score"),
        payload.get("_replay_result"),
    )


def _has_minimum_prior_history(
    match: Match,
    completed_matches: list[Match],
    min_history: int,
) -> bool:
    return (
        _prior_team_match_count(match.home_team, match.kickoff_time, completed_matches)
        >= min_history
        and _prior_team_match_count(match.away_team, match.kickoff_time, completed_matches)
        >= min_history
    )


def _prior_team_match_count(team: str, kickoff_time: str, completed_matches: list[Match]) -> int:
    return sum(
        1
        for completed_match in completed_matches
        if completed_match.kickoff_time < kickoff_time
        and (
            completed_match.home_team == team
            or completed_match.away_team == team
        )
    )


def _is_inside_date_window(
    kickoff_time: str,
    from_date: str | None,
    to_date: str | None,
) -> bool:
    kickoff_date = kickoff_time[:10]
    if from_date is not None and kickoff_date < from_date:
        return False
    if to_date is not None and kickoff_date > to_date:
        return False
    return True


def _safe_report_name(report_name: str) -> str:
    safe_characters = [
        character if character.isalnum() or character in "-_" else "_"
        for character in report_name
    ]
    return "".join(safe_characters).strip("_") or "replay_report"
