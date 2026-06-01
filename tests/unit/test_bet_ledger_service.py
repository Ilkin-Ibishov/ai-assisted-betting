from datetime import UTC, datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import text

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, PaperRecommendation
from app.db.repositories import MatchRepository, PaperBetRepository, PredictionRepository
from app.services import bet_ledger_service as ledger_module
from app.services.bet_ledger_service import BetLedgerService


def create_database(tmp_path: Path) -> str:
    database_url = f"sqlite:///{tmp_path / 'ledger.db'}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return database_url


def seed_prediction_and_bet(
    database_url: str,
    *,
    source_match_id: str,
    kickoff_time: str,
    selection: str,
    status: str = "open",
    expected_value: float = 0.12,
    profit_loss_units: float | None = None,
    settled_at: str | None = None,
    confidence_score: float | None = 0.7,
) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=source_match_id,
            league="Sample Premier",
            home_team=f"Home {source_match_id}",
            away_team=f"Away {source_match_id}",
            kickoff_time=kickoff_time,
        )
        prediction = PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection=selection,
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.58,
            bookmaker_probability=0.42,
            edge=0.16,
            confidence_score=confidence_score,
            decision="BET",
            reason="seed bet",
        )
        bet = PaperBetRepository(session).add(
            prediction_id=prediction.id,
            match_id=match.id,
            market="1X2",
            selection=selection,
            odds_taken=2.4,
            stake_units=1.0,
            expected_value=expected_value,
            status=status,
        )
        bet.profit_loss_units = profit_loss_units
        bet.settled_at = settled_at
    engine.dispose()


def seed_recommendation(
    database_url: str,
    *,
    source_match_id: str,
    kickoff_time: str,
    selection: str = "HOME",
    prediction_id: int | None = None,
    status: str = "active",
    grade: str = "recommended",
    risk_flags: str = '["no_current_risk_flags"]',
) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=source_match_id,
            league="Sample Premier",
            home_team=f"Home {source_match_id}",
            away_team=f"Away {source_match_id}",
            kickoff_time=kickoff_time,
        )
        session.add(
            PaperRecommendation(
                match_id=match.id,
                prediction_id=prediction_id,
                source_match_id=source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                latest_snapshot_time="2026-05-29T08:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade=grade,
                status=status,
                model_probability=0.61,
                implied_probability=0.45,
                edge=0.16,
                confidence_score=0.73,
                current_odds=2.22,
                expected_value=0.35,
                risk_flags_json=risk_flags,
                rationale="Positive edge is above the recommendation gate.",
            )
        )
    engine.dispose()


def seed_recommendation_for_existing_match(
    database_url: str,
    *,
    source_match_id: str,
    selection: str = "HOME",
    prediction_id: int | None = None,
) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match_id = session.execute(
            text(
                "SELECT id FROM matches "
                "WHERE source = :source AND source_match_id = :source_match_id"
            ),
            {"source": "misli_public", "source_match_id": source_match_id},
        ).scalar_one()
        session.add(
            PaperRecommendation(
                match_id=match_id,
                prediction_id=prediction_id,
                source_match_id=source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                latest_snapshot_time="2026-05-29T08:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade="recommended",
                status="active",
                model_probability=0.61,
                implied_probability=0.45,
                edge=0.16,
                confidence_score=0.73,
                current_odds=2.22,
                expected_value=0.35,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Positive edge is above the recommendation gate.",
            )
        )
    engine.dispose()


def test_ledger_classifies_fresh_candidate_and_tracked_bet(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="candidate-future",
        kickoff_time="2026-05-30T20:30:00+04:00",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="tracked-future",
        kickoff_time="2026-05-31T20:30:00+04:00",
        selection="AWAY",
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert payload["summary"]["fresh_count"] == 2
    assert [row["row_type"] for row in payload["rows"]] == ["candidate", "tracked"]
    assert {row["state"] for row in payload["rows"]} == {"fresh"}
    assert payload["rows"][0]["model_probability"] is not None
    assert payload["rows"][0]["implied_probability"] is not None


def test_ledger_surfaces_needs_result_and_resulted_rows(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="past-open",
        kickoff_time="2026-05-28T20:30:00+04:00",
        selection="HOME",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="past-won",
        kickoff_time="2026-05-27T20:30:00+04:00",
        selection="AWAY",
        status="won",
        profit_loss_units=1.4,
        settled_at="2026-05-27T23:00:00+00:00",
    )

    payload = BetLedgerService(database_url).ledger(
        status="all",
        date_range="last_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    rows_by_match = {row["source_match_id"]: row for row in payload["rows"]}
    assert rows_by_match["past-open"]["state"] == "needs_result"
    assert rows_by_match["past-open"]["outcome"] is None
    assert rows_by_match["past-won"]["state"] == "resulted"
    assert rows_by_match["past-won"]["outcome"] == "won"
    assert rows_by_match["past-won"]["paper_profit_loss"] == 1.4


def test_ledger_excludes_voided_from_default_fresh_view(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="voided",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
        status="void",
        profit_loss_units=0.0,
        settled_at="2026-05-29T09:00:00+00:00",
    )

    fresh = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )
    all_rows = BetLedgerService(database_url).ledger(
        status="all",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert fresh["rows"] == []
    assert all_rows["rows"][0]["state"] == "voided"
    assert all_rows["summary"]["voided_count"] == 1


def test_resulted_and_voided_paper_bets_remain_tracked_rows(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="tracked-won",
        kickoff_time="2026-05-27T20:30:00+04:00",
        selection="HOME",
        status="won",
        profit_loss_units=1.2,
        settled_at="2026-05-27T23:00:00+00:00",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="tracked-voided",
        kickoff_time="2026-05-28T20:30:00+04:00",
        selection="AWAY",
        status="void",
        profit_loss_units=0.0,
        settled_at="2026-05-28T23:00:00+00:00",
    )

    payload = BetLedgerService(database_url).ledger(
        status="all",
        date_range="last_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    rows_by_match = {row["source_match_id"]: row for row in payload["rows"]}
    assert rows_by_match["tracked-won"]["state"] == "resulted"
    assert rows_by_match["tracked-won"]["row_type"] == "tracked"
    assert rows_by_match["tracked-voided"]["state"] == "voided"
    assert rows_by_match["tracked-voided"]["row_type"] == "tracked"
    assert payload["summary"]["tracked_count"] == 2


def test_ledger_deduplicates_candidate_when_matching_paper_bet_exists(
    tmp_path: Path,
) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="same-match",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
    )
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        prediction_id = session.execute(text("SELECT id FROM predictions LIMIT 1")).scalar_one()
    engine.dispose()
    seed_recommendation_for_existing_match(
        database_url,
        source_match_id="same-match",
        selection="HOME",
        prediction_id=prediction_id,
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["row_type"] == "tracked"
    assert payload["rows"][0]["paper_bet_id"] is not None


def test_fresh_ledger_excludes_future_paper_bet_with_risk_flags(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="future-negative-ev",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
        expected_value=-0.01,
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="future-low-confidence",
        kickoff_time="2026-05-31T20:30:00+04:00",
        selection="AWAY",
        confidence_score=0.4,
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert payload["rows"] == []
    assert payload["summary"]["fresh_count"] == 0


def test_fresh_ledger_excludes_risky_or_non_recommended_candidates(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="risky-candidate",
        kickoff_time="2026-05-30T20:30:00+04:00",
        risk_flags='["low_confidence"]',
    )
    seed_recommendation(
        database_url,
        source_match_id="lean-candidate",
        kickoff_time="2026-05-31T20:30:00+04:00",
        grade="lean",
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert payload["rows"] == []
    assert payload["summary"]["fresh_count"] == 0


def test_next_7_days_includes_seven_local_calendar_days(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="next-window-included",
        kickoff_time="2026-06-04T20:30:00+04:00",
    )
    seed_recommendation(
        database_url,
        source_match_id="next-window-excluded",
        kickoff_time="2026-06-05T20:30:00+04:00",
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=timezone(timedelta(hours=4))),
    )

    assert [row["source_match_id"] for row in payload["rows"]] == ["next-window-included"]


def test_last_7_days_includes_seven_local_calendar_days(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="last-window-excluded",
        kickoff_time="2026-05-22T20:30:00+04:00",
        selection="HOME",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="last-window-included",
        kickoff_time="2026-05-23T20:30:00+04:00",
        selection="AWAY",
    )

    payload = BetLedgerService(database_url).ledger(
        status="all",
        date_range="last_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=timezone(timedelta(hours=4))),
    )

    assert [row["source_match_id"] for row in payload["rows"]] == ["last-window-included"]


def test_last_30_days_includes_thirty_local_calendar_days(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="last-30-window-excluded",
        kickoff_time="2026-04-29T20:30:00+04:00",
        selection="HOME",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="last-30-window-included",
        kickoff_time="2026-04-30T20:30:00+04:00",
        selection="AWAY",
    )

    payload = BetLedgerService(database_url).ledger(
        status="all",
        date_range="last_30_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=timezone(timedelta(hours=4))),
    )

    assert [row["source_match_id"] for row in payload["rows"]] == ["last-30-window-included"]


def test_tomorrow_ledger_uses_kickoff_local_calendar_day(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="local-tomorrow",
        kickoff_time="2026-05-30T01:00:00+04:00",
    )

    today_payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="today",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=timezone(timedelta(hours=4))),
    )
    tomorrow_payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="tomorrow",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=timezone(timedelta(hours=4))),
    )

    assert today_payload["rows"] == []
    assert [row["source_match_id"] for row in tomorrow_payload["rows"]] == ["local-tomorrow"]


def test_default_reference_time_uses_provider_local_timezone() -> None:
    assert ledger_module._default_reference_time().utcoffset() == timedelta(hours=4)


def test_summary_counts_date_filtered_rows_before_status_filtering(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="summary-fresh",
        kickoff_time="2026-05-30T20:30:00+04:00",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="summary-needs-result",
        kickoff_time="2026-05-28T20:30:00+04:00",
        selection="HOME",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="summary-won",
        kickoff_time="2026-05-27T20:30:00+04:00",
        selection="AWAY",
        status="won",
        profit_loss_units=1.4,
        settled_at="2026-05-27T23:00:00+00:00",
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="all",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert [row["source_match_id"] for row in payload["rows"]] == ["summary-fresh"]
    assert payload["summary"]["fresh_count"] == 1
    assert payload["summary"]["needs_result_count"] == 1
    assert payload["summary"]["resulted_count"] == 1
    assert payload["summary"]["paper_profit_loss"] == 1.4
    assert payload["summary"]["win_rate"] == 1.0
