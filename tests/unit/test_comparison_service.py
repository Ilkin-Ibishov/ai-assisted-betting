import json
import threading
import time
from pathlib import Path

from app.config import Settings
from app.services import comparison_service
from app.services.comparison_service import (
    ReplayComparisonRequest,
    ReplayComparisonService,
    _annotate_rankings,
    _comparison_worker_count,
)


def test_annotate_rankings_marks_winners_and_ranks_null_metrics_last() -> None:
    runs: list[dict[str, object]] = [
        {
            "model": "baseline_heuristic",
            "bookmaker": "B365",
            "roi": 0.05,
            "brier_score": 0.22,
            "log_loss": None,
        },
        {
            "model": "elo",
            "bookmaker": "Avg",
            "roi": None,
            "brier_score": 0.18,
            "log_loss": 0.61,
        },
        {
            "model": "elo",
            "bookmaker": "B365",
            "roi": 0.12,
            "brier_score": None,
            "log_loss": 0.57,
        },
    ]

    rankings = _annotate_rankings(runs)

    assert rankings == {
        "best_roi": {"model": "elo", "bookmaker": "B365", "value": 0.12},
        "best_brier_score": {"model": "elo", "bookmaker": "Avg", "value": 0.18},
        "best_log_loss": {"model": "elo", "bookmaker": "B365", "value": 0.57},
    }
    assert runs[2]["roi_rank"] == 1
    assert runs[1]["roi_rank"] == 3
    assert runs[1]["brier_score_rank"] == 1
    assert runs[2]["brier_score_rank"] == 3
    assert runs[2]["log_loss_rank"] == 1
    assert runs[0]["log_loss_rank"] == 3


def test_compare_runs_model_bookmaker_pairs_concurrently(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "source.csv"
    source_path.write_text("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n", encoding="utf-8")

    active_runs = 0
    max_active_runs = 0
    lock = threading.Lock()

    class FakeEngine:
        def dispose(self) -> None:
            pass

    class FakeReplayService:
        def __init__(self, _engine, _settings: Settings) -> None:
            pass

        def replay_football_data(
            self,
            *,
            league: str,
            season: str,
            bookmaker: str,
            path: Path,
            url: str | None,
            from_date: str | None,
            to_date: str | None,
            min_history: int,
            report_name: str,
        ) -> str:
            nonlocal active_runs, max_active_runs
            with lock:
                active_runs += 1
                max_active_runs = max(max_active_runs, active_runs)
            time.sleep(0.05)
            with lock:
                active_runs -= 1

            reports_dir = Path("reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / f"{report_name}_summary.json").write_text(
                json.dumps(
                    {
                        "model_config": {"model_name": report_name},
                        "total_bets": 1,
                        "settled_bets": 1,
                        "wins": 1,
                        "losses": 0,
                        "roi": 0.1,
                        "profit_loss_units": 0.1,
                        "average_odds": 2.0,
                        "average_edge": 0.05,
                        "brier_score": 0.2,
                        "log_loss": 0.6,
                    }
                ),
                encoding="utf-8",
            )
            return "ok"

    monkeypatch.setattr(comparison_service, "ReplayService", FakeReplayService)
    monkeypatch.setattr(comparison_service, "create_engine_from_url", lambda _url: FakeEngine())

    settings = Settings(
        database_url="sqlite:///unused.sqlite",
        default_sport="football",
        default_market="1X2",
        default_stake_units=1.0,
        min_edge=0.01,
        min_odds=1.7,
        max_odds=3.5,
        feature_version="v0",
        model_name="baseline_heuristic",
        model_version="v0",
        elo_initial_rating=1500,
        elo_k_factor=20,
        elo_home_advantage=65,
        log_level="INFO",
        live_collection_enabled=False,
    )

    ReplayComparisonService(settings).compare(
        ReplayComparisonRequest(
            league="E0",
            season="2526",
            models=["baseline_heuristic", "elo"],
            bookmakers=["B365", "Avg"],
            report_name="parallel_test",
            path=source_path,
        )
    )

    assert max_active_runs > 1


def test_comparison_worker_count_uses_requested_limit_and_rejects_invalid_values() -> None:
    assert _comparison_worker_count(job_count=4, requested_workers=2) == 2
    assert _comparison_worker_count(job_count=2, requested_workers=8) == 2
    assert _comparison_worker_count(job_count=3, requested_workers=None) == 3

    try:
        _comparison_worker_count(job_count=4, requested_workers=0)
    except ValueError as exc:
        assert str(exc) == "workers must be at least 1"
    else:
        raise AssertionError("expected invalid worker count to fail")
