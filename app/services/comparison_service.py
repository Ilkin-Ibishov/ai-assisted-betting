import csv
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from app.config import Settings
from app.db.engine import create_engine_from_url
from app.services.replay_service import ReplayService


@dataclass(frozen=True)
class ReplayComparisonRequest:
    league: str
    season: str
    models: list[str]
    bookmakers: list[str]
    report_name: str
    path: Path | None = None
    url: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    min_history: int = 3
    keep_run_dbs: bool = False
    workers: int | None = None


class ReplayComparisonService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def compare(self, request: ReplayComparisonRequest) -> tuple[str, str, list[dict[str, object]]]:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_report_name(request.report_name)
        comparison_dir = Path("data") / "comparisons" / safe_name
        if comparison_dir.exists():
            shutil.rmtree(comparison_dir)
        comparison_dir.mkdir(parents=True, exist_ok=True)
        cached_source_path = _cache_source_csv(request, comparison_dir)
        if request.keep_run_dbs:
            return self._compare_with_run_directory(
                request=request,
                reports_dir=reports_dir,
                safe_name=safe_name,
                cached_source_path=cached_source_path,
                run_database_dir=comparison_dir,
            )

        with tempfile.TemporaryDirectory(
            prefix=f"paper-odds-lab-{safe_name}-",
            ignore_cleanup_errors=True,
        ) as temp_dir:
            return self._compare_with_run_directory(
                request=request,
                reports_dir=reports_dir,
                safe_name=safe_name,
                cached_source_path=cached_source_path,
                run_database_dir=Path(temp_dir),
            )

    def _compare_with_run_directory(
        self,
        *,
        request: ReplayComparisonRequest,
        reports_dir: Path,
        safe_name: str,
        cached_source_path: Path,
        run_database_dir: Path,
    ) -> tuple[str, str, list[dict[str, object]]]:
        jobs = [
            (model_name, bookmaker)
            for model_name in request.models
            for bookmaker in request.bookmakers
        ]
        worker_count = _comparison_worker_count(len(jobs), request.workers)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            runs = list(
                executor.map(
                    lambda job: self._run_comparison_job(
                        request=request,
                        safe_name=safe_name,
                        cached_source_path=cached_source_path,
                        run_database_dir=run_database_dir,
                        model_name=job[0],
                        bookmaker=job[1],
                    ),
                    jobs,
                )
            )

        rankings = _annotate_rankings(runs)
        csv_path = reports_dir / f"{safe_name}_comparison.csv"
        json_path = reports_dir / f"{safe_name}_comparison.json"
        _write_comparison_csv(csv_path, runs)
        metadata = {
            "models": request.models,
            "bookmakers": request.bookmakers,
            "league": request.league,
            "season": request.season,
            "from_date": request.from_date,
            "to_date": request.to_date,
            "min_history": request.min_history,
            "generated_at": datetime.now(UTC).isoformat(),
            "source_path": request.path.as_posix() if request.path is not None else None,
            "source_url": request.url,
            "cached_source_path": cached_source_path.as_posix(),
            "keep_run_dbs": request.keep_run_dbs,
            "run_database_dir": (
                run_database_dir.as_posix() if request.keep_run_dbs else None
            ),
            "parallel_workers": worker_count,
        }
        json_path.write_text(
            json.dumps(
                {"metadata": metadata, "rankings": rankings, "runs": runs},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return csv_path.as_posix(), json_path.as_posix(), runs

    def _run_comparison_job(
        self,
        *,
        request: ReplayComparisonRequest,
        safe_name: str,
        cached_source_path: Path,
        run_database_dir: Path,
        model_name: str,
        bookmaker: str,
    ) -> dict[str, object]:
        run_name = f"{safe_name}_{model_name}_{bookmaker}"
        database_path = run_database_dir / f"{run_name}.sqlite"
        database_url = f"sqlite:///{database_path.as_posix()}"
        run_settings = self.settings.__class__(
            **{
                **self.settings.__dict__,
                "database_url": database_url,
                "model_name": model_name,
            }
        )
        engine = create_engine_from_url(database_url)
        try:
            ReplayService(engine, run_settings).replay_football_data(
                league=request.league,
                season=request.season,
                bookmaker=bookmaker,
                path=cached_source_path,
                url=None,
                from_date=request.from_date,
                to_date=request.to_date,
                min_history=request.min_history,
                report_name=run_name,
            )
        finally:
            engine.dispose()
        summary_path = Path("reports") / f"{run_name}_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return {
            "model": model_name,
            "bookmaker": bookmaker,
            "model_config": summary["model_config"],
            "total_bets": summary["total_bets"],
            "settled_bets": summary["settled_bets"],
            "wins": summary["wins"],
            "losses": summary["losses"],
            "roi": summary["roi"],
            "profit_loss_units": summary["profit_loss_units"],
            "average_odds": summary["average_odds"],
            "average_edge": summary["average_edge"],
            "brier_score": summary["brier_score"],
            "log_loss": summary["log_loss"],
        }


def _write_comparison_csv(path: Path, runs: list[dict[str, object]]) -> None:
    fieldnames = [
        "model",
        "bookmaker",
        "total_bets",
        "settled_bets",
        "wins",
        "losses",
        "roi",
        "profit_loss_units",
        "average_odds",
        "average_edge",
        "brier_score",
        "log_loss",
        "roi_rank",
        "brier_score_rank",
        "log_loss_rank",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            writer.writerow({field: run[field] for field in fieldnames})


def _comparison_worker_count(job_count: int, requested_workers: int | None) -> int:
    if requested_workers is not None and requested_workers < 1:
        raise ValueError("workers must be at least 1")
    configured_workers = requested_workers or 4
    return max(1, min(job_count, configured_workers))


def _annotate_rankings(runs: list[dict[str, object]]) -> dict[str, dict[str, object] | None]:
    ranking_specs = {
        "roi": True,
        "brier_score": False,
        "log_loss": False,
    }
    rankings: dict[str, dict[str, object] | None] = {}

    for metric, reverse in ranking_specs.items():
        rank_field = f"{metric}_rank"
        ranked_runs = sorted(
            runs,
            key=lambda run, metric=metric, reverse=reverse: _ranking_key(
                run.get(metric),
                reverse=reverse,
            ),
        )
        for rank, run in enumerate(ranked_runs, start=1):
            run[rank_field] = rank

        winner = next(
            (run for run in ranked_runs if _metric_value(run.get(metric)) is not None),
            None,
        )
        rankings[f"best_{metric}"] = (
            {
                "model": winner["model"],
                "bookmaker": winner["bookmaker"],
                "value": winner[metric],
            }
            if winner is not None
            else None
        )

    return rankings


def _ranking_key(value: object, *, reverse: bool) -> tuple[int, float]:
    metric_value = _metric_value(value)
    if metric_value is None:
        return (1, 0.0)
    return (0, -metric_value if reverse else metric_value)


def _metric_value(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _cache_source_csv(request: ReplayComparisonRequest, comparison_dir: Path) -> Path:
    cached_source_path = comparison_dir / "source.csv"
    if request.path is not None:
        shutil.copyfile(request.path, cached_source_path)
        return cached_source_path

    source_url = request.url or (
        f"https://www.football-data.co.uk/mmz4281/{request.season}/{request.league}.csv"
    )
    with urlopen(source_url, timeout=30) as response:
        cached_source_path.write_bytes(response.read())
    return cached_source_path


def _safe_report_name(report_name: str) -> str:
    safe_characters = [
        character if character.isalnum() or character in "-_" else "_"
        for character in report_name
    ]
    return "".join(safe_characters).strip("_") or "replay_comparison"
