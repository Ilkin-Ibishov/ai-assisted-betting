from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, DecisionLog, PaperBet
from app.db.repositories import MatchRepository, PaperBetRepository, PredictionRepository
from app.services.paper_bet_maintenance_service import PaperBetMaintenanceService


def test_void_unsafe_open_bets_marks_legacy_rows_void(tmp_path: Path) -> None:
    database_url = _create_database(tmp_path)
    engine = create_engine_from_url(database_url)
    safe_bet_id, unsafe_bet_id = _seed_paper_bets(database_url)

    summary = PaperBetMaintenanceService(engine).void_unsafe_open_bets(
        dry_run=False,
        now=datetime(2026, 5, 28, 18, 0, tzinfo=UTC),
    )

    with session_scope(engine) as session:
        safe_bet = session.get(PaperBet, safe_bet_id)
        unsafe_bet = session.get(PaperBet, unsafe_bet_id)
        logs = list(session.scalars(select(DecisionLog)))

    assert summary.items_read == 2
    assert summary.unsafe_count == 1
    assert summary.risk_flag_counts == {
        "low_confidence": 1,
        "negative_expected_value": 1,
        "past_kickoff_open": 1,
    }
    assert summary.items_updated == 1
    assert summary.items_skipped == 1
    assert safe_bet is not None
    assert safe_bet.status == "open"
    assert unsafe_bet is not None
    assert unsafe_bet.status == "void"
    assert unsafe_bet.profit_loss_units == 0.0
    assert unsafe_bet.settled_at == "2026-05-28T18:00:00+00:00"
    assert logs[0].stage == "VOID_UNSAFE_PAPER_BET"
    assert "negative_expected_value" in logs[0].message


def test_void_unsafe_open_bets_dry_run_does_not_mutate(tmp_path: Path) -> None:
    database_url = _create_database(tmp_path)
    engine = create_engine_from_url(database_url)
    _, unsafe_bet_id = _seed_paper_bets(database_url)

    summary = PaperBetMaintenanceService(engine).void_unsafe_open_bets(
        dry_run=True,
        now=datetime(2026, 5, 28, 18, 0, tzinfo=UTC),
    )

    with session_scope(engine) as session:
        unsafe_bet = session.get(PaperBet, unsafe_bet_id)
        logs_count = len(list(session.scalars(select(DecisionLog))))

    assert summary.unsafe_count == 1
    assert summary.risk_flag_counts == {
        "low_confidence": 1,
        "negative_expected_value": 1,
        "past_kickoff_open": 1,
    }
    assert summary.items_updated == 0
    assert unsafe_bet is not None
    assert unsafe_bet.status == "open"
    assert logs_count == 0


def _create_database(tmp_path: Path) -> str:
    database_url = f"sqlite:///{(tmp_path / 'paper_bets.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return database_url


def _seed_paper_bets(database_url: str) -> tuple[int, int]:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        matches = MatchRepository(session)
        predictions = PredictionRepository(session)
        bets = PaperBetRepository(session)
        safe_match = matches.add(
            source="sample",
            source_match_id="safe",
            league="Sample Premier",
            home_team="Safe Home",
            away_team="Safe Away",
            kickoff_time="2026-05-29T20:30:00+00:00",
        )
        unsafe_match = matches.add(
            source="sample",
            source_match_id="unsafe",
            league="Sample Premier",
            home_team="Unsafe Home",
            away_team="Unsafe Away",
            kickoff_time="2026-05-28T17:00:00+00:00",
        )
        safe_prediction = predictions.add(
            match_id=safe_match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.60,
            bookmaker_probability=0.50,
            edge=0.10,
            confidence_score=0.65,
            decision="BET",
        )
        unsafe_prediction = predictions.add(
            match_id=unsafe_match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.40,
            bookmaker_probability=0.32,
            edge=0.08,
            confidence_score=0.35,
            decision="BET",
        )
        safe_bet = bets.add(
            prediction_id=safe_prediction.id,
            match_id=safe_match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.0,
            stake_units=1.0,
            expected_value=0.2,
            status="open",
        )
        unsafe_bet = bets.add(
            prediction_id=unsafe_prediction.id,
            match_id=unsafe_match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.2,
            stake_units=1.0,
            expected_value=-0.12,
            status="open",
        )
        return safe_bet.id, unsafe_bet.id
