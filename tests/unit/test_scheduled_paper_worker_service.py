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
    PaperRecommendation,
)
from app.db.repositories import LiveRunRepository
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

    assert worker_run is not None
    assert worker_run.status == "completed"
    assert worker_run.items_created == summary.items_created
    assert len(paper_bets) == summary.cycle_summary.write_paper_bets.items_created
    assert len(recommendations) == summary.recommendation_items
    assert len(combinations) == summary.combination_items
    assert len(ai_reviews) == 1


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
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                ],
                "raw_text": "20:30 1 Forest City - Eastport Athletic 1 2.16 X 3.18 2 2.94",
            }
        ],
    }
