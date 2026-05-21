from datetime import UTC, datetime

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base
from app.db.repositories import MatchRepository, OddsSnapshotRepository
from app.services.odds_movement_service import OddsMovementService


def test_odds_movement_service_summarizes_repeated_snapshots(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'movement.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_movement_snapshots(engine)

    summaries = OddsMovementService(engine).summaries(
        now=datetime(2026, 5, 19, 12, 10, tzinfo=UTC),
        stale_after_minutes=60,
    )

    by_selection = {summary["selection"]: summary for summary in summaries}
    assert by_selection["HOME"]["opening_odds"] == 2.1
    assert by_selection["HOME"]["previous_odds"] == 2.1
    assert by_selection["HOME"]["current_odds"] == 2.3
    assert by_selection["HOME"]["movement_direction"] == "up"
    assert by_selection["HOME"]["status"] == "active"
    assert by_selection["DRAW"]["movement_direction"] == "stable"
    assert by_selection["AWAY"]["movement_direction"] == "down"
    assert by_selection["AWAY"]["current_odds"] == 2.8


def test_odds_movement_service_marks_missing_and_stale_outcomes(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'movement.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_movement_snapshots(engine, include_latest_draw=False)

    summaries = OddsMovementService(engine).summaries(
        now=datetime(2026, 5, 19, 14, 30, tzinfo=UTC),
        stale_after_minutes=60,
    )

    by_selection = {summary["selection"]: summary for summary in summaries}
    assert by_selection["DRAW"]["status"] == "missing"
    assert by_selection["DRAW"]["movement_direction"] == "missing"
    assert by_selection["DRAW"]["current_odds"] is None
    assert by_selection["DRAW"]["previous_odds"] == 3.1
    assert by_selection["HOME"]["status"] == "stale"
    assert by_selection["HOME"]["is_stale"] is True
    assert by_selection["HOME"]["movement_direction"] == "stale"


def _seed_movement_snapshots(engine, *, include_latest_draw: bool = True) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        odds = OddsSnapshotRepository(session)
        for selection, value in (("HOME", 2.1), ("DRAW", 3.1), ("AWAY", 3.0)):
            odds.add(
                match_id=match.id,
                source="misli_public",
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                odds_decimal=value,
                implied_probability=1 / value,
                snapshot_time="2026-05-19T11:00:00+00:00",
            )
        latest_values = {"HOME": 2.3, "AWAY": 2.8}
        if include_latest_draw:
            latest_values["DRAW"] = 3.1
        for selection, value in latest_values.items():
            odds.add(
                match_id=match.id,
                source="misli_public",
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                odds_decimal=value,
                implied_probability=1 / value,
                snapshot_time="2026-05-19T12:00:00+00:00",
            )
