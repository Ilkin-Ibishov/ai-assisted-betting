import json

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, LiveRun, Match, OddsSnapshot
from app.services.live_collection_service import LiveCollectionRequest, LiveCollectionService


def test_live_collection_imports_valid_misli_snapshot_idempotently(tmp_path) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    request = LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)

    first_matches = LiveCollectionService(engine).collect_matches(request)
    first_odds = LiveCollectionService(engine).collect_odds(request)
    second_matches = LiveCollectionService(engine).collect_matches(request)
    second_odds = LiveCollectionService(engine).collect_odds(request)

    assert first_matches.items_read == 1
    assert first_matches.items_created == 1
    assert first_odds.items_created == 3
    assert second_matches.items_created == 0
    assert second_matches.items_skipped == 1
    assert second_odds.items_created == 0
    assert second_odds.items_skipped == 3

    with session_scope(engine) as session:
        matches = list(session.scalars(select(Match)))
        odds = list(session.scalars(select(OddsSnapshot)))
        live_runs = list(session.scalars(select(LiveRun)))

    assert len(matches) == 1
    assert matches[0].source == "misli_public"
    assert matches[0].kickoff_time == "2026-05-19T20:30:00+04:00"
    assert len(odds) == 3
    assert {snapshot.selection for snapshot in odds} == {"HOME", "DRAW", "AWAY"}
    assert {run.status for run in live_runs} == {"completed"}


def test_live_collection_refuses_misli_match_without_full_kickoff_date(tmp_path) -> None:
    snapshot = _valid_snapshot()
    snapshot["events"][0]["kickoff_date"] = ""
    snapshot["events"][0]["kickoff_time"] = ""
    snapshot_path = tmp_path / "misli-missing-date.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveCollectionService(engine).collect_matches(
        LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.items_read == 1
    assert summary.items_created == 0
    assert summary.items_skipped == 1
    assert summary.errors_count == 1

    with session_scope(engine) as session:
        assert session.scalar(select(Match)) is None
        live_run = session.scalar(select(LiveRun))

    assert live_run is not None
    assert live_run.status == "failed"
    assert "full kickoff date" in (live_run.error_summary or "")


def test_live_collection_imports_relative_today_misli_kickoff_date(tmp_path) -> None:
    snapshot = _valid_snapshot()
    snapshot["scraped_at"] = "2026-05-20T18:52:54.693Z"
    snapshot["events"][0]["kickoff_date"] = ""
    snapshot["events"][0]["kickoff_time"] = "Bu Gün 23:00"
    snapshot_path = tmp_path / "misli-relative-date.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveCollectionService(engine).collect_matches(
        LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.items_created == 1
    assert summary.errors_count == 0
    with session_scope(engine) as session:
        match = session.scalar(select(Match))

    assert match is not None
    assert match.kickoff_time == "2026-05-20T23:00:00+04:00"


def test_live_collection_refuses_incomplete_misli_1x2_odds(tmp_path) -> None:
    snapshot = _valid_snapshot()
    snapshot["events"][0]["odds"] = snapshot["events"][0]["odds"][:2]
    snapshot_path = tmp_path / "misli-incomplete-odds.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveCollectionService(engine).collect_odds(
        LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.items_read == 1
    assert summary.items_created == 0
    assert summary.items_skipped == 1
    assert summary.errors_count == 1

    with session_scope(engine) as session:
        assert session.scalar(select(OddsSnapshot)) is None
        live_run = session.scalar(select(LiveRun))

    assert live_run is not None
    assert live_run.status == "failed"
    assert "complete 1X2" in (live_run.error_summary or "")


def test_live_collection_records_empty_misli_snapshot_as_parser_drift(tmp_path) -> None:
    snapshot = _valid_snapshot()
    snapshot["event_count"] = 0
    snapshot["events"] = []
    snapshot_path = tmp_path / "misli-empty.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveCollectionService(engine).collect_matches(
        LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.items_read == 0
    assert summary.items_created == 0
    assert summary.items_skipped == 0
    assert summary.errors_count == 1

    with session_scope(engine) as session:
        live_run = session.scalar(select(LiveRun))

    assert live_run is not None
    assert live_run.status == "failed"
    assert "possible Misli parser drift" in (live_run.error_summary or "")


def test_live_collection_records_misli_low_extraction_confidence(tmp_path) -> None:
    snapshot = _valid_snapshot()
    snapshot["event_count"] = 1
    snapshot["events"] = []
    snapshot["extraction_summary"] = {
        "row_count": 4,
        "event_count": 0,
        "skipped_rows_count": 4,
    }
    snapshot_path = tmp_path / "misli-low-confidence.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveCollectionService(engine).collect_matches(
        LiveCollectionRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.errors_count == 2

    with session_scope(engine) as session:
        live_run = session.scalar(select(LiveRun))

    assert live_run is not None
    assert "possible Misli parser drift" in (live_run.error_summary or "")
    assert "extraction confidence is low" in (live_run.error_summary or "")


def _valid_snapshot() -> dict:
    return {
        "source": "misli_public",
        "page_url": "https://www.misli.az/idman-novleri/futbol",
        "scraped_at": "2026-05-19T13:43:22.194Z",
        "event_count": 1,
        "events": [
            {
                "source": "misli_public",
                "sport": "football",
                "event_id": "2816300",
                "source_match_id": "misli:football:2816300",
                "detail_url": "https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                "home_team": "Rid",
                "away_team": "Volfsberq",
                "kickoff_date": "19.05.2026",
                "kickoff_time": "20:30",
                "league": "Bundesliqa, Avropa Liqasi Pley-Off",
                "odds": [
                    {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                    {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                ],
                "raw_text": "20:30 1 Rid - Volfsberq 1 2.16 X 3.18 2 2.94",
            }
        ],
    }
