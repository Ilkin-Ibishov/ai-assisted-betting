from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base
from app.db.repositories import LiveRunRepository
from app.services.worker_monitoring_service import WorkerMonitoringService


def test_worker_monitoring_reports_never_run(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'worker-status-empty.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)

    status = WorkerMonitoringService(database_url).status()

    assert status["status"] == "never_run"
    assert status["healthy"] is False
    assert status["latest_worker_run"] is None
    assert status["freshness_minutes"] is None


def test_worker_monitoring_reports_fresh_completed_worker(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'worker-status-fresh.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="scheduled-worker-fresh",
        status="completed",
        started_at="2026-05-22T08:30:00+00:00",
        finished_at="2026-05-22T08:31:00+00:00",
    )

    status = WorkerMonitoringService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        fresh_after_minutes=60,
    )

    assert status["status"] == "fresh"
    assert status["healthy"] is True
    assert status["freshness_minutes"] == 29
    assert status["latest_worker_run"]["run_id"] == "scheduled-worker-fresh"


def test_worker_monitoring_reports_stale_completed_worker(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'worker-status-stale.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="scheduled-worker-stale",
        status="completed",
        started_at="2026-05-22T07:00:00+00:00",
        finished_at="2026-05-22T07:01:00+00:00",
    )

    status = WorkerMonitoringService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        fresh_after_minutes=60,
    )

    assert status["status"] == "stale"
    assert status["healthy"] is False
    assert status["freshness_minutes"] == 119


def test_worker_monitoring_reports_failed_worker(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'worker-status-failed.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    _seed_worker_run(
        engine,
        run_id="scheduled-worker-failed",
        status="failed",
        started_at="2026-05-22T08:55:00+00:00",
        finished_at="2026-05-22T08:56:00+00:00",
        error_summary="provider parser drift",
    )

    status = WorkerMonitoringService(database_url).status(
        now_iso="2026-05-22T09:00:00+00:00",
        fresh_after_minutes=60,
    )

    assert status["status"] == "failed"
    assert status["healthy"] is False
    assert status["latest_worker_run"]["error_summary"] == "provider parser drift"


def _seed_worker_run(
    engine,
    *,
    run_id: str,
    status: str,
    started_at: str,
    finished_at: str | None,
    error_summary: str | None = None,
) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id=run_id,
            run_type="scheduled_paper_worker",
            provider="misli_public",
            model_name="baseline_heuristic",
        )
        live_run = repository.get_by_run_id(run_id)
        assert live_run is not None
        live_run.started_at = started_at
        if status == "completed":
            repository.complete(run_id=run_id, items_read=5, items_created=2)
        elif status == "failed":
            repository.fail(run_id=run_id, errors_count=1, error_summary=error_summary)
        live_run = repository.get_by_run_id(run_id)
        assert live_run is not None
        live_run.started_at = started_at
        live_run.finished_at = finished_at
