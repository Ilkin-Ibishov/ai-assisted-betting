import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast, get_args

from fastapi import Body, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import load_settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, PaperCombination, PaperRecommendation
from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService
from app.services.bet_ledger_service import BetLedgerService, DateRange, LedgerStatus
from app.services.live_snapshot_service import LiveSnapshotService
from app.services.live_status_service import LiveStatusService
from app.services.odds_movement_service import OddsMovementService
from app.services.operational_guardrail_service import OperationalGuardrailService
from app.services.worker_monitoring_service import WorkerMonitoringService

SNAPSHOT_BODY = Body(...)
AUTHORIZATION_HEADER = Header(default=None)
BET_LEDGER_STATUSES = set(get_args(LedgerStatus))
BET_LEDGER_DATE_RANGES = set(get_args(DateRange))


def create_api(
    reports_dir: Path = Path("reports"),
    database_url: str | None = None,
) -> FastAPI:
    api = FastAPI(title="Paper Odds Lab API")
    settings = load_settings()
    live_database_url = database_url or settings.database_url
    live_status = LiveStatusService(live_database_url)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_origin_regex=settings.cors_allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @api.get("/api/health")
    def get_health() -> dict[str, Any]:
        return _health_payload(live_database_url)

    @api.get("/api/reports/comparisons")
    def list_comparisons(include_test_reports: bool = False) -> list[dict[str, Any]]:
        return [
            _comparison_summary(path)
            for path in sorted(reports_dir.glob("*_comparison.json"))
            if include_test_reports or not _is_test_report(path)
        ]

    @api.get("/api/reports/comparisons/{name}")
    def get_comparison(name: str) -> dict[str, Any]:
        report_path = _comparison_report_path(reports_dir, name)
        report = _load_comparison_report(report_path, name)
        analysis = _optional_analysis_payload(report_path, name)
        if isinstance(analysis, dict):
            report["analysis"] = analysis
        else:
            report["analysis_error"] = analysis
        return report

    @api.get("/api/reports/comparisons/{name}/analysis")
    def get_comparison_analysis(name: str) -> dict[str, Any]:
        report_path = _comparison_report_path(reports_dir, name)
        return _analysis_payload(report_path, name)

    @api.get("/api/live/status")
    def get_live_status() -> dict[str, Any]:
        return live_status.status()

    @api.get("/api/live/worker-status")
    def get_worker_status(
        fresh_after_minutes: int = 90,
        now: str | None = None,
    ) -> dict[str, Any]:
        return WorkerMonitoringService(live_database_url).status(
            fresh_after_minutes=fresh_after_minutes,
            now_iso=now,
        )

    @api.get("/api/operations/guardrails")
    def get_operational_guardrails(
        worker_fresh_after_minutes: int = 90,
        repeated_failure_threshold: int = 3,
        now: str | None = None,
    ) -> dict[str, Any]:
        return OperationalGuardrailService(live_database_url).status(
            worker_fresh_after_minutes=worker_fresh_after_minutes,
            repeated_failure_threshold=repeated_failure_threshold,
            now_iso=now,
        )

    @api.get("/api/live/runs")
    def list_live_runs(limit: int = 20) -> list[dict[str, Any]]:
        return live_status.recent_runs(limit=limit)

    @api.get("/api/live/runs/{run_id:path}")
    def get_live_run(run_id: str) -> dict[str, Any]:
        live_run = live_status.run(run_id)
        if live_run is None:
            raise HTTPException(status_code=404, detail=f"live run not found: {run_id}")
        return live_run

    @api.get("/api/live/odds-movement")
    def get_live_odds_movement(
        stale_after_minutes: int = 60,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        engine = create_engine_from_url(live_database_url)
        try:
            return OddsMovementService(engine).summaries(
                stale_after_minutes=stale_after_minutes,
                limit=limit,
            )
        finally:
            engine.dispose()

    @api.get("/api/live/recommendations")
    def list_live_recommendations(limit: int = 100) -> list[dict[str, Any]]:
        return _paper_recommendation_payloads(live_database_url, limit=limit)

    @api.get("/api/live/bet-ledger")
    def get_live_bet_ledger(
        status: str = "fresh",
        date_range: str = "next_7_days",
        from_date: str | None = None,
        to_date: str | None = None,
        include_voided: bool = False,
        limit: int = 500,
        now: str | None = None,
    ) -> dict[str, Any]:
        ledger_status = _validate_bet_ledger_status(status)
        ledger_date_range = _validate_bet_ledger_date_range(date_range)
        reference_time = _parse_optional_query_datetime(now, parameter="now")
        return BetLedgerService(live_database_url).ledger(
            status=ledger_status,
            date_range=ledger_date_range,
            from_date=from_date,
            to_date=to_date,
            include_voided=include_voided,
            limit=limit,
            now=reference_time,
        )

    @api.get("/api/live/combinations")
    def list_live_combinations(limit: int = 100) -> list[dict[str, Any]]:
        return _paper_combination_payloads(live_database_url, limit=limit)

    @api.post("/api/live/snapshots/latest/{provider}")
    def post_live_snapshot(
        provider: str,
        payload: dict[str, Any] = SNAPSHOT_BODY,
        authorization: str | None = AUTHORIZATION_HEADER,
    ) -> dict[str, Any]:
        _require_snapshot_ingest_token(
            configured_token=settings.snapshot_ingest_token,
            authorization=authorization,
        )
        engine = create_engine_from_url(live_database_url)
        try:
            snapshot = LiveSnapshotService(engine).store_latest(
                provider=provider,
                payload=payload,
            )
            return {
                "id": snapshot.id,
                "provider": snapshot.provider,
                "snapshot_hash": snapshot.snapshot_hash,
                "event_count": snapshot.event_count,
                "created_at": snapshot.created_at,
            }
        finally:
            engine.dispose()

    @api.get("/api/live/snapshots/latest/{provider}")
    def get_live_snapshot(provider: str) -> Response:
        engine = create_engine_from_url(live_database_url)
        try:
            payload = LiveSnapshotService(engine).latest_payload(provider)
        finally:
            engine.dispose()
        if payload is None:
            raise HTTPException(status_code=404, detail=f"live snapshot not found: {provider}")
        return Response(
            content=json.dumps(payload, indent=2, sort_keys=True) + "\n",
            media_type="application/json",
        )

    @api.get("/api/ai/analysis/latest")
    def get_latest_ai_analysis() -> dict[str, Any]:
        analysis = _latest_ai_analysis_payload(live_database_url)
        if analysis is None:
            raise HTTPException(status_code=404, detail="AI analysis run not found")
        return analysis

    @api.get("/api/ai/recommendation-review/latest")
    def get_latest_ai_recommendation_review() -> dict[str, Any]:
        analysis = _latest_ai_analysis_payload(
            live_database_url,
            analysis_type="recommendation_review",
        )
        if analysis is None:
            raise HTTPException(status_code=404, detail="AI recommendation review not found")
        return analysis

    @api.get("/api/ai/analysis/runs")
    def list_ai_analysis_runs(limit: int = 20) -> list[dict[str, Any]]:
        return _ai_analysis_run_payloads(live_database_url, limit=limit)

    @api.get("/api/ai/analysis/runs/{analysis_id}")
    def get_ai_analysis_run(analysis_id: int) -> dict[str, Any]:
        analysis = _ai_analysis_run_payload(live_database_url, analysis_id)
        if analysis is None:
            raise HTTPException(
                status_code=404,
                detail=f"AI analysis run not found: {analysis_id}",
            )
        return analysis

    return api


api = create_api()


def _comparison_summary(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    metadata = report.get("metadata", {})
    runs = report.get("runs", [])
    rankings = report.get("rankings", {})
    sample_size = _sample_size(runs)
    return {
        "name": _comparison_name_from_path(path),
        "filename": path.name,
        "league": metadata.get("league"),
        "season": metadata.get("season"),
        "models": metadata.get("models", []),
        "bookmakers": metadata.get("bookmakers", []),
        "runs": len(runs),
        "modified_at": _report_timestamp(path, metadata),
        "total_settled_bets": _sum_run_metric(runs, "settled_bets"),
        "best_roi": _ranking_value(rankings, "best_roi", runs, "roi", higher_is_better=True),
        "best_brier_score": _ranking_value(
            rankings,
            "best_brier_score",
            runs,
            "brier_score",
            higher_is_better=False,
        ),
        "best_log_loss": _ranking_value(
            rankings,
            "best_log_loss",
            runs,
            "log_loss",
            higher_is_better=False,
        ),
        "sample_size_smallest": sample_size[0],
        "sample_size_largest": sample_size[1],
    }


def _health_payload(database_url: str) -> dict[str, Any]:
    engine = create_engine_from_url(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    finally:
        engine.dispose()


def _require_snapshot_ingest_token(
    *,
    configured_token: str,
    authorization: str | None,
) -> None:
    if not configured_token:
        raise HTTPException(status_code=403, detail="snapshot ingest is not configured")
    expected = f"Bearer {configured_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid snapshot ingest token")


def _comparison_report_path(reports_dir: Path, name: str) -> Path:
    return reports_dir / f"{name}_comparison.json"


def _comparison_name_from_path(path: Path) -> str:
    return path.name.removesuffix("_comparison.json")


def _is_test_report(path: Path) -> bool:
    return _comparison_name_from_path(path).startswith("pytest_")


def _report_timestamp(path: Path, metadata: Any) -> str:
    if isinstance(metadata, dict) and isinstance(metadata.get("generated_at"), str):
        generated_at = metadata["generated_at"]
        try:
            datetime.fromisoformat(generated_at)
        except ValueError:
            pass
        else:
            return generated_at

    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def _load_comparison_report(path: Path, name: str) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"comparison report not found: {name}")
    return _read_json(path)


def _read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def _analysis_payload(path: Path, name: str) -> dict[str, Any]:
    try:
        return ComparisonAnalysisService().analyze_comparison_data(path)
    except ComparisonAnalysisError as exc:
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"comparison report not found: {name}",
            ) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _optional_analysis_payload(path: Path, name: str) -> dict[str, Any] | str:
    try:
        return _analysis_payload(path, name)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise
        return str(exc.detail)


def _sum_run_metric(runs: Any, metric: str) -> int:
    if not isinstance(runs, list):
        return 0
    return sum(int(run.get(metric, 0)) for run in runs if isinstance(run, dict))


def _sample_size(runs: Any) -> tuple[int | None, int | None]:
    if not isinstance(runs, list):
        return None, None
    settled_counts = [
        int(run["settled_bets"])
        for run in runs
        if isinstance(run, dict) and isinstance(run.get("settled_bets"), int | float)
    ]
    if not settled_counts:
        return None, None
    return min(settled_counts), max(settled_counts)


def _ranking_value(
    rankings: Any,
    ranking_key: str,
    runs: Any,
    metric: str,
    *,
    higher_is_better: bool,
) -> float | None:
    if isinstance(rankings, dict):
        ranking = rankings.get(ranking_key)
        if isinstance(ranking, dict) and isinstance(ranking.get("value"), int | float):
            return float(ranking["value"])

    if not isinstance(runs, list):
        return None
    values = [
        float(run[metric])
        for run in runs
        if isinstance(run, dict) and isinstance(run.get(metric), int | float)
    ]
    if not values:
        return None
    return max(values) if higher_is_better else min(values)


def _latest_ai_analysis_payload(
    database_url: str,
    *,
    analysis_type: str | None = None,
) -> dict[str, Any] | None:
    engine = create_engine_from_url(database_url)
    try:
        with session_scope(engine) as session:
            query = select(AIAnalysisRun)
            if analysis_type is not None:
                query = query.where(AIAnalysisRun.analysis_type == analysis_type)
            analysis = session.scalar(
                query
                .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
                .limit(1)
            )
            return _ai_analysis_payload(analysis)
    finally:
        engine.dispose()


def _ai_analysis_run_payloads(database_url: str, *, limit: int) -> list[dict[str, Any]]:
    engine = create_engine_from_url(database_url)
    try:
        with session_scope(engine) as session:
            analyses = session.scalars(
                select(AIAnalysisRun)
                .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
                .limit(max(1, min(limit, 100)))
            ).all()
            return [payload for analysis in analyses if (payload := _ai_analysis_payload(analysis))]
    finally:
        engine.dispose()


def _ai_analysis_run_payload(database_url: str, analysis_id: int) -> dict[str, Any] | None:
    engine = create_engine_from_url(database_url)
    try:
        with session_scope(engine) as session:
            return _ai_analysis_payload(session.get(AIAnalysisRun, analysis_id))
    finally:
        engine.dispose()


def _ai_analysis_payload(analysis: AIAnalysisRun | None) -> dict[str, Any] | None:
    if analysis is None:
        return None
    return {
        "id": analysis.id,
        "analysis_type": analysis.analysis_type,
        "source_type": analysis.source_type,
        "source_id": analysis.source_id,
        "input": json.loads(analysis.input_json),
        "output": json.loads(analysis.output_json),
        "model_name": analysis.model_name,
        "prompt_version": analysis.prompt_version,
        "status": analysis.status,
        "error_summary": analysis.error_summary,
        "created_at": analysis.created_at,
    }


def _paper_recommendation_payloads(database_url: str, *, limit: int) -> list[dict[str, Any]]:
    engine = create_engine_from_url(database_url)
    try:
        with session_scope(engine) as session:
            recommendations = session.scalars(
                select(PaperRecommendation)
                .order_by(PaperRecommendation.created_at.desc(), PaperRecommendation.id.desc())
                .limit(max(1, min(limit, 500)))
            ).all()
            return [_paper_recommendation_payload(item) for item in recommendations]
    finally:
        engine.dispose()


def _paper_recommendation_payload(recommendation: PaperRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "match_id": recommendation.match_id,
        "prediction_id": recommendation.prediction_id,
        "source_run_id": recommendation.source_run_id,
        "source_match_id": recommendation.source_match_id,
        "bookmaker": recommendation.bookmaker,
        "market": recommendation.market,
        "selection": recommendation.selection,
        "latest_snapshot_time": recommendation.latest_snapshot_time,
        "model_name": recommendation.model_name,
        "model_version": recommendation.model_version,
        "grade": recommendation.grade,
        "status": recommendation.status,
        "model_probability": recommendation.model_probability,
        "implied_probability": recommendation.implied_probability,
        "edge": recommendation.edge,
        "confidence_score": recommendation.confidence_score,
        "current_odds": recommendation.current_odds,
        "expected_value": recommendation.expected_value,
        "risk_flags": json.loads(recommendation.risk_flags_json),
        "rationale": recommendation.rationale,
        "created_at": recommendation.created_at,
    }


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_optional_query_datetime(value: str | None, *, parameter: str) -> datetime | None:
    if value is None:
        return None
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {parameter}: expected ISO 8601 datetime",
        )
    return parsed


def _validate_bet_ledger_status(value: str) -> LedgerStatus:
    if value not in BET_LEDGER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status: expected one of {sorted(BET_LEDGER_STATUSES)}",
        )
    return cast(LedgerStatus, value)


def _validate_bet_ledger_date_range(value: str) -> DateRange:
    if value not in BET_LEDGER_DATE_RANGES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date_range: expected one of {sorted(BET_LEDGER_DATE_RANGES)}",
        )
    return cast(DateRange, value)


def _paper_combination_payloads(database_url: str, *, limit: int) -> list[dict[str, Any]]:
    engine = create_engine_from_url(database_url)
    try:
        with session_scope(engine) as session:
            combinations = session.scalars(
                select(PaperCombination)
                .order_by(PaperCombination.rank.asc(), PaperCombination.id.asc())
                .limit(max(1, min(limit, 500)))
            ).all()
            return [_paper_combination_payload(item) for item in combinations]
    finally:
        engine.dispose()


def _paper_combination_payload(combination: PaperCombination) -> dict[str, Any]:
    return {
        "id": combination.id,
        "leg_recommendation_ids": json.loads(combination.leg_recommendation_ids_json),
        "leg_count": combination.leg_count,
        "model_name": combination.model_name,
        "model_version": combination.model_version,
        "grade": combination.grade,
        "status": combination.status,
        "rank": combination.rank,
        "combined_odds": combination.combined_odds,
        "estimated_probability": combination.estimated_probability,
        "combined_expected_value": combination.combined_expected_value,
        "confidence_score": combination.confidence_score,
        "risk_flags": json.loads(combination.risk_flags_json),
        "rationale": combination.rationale,
        "created_at": combination.created_at,
    }
