import json
from pathlib import Path

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, Match, PaperCombination, PaperRecommendation
from app.services.recommendation_backtest_service import (
    RecommendationBacktestRequest,
    RecommendationBacktestService,
)


def test_recommendation_backtest_reports_singles_and_combinations(tmp_path: Path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'backtest.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_backtest_dataset(engine)

    report = RecommendationBacktestService(engine).backtest(
        RecommendationBacktestRequest(report_name="pytest_recommendation_backtest")
    )

    assert report["metadata"]["report_type"] == "recommendation_backtest"
    assert report["singles"]["settled_bets"] == 3
    assert report["singles"]["wins"] == 2
    assert report["singles"]["losses"] == 1
    assert report["singles"]["roi"] == 0.3
    assert report["singles"]["max_drawdown_units"] == 1.0
    assert report["combinations"]["settled_bets"] == 1
    assert report["combinations"]["wins"] == 1
    assert report["combinations"]["roi"] == 2.8
    assert report["market_buckets"]["1X2"]["settled_bets"] == 3
    assert report["model_provider_splits"]["baseline_heuristic/Misli.az"]["settled_bets"] == 3


def test_recommendation_backtest_thresholds_change_selected_candidates(
    tmp_path: Path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'thresholds.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_backtest_dataset(engine)

    loose = RecommendationBacktestService(engine).backtest(
        RecommendationBacktestRequest(min_edge=0.0, min_confidence=0.0)
    )
    strict = RecommendationBacktestService(engine).backtest(
        RecommendationBacktestRequest(min_edge=0.1, min_confidence=0.7)
    )

    assert loose["singles"]["settled_bets"] == 3
    assert strict["singles"]["settled_bets"] == 2
    assert loose["threshold_sensitivity"][0]["settled_bets"] >= strict["singles"]["settled_bets"]
    assert strict["singles"]["roi"] > loose["singles"]["roi"]


def test_recommendation_backtest_exports_dashboard_consumable_report(
    tmp_path: Path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'export.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_backtest_dataset(engine)
    reports_dir = tmp_path / "reports"

    _csv_path, json_path, report = RecommendationBacktestService(engine).export(
        RecommendationBacktestRequest(report_name="pytest_rec_backtest"),
        reports_dir=reports_dir,
    )

    assert json_path == reports_dir / "pytest_rec_backtest_recommendation_backtest.json"
    comparison_path = reports_dir / "pytest_rec_backtest_comparison.json"
    stored = json.loads(json_path.read_text(encoding="utf-8"))
    dashboard_report = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert stored == report
    assert stored["dashboard_summary"]["name"] == "pytest_rec_backtest"
    assert stored["dashboard_summary"]["total_settled_bets"] == 4
    assert dashboard_report["metadata"]["report_type"] == "recommendation_backtest"
    assert dashboard_report["runs"][0]["model"] == "recommendation_singles"
    assert dashboard_report["runs"][1]["model"] == "recommendation_combinations"
    assert dashboard_report["recommendation_backtest"] == report


def _seed_backtest_dataset(engine) -> None:
    with session_scope(engine) as session:
        home_win = _match(session, "match-home", "HOME")
        away_win = _match(session, "match-away", "AWAY")
        draw = _match(session, "match-draw", "DRAW")
        first = _recommendation(session, home_win, "HOME", odds=2.0, edge=0.12, confidence=0.72)
        second = _recommendation(session, away_win, "AWAY", odds=1.9, edge=0.11, confidence=0.71)
        _recommendation(session, draw, "HOME", odds=2.1, edge=0.05, confidence=0.62)
        session.add(
            PaperCombination(
                leg_recommendation_ids_json=json.dumps([first.id, second.id]),
                leg_count=2,
                model_name="baseline_heuristic",
                model_version="v0",
                grade="recommended",
                status="active",
                rank=1,
                combined_odds=3.8,
                estimated_probability=0.36,
                combined_expected_value=0.368,
                confidence_score=0.715,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Seed combination",
            )
        )


def _match(session, source_match_id: str, result: str) -> Match:
    match = Match(
        source="misli_public",
        source_match_id=source_match_id,
        league="Sample Premier",
        home_team=f"{source_match_id} Home",
        away_team=f"{source_match_id} Away",
        kickoff_time="2026-05-19T20:30:00+04:00",
        status="completed",
        result=result,
    )
    session.add(match)
    session.flush()
    return match


def _recommendation(
    session,
    match: Match,
    selection: str,
    *,
    odds: float,
    edge: float,
    confidence: float,
) -> PaperRecommendation:
    recommendation = PaperRecommendation(
        match_id=match.id,
        source_match_id=match.source_match_id,
        bookmaker="Misli.az",
        market="1X2",
        selection=selection,
        latest_snapshot_time="2026-05-19T12:00:00+00:00",
        model_name="baseline_heuristic",
        model_version="v0",
        grade="recommended",
        status="active",
        model_probability=0.6,
        implied_probability=1 / odds,
        edge=edge,
        confidence_score=confidence,
        current_odds=odds,
        expected_value=(0.6 * odds) - 1,
        risk_flags_json='["no_current_risk_flags"]',
        rationale="Seed recommendation",
    )
    session.add(recommendation)
    session.flush()
    return recommendation
