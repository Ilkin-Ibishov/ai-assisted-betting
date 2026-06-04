from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("source", "source_match_id", name="uq_matches_source_match_id"),
        Index("idx_matches_kickoff_time", "kickoff_time"),
        Index("idx_matches_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_match_id: Mapped[str] = mapped_column(String, nullable=False)
    league: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[str | None] = mapped_column(String)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    kickoff_time: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="scheduled")
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(String)
    raw_payload_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=utc_now_iso,
        onupdate=utc_now_iso,
    )


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "source",
            "bookmaker",
            "market",
            "selection",
            "snapshot_time",
            name="uq_odds_snapshot_identity",
        ),
        Index("idx_odds_match_market", "match_id", "market"),
        Index("idx_odds_snapshot_time", "snapshot_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    odds_decimal: Mapped[float] = mapped_column(nullable=False)
    implied_probability: Mapped[float] = mapped_column(nullable=False)
    snapshot_time: Mapped[str] = mapped_column(String, nullable=False)
    minutes_before_kickoff: Mapped[int | None] = mapped_column(Integer)
    is_closing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_payload_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "market",
            "selection",
            "feature_version",
            name="uq_features_match_market_selection_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    home_form_points_5: Mapped[float | None]
    away_form_points_5: Mapped[float | None]
    home_goals_for_avg_5: Mapped[float | None]
    away_goals_for_avg_5: Mapped[float | None]
    home_goals_against_avg_5: Mapped[float | None]
    away_goals_against_avg_5: Mapped[float | None]
    home_advantage_flag: Mapped[int | None] = mapped_column(Integer)
    bookmaker_probability: Mapped[float | None]
    bookmaker_margin_estimate: Mapped[float | None]
    home_elo_rating: Mapped[float | None]
    away_elo_rating: Mapped[float | None]
    enrichment_tier: Mapped[str | None] = mapped_column(String)
    feature_provenance_json: Mapped[str | None] = mapped_column(Text)
    home_rest_days: Mapped[float | None]
    away_rest_days: Mapped[float | None]
    home_goal_difference_trend_5: Mapped[float | None]
    away_goal_difference_trend_5: Mapped[float | None]
    odds_movement_velocity: Mapped[float | None]
    feature_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (Index("idx_predictions_match", "match_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    model_probability: Mapped[float] = mapped_column(nullable=False)
    bookmaker_probability: Mapped[float] = mapped_column(nullable=False)
    edge: Mapped[float] = mapped_column(nullable=False)
    confidence_score: Mapped[float | None]
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class PaperBet(Base):
    __tablename__ = "paper_bets"
    __table_args__ = (
        UniqueConstraint("prediction_id", name="uq_paper_bets_prediction_id"),
        Index("idx_paper_bets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    odds_taken: Mapped[float] = mapped_column(nullable=False)
    stake_units: Mapped[float] = mapped_column(nullable=False)
    expected_value: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    profit_loss_units: Mapped[float | None]
    closing_odds: Mapped[float | None]
    clv: Mapped[float | None]
    settled_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class PaperRecommendation(Base):
    __tablename__ = "paper_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "source_match_id",
            "market",
            "selection",
            "model_name",
            "model_version",
            "latest_snapshot_time",
            name="uq_paper_recommendation_identity",
        ),
        Index("idx_paper_recommendations_grade", "grade"),
        Index("idx_paper_recommendations_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id"))
    source_run_id: Mapped[str | None] = mapped_column(String)
    source_match_id: Mapped[str] = mapped_column(String, nullable=False)
    bookmaker: Mapped[str] = mapped_column(String, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    latest_snapshot_time: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    model_probability: Mapped[float | None]
    implied_probability: Mapped[float | None]
    edge: Mapped[float | None]
    confidence_score: Mapped[float | None]
    model_confidence_score: Mapped[float | None]
    recommendation_confidence_score: Mapped[float | None]
    confidence_adjustment_reason: Mapped[str | None] = mapped_column(String)
    current_odds: Mapped[float | None]
    expected_value: Mapped[float | None]
    risk_flags_json: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class PaperCombination(Base):
    __tablename__ = "paper_combinations"
    __table_args__ = (
        UniqueConstraint(
            "leg_recommendation_ids_json",
            "model_name",
            "model_version",
            name="uq_paper_combination_identity",
        ),
        Index("idx_paper_combinations_grade", "grade"),
        Index("idx_paper_combinations_rank", "rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    leg_recommendation_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    leg_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    combined_odds: Mapped[float] = mapped_column(nullable=False)
    estimated_probability: Mapped[float] = mapped_column(nullable=False)
    combined_expected_value: Mapped[float] = mapped_column(nullable=False)
    confidence_score: Mapped[float | None]
    risk_flags_json: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class PaperJournalEntry(Base):
    __tablename__ = "paper_journal_entries"
    __table_args__ = (
        UniqueConstraint("journal_date", name="uq_paper_journal_entries_date"),
        Index("idx_paper_journal_entries_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_date: Mapped[str] = mapped_column(String, nullable=False)
    decision_state: Mapped[str] = mapped_column(String, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=utc_now_iso,
        onupdate=utc_now_iso,
    )


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (Index("idx_decision_logs_match_stage", "match_id", "stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"))
    stage: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text)
    warnings_json: Mapped[str | None] = mapped_column(Text)
    errors_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_name: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String)
    model_name: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    start_time: Mapped[str] = mapped_column(String, nullable=False)
    end_time: Mapped[str] = mapped_column(String, nullable=False)
    total_bets: Mapped[int] = mapped_column(Integer, nullable=False)
    won: Mapped[int] = mapped_column(Integer, nullable=False)
    lost: Mapped[int] = mapped_column(Integer, nullable=False)
    voided: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_loss_units: Mapped[float] = mapped_column(nullable=False)
    roi: Mapped[float] = mapped_column(nullable=False)
    hit_rate: Mapped[float | None]
    average_odds: Mapped[float | None]
    average_edge: Mapped[float | None]
    brier_score: Mapped[float | None]
    log_loss: Mapped[float | None]
    report_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class LiveRun(Base):
    __tablename__ = "live_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_live_runs_run_id"),
        Index("idx_live_runs_status", "status"),
        Index("idx_live_runs_started_at", "started_at"),
        Index("idx_live_runs_provider_type", "provider", "run_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    run_type: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    league: Mapped[str | None] = mapped_column(String)
    season: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    finished_at: Mapped[str | None] = mapped_column(String)
    items_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class LiveSnapshot(Base):
    __tablename__ = "live_snapshots"
    __table_args__ = (
        UniqueConstraint("provider", "snapshot_hash", name="uq_live_snapshots_provider_hash"),
        Index("idx_live_snapshots_provider_created", "provider", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)


class ResultFetchJob(Base):
    __tablename__ = "result_fetch_jobs"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_result_fetch_jobs_match_id"),
        Index("idx_result_fetch_jobs_status_next", "status", "next_attempt_at"),
        Index("idx_result_fetch_jobs_source_match", "source_match_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    source_match_id: Mapped[str] = mapped_column(String, nullable=False)
    misli_event_id: Mapped[str | None] = mapped_column(String)
    detail_url: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    next_attempt_at: Mapped[str] = mapped_column(String, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_result_payload_json: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=utc_now_iso,
        onupdate=utc_now_iso,
    )


class AIAnalysisRun(Base):
    __tablename__ = "ai_analysis_runs"
    __table_args__ = (
        Index("idx_ai_analysis_type_created", "analysis_type", "created_at"),
        Index("idx_ai_analysis_source", "source_type", "source_id"),
        Index("idx_ai_analysis_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_type: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
