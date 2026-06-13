import json

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, Match, PaperBet, Prediction, ResultFetchJob
from app.db.repositories import MatchRepository
from app.providers.misli_results import (
    MisliResult,
    match_misli_result,
    parse_misli_match_detail_payload,
    parse_misli_results_payload,
)
from app.services.misli_result_service import MisliResultService, result_jobs_payload


def test_parse_misli_results_payload_maps_completed_home_draw_and_away() -> None:
    payload = {
        "success": True,
        "data": {
            "data": [
                _result_item("2816300", "Home FC", "Away FC", "ENDED", 2, 1),
                _result_item("2816301", "Draw FC", "Level FC", "ENDED", 1, 1),
                _result_item("2816302", "Guest FC", "Road FC", "ENDED", 0, 3),
            ]
        },
    }

    results = parse_misli_results_payload(payload)

    assert [
        (result.source_match_id, result.status, result.home_score, result.away_score, result.result)
        for result in results
    ] == [
        ("misli:football:2816300", "completed", 2, 1, "HOME"),
        ("misli:football:2816301", "completed", 1, 1, "DRAW"),
        ("misli:football:2816302", "completed", 0, 3, "AWAY"),
    ]


def test_parse_misli_results_payload_keeps_non_final_games_unsettleable() -> None:
    payload = {
        "success": True,
        "data": {
            "data": [
                _result_item("2816300", "Scheduled FC", "Later FC", "SCHEDULED", None, None),
                _result_item("2816301", "Live FC", "Current FC", "LIVE", 1, 0),
                _result_item("2816302", "Postponed FC", "Delay FC", "POSTPONED", None, None),
            ]
        },
    }

    results = parse_misli_results_payload(payload)

    assert [(result.source_match_id, result.status, result.result) for result in results] == [
        ("misli:football:2816300", "scheduled", None),
        ("misli:football:2816301", "in_progress", None),
        ("misli:football:2816302", "postponed", None),
    ]


def test_parse_misli_match_detail_payload_maps_direct_match_result() -> None:
    payload = {
        "success": True,
        "data": {
            "sgi": 2842611,
            "d": 1781258400000,
            "s": "ENDED",
            "ht": {"n": "Nepean FC", "s": {"r": 0, "c": 0, "ht": 0}},
            "at": {"n": "Dunbar Rovers FC", "s": {"r": 2, "c": 2, "ht": 1}},
        },
    }

    result = parse_misli_match_detail_payload(payload)

    assert result is not None
    assert result.source_match_id == "misli:football:2842611"
    assert result.status == "completed"
    assert result.home_team == "Nepean FC"
    assert result.away_team == "Dunbar Rovers FC"
    assert result.home_score == 0
    assert result.away_score == 2
    assert result.result == "AWAY"


def test_parse_misli_match_detail_payload_preserves_completed_missing_score() -> None:
    payload = {
        "success": True,
        "data": {
            "sgi": 2842605,
            "d": 1781256600000,
            "s": "ENDED",
            "ht": {"n": "Gold Coast Knights"},
            "at": {"n": "Brisbane City FC"},
        },
    }

    result = parse_misli_match_detail_payload(payload)

    assert result is not None
    assert result.status == "completed"
    assert result.home_score is None
    assert result.away_score is None
    assert result.result is None


def test_match_misli_result_uses_sgid_then_rejects_ambiguous_fallback() -> None:
    match = _memory_match(
        source_match_id="misli:football:2816300",
        home_team="Forest City",
        away_team="Eastport Athletic",
        kickoff_time="2026-05-19T20:30:00+04:00",
    )
    exact = MisliResult(
        source_match_id="misli:football:2816300",
        misli_event_id="2816300",
        status="completed",
        home_team="Different Name",
        away_team="Other Name",
        kickoff_time="2026-05-19T20:30:00+04:00",
        home_score=1,
        away_score=0,
        result="HOME",
        raw_payload={"sgId": 2816300},
    )
    fallback = MisliResult(
        source_match_id="misli:football:9999999",
        misli_event_id="9999999",
        status="completed",
        home_team="Forest City",
        away_team="Eastport Athletic",
        kickoff_time="2026-05-19T20:30:00+04:00",
        home_score=1,
        away_score=0,
        result="HOME",
        raw_payload={"sgId": 9999999},
    )

    assert match_misli_result(match, [fallback, exact]) == exact
    assert match_misli_result(match, [fallback]) == fallback
    assert match_misli_result(match, [fallback, fallback]) is None


def test_collect_due_results_updates_completed_match_and_result_job(tmp_path) -> None:
    engine = _engine(tmp_path, "completed.sqlite")
    match_id = _seed_misli_match(engine, event_id="2816300")
    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816300", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=10,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    assert summary.errors_count == 0
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "completed"
    assert match.home_score == 2
    assert match.away_score == 1
    assert match.result == "HOME"
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 1


def test_collect_due_results_reschedules_postponed_match_without_settlement_state(tmp_path) -> None:
    engine = _engine(tmp_path, "postponed.sqlite")
    match_id = _seed_misli_match(engine, event_id="2816300")
    payload = {
        "success": True,
        "data": {
            "data": [
                _result_item(
                    "2816300",
                    "Forest City",
                    "Eastport Athletic",
                    "POSTPONED",
                    None,
                    None,
                )
            ]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=10,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 0
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "scheduled"
    assert match.home_score is None
    assert job is not None
    assert job.status == "postponed"
    assert job.next_attempt_at > "2026-05-20T01:00:00+04:00"


def test_collect_due_results_dry_run_does_not_update_match(tmp_path) -> None:
    engine = _engine(tmp_path, "dry-run.sqlite")
    match_id = _seed_misli_match(engine, event_id="2816300")
    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816300", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=True,
        limit=10,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 0
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "scheduled"
    assert job is not None
    assert job.status == "preview_completed"


def test_collect_due_results_retires_stale_jobs_before_due_limit(tmp_path) -> None:
    engine = _engine(tmp_path, "stale-jobs.sqlite")
    stale_match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-10T20:30:00+04:00",
    )
    fresh_match_id = _seed_misli_match(
        engine,
        event_id="2816300",
        kickoff_time="2026-05-19T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        session.add(
            ResultFetchJob(
                match_id=stale_match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816200",
                status="pending",
                next_attempt_at="2026-05-11T00:00:00+04:00",
                attempt_count=12,
                last_error="result not found in Misli response",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=fresh_match_id,
                source_match_id="misli:football:2816300",
                misli_event_id="2816300",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                status="pending",
                next_attempt_at="2026-05-19T22:30:00+04:00",
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816300", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        stale_job = session.scalar(
            select(ResultFetchJob).where(ResultFetchJob.match_id == stale_match_id)
        )
        fresh_job = session.scalar(
            select(ResultFetchJob).where(ResultFetchJob.match_id == fresh_match_id)
        )
    assert stale_job is not None
    assert stale_job.status == "unresolvable"
    assert stale_job.last_error == "result unavailable after repeated Misli lookups"
    assert fresh_job is not None
    assert fresh_job.status == "completed"


def test_collect_due_results_prioritizes_recent_due_jobs(tmp_path) -> None:
    engine = _engine(tmp_path, "recent-due.sqlite")
    old_match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-18T20:30:00+04:00",
    )
    recent_match_id = _seed_misli_match(
        engine,
        event_id="2816300",
        kickoff_time="2026-05-19T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        session.add(
            ResultFetchJob(
                match_id=old_match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816200",
                status="pending",
                next_attempt_at="2026-05-18T22:30:00+04:00",
                last_error="result not found in Misli response",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=recent_match_id,
                source_match_id="misli:football:2816300",
                misli_event_id="2816300",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                status="pending",
                next_attempt_at="2026-05-19T22:30:00+04:00",
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816300", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        old_job = session.scalar(
            select(ResultFetchJob).where(ResultFetchJob.match_id == old_match_id)
        )
        recent_job = session.scalar(
            select(ResultFetchJob).where(ResultFetchJob.match_id == recent_match_id)
        )
    assert old_job is not None
    assert old_job.status == "pending"
    assert recent_job is not None
    assert recent_job.status == "completed"


def test_collect_due_results_prioritizes_open_paper_bet_jobs(tmp_path) -> None:
    engine = _engine(tmp_path, "open-bet-priority.sqlite")
    bet_match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-18T20:30:00+04:00",
    )
    non_bet_match_id = _seed_misli_match(
        engine,
        event_id="2816300",
        kickoff_time="2026-05-19T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        prediction = Prediction(
            match_id=bet_match_id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.5,
            bookmaker_probability=0.48,
            edge=0.02,
            confidence_score=0.133333,
            decision="BET",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=bet_match_id,
                market="1X2",
                selection="HOME",
                odds_taken=2.0,
                stake_units=1.0,
                expected_value=0.01,
                status="open",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=bet_match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816200",
                status="pending",
                next_attempt_at="2026-05-18T22:30:00+04:00",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=non_bet_match_id,
                source_match_id="misli:football:2816300",
                misli_event_id="2816300",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                status="pending",
                next_attempt_at="2026-05-19T22:30:00+04:00",
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816200", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        bet_match = session.get(Match, bet_match_id)
        non_bet_job = session.scalar(
            select(ResultFetchJob).where(ResultFetchJob.match_id == non_bet_match_id)
        )
    assert bet_match is not None
    assert bet_match.status == "completed"
    assert non_bet_job is not None
    assert non_bet_job.status == "pending"


def test_collect_due_results_reopens_unresolvable_open_paper_bet_job(tmp_path) -> None:
    engine = _engine(tmp_path, "reopen-open-bet.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-18T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        prediction = Prediction(
            match_id=match_id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.5,
            bookmaker_probability=0.48,
            edge=0.02,
            confidence_score=0.133333,
            decision="BET",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=match_id,
                market="1X2",
                selection="HOME",
                odds_taken=2.0,
                stake_units=1.0,
                expected_value=0.01,
                status="open",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816200",
                status="unresolvable",
                next_attempt_at="2026-05-18T22:30:00+04:00",
                attempt_count=5,
                last_error="result unavailable after repeated Misli lookups",
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816200", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "completed"
    assert job is not None
    assert job.status == "completed"


def test_collect_due_results_reopens_completed_job_when_open_bet_match_is_unsettleable(
    tmp_path,
) -> None:
    engine = _engine(tmp_path, "reopen-completed-job.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-18T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        prediction = Prediction(
            match_id=match_id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.5,
            bookmaker_probability=0.48,
            edge=0.02,
            confidence_score=0.133333,
            decision="BET",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=match_id,
                market="1X2",
                selection="HOME",
                odds_taken=2.0,
                stake_units=1.0,
                expected_value=0.01,
                status="open",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816200",
                status="completed",
                next_attempt_at="2026-05-18T22:30:00+04:00",
                attempt_count=1,
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816200", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T01:00:00+04:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "completed"
    assert match.result == "HOME"
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 2


def test_collect_due_results_normalizes_open_bet_job_attempt_timezones(tmp_path) -> None:
    engine = _engine(tmp_path, "normalize-open-bet-attempt-time.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-20T21:00:00+04:00",
    )
    with session_scope(engine) as session:
        prediction = Prediction(
            match_id=match_id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.5,
            bookmaker_probability=0.48,
            edge=0.02,
            confidence_score=0.133333,
            decision="BET",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=match_id,
                market="1X2",
                selection="HOME",
                odds_taken=2.0,
                stake_units=1.0,
                expected_value=0.01,
                status="open",
            )
        )
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                status="pending",
                next_attempt_at="2026-05-20T23:00:00+04:00",
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816200", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(engine, fetcher=lambda: payload).collect_due_results(
        now_iso="2026-05-20T21:00:00+00:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert job is not None
    assert job.next_attempt_at == "2026-05-20T21:00:00+00:00"


def test_collect_due_results_classifies_open_bet_provider_retention_miss(tmp_path) -> None:
    engine = _engine(tmp_path, "provider-retention-miss.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-20T10:00:00+04:00",
    )
    with session_scope(engine) as session:
        _seed_open_paper_bet(session, match_id)
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                status="pending",
                next_attempt_at="2026-05-20T15:00:00+00:00",
                attempt_count=2,
                last_error="result not found in Misli response",
            )
        )

    payload = {"success": True, "data": {"data": []}}

    summary = MisliResultService(
        engine,
        fetcher=lambda: payload,
        match_detail_fetcher=lambda event_id: {"success": False},
    ).collect_due_results(
        now_iso="2026-05-20T15:00:00+00:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 0
    assert summary.items_skipped == 1
    with session_scope(engine) as session:
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert job is not None
    assert job.status == "unresolvable"
    assert job.last_error == (
        "provider_retention_miss: Misli current feed no longer contains event "
        "after repeated lookups"
    )

    result_payload = result_jobs_payload(
        engine,
        now_iso="2026-05-20T15:30:00+00:00",
    )

    assert result_payload["summary"]["retention_miss"] == 1
    assert result_payload["jobs"][0]["diagnostic_reason"] == "provider_retention_miss"
    assert result_payload["jobs"][0]["is_due"] is False


def test_collect_due_results_does_not_reopen_provider_result_missing_score(tmp_path) -> None:
    engine = _engine(tmp_path, "provider-result-missing-score-stays-terminal.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-20T10:00:00+04:00",
    )
    with session_scope(engine) as session:
        _seed_open_paper_bet(session, match_id)
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816200",
                misli_event_id="2816200",
                status="unresolvable",
                next_attempt_at="2026-05-20T15:00:00+00:00",
                attempt_count=3,
                last_error=(
                    "provider_result_missing_score: Misli match detail returned final event "
                    "without score"
                ),
            )
        )

    payload = {
        "success": True,
        "data": {
            "data": [_result_item("2816200", "Forest City", "Eastport Athletic", "ENDED", 2, 1)]
        },
    }

    summary = MisliResultService(
        engine,
        fetcher=lambda: payload,
        match_detail_fetcher=lambda event_id: payload,
    ).collect_due_results(
        now_iso="2026-05-20T16:00:00+00:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 0
    assert summary.items_updated == 0
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "scheduled"
    assert job is not None
    assert job.status == "unresolvable"
    assert job.last_error == (
        "provider_result_missing_score: Misli match detail returned final event without score"
    )


def test_collect_due_results_uses_match_detail_for_provider_retention_miss(tmp_path) -> None:
    engine = _engine(tmp_path, "provider-retention-detail-settlement.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2842611",
        kickoff_time="2026-06-12T14:00:00+04:00",
    )
    with session_scope(engine) as session:
        _seed_open_paper_bet(session, match_id)
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2842611",
                misli_event_id="2842611",
                status="unresolvable",
                next_attempt_at="2026-06-13T08:32:11+00:00",
                attempt_count=18,
                last_error=(
                    "provider_retention_miss: Misli current feed no longer contains event "
                    "after repeated lookups"
                ),
            )
        )

    detail_payload = {
        "success": True,
        "data": {
            "sgi": 2842611,
            "d": 1781258400000,
            "s": "ENDED",
            "ht": {"n": "Nepean FC", "s": {"r": 0, "c": 0, "ht": 0}},
            "at": {"n": "Dunbar Rovers FC", "s": {"r": 2, "c": 2, "ht": 1}},
        },
    }

    summary = MisliResultService(
        engine,
        fetcher=lambda: {"success": True, "data": {"data": []}},
        match_detail_fetcher=lambda event_id: detail_payload,
    ).collect_due_results(
        now_iso="2026-06-13T09:00:00+00:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 1
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "completed"
    assert match.home_score == 0
    assert match.away_score == 2
    assert match.result == "AWAY"
    assert job is not None
    assert job.status == "completed"


def test_collect_due_results_classifies_match_detail_missing_score(tmp_path) -> None:
    engine = _engine(tmp_path, "provider-detail-missing-score.sqlite")
    match_id = _seed_misli_match(
        engine,
        event_id="2842605",
        kickoff_time="2026-06-12T13:30:00+04:00",
    )
    with session_scope(engine) as session:
        _seed_open_paper_bet(session, match_id)
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2842605",
                misli_event_id="2842605",
                status="unresolvable",
                next_attempt_at="2026-06-13T08:32:11+00:00",
                attempt_count=18,
                last_error=(
                    "provider_retention_miss: Misli current feed no longer contains event "
                    "after repeated lookups"
                ),
            )
        )

    detail_payload = {
        "success": True,
        "data": {
            "sgi": 2842605,
            "d": 1781256600000,
            "s": "ENDED",
            "ht": {"n": "Gold Coast Knights"},
            "at": {"n": "Brisbane City FC"},
        },
    }

    summary = MisliResultService(
        engine,
        fetcher=lambda: {"success": True, "data": {"data": []}},
        match_detail_fetcher=lambda event_id: detail_payload,
    ).collect_due_results(
        now_iso="2026-06-13T09:00:00+00:00",
        dry_run=False,
        limit=1,
    )

    assert summary.items_read == 1
    assert summary.items_updated == 0
    assert summary.items_skipped == 1
    with session_scope(engine) as session:
        match = session.get(Match, match_id)
        job = session.scalar(select(ResultFetchJob).where(ResultFetchJob.match_id == match_id))
    assert match is not None
    assert match.status == "scheduled"
    assert job is not None
    assert job.status == "unresolvable"
    assert job.last_error == (
        "provider_result_missing_score: Misli match detail returned final event without score"
    )

    result_payload = result_jobs_payload(engine, now_iso="2026-06-13T09:30:00+00:00")

    assert result_payload["summary"]["missing_score"] == 1
    assert result_payload["jobs"][0]["diagnostic_reason"] == "provider_result_missing_score"


def test_result_jobs_payload_counts_unresolvable_jobs(tmp_path) -> None:
    engine = _engine(tmp_path, "result-job-payload.sqlite")
    match_id = _seed_misli_match(engine, event_id="2816300")
    with session_scope(engine) as session:
        session.add(
            ResultFetchJob(
                match_id=match_id,
                source_match_id="misli:football:2816300",
                misli_event_id="2816300",
                detail_url="https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
                status="unresolvable",
                next_attempt_at="2026-05-19T22:30:00+04:00",
                last_error="result unavailable after repeated Misli lookups",
            )
        )

    payload = result_jobs_payload(
        engine,
        now_iso="2026-05-20T01:00:00+04:00",
    )

    assert payload["summary"]["unresolvable"] == 1
    assert payload["summary"]["pending"] == 0
    assert payload["jobs"][0]["is_due"] is False


def test_result_jobs_payload_prioritizes_open_paper_bet_jobs(tmp_path) -> None:
    engine = _engine(tmp_path, "result-job-open-bet-first.sqlite")
    stale_match_id = _seed_misli_match(
        engine,
        event_id="2816300",
        kickoff_time="2026-05-18T20:30:00+04:00",
    )
    open_bet_match_id = _seed_misli_match(
        engine,
        event_id="2816200",
        kickoff_time="2026-05-20T20:30:00+04:00",
    )
    with session_scope(engine) as session:
        prediction = Prediction(
            match_id=open_bet_match_id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.5,
            bookmaker_probability=0.48,
            edge=0.02,
            confidence_score=0.133333,
            decision="BET",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=open_bet_match_id,
                market="1X2",
                selection="HOME",
                odds_taken=2.0,
                stake_units=1.0,
                expected_value=0.01,
                status="open",
            )
        )
        session.add_all(
            [
                ResultFetchJob(
                    match_id=stale_match_id,
                    source_match_id="misli:football:2816300",
                    misli_event_id="2816300",
                    status="unresolvable",
                    next_attempt_at="2026-05-18T22:30:00+04:00",
                    last_error="result unavailable after repeated Misli lookups",
                ),
                ResultFetchJob(
                    match_id=open_bet_match_id,
                    source_match_id="misli:football:2816200",
                    misli_event_id="2816200",
                    status="pending",
                    next_attempt_at="2026-05-20T22:30:00+04:00",
                ),
            ]
        )

    payload = result_jobs_payload(
        engine,
        now_iso="2026-05-20T23:00:00+04:00",
    )

    assert payload["jobs"][0]["match_id"] == open_bet_match_id


def _result_item(
    sg_id: str,
    home_team: str,
    away_team: str,
    status: str,
    home_score: int | None,
    away_score: int | None,
) -> dict:
    return {
        "id": int(sg_id) + 1000,
        "sgId": int(sg_id),
        "date": 1779204600000,
        "status": status,
        "homeTeam": {
            "teamName": home_team,
            "scores": {"CURRENT": home_score} if home_score is not None else None,
        },
        "awayTeam": {
            "teamName": away_team,
            "scores": {"CURRENT": away_score} if away_score is not None else None,
        },
    }


def _engine(tmp_path, filename: str):
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(engine)
    return engine


def _seed_misli_match(
    engine,
    *,
    event_id: str,
    kickoff_time: str = "2026-05-19T20:30:00+04:00",
) -> int:
    raw_payload = {
        "event_id": event_id,
        "source_match_id": f"misli:football:{event_id}",
        "detail_url": f"https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/{event_id}",
    }
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=f"misli:football:{event_id}",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time=kickoff_time,
            raw_payload_json=json.dumps(raw_payload),
        )
        return match.id


def _seed_open_paper_bet(session, match_id: int) -> None:
    prediction = Prediction(
        match_id=match_id,
        market="1X2",
        selection="HOME",
        model_name="baseline_heuristic",
        model_version="v0",
        model_probability=0.5,
        bookmaker_probability=0.48,
        edge=0.02,
        confidence_score=0.133333,
        decision="BET",
    )
    session.add(prediction)
    session.flush()
    session.add(
        PaperBet(
            prediction_id=prediction.id,
            match_id=match_id,
            market="1X2",
            selection="HOME",
            odds_taken=2.0,
            stake_units=1.0,
            expected_value=0.01,
            status="open",
        )
    )


def _memory_match(*, source_match_id: str, home_team: str, away_team: str, kickoff_time: str):
    class MemoryMatch:
        pass

    match = MemoryMatch()
    match.source_match_id = source_match_id
    match.home_team = home_team
    match.away_team = away_team
    match.kickoff_time = kickoff_time
    return match
