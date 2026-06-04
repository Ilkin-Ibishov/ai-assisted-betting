import json
from dataclasses import dataclass

from sqlalchemy import Engine, select

from app.config import Settings
from app.core.feature_builder import FeatureBuilder
from app.core.paper_bet_logger import PaperBetLogger
from app.core.prediction_engine import PredictionInput, create_prediction_engine
from app.core.value_detector import ValueDetector
from app.db.engine import session_scope
from app.db.models import Feature, Match, OddsSnapshot, Prediction
from app.db.repositories import (
    DecisionLogRepository,
    FeatureRepository,
    PaperBetRepository,
    PredictionRepository,
)


@dataclass(frozen=True)
class StepSummary:
    items_read: int
    items_created: int
    items_updated: int
    items_skipped: int
    errors_count: int


class PredictionService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def generate_features(self) -> StepSummary:
        return self.generate_features_for_matches(None)

    def generate_features_for_matches(
        self,
        match_ids: set[int] | None,
        *,
        allow_cold_start_features: bool = False,
    ) -> StepSummary:
        builder = FeatureBuilder(
            elo_initial_rating=self.settings.elo_initial_rating,
            elo_k_factor=self.settings.elo_k_factor,
            elo_home_advantage=self.settings.elo_home_advantage,
            allow_cold_start_features=allow_cold_start_features,
        )
        items_read = 0
        items_created = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            feature_repository = FeatureRepository(session)
            log_repository = DecisionLogRepository(session)
            scheduled_query = select(Match).where(Match.status == "scheduled")
            if match_ids is not None:
                if not match_ids:
                    return StepSummary(0, 0, 0, 0, 0)
                scheduled_query = scheduled_query.where(Match.id.in_(match_ids))
            scheduled_matches = list(session.scalars(scheduled_query))
            completed_matches = list(
                session.scalars(select(Match).where(Match.status == "completed"))
            )

            for match in scheduled_matches:
                odds = list(
                    session.scalars(
                        select(OddsSnapshot)
                        .where(
                            OddsSnapshot.match_id == match.id,
                            OddsSnapshot.market == self.settings.default_market,
                        )
                        .order_by(OddsSnapshot.selection)
                    )
                )
                built_features = builder.build_for_match(
                    match=match,
                    completed_matches=completed_matches,
                    odds_snapshots=odds,
                )
                items_read += len(odds)
                if not built_features:
                    log_repository.add(
                        match_id=match.id,
                        stage="BUILD_FEATURES",
                        level="WARNING",
                        message="Skipped feature generation due to insufficient history or odds",
                    )
                    items_skipped += len(odds)
                    continue

                for built_feature in built_features:
                    if feature_repository.exists(
                        match_id=built_feature.match_id,
                        market=built_feature.market,
                        selection=built_feature.selection,
                        feature_version=self.settings.feature_version,
                    ):
                        items_skipped += 1
                        continue

                    feature_repository.add(
                        match_id=built_feature.match_id,
                        market=built_feature.market,
                        selection=built_feature.selection,
                        home_form_points_5=built_feature.home_form_points_5,
                        away_form_points_5=built_feature.away_form_points_5,
                        home_goals_for_avg_5=built_feature.home_goals_for_avg_5,
                        away_goals_for_avg_5=built_feature.away_goals_for_avg_5,
                        home_goals_against_avg_5=built_feature.home_goals_against_avg_5,
                        away_goals_against_avg_5=built_feature.away_goals_against_avg_5,
                        home_advantage_flag=built_feature.home_advantage_flag,
                        bookmaker_probability=built_feature.bookmaker_probability,
                        bookmaker_margin_estimate=built_feature.bookmaker_margin_estimate,
                        home_elo_rating=built_feature.home_elo_rating,
                        away_elo_rating=built_feature.away_elo_rating,
                        enrichment_tier=built_feature.enrichment_tier,
                        feature_provenance_json=json.dumps(
                            list(built_feature.feature_provenance)
                        ),
                        home_rest_days=built_feature.home_rest_days,
                        away_rest_days=built_feature.away_rest_days,
                        home_goal_difference_trend_5=(
                            built_feature.home_goal_difference_trend_5
                        ),
                        away_goal_difference_trend_5=(
                            built_feature.away_goal_difference_trend_5
                        ),
                        odds_movement_velocity=built_feature.odds_movement_velocity,
                        feature_version=self.settings.feature_version,
                    )
                    items_created += 1
                    log_repository.add(
                        match_id=built_feature.match_id,
                        stage="BUILD_FEATURES",
                        level="INFO",
                        message="Generated baseline feature row",
                    )

        return StepSummary(items_read, items_created, 0, items_skipped, 0)

    def generate_predictions(self) -> StepSummary:
        return self.generate_predictions_for_matches(None)

    def generate_predictions_for_matches(self, match_ids: set[int] | None) -> StepSummary:
        predictor = create_prediction_engine(
            self.settings.model_name,
            elo_home_advantage=self.settings.elo_home_advantage,
        )
        items_read = 0
        items_created = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            prediction_repository = PredictionRepository(session)
            log_repository = DecisionLogRepository(session)
            feature_query = select(Feature).where(
                Feature.feature_version == self.settings.feature_version
            )
            if match_ids is not None:
                if not match_ids:
                    return StepSummary(0, 0, 0, 0, 0)
                feature_query = feature_query.where(Feature.match_id.in_(match_ids))
            features = list(
                session.scalars(feature_query)
            )

            for feature in features:
                items_read += 1
                if prediction_repository.exists(
                    match_id=feature.match_id,
                    market=feature.market,
                    selection=feature.selection,
                    model_name=self.settings.model_name,
                    model_version=self.settings.model_version,
                ):
                    items_skipped += 1
                    continue

                output = predictor.predict(
                    PredictionInput(
                        match_id=feature.match_id,
                        market=feature.market,
                        selection=feature.selection,
                        bookmaker_probability=feature.bookmaker_probability or 0,
                        home_form_points_5=feature.home_form_points_5 or 0,
                        away_form_points_5=feature.away_form_points_5 or 0,
                        home_goals_for_avg_5=feature.home_goals_for_avg_5 or 0,
                        away_goals_for_avg_5=feature.away_goals_for_avg_5 or 0,
                        home_goals_against_avg_5=feature.home_goals_against_avg_5 or 0,
                        away_goals_against_avg_5=feature.away_goals_against_avg_5 or 0,
                        home_advantage_flag=feature.home_advantage_flag or 0,
                        home_elo_rating=feature.home_elo_rating,
                        away_elo_rating=feature.away_elo_rating,
                        enrichment_tier=feature.enrichment_tier or "cold_start",
                        home_rest_days=feature.home_rest_days,
                        away_rest_days=feature.away_rest_days,
                        home_goal_difference_trend_5=(
                            feature.home_goal_difference_trend_5 or 0
                        ),
                        away_goal_difference_trend_5=(
                            feature.away_goal_difference_trend_5 or 0
                        ),
                        odds_movement_velocity=feature.odds_movement_velocity or 0,
                    )
                )
                reason = (
                    f"{output.reason}; feature_tier={feature.enrichment_tier or 'cold_start'}; "
                    f"feature_provenance={_feature_provenance_label(feature.feature_provenance_json)}"
                )
                prediction_repository.add(
                    match_id=output.match_id,
                    market=output.market,
                    selection=output.selection,
                    model_name=self.settings.model_name,
                    model_version=self.settings.model_version,
                    model_probability=output.model_probability,
                    bookmaker_probability=output.bookmaker_probability,
                    edge=output.edge,
                    confidence_score=output.confidence_score,
                    decision=output.decision,
                    reason=reason,
                )
                items_created += 1
                log_repository.add(
                    match_id=output.match_id,
                    stage="PREDICT",
                    level="INFO",
                    message="Generated baseline prediction",
                )

        return StepSummary(items_read, items_created, 0, items_skipped, 0)

    def write_paper_bets(self) -> StepSummary:
        return self.write_paper_bets_for_matches(None)

    def write_paper_bets_for_matches(self, match_ids: set[int] | None) -> StepSummary:
        detector = ValueDetector(self.settings)
        logger = PaperBetLogger()
        items_read = 0
        items_created = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            paper_bet_repository = PaperBetRepository(session)
            log_repository = DecisionLogRepository(session)
            prediction_query = select(Prediction).where(
                Prediction.model_name == self.settings.model_name,
                Prediction.model_version == self.settings.model_version,
            )
            if match_ids is not None:
                if not match_ids:
                    return StepSummary(0, 0, 0, 0, 0)
                prediction_query = prediction_query.where(Prediction.match_id.in_(match_ids))
            predictions = list(
                session.scalars(prediction_query)
            )

            for prediction in predictions:
                items_read += 1
                match = session.get(Match, prediction.match_id)
                odds = session.scalar(
                    select(OddsSnapshot)
                    .where(
                        OddsSnapshot.match_id == prediction.match_id,
                        OddsSnapshot.market == prediction.market,
                        OddsSnapshot.selection == prediction.selection,
                    )
                    .order_by(OddsSnapshot.snapshot_time.desc())
                )
                existing_bet = paper_bet_repository.get_by_prediction_id(prediction.id)
                if match is None or odds is None:
                    items_skipped += 1
                    continue

                value_decision = detector.evaluate(
                    edge=prediction.edge,
                    odds_decimal=odds.odds_decimal,
                    model_probability=prediction.model_probability,
                )
                prediction.decision = value_decision.decision
                prediction.reason = _merge_reason_with_feature_provenance(
                    value_decision.reason,
                    prediction.reason,
                )

                if not logger.should_create(
                    prediction=prediction,
                    match=match,
                    existing_bet=existing_bet,
                ):
                    items_skipped += 1
                    log_repository.add(
                        match_id=prediction.match_id,
                        stage="VALUE_DETECTION",
                        level="INFO",
                        message=value_decision.reason,
                    )
                    continue

                paper_bet_repository.add(
                    prediction_id=prediction.id,
                    match_id=prediction.match_id,
                    market=prediction.market,
                    selection=prediction.selection,
                    odds_taken=odds.odds_decimal,
                    stake_units=self.settings.default_stake_units,
                    expected_value=value_decision.expected_value or 0,
                )
                items_created += 1
                log_repository.add(
                    match_id=prediction.match_id,
                    stage="WRITE_PAPER_BET",
                    level="INFO",
                    message="Created paper bet",
                )

        return StepSummary(items_read, items_created, 0, items_skipped, 0)


def _feature_provenance_label(raw_value: str | None) -> str:
    if not raw_value:
        return "unknown"
    try:
        values = json.loads(raw_value)
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(values, list):
        return "unknown"
    labels = [str(value) for value in values if value]
    return ",".join(labels) if labels else "unknown"


def _merge_reason_with_feature_provenance(reason: str, previous_reason: str | None) -> str:
    if not previous_reason:
        return reason
    provenance_parts = [
        part.strip()
        for part in previous_reason.split(";")
        if part.strip().startswith(("feature_tier=", "feature_provenance="))
    ]
    if not provenance_parts:
        return reason
    return f"{reason}; {'; '.join(provenance_parts)}"
