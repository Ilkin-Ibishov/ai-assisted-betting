import json
from pathlib import Path

import typer

from app.config import load_settings
from app.db.engine import create_engine_from_url
from app.db.migrations import init_db as run_init_db
from app.services.ai_analysis_service import AIAnalysisService
from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService
from app.services.collection_service import CollectionService
from app.services.comparison_service import ReplayComparisonRequest, ReplayComparisonService
from app.services.evaluation_service import EvaluationService, format_evaluation_report
from app.services.football_data_service import FootballDataImportRequest, FootballDataImportService
from app.services.live_collection_service import LiveCollectionRequest, LiveCollectionService
from app.services.live_cycle_service import LivePaperCycleRequest, LivePaperCycleService
from app.services.live_result_service import LiveResultRequest, LiveResultService
from app.services.prediction_service import PredictionService
from app.services.replay_service import ReplayService
from app.services.scheduled_worker_service import (
    ScheduledPaperWorkerRequest,
    ScheduledPaperWorkerService,
)
from app.services.settlement_service import SettlementService

app = typer.Typer(help="Paper Odds Lab CLI.")
LEAGUE_OPTION = typer.Option(..., help="Football-Data league code, for example E0.")
SEASON_OPTION = typer.Option(..., help="Season code, for example 2526.")
PATH_OPTION = typer.Option(None, help="Local Football-Data CSV file.")
URL_OPTION = typer.Option(None, help="Football-Data CSV URL.")
BOOKMAKER_OPTION = typer.Option("B365", help="Bookmaker code, such as B365, Avg, or ALL.")
FROM_DATE_OPTION = typer.Option(None, help="Replay candidate start date, YYYY-MM-DD.")
TO_DATE_OPTION = typer.Option(None, help="Replay candidate end date, YYYY-MM-DD.")
MIN_HISTORY_OPTION = typer.Option(3, help="Minimum prior completed matches per team.")
WORKERS_OPTION = typer.Option(None, help="Parallel comparison worker count.")
REPORT_NAME_OPTION = typer.Option(None, help="Report name for CSV and JSON exports.")
ANALYSIS_REPORT_OPTION = typer.Option(..., help="Comparison JSON report path.")
MODEL_OPTION = typer.Option(None, help="Prediction model: baseline_heuristic or elo.")
MODELS_OPTION = typer.Option("baseline_heuristic,elo", help="Comma-separated model names.")
BOOKMAKERS_OPTION = typer.Option("B365,Avg", help="Comma-separated bookmaker codes.")
LIVE_PROVIDER_OPTION = typer.Option("misli-public", help="Live provider key.")
SNAPSHOT_OPTION = typer.Option(..., help="Live provider snapshot JSON path.")
RESULT_PROVIDER_OPTION = typer.Option("manual", help="Result provider key.")
RESULT_PATH_OPTION = typer.Option(..., help="Manual result JSON path.")


def _not_implemented(command_name: str) -> None:
    typer.echo(f"{command_name}: not implemented yet")


def _print_summary(command_name: str, summary) -> None:
    typer.echo(f"{command_name}: started")
    typer.echo(f"items_read={summary.items_read}")
    typer.echo(f"items_created={summary.items_created}")
    typer.echo(f"items_updated={summary.items_updated}")
    typer.echo(f"items_skipped={summary.items_skipped}")
    typer.echo(f"errors_count={summary.errors_count}")
    typer.echo(f"{command_name}: finished")


def _print_stage_summary(stage: str, summary) -> None:
    typer.echo(f"{stage}.items_read={summary.items_read}")
    typer.echo(f"{stage}.items_created={summary.items_created}")
    typer.echo(f"{stage}.items_updated={summary.items_updated}")
    typer.echo(f"{stage}.items_skipped={summary.items_skipped}")
    typer.echo(f"{stage}.errors_count={summary.errors_count}")


def _settings_with_model(settings, model: str | None):
    if model is None:
        return settings
    return settings.__class__(**{**settings.__dict__, "model_name": model})


@app.callback()
def main() -> None:
    """Run Paper Odds Lab commands."""


@app.command("init-db")
def init_db() -> None:
    settings = load_settings()
    run_init_db(settings.database_url)
    typer.echo(f"init-db: created tables at {settings.database_url}")


@app.command("import-sample-data")
def import_sample_data() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = CollectionService(engine).import_sample_data()
    _print_summary("import-sample-data", summary)


@app.command("import-football-data")
def import_football_data(
    league: str = LEAGUE_OPTION,
    season: str = SEASON_OPTION,
    bookmaker: str = BOOKMAKER_OPTION,
    path: Path | None = PATH_OPTION,
    url: str | None = URL_OPTION,
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = FootballDataImportService(engine).import_csv(
        FootballDataImportRequest(
            league=league,
            season=season,
            bookmaker=bookmaker,
            path=path,
            url=url,
        )
    )
    _print_summary("import-football-data", summary)


@app.command("replay-football-data")
def replay_football_data(
    league: str = LEAGUE_OPTION,
    season: str = SEASON_OPTION,
    bookmaker: str = BOOKMAKER_OPTION,
    path: Path | None = PATH_OPTION,
    url: str | None = URL_OPTION,
    from_date: str | None = FROM_DATE_OPTION,
    to_date: str | None = TO_DATE_OPTION,
    min_history: int = MIN_HISTORY_OPTION,
    report_name: str | None = REPORT_NAME_OPTION,
    model: str | None = MODEL_OPTION,
) -> None:
    settings = load_settings()
    settings = _settings_with_model(settings, model)
    engine = create_engine_from_url(settings.database_url)
    output = ReplayService(engine, settings).replay_football_data(
        league=league,
        season=season,
        bookmaker=bookmaker,
        path=path,
        url=url,
        from_date=from_date,
        to_date=to_date,
        min_history=min_history,
        report_name=report_name,
    )
    typer.echo(output)


@app.command("compare-replays")
def compare_replays(
    league: str = LEAGUE_OPTION,
    season: str = SEASON_OPTION,
    models: str = MODELS_OPTION,
    bookmakers: str = BOOKMAKERS_OPTION,
    path: Path | None = PATH_OPTION,
    url: str | None = URL_OPTION,
    from_date: str | None = FROM_DATE_OPTION,
    to_date: str | None = TO_DATE_OPTION,
    min_history: int = MIN_HISTORY_OPTION,
    workers: int | None = WORKERS_OPTION,
    report_name: str = typer.Option("replay_comparison", help="Comparison report name."),
    keep_run_dbs: bool = typer.Option(False, help="Keep per-run scratch SQLite DBs."),
) -> None:
    if workers is not None and workers < 1:
        raise typer.BadParameter("workers must be at least 1")
    settings = load_settings()
    csv_path, json_path, runs = ReplayComparisonService(settings).compare(
        ReplayComparisonRequest(
            league=league,
            season=season,
            models=_split_csv_option(models),
            bookmakers=_split_csv_option(bookmakers),
            report_name=report_name,
            path=path,
            url=url,
            from_date=from_date,
            to_date=to_date,
            min_history=min_history,
            keep_run_dbs=keep_run_dbs,
            workers=workers,
        )
    )
    typer.echo("compare-replays: started")
    for run in runs:
        typer.echo(
            f"{run['model']} {run['bookmaker']} "
            f"bets={run['total_bets']} roi={run['roi']}"
        )
    typer.echo(f"comparison_csv={csv_path}")
    typer.echo(f"comparison_json={json_path}")
    typer.echo("compare-replays: finished")


@app.command("analyze-comparison")
def analyze_comparison(
    report: Path = ANALYSIS_REPORT_OPTION,
) -> None:
    try:
        typer.echo(ComparisonAnalysisService().analyze_comparison_report(report))
    except ComparisonAnalysisError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc


@app.command("analyze-live-status")
def analyze_live_status() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    analysis = AIAnalysisService(engine).analyze_live_status()
    output = json.loads(analysis.output_json)
    typer.echo("analyze-live-status: started")
    typer.echo(f"analysis_id={analysis.id}")
    typer.echo(f"analysis_type={analysis.analysis_type}")
    typer.echo(f"model_name={analysis.model_name}")
    typer.echo(f"prompt_version={analysis.prompt_version}")
    typer.echo(f"label={output.get('label')}")
    typer.echo(f"short_summary={output.get('short_summary')}")
    typer.echo("analyze-live-status: finished")


@app.command("analyze-comparison-ai")
def analyze_comparison_ai(
    report: Path = ANALYSIS_REPORT_OPTION,
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    analysis = AIAnalysisService(engine).analyze_comparison_report(report)
    output = json.loads(analysis.output_json)
    typer.echo("analyze-comparison-ai: started")
    typer.echo(f"analysis_id={analysis.id}")
    typer.echo(f"analysis_type={analysis.analysis_type}")
    typer.echo(f"model_name={analysis.model_name}")
    typer.echo(f"prompt_version={analysis.prompt_version}")
    typer.echo(f"label={output.get('label')}")
    typer.echo(f"short_summary={output.get('short_summary')}")
    typer.echo("analyze-comparison-ai: finished")


@app.command("analyze-provider-health")
def analyze_provider_health(
    provider: str = typer.Option("misli_public", help="Live provider key in live_runs."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    analysis = AIAnalysisService(engine).analyze_provider_health(provider)
    output = json.loads(analysis.output_json)
    typer.echo("analyze-provider-health: started")
    typer.echo(f"analysis_id={analysis.id}")
    typer.echo(f"analysis_type={analysis.analysis_type}")
    typer.echo(f"model_name={analysis.model_name}")
    typer.echo(f"prompt_version={analysis.prompt_version}")
    typer.echo(f"label={output.get('label')}")
    typer.echo(f"short_summary={output.get('short_summary')}")
    typer.echo("analyze-provider-health: finished")


def _split_csv_option(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.command("collect-matches")
def collect_matches(
    provider: str = LIVE_PROVIDER_OPTION,
    snapshot: Path = SNAPSHOT_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for imported live rows."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = LiveCollectionService(engine).collect_matches(
        LiveCollectionRequest(
            provider=provider,
            snapshot=snapshot,
            league=league,
            season=season,
        )
    )
    _print_summary("collect-matches", summary)


@app.command("collect-odds")
def collect_odds(
    provider: str = LIVE_PROVIDER_OPTION,
    snapshot: Path = SNAPSHOT_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for imported live rows."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = LiveCollectionService(engine).collect_odds(
        LiveCollectionRequest(
            provider=provider,
            snapshot=snapshot,
            league=league,
            season=season,
        )
    )
    _print_summary("collect-odds", summary)


@app.command("run-live-paper-cycle")
def run_live_paper_cycle(
    provider: str = LIVE_PROVIDER_OPTION,
    snapshot: Path = SNAPSHOT_OPTION,
    model: str | None = MODEL_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for imported live rows."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = LivePaperCycleService(engine, settings).run(
        LivePaperCycleRequest(
            provider=provider,
            snapshot=snapshot,
            model=model,
            league=league,
            season=season,
        )
    )
    typer.echo("run-live-paper-cycle: started")
    typer.echo(f"status={summary.status}")
    _print_stage_summary("collect_matches", summary.collect_matches)
    _print_stage_summary("collect_odds", summary.collect_odds)
    _print_stage_summary("generate_features", summary.generate_features)
    _print_stage_summary("generate_predictions", summary.generate_predictions)
    _print_stage_summary("write_paper_bets", summary.write_paper_bets)
    typer.echo(f"items_read={summary.items_read}")
    typer.echo(f"items_created={summary.items_created}")
    typer.echo(f"items_updated={summary.items_updated}")
    typer.echo(f"items_skipped={summary.items_skipped}")
    typer.echo(f"errors_count={summary.errors_count}")
    typer.echo("run-live-paper-cycle: finished")


@app.command("run-scheduled-paper-worker")
def run_scheduled_paper_worker(
    provider: str = LIVE_PROVIDER_OPTION,
    snapshot: Path = SNAPSHOT_OPTION,
    model: str | None = MODEL_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for imported live rows."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = ScheduledPaperWorkerService(engine, settings).run_once(
        ScheduledPaperWorkerRequest(
            provider=provider,
            snapshot=snapshot,
            model=model,
            league=league,
            season=season,
        )
    )
    typer.echo("run-scheduled-paper-worker: started")
    typer.echo(f"status={summary.status}")
    typer.echo(f"run_id={summary.run_id}")
    if summary.cycle_summary is not None:
        typer.echo(f"cycle.status={summary.cycle_summary.status}")
        _print_stage_summary("cycle.collect_matches", summary.cycle_summary.collect_matches)
        _print_stage_summary("cycle.collect_odds", summary.cycle_summary.collect_odds)
        _print_stage_summary(
            "cycle.generate_features",
            summary.cycle_summary.generate_features,
        )
        _print_stage_summary(
            "cycle.generate_predictions",
            summary.cycle_summary.generate_predictions,
        )
        _print_stage_summary("cycle.write_paper_bets", summary.cycle_summary.write_paper_bets)
    if summary.error_summary:
        typer.echo(f"error_summary={summary.error_summary}")
    typer.echo(f"items_read={summary.items_read}")
    typer.echo(f"items_created={summary.items_created}")
    typer.echo(f"items_updated={summary.items_updated}")
    typer.echo(f"items_skipped={summary.items_skipped}")
    typer.echo(f"errors_count={summary.errors_count}")
    typer.echo("run-scheduled-paper-worker: finished")


@app.command("collect-results")
def collect_results(
    provider: str = RESULT_PROVIDER_OPTION,
    path: Path = RESULT_PATH_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for result rows."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = LiveResultService(engine).collect_results(
        LiveResultRequest(
            provider=provider,
            path=path,
            league=league,
            season=season,
        )
    )
    _print_summary("collect-results", summary)


@app.command("generate-features")
def generate_features() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = PredictionService(engine, settings).generate_features()
    _print_summary("generate-features", summary)


@app.command("generate-predictions")
def generate_predictions(model: str | None = MODEL_OPTION) -> None:
    settings = load_settings()
    settings = _settings_with_model(settings, model)
    engine = create_engine_from_url(settings.database_url)
    summary = PredictionService(engine, settings).generate_predictions()
    _print_summary("generate-predictions", summary)


@app.command("write-paper-bets")
def write_paper_bets(model: str | None = MODEL_OPTION) -> None:
    settings = load_settings()
    settings = _settings_with_model(settings, model)
    engine = create_engine_from_url(settings.database_url)
    summary = PredictionService(engine, settings).write_paper_bets()
    _print_summary("write-paper-bets", summary)


@app.command("settle-results")
def settle_results() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = SettlementService(engine).settle_results()
    _print_summary("settle-results", summary)


@app.command("evaluate")
def evaluate() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    report = EvaluationService(engine, settings).evaluate()
    typer.echo(format_evaluation_report(report))


@app.command("show-config")
def show_config() -> None:
    settings = load_settings()
    typer.echo(f"database_url={settings.database_url}")
    typer.echo(f"default_market={settings.default_market}")
    typer.echo(f"min_edge={settings.min_edge}")
    typer.echo(f"odds_range={settings.min_odds}-{settings.max_odds}")


if __name__ == "__main__":
    app()
