import json

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, LiveRun, Match
from app.db.repositories import MatchRepository
from app.services.live_result_service import LiveResultRequest, LiveResultService


def test_live_result_service_updates_matching_scheduled_match(tmp_path) -> None:
    result_path = tmp_path / "results.json"
    result_path.write_text(json.dumps(_results_payload()), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _insert_match(engine)

    summary = LiveResultService(engine).collect_results(
        LiveResultRequest(provider="manual", path=result_path)
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    assert summary.errors_count == 0

    with session_scope(engine) as session:
        match = session.scalar(select(Match))
        live_run = session.scalar(select(LiveRun))

    assert match is not None
    assert match.status == "completed"
    assert match.home_score == 2
    assert match.away_score == 1
    assert match.result == "HOME"
    assert live_run is not None
    assert live_run.status == "completed"


def test_live_result_service_is_idempotent_for_completed_match(tmp_path) -> None:
    result_path = tmp_path / "results.json"
    result_path.write_text(json.dumps(_results_payload()), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _insert_match(engine)

    first = LiveResultService(engine).collect_results(
        LiveResultRequest(provider="manual", path=result_path)
    )
    second = LiveResultService(engine).collect_results(
        LiveResultRequest(provider="manual", path=result_path)
    )

    assert first.items_updated == 1
    assert second.items_updated == 0
    assert second.items_skipped == 1


def test_live_result_service_records_missing_match_as_failed_run(tmp_path) -> None:
    result_path = tmp_path / "results.json"
    result_path.write_text(json.dumps(_results_payload()), encoding="utf-8")
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    Base.metadata.create_all(engine)

    summary = LiveResultService(engine).collect_results(
        LiveResultRequest(provider="manual", path=result_path)
    )

    assert summary.items_read == 1
    assert summary.items_updated == 0
    assert summary.items_skipped == 1
    assert summary.errors_count == 1

    with session_scope(engine) as session:
        live_run = session.scalar(select(LiveRun))

    assert live_run is not None
    assert live_run.status == "failed"
    assert "Missing match" in (live_run.error_summary or "")


def _insert_match(engine) -> None:
    with session_scope(engine) as session:
        MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Northbridge FC",
            away_team="Metro United",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )


def _results_payload() -> dict:
    return {
        "source": "manual",
        "collected_at": "2026-05-20T01:00:00+04:00",
        "results": [
            {
                "source": "misli_public",
                "source_match_id": "misli:football:2816300",
                "home_score": 2,
                "away_score": 1,
                "result": "HOME",
            }
        ],
    }
