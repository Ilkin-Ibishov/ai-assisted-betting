import json
from pathlib import Path

import typer
from sqlalchemy.engine import make_url

from app.config import load_settings
from app.db.engine import create_engine_from_url
from app.db.migrations import init_db as run_init_db
from app.providers.api_football_provider import ApiFootballProvider
from app.services.ai_analysis_service import AIAnalysisService
from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService
from app.services.collection_service import CollectionService
from app.services.combination_service import CombinationService
from app.services.comparison_service import ReplayComparisonRequest, ReplayComparisonService
from app.services.daily_paper_journal_service import DailyPaperJournalService
from app.services.evaluation_service import EvaluationService, format_evaluation_report
from app.services.external_context_probe_service import (
    ExternalContextProbeRequest,
    ExternalContextProbeService,
)
from app.services.feature_enrichment_audit_service import FeatureEnrichmentAuditService
from app.services.football_data_service import FootballDataImportRequest, FootballDataImportService
from app.services.live_collection_service import LiveCollectionRequest, LiveCollectionService
from app.services.live_cycle_service import LivePaperCycleRequest, LivePaperCycleService
from app.services.live_result_service import LiveResultRequest, LiveResultService
from app.services.misli_result_service import MisliResultService
from app.services.operational_guardrail_service import OperationalGuardrailService
from app.services.paper_bet_maintenance_service import PaperBetMaintenanceService
from app.services.prediction_service import PredictionService
from app.services.production_smoke_service import (
    ProductionSmokeError,
    ProductionSmokeRequest,
    ProductionSmokeService,
)
from app.services.recommendation_backtest_service import (
    RecommendationBacktestRequest,
    RecommendationBacktestService,
)
from app.services.recommendation_quality_service import RecommendationQualityService
from app.services.recommendation_service import RecommendationService
from app.services.replay_service import ReplayService
from app.services.scheduled_worker_service import (
    ScheduledPaperWorkerRequest,
    ScheduledPaperWorkerService,
)
from app.services.settlement_service import SettlementService
from app.services.threshold_policy_service import ThresholdPolicyService

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
WORKER_SNAPSHOT_OPTION = typer.Option(None, help="Live provider snapshot JSON path.")
SNAPSHOT_URL_OPTION = typer.Option(
    None,
    help="HTTPS URL returning a fresh live provider snapshot JSON document.",
)
RESULT_PROVIDER_OPTION = typer.Option("manual", help="Result provider key.")
RESULT_PATH_OPTION = typer.Option(None, help="Manual result JSON path.")
RECOMMENDATION_BACKTEST_REPORT_OPTION = typer.Option(
    ...,
    help="Recommendation backtest JSON report path.",
)
REPORTS_DIR_OPTION = typer.Option(Path("reports"), help="Directory for report exports.")
PRODUCTION_API_URL_OPTION = typer.Option(
    "",
    help="Deployed API base URL, for example https://api.up.railway.app.",
)
PRODUCTION_DASHBOARD_URL_OPTION = typer.Option(
    "",
    help="Optional deployed dashboard URL.",
)


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


def _safe_database_url(database_url: str) -> str:
    return make_url(database_url).render_as_string(hide_password=True)


@app.callback()
def main() -> None:
    """Run Paper Odds Lab commands."""


@app.command("init-db")
def init_db() -> None:
    settings = load_settings()
    run_init_db(settings.database_url)
    typer.echo(f"init-db: created tables at {_safe_database_url(settings.database_url)}")


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


@app.command("analyze-recommendations")
def analyze_recommendations(
    limit: int = typer.Option(50, help="Maximum recommendations and combinations to review."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    analysis = AIAnalysisService(engine).analyze_recommendation_review(limit=limit)
    output = json.loads(analysis.output_json)
    typer.echo("analyze-recommendations: started")
    typer.echo(f"analysis_id={analysis.id}")
    typer.echo(f"analysis_type={analysis.analysis_type}")
    typer.echo(f"model_name={analysis.model_name}")
    typer.echo(f"prompt_version={analysis.prompt_version}")
    typer.echo(f"status={analysis.status}")
    typer.echo(f"approval_state={output.get('approval_state')}")
    typer.echo(f"short_summary={output.get('short_summary')}")
    typer.echo("analyze-recommendations: finished")


@app.command("backtest-recommendations")
def backtest_recommendations(
    report_name: str = typer.Option("recommendation_backtest", help="Backtest report name."),
    reports_dir: Path = REPORTS_DIR_OPTION,
    min_edge: float = typer.Option(0.0, help="Minimum edge for included recommendations."),
    min_confidence: float = typer.Option(
        0.0,
        help="Minimum confidence for included recommendations.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    csv_path, json_path, report = RecommendationBacktestService(engine).export(
        RecommendationBacktestRequest(
            report_name=report_name,
            min_edge=min_edge,
            min_confidence=min_confidence,
        ),
        reports_dir=reports_dir,
    )
    typer.echo("backtest-recommendations: started")
    typer.echo(f"report_csv={csv_path}")
    typer.echo(f"report_json={json_path}")
    typer.echo(f"singles.settled_bets={report['singles']['settled_bets']}")
    typer.echo(f"singles.roi={report['singles']['roi']}")
    typer.echo(f"combinations.settled_bets={report['combinations']['settled_bets']}")
    typer.echo(f"combinations.roi={report['combinations']['roi']}")
    typer.echo("backtest-recommendations: finished")


@app.command("analyze-recommendation-backtest")
def analyze_recommendation_backtest(
    report: Path = RECOMMENDATION_BACKTEST_REPORT_OPTION,
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    analysis = AIAnalysisService(engine).analyze_recommendation_backtest_report(report)
    output = json.loads(analysis.output_json)
    typer.echo("analyze-recommendation-backtest: started")
    typer.echo(f"analysis_id={analysis.id}")
    typer.echo(f"analysis_type={analysis.analysis_type}")
    typer.echo(f"model_name={analysis.model_name}")
    typer.echo(f"prompt_version={analysis.prompt_version}")
    typer.echo(f"status={analysis.status}")
    typer.echo(f"label={output.get('label')}")
    typer.echo(f"short_summary={output.get('short_summary')}")
    typer.echo("analyze-recommendation-backtest: finished")


@app.command("production-smoke")
def production_smoke(
    api_base_url: str = PRODUCTION_API_URL_OPTION,
    dashboard_url: str = PRODUCTION_DASHBOARD_URL_OPTION,
) -> None:
    typer.echo("production-smoke: started")
    try:
        report = ProductionSmokeService().run(
            ProductionSmokeRequest(
                api_base_url=api_base_url,
                dashboard_url=dashboard_url or None,
            )
        )
    except ProductionSmokeError as exc:
        typer.echo("production-smoke: failed")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(report, indent=2, sort_keys=True))
    typer.echo("production-smoke: finished")


@app.command("operational-status")
def operational_status(
    worker_fresh_after_minutes: int = typer.Option(
        90,
        help="Minutes before the latest scheduled worker run is considered stale.",
    ),
    repeated_failure_threshold: int = typer.Option(
        3,
        help="Consecutive failed worker runs required for critical status.",
    ),
) -> None:
    settings = load_settings()
    report = OperationalGuardrailService(settings.database_url).status(
        worker_fresh_after_minutes=worker_fresh_after_minutes,
        repeated_failure_threshold=repeated_failure_threshold,
    )
    typer.echo("operational-status: started")
    typer.echo(f"overall_status={report['overall_status']}")
    for guardrail in report["guardrails"]:
        typer.echo(f"{guardrail['name']}={guardrail['severity']}:{guardrail['state']}")
    typer.echo("operational-status: finished")


@app.command("recommendation-quality")
def recommendation_quality(
    fresh_after_minutes: int = typer.Option(
        90,
        help="Minutes before recommendation snapshots are treated as stale.",
    ),
    limit: int = typer.Option(500, help="Maximum recommendations and combinations to inspect."),
) -> None:
    settings = load_settings()
    report = RecommendationQualityService(settings.database_url).report(
        fresh_after_minutes=fresh_after_minutes,
        limit=limit,
    )
    typer.echo("recommendation-quality: started")
    typer.echo(f"overall_state={report['overall_state']}")
    typer.echo(f"actionable_count={report['summary']['actionable_count']}")
    typer.echo(f"watchlist_count={report['summary']['watchlist_count']}")
    typer.echo(f"rejected_count={report['summary']['rejected_count']}")
    typer.echo(f"fresh_snapshot_count={report['summary']['fresh_snapshot_count']}")
    typer.echo(f"ai_approval_state={report['ai_review']['approval_state']}")
    typer.echo("recommendation-quality: finished")


@app.command("feature-enrichment-audit")
def feature_enrichment_audit(
    limit: int = typer.Option(100, help="Maximum scheduled matches to audit."),
    minimum_history: int = typer.Option(3, help="Minimum prior matches required per team."),
    include_past: bool = typer.Option(False, help="Include past scheduled rows."),
    source: str | None = typer.Option("misli_public", help="Match source to audit."),
    source_match_id_prefix: str | None = typer.Option(
        "misli:football:",
        help="Source match id prefix to audit.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        report = FeatureEnrichmentAuditService(engine).report(
            limit=limit,
            minimum_history=minimum_history,
            include_past=include_past,
            source=source or None,
            source_match_id_prefix=source_match_id_prefix or None,
        )
    finally:
        engine.dispose()
    typer.echo("feature-enrichment-audit: started")
    typer.echo(f"scheduled_matches={report['scheduled_matches']}")
    typer.echo(f"source={report['source']}")
    typer.echo(f"source_match_id_prefix={report['source_match_id_prefix']}")
    typer.echo(f"audited_matches={report['audited_matches']}")
    typer.echo(f"full_enriched_candidates={report['full_enriched_candidates']}")
    typer.echo(f"partial_enriched_candidates={report['partial_enriched_candidates']}")
    typer.echo(f"cold_start_candidates={report['cold_start_candidates']}")
    typer.echo(f"unmatched_team_slots={report['team_coverage']['unmatched_team_slots']}")
    for team in report["unmatched_teams"][:10]:
        typer.echo(
            "unmatched_team="
            f"{team['team']}|league={team['league']}|history_count={team['history_count']}"
        )
    typer.echo("feature-enrichment-audit: finished")


@app.command("probe-external-context")
def probe_external_context(
    provider: str = typer.Option("api-football", help="External context provider."),
    limit: int = typer.Option(20, help="Maximum unmatched teams to probe."),
    minimum_history: int = typer.Option(3, help="Minimum recent fixtures required."),
    history_sample_size: int = typer.Option(5, help="Recent fixtures to request per candidate."),
    max_query_variants: int = typer.Option(3, help="Maximum search variants per team."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    api_football = None
    if provider == "api-football" and settings.api_football_key:
        api_football = ApiFootballProvider(
            api_key=settings.api_football_key,
            base_url=settings.api_football_base_url,
        )
    try:
        report = ExternalContextProbeService(
            engine,
            api_football_provider=api_football,
        ).probe(
            ExternalContextProbeRequest(
                provider=provider,
                limit=limit,
                minimum_history=minimum_history,
                history_sample_size=history_sample_size,
                max_query_variants=max_query_variants,
            )
        )
    finally:
        engine.dispose()

    typer.echo("probe-external-context: started")
    typer.echo(f"provider={report['provider']}")
    typer.echo(f"status={report['status']}")
    if report["status"] == "missing_credentials":
        typer.echo(f"required_env={report['required_env']}")
    typer.echo(f"teams_read={report['teams_read']}")
    typer.echo(f"matched_count={report['matched_count']}")
    typer.echo(f"ambiguous_count={report['ambiguous_count']}")
    typer.echo(f"insufficient_history_count={report.get('insufficient_history_count', 0)}")
    typer.echo(f"unmatched_count={report['unmatched_count']}")
    typer.echo(json.dumps(report, indent=2, sort_keys=True))
    typer.echo("probe-external-context: finished")


@app.command("daily-paper-journal")
def daily_paper_journal(
    journal_date: str | None = typer.Option(
        None,
        help="Journal date in YYYY-MM-DD format. Defaults to today.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        journal = DailyPaperJournalService(
            engine,
            product_timezone=settings.product_timezone,
        ).generate(journal_date=journal_date)
    finally:
        engine.dispose()
    typer.echo("daily-paper-journal: started")
    typer.echo(f"journal_date={journal['journal_date']}")
    typer.echo(f"decision_state={journal['decision_state']}")
    typer.echo(f"candidate_count={journal['summary']['candidate_count']}")
    typer.echo(f"watchlist_count={journal['summary']['watchlist_count']}")
    typer.echo(f"settled_count={journal['summary']['settled_count']}")
    typer.echo(f"ai_approval_state={journal['summary']['ai_approval_state']}")
    typer.echo("daily-paper-journal: finished")


@app.command("threshold-policy-evaluate")
def threshold_policy_evaluate() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        policy = ThresholdPolicyService(engine, settings).evaluate_latest()
    finally:
        engine.dispose()
    _print_threshold_policy("threshold-policy-evaluate", policy)


@app.command("threshold-policy-latest")
def threshold_policy_latest() -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        policy = ThresholdPolicyService(engine, settings).latest()
    finally:
        engine.dispose()
    if policy is None:
        typer.echo("threshold-policy-latest: not found")
        raise typer.Exit(code=1)
    _print_threshold_policy("threshold-policy-latest", policy)


@app.command("threshold-policy-approve")
def threshold_policy_approve(
    policy_id: int = typer.Option(..., help="Threshold policy id to approve."),
    reviewer: str = typer.Option("human", help="Reviewer name or role."),
    rationale: str = typer.Option(..., help="Approval rationale."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        policy = ThresholdPolicyService(engine, settings).approve(
            policy_id,
            reviewer=reviewer,
            rationale=rationale,
        )
    finally:
        engine.dispose()
    _print_threshold_policy("threshold-policy-approve", policy)


@app.command("threshold-policy-apply")
def threshold_policy_apply(
    policy_id: int = typer.Option(..., help="Approved threshold policy id to apply."),
    reviewer: str = typer.Option("human", help="Reviewer name or role."),
    rationale: str = typer.Option(..., help="Apply rationale."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        policy = ThresholdPolicyService(engine, settings).apply(
            policy_id,
            reviewer=reviewer,
            rationale=rationale,
        )
    finally:
        engine.dispose()
    _print_threshold_policy("threshold-policy-apply", policy)


@app.command("threshold-policy-rollback")
def threshold_policy_rollback(
    policy_id: int = typer.Option(..., help="Applied threshold policy id to roll back."),
    reviewer: str = typer.Option("human", help="Reviewer name or role."),
    rationale: str = typer.Option(..., help="Rollback rationale."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    try:
        policy = ThresholdPolicyService(engine, settings).rollback(
            policy_id,
            reviewer=reviewer,
            rationale=rationale,
        )
    finally:
        engine.dispose()
    _print_threshold_policy("threshold-policy-rollback", policy)


def _print_threshold_policy(command_name: str, policy: dict[str, object]) -> None:
    typer.echo(f"{command_name}: started")
    typer.echo(f"id={policy.get('id')}")
    typer.echo(f"state={policy.get('state')}")
    typer.echo(f"decision={policy.get('decision')}")
    typer.echo(f"active={str(policy.get('active')).lower()}")
    typer.echo(f"sample_size={policy.get('sample_size')}")
    metrics = policy.get("metrics")
    if isinstance(metrics, dict):
        typer.echo(f"roi={metrics.get('roi')}")
    typer.echo(f"policy_values={json.dumps(policy.get('policy_values'), sort_keys=True)}")
    typer.echo(f"risk_flags={json.dumps(policy.get('risk_flags'), sort_keys=True)}")
    typer.echo(f"{command_name}: finished")


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
    snapshot: Path | None = WORKER_SNAPSHOT_OPTION,
    snapshot_url: str | None = SNAPSHOT_URL_OPTION,
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
            snapshot_url=snapshot_url,
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
    if summary.snapshot_path is not None:
        typer.echo(f"snapshot_path={summary.snapshot_path}")
        typer.echo(f"recommendations.created={summary.recommendation_items}")
        typer.echo(f"combinations.created={summary.combination_items}")
        if summary.result_summary is not None:
            _print_stage_summary("results", summary.result_summary)
        if summary.settlement_summary is not None:
            _print_stage_summary("settlement", summary.settlement_summary)
        typer.echo(f"ai_review_id={summary.ai_review_id}")
        typer.echo(f"threshold_review_id={summary.threshold_review_id}")
        typer.echo(f"threshold_policy_id={summary.threshold_policy_id}")
        typer.echo(f"journal_id={summary.journal_id}")
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
    path: Path | None = RESULT_PATH_OPTION,
    league: str | None = typer.Option(None, help="Live league name or provider sport."),
    season: str | None = typer.Option(None, help="Season label for result rows."),
    limit: int = typer.Option(50, help="Maximum Misli result jobs to process."),
    now: str | None = typer.Option(None, help="ISO timestamp used for due result jobs."),
    dry_run: bool | None = typer.Option(
        None,
        "--dry-run/--execute",
        help="Preview Misli result collection unless --execute is used.",
    ),
    fixture: str | None = typer.Option(
        None,
        help="JSON Misli result fixture for tests or dry local verification.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    if provider == "misli-public":
        effective_dry_run = settings.misli_result_preview_mode if dry_run is None else dry_run
        fetcher = (lambda: json.loads(fixture)) if fixture is not None else None
        summary = MisliResultService(engine, fetcher=fetcher).collect_due_results(
            now_iso=now,
            dry_run=effective_dry_run,
            limit=limit,
        )
        _print_summary("collect-results", summary)
        typer.echo(f"dry_run={str(effective_dry_run).lower()}")
        return
    if path is None:
        raise typer.BadParameter("--path is required for manual result collection")
    summary = LiveResultService(engine).collect_results(
        LiveResultRequest(
            provider=provider,
            path=path,
            league=league,
            season=season,
        )
    )
    _print_summary("collect-results", summary)


@app.command("generate-recommendations")
def generate_recommendations(
    stale_after_minutes: int = typer.Option(
        60,
        help="Minutes after which latest odds are considered stale.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = RecommendationService(engine, settings).generate(
        stale_after_minutes=stale_after_minutes
    )
    _print_summary("generate-recommendations", summary)


@app.command("generate-combinations")
def generate_combinations(
    max_legs: int = typer.Option(3, help="Maximum number of paper combination legs."),
    min_leg_confidence: float = typer.Option(
        0.6,
        help="Minimum confidence score required for each leg.",
    ),
    max_risk_flags: int = typer.Option(
        6,
        help="Maximum non-neutral risk flags allowed on a persisted research combination.",
    ),
    max_combinations: int = typer.Option(100, help="Maximum combinations to persist."),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = CombinationService(engine).generate(
        max_legs=max_legs,
        min_leg_confidence=min_leg_confidence,
        max_risk_flags=max_risk_flags,
        max_combinations=max_combinations,
    )
    _print_summary("generate-combinations", summary)


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


@app.command("void-unsafe-paper-bets")
def void_unsafe_paper_bets(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Preview unsafe open paper bets by default; use --execute to void them.",
    ),
) -> None:
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    summary = PaperBetMaintenanceService(engine).void_unsafe_open_bets(dry_run=dry_run)
    _print_summary("void-unsafe-paper-bets", summary)
    typer.echo(f"unsafe_count={summary.unsafe_count}")
    typer.echo(f"risk_flag_counts={json.dumps(summary.risk_flag_counts, sort_keys=True)}")
    typer.echo(f"dry_run={str(summary.dry_run).lower()}")


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
    typer.echo(f"database_url={_safe_database_url(settings.database_url)}")
    typer.echo(f"default_market={settings.default_market}")
    typer.echo(f"min_edge={settings.min_edge}")
    typer.echo(f"odds_range={settings.min_odds}-{settings.max_odds}")


if __name__ == "__main__":
    app()
