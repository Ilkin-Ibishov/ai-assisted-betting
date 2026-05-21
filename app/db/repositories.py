from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DecisionLog,
    EvaluationRun,
    Feature,
    LiveRun,
    Match,
    OddsSnapshot,
    PaperBet,
    Prediction,
)


class MatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        source: str,
        source_match_id: str,
        league: str,
        home_team: str,
        away_team: str,
        kickoff_time: str,
        season: str | None = None,
        status: str = "scheduled",
        home_score: int | None = None,
        away_score: int | None = None,
        result: str | None = None,
        raw_payload_json: str | None = None,
    ) -> Match:
        match = Match(
            source=source,
            source_match_id=source_match_id,
            league=league,
            season=season,
            home_team=home_team,
            away_team=away_team,
            kickoff_time=kickoff_time,
            status=status,
            home_score=home_score,
            away_score=away_score,
            result=result,
            raw_payload_json=raw_payload_json,
        )
        self.session.add(match)
        self.session.flush()
        return match

    def get_by_source_id(self, source: str, source_match_id: str) -> Match | None:
        return self.session.scalar(
            select(Match).where(
                Match.source == source,
                Match.source_match_id == source_match_id,
            )
        )


class OddsSnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        match_id: int,
        source: str,
        bookmaker: str,
        market: str,
        selection: str,
        odds_decimal: float,
        implied_probability: float,
        snapshot_time: str,
        minutes_before_kickoff: int | None = None,
        is_closing: bool = False,
        raw_payload_json: str | None = None,
    ) -> OddsSnapshot:
        snapshot = OddsSnapshot(
            match_id=match_id,
            source=source,
            bookmaker=bookmaker,
            market=market,
            selection=selection,
            odds_decimal=odds_decimal,
            implied_probability=implied_probability,
            snapshot_time=snapshot_time,
            minutes_before_kickoff=minutes_before_kickoff,
            is_closing=is_closing,
            raw_payload_json=raw_payload_json,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def exists_snapshot(
        self,
        *,
        match_id: int,
        source: str,
        bookmaker: str,
        market: str,
        selection: str,
        snapshot_time: str,
    ) -> bool:
        snapshot_id = self.session.scalar(
            select(OddsSnapshot.id).where(
                OddsSnapshot.match_id == match_id,
                OddsSnapshot.source == source,
                OddsSnapshot.bookmaker == bookmaker,
                OddsSnapshot.market == market,
                OddsSnapshot.selection == selection,
                OddsSnapshot.snapshot_time == snapshot_time,
            )
        )
        return snapshot_id is not None


class DecisionLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        stage: str,
        level: str,
        message: str,
        match_id: int | None = None,
        input_json: str | None = None,
        output_json: str | None = None,
        warnings_json: str | None = None,
        errors_json: str | None = None,
    ) -> DecisionLog:
        decision_log = DecisionLog(
            match_id=match_id,
            stage=stage,
            level=level,
            message=message,
            input_json=input_json,
            output_json=output_json,
            warnings_json=warnings_json,
            errors_json=errors_json,
        )
        self.session.add(decision_log)
        self.session.flush()
        return decision_log


class FeatureRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **values: object) -> Feature:
        feature = Feature(**values)
        self.session.add(feature)
        self.session.flush()
        return feature

    def exists(self, *, match_id: int, market: str, selection: str, feature_version: str) -> bool:
        feature_id = self.session.scalar(
            select(Feature.id).where(
                Feature.match_id == match_id,
                Feature.market == market,
                Feature.selection == selection,
                Feature.feature_version == feature_version,
            )
        )
        return feature_id is not None


class PredictionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **values: object) -> Prediction:
        prediction = Prediction(**values)
        self.session.add(prediction)
        self.session.flush()
        return prediction

    def exists(
        self,
        *,
        match_id: int,
        market: str,
        selection: str,
        model_name: str,
        model_version: str,
    ) -> bool:
        prediction_id = self.session.scalar(
            select(Prediction.id).where(
                Prediction.match_id == match_id,
                Prediction.market == market,
                Prediction.selection == selection,
                Prediction.model_name == model_name,
                Prediction.model_version == model_version,
            )
        )
        return prediction_id is not None


class PaperBetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **values: object) -> PaperBet:
        paper_bet = PaperBet(**values)
        self.session.add(paper_bet)
        self.session.flush()
        return paper_bet

    def get_by_prediction_id(self, prediction_id: int) -> PaperBet | None:
        return self.session.scalar(
            select(PaperBet).where(PaperBet.prediction_id == prediction_id)
        )


class EvaluationRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **values: object) -> EvaluationRun:
        evaluation_run = EvaluationRun(**values)
        self.session.add(evaluation_run)
        self.session.flush()
        return evaluation_run


class LiveRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(
        self,
        *,
        run_id: str,
        run_type: str,
        provider: str,
        league: str | None = None,
        season: str | None = None,
        model_name: str | None = None,
    ) -> LiveRun:
        existing = self.get_by_run_id(run_id)
        if existing is not None:
            return existing

        live_run = LiveRun(
            run_id=run_id,
            run_type=run_type,
            provider=provider,
            league=league,
            season=season,
            status="running",
            model_name=model_name,
        )
        self.session.add(live_run)
        self.session.flush()
        return live_run

    def complete(
        self,
        *,
        run_id: str,
        items_read: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_skipped: int = 0,
    ) -> LiveRun:
        live_run = self._require_run(run_id)
        live_run.status = "completed"
        live_run.finished_at = _utc_now_iso()
        live_run.items_read = items_read
        live_run.items_created = items_created
        live_run.items_updated = items_updated
        live_run.items_skipped = items_skipped
        live_run.errors_count = 0
        live_run.error_summary = None
        self.session.flush()
        return live_run

    def fail(
        self,
        *,
        run_id: str,
        errors_count: int,
        error_summary: str,
        items_read: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_skipped: int = 0,
    ) -> LiveRun:
        live_run = self._require_run(run_id)
        live_run.status = "failed"
        live_run.finished_at = _utc_now_iso()
        live_run.items_read = items_read
        live_run.items_created = items_created
        live_run.items_updated = items_updated
        live_run.items_skipped = items_skipped
        live_run.errors_count = errors_count
        live_run.error_summary = error_summary
        self.session.flush()
        return live_run

    def get_by_run_id(self, run_id: str) -> LiveRun | None:
        return self.session.scalar(select(LiveRun).where(LiveRun.run_id == run_id))

    def _require_run(self, run_id: str) -> LiveRun:
        live_run = self.get_by_run_id(run_id)
        if live_run is None:
            raise ValueError(f"Live run not found: {run_id}")
        return live_run


def _utc_now_iso() -> str:
    from app.db.models import utc_now_iso

    return utc_now_iso()
