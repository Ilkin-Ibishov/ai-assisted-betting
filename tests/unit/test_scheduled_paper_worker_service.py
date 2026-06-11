import json

from sqlalchemy import select

from app.config import load_settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import (
    AIAnalysisRun,
    Base,
    LiveRun,
    PaperBet,
    PaperCombination,
    PaperJournalEntry,
    PaperRecommendation,
)
from app.db.repositories import (
    LiveRunRepository,
    MatchRepository,
    PaperBetRepository,
    PredictionRepository,
)
from app.services.collection_service import CollectionService
from app.services.scheduled_worker_service import (
    ScheduledPaperWorkerRequest,
    ScheduledPaperWorkerService,
)


def test_scheduled_worker_runs_one_paper_cycle_when_enabled(tmp_path, monkeypatch) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "worker.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LIVE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("MIN_EDGE", "0.01")
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    CollectionService(engine).import_sample_data()

    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(
            provider="misli-public",
            snapshot=snapshot_path,
            model="baseline_heuristic",
        )
    )

    assert summary.status == "completed"
    assert summary.cycle_summary is not None
    assert summary.cycle_summary.status == "completed"
    assert summary.errors_count == 0
    assert summary.snapshot_path == snapshot_path
    assert summary.ai_review_id is not None
    assert summary.journal_id is not None
    assert summary.settlement_summary is not None
    assert summary.settlement_summary.errors_count == 0

    with session_scope(engine) as session:
        worker_run = session.scalar(
            select(LiveRun).where(LiveRun.run_type == "scheduled_paper_worker")
        )
        paper_bets = list(session.scalars(select(PaperBet)))
        recommendations = list(session.scalars(select(PaperRecommendation)))
        combinations = list(session.scalars(select(PaperCombination)))
        ai_reviews = list(
            session.scalars(
                select(AIAnalysisRun).where(AIAnalysisRun.analysis_type == "recommendation_review")
            )
        )
        threshold_reviews = list(
            session.scalars(
                select(AIAnalysisRun).where(
                    AIAnalysisRun.analysis_type == "recommendation_backtest_summary"
                )
            )
        )
        journals = list(session.scalars(select(PaperJournalEntry)))

    assert worker_run is not None
    assert worker_run.status == "completed"
    assert worker_run.items_created == summary.items_created
    assert len(paper_bets) == summary.cycle_summary.write_paper_bets.items_created
    assert len(recommendations) == summary.recommendation_items
    assert len(combinations) == summary.combination_items
    assert len(ai_reviews) == 1
    assert len(threshold_reviews) == 1
    assert len(journals) == 1
    assert journals[0].id == summary.journal_id
    journal_payload = json.loads(journals[0].summary_json)
    assert journal_payload["threshold_review"]["overall_decision"] != "missing"
    assert f"ai_analysis:{threshold_reviews[0].id}" in journal_payload["source_ids"]


def test_scheduled_worker_settles_completed_open_bets_when_enabled(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "worker-settlement.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LIVE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("SCHEDULED_SETTLEMENT_ENABLED", "true")
    monkeypatch.setenv("MIN_EDGE", "0.01")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    CollectionService(engine).import_sample_data()
    _seed_completed_open_bet(engine)

    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(
            provider="misli-public",
            snapshot=snapshot_path,
            model="baseline_heuristic",
        )
    )

    assert summary.status == "completed"
    assert summary.settlement_summary is not None
    assert summary.settlement_summary.items_read >= 1
    assert summary.settlement_summary.items_updated == 1

    with session_scope(engine) as session:
        settled_bets = list(session.scalars(select(PaperBet).where(PaperBet.status == "won")))

    assert len(settled_bets) == 1
    assert settled_bets[0].profit_loss_units == 1.0


def test_scheduled_worker_can_resolve_fresh_snapshot_url(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "fresh-misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "worker-url.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LIVE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("MIN_EDGE", "0.01")
    monkeypatch.setattr(
        "app.services.scheduled_worker_service._download_snapshot_url",
        lambda url: snapshot_path,
    )
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    CollectionService(engine).import_sample_data()

    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(
            provider="misli-public",
            snapshot_url="https://example.com/misli/latest.json",
            model="baseline_heuristic",
        )
    )

    assert summary.status == "completed"
    assert summary.snapshot_path == snapshot_path
    assert summary.ai_review_id is not None
    assert summary.journal_id is not None

    with session_scope(engine) as session:
        worker_run = session.scalar(
            select(LiveRun).where(LiveRun.run_type == "scheduled_paper_worker")
        )

    assert worker_run is not None
    assert worker_run.run_id.startswith(
        "scheduled_paper_worker:misli-public:baseline_heuristic:url:example.com/misli/latest.json"
    )


def test_scheduled_worker_refuses_to_run_when_live_collection_disabled(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "worker-disabled.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LIVE_COLLECTION_ENABLED", "false")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)

    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.status == "failed"
    assert summary.errors_count == 1
    assert summary.error_summary == "LIVE_COLLECTION_ENABLED must be true"
    assert summary.cycle_summary is None
    assert summary.ai_review_id is None

    with session_scope(engine) as session:
        worker_run = session.scalar(
            select(LiveRun).where(LiveRun.run_type == "scheduled_paper_worker")
        )

    assert worker_run is not None
    assert worker_run.status == "failed"
    assert worker_run.error_summary == "LIVE_COLLECTION_ENABLED must be true"


def test_scheduled_worker_skips_when_another_worker_is_running(tmp_path, monkeypatch) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "worker-overlap.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LIVE_COLLECTION_ENABLED", "true")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        LiveRunRepository(session).start(
            run_id="scheduled_paper_worker:existing",
            run_type="scheduled_paper_worker",
            provider="misli_public",
        )

    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(provider="misli-public", snapshot=snapshot_path)
    )

    assert summary.status == "skipped"
    assert summary.errors_count == 0
    assert summary.error_summary == "another scheduled_paper_worker run is already running"
    assert summary.cycle_summary is None

    with session_scope(engine) as session:
        worker_runs = list(
            session.scalars(select(LiveRun).where(LiveRun.run_type == "scheduled_paper_worker"))
        )
        paper_bets = list(session.scalars(select(PaperBet)))

    assert len(worker_runs) == 1
    assert worker_runs[0].status == "running"
    assert paper_bets == []


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
                "home_team": "Forest City",
                "away_team": "Eastport Athletic",
                "kickoff_date": "19.05.2026",
                "kickoff_time": "20:30",
                "league": "Sample Premier",
                "odds": [
                    {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                    {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 3.40},
                ],
                "raw_text": "20:30 1 Forest City - Eastport Athletic 1 2.16 X 3.18 2 3.40",
            }
        ],
    }


def _seed_completed_open_bet(engine) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="manual",
            source_match_id="completed-001",
            league="Sample Premier",
            home_team="Completed Home",
            away_team="Completed Away",
            kickoff_time="2026-05-18T20:30:00+04:00",
            status="completed",
        )
        match.home_score = 2
        match.away_score = 1
        match.result = "HOME"
        prediction = PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.6,
            bookmaker_probability=0.5,
            edge=0.1,
            confidence_score=0.7,
            decision="BET",
            reason="seed completed open bet",
        )
        PaperBetRepository(session).add(
            prediction_id=prediction.id,
            match_id=match.id,
            market="1X2",
            selection="HOME",
            odds_taken=2.0,
            stake_units=1.0,
            expected_value=0.2,
            status="open",
        )
