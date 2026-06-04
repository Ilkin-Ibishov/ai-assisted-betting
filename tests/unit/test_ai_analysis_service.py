import json
from pathlib import Path

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.migrations import init_db
from app.db.models import AIAnalysisRun, PaperCombination, PaperRecommendation, Prediction
from app.db.repositories import LiveRunRepository
from app.services.ai_analysis_service import AIAnalysisProvider, AIAnalysisService
from app.services.ai_prompt_registry import LiveStatusPrompt, RecommendationReviewPrompt


def test_ai_analysis_service_records_deterministic_live_status_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine).analyze_live_status()

    assert analysis.analysis_type == "live_status_summary"
    assert analysis.source_type == "live_status"
    assert analysis.model_name == "deterministic_ai_fallback"
    assert analysis.prompt_version == "ai-live-status-v1"
    assert analysis.status == "completed"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "kickoff date" in output["root_cause"].lower()
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    assert output["source_record_ids"] == ["failed-run"]

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert stored.id == analysis.id
    assert "failed-run" in stored.input_json
    engine.dispose()


def test_ai_analysis_service_records_empty_live_status_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'empty-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_live_status()

    output = json.loads(analysis.output_json)
    assert output["short_summary"] == "No live paper runs have been recorded yet."
    assert output["risk_flags"] == ["no_live_runs"]
    assert output["recommended_next_actions"] == [
        "Run the deterministic live paper dry-run before enabling scheduling."
    ]
    engine.dispose()


def test_ai_analysis_service_uses_injected_provider_metadata(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'provider-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine, provider=RecordingProvider()).analyze_live_status()

    assert analysis.model_name == "custom_provider_model"
    assert analysis.prompt_version == "custom-live-status-v2"
    output = json.loads(analysis.output_json)
    assert output["short_summary"] == "Custom provider summary."
    assert output["source_record_ids"] == ["failed-run"]
    engine.dispose()


def test_ai_analysis_service_fails_closed_on_provider_eval_failure(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'unsafe-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_failed_misli_run(engine)

    analysis = AIAnalysisService(engine, provider=UnsafeProvider()).analyze_live_status()

    assert analysis.status == "failed"
    assert analysis.error_summary is not None
    assert "unsafe_real_money_language" in analysis.error_summary
    output = json.loads(analysis.output_json)
    assert output["risk_flags"] == ["ai_eval_failed"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    engine.dispose()


def test_ai_analysis_service_records_comparison_report_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'comparison-ai.sqlite').as_posix()}"
    init_db(database_url)
    report_path = tmp_path / "e0_compare_comparison.json"
    _write_comparison_report(report_path)
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_comparison_report(report_path)

    assert analysis.analysis_type == "model_comparison_summary"
    assert analysis.source_type == "comparison_report"
    assert analysis.source_id == "e0_compare"
    assert analysis.model_name == "deterministic_ai_fallback"
    assert analysis.prompt_version == "ai-comparison-report-v1"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "calibration" in output["root_cause"].lower()
    assert "small_sample_size" in output["risk_flags"]
    assert output["source_record_ids"] == ["e0_compare"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert stored.analysis_type == "model_comparison_summary"
    assert "baseline_heuristic" in stored.input_json
    engine.dispose()


def test_ai_analysis_service_records_provider_health_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'provider-health-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_provider_health_runs(engine)

    analysis = AIAnalysisService(engine).analyze_provider_health("misli_public")

    assert analysis.analysis_type == "provider_health_summary"
    assert analysis.source_type == "live_provider"
    assert analysis.source_id == "misli_public"
    assert analysis.prompt_version == "ai-provider-health-v1"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert "Misli" in output["short_summary"]
    assert "provider_datetime_missing" in output["risk_flags"]
    assert output["source_record_ids"] == ["failed-provider-run", "completed-provider-run"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert "failed_runs_count" in stored.input_json
    engine.dispose()


def test_provider_health_flags_parser_drift_stale_snapshot_and_low_confidence(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'provider-health-drift.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="drift-run",
            run_type="collect_matches",
            provider="misli_public",
        )
        repository.fail(
            run_id="drift-run",
            errors_count=3,
            error_summary=(
                "Misli snapshot contains no events; possible Misli parser drift\n"
                "Misli snapshot is stale\n"
                "Misli extraction confidence is low"
            ),
            items_read=0,
            items_skipped=0,
        )

    analysis = AIAnalysisService(engine).analyze_provider_health("misli_public")

    output = json.loads(analysis.output_json)
    assert "provider_parser_drift" in output["risk_flags"]
    assert "provider_stale_snapshot" in output["risk_flags"]
    assert "provider_low_extraction_confidence" in output["risk_flags"]
    assert "Review Misli public selectors" in output["recommended_next_actions"][0]
    engine.dispose()


def test_ai_analysis_service_records_recommendation_review_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'recommendation-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_recommendation_review_inputs(engine)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    assert analysis.analysis_type == "recommendation_review"
    assert analysis.source_type == "paper_recommendations"
    assert analysis.source_id == "latest"
    assert analysis.prompt_version == "ai-recommendation-review-v1"
    assert analysis.status == "completed"
    output = json.loads(analysis.output_json)
    assert output["label"] == "AI-assisted advisory analysis"
    assert output["approval_state"] == "caution"
    assert "combination_correlation_heuristic" in output["risk_flags"]
    assert "combination_quarantined" in output["risk_flags"]
    assert output["combination_quality"]["experimental_count"] == 1
    assert output["combination_quality"]["quarantined_count"] == 1
    assert "combination" in output["short_summary"].lower()
    assert output["concerns"]
    assert output["confidence_explanation"]
    assert output["rejected_assumptions"]
    assert output["next_checks"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    assert "paper_recommendation:1" in output["source_record_ids"]
    assert "paper_combination:1" in output["source_record_ids"]

    with session_scope(engine) as session:
        stored = session.scalar(select(AIAnalysisRun))

    assert stored is not None
    assert "paper_combinations" in stored.input_json
    engine.dispose()


def test_ai_analysis_service_explains_cold_start_watchlist_without_actionable_rows(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'cold-start-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_low_confidence_watchlist_review_inputs(engine)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    output = json.loads(analysis.output_json)
    assert output["approval_state"] == "reject"
    assert "cold_start_confidence_ceiling" in output["risk_flags"]
    assert output["model_quality"]["watchlist_count"] == 2
    assert output["model_quality"]["actionable_count"] == 0
    assert output["model_quality"]["max_confidence_score"] == 0.133333
    assert "Calibrate baseline confidence" in output["recommended_next_actions"][0]
    engine.dispose()


def test_ai_analysis_service_flags_calibrated_actionable_confidence(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'calibrated-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_calibrated_recommendation_review_inputs(engine)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    input_payload = json.loads(analysis.input_json)
    output = json.loads(analysis.output_json)
    reviewed = input_payload["paper_recommendations"][0]
    assert reviewed["model_confidence_score"] == 0.133333
    assert reviewed["recommendation_confidence_score"] == 0.52
    assert reviewed["confidence_adjustment_reason"] == "high_ev_confidence_calibration"
    assert output["model_quality"]["confidence_adjusted_count"] == 1
    assert "confidence_calibrated_recommendations" in output["risk_flags"]
    assert any("calibrated" in concern.lower() for concern in output["concerns"])
    engine.dispose()


def test_ai_analysis_service_reviews_fresh_recommendations_before_refreshed_stale_rows(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'fresh-recommendation-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_mixed_freshness_recommendation_review_inputs(engine)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    input_payload = json.loads(analysis.input_json)
    assert [
        item["source_match_id"] for item in input_payload["paper_recommendations"]
    ] == ["fresh-match", "stale-match"]
    engine.dispose()


def test_ai_analysis_service_rejects_recommendation_review_without_inputs(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'empty-recommendation-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    assert analysis.status == "failed"
    assert analysis.error_summary == "recommendation_inputs_missing"
    output = json.loads(analysis.output_json)
    assert output["approval_state"] == "reject"
    assert output["risk_flags"] == ["recommendation_inputs_missing"]
    assert output["source_record_ids"] == []
    engine.dispose()


def test_ai_analysis_service_fails_closed_on_unsafe_recommendation_review_output(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'unsafe-recommendation-review.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_recommendation_review_inputs(engine)

    analysis = AIAnalysisService(
        engine,
        provider=UnsafeRecommendationReviewProvider(),
    ).analyze_recommendation_review()

    assert analysis.status == "failed"
    assert analysis.error_summary is not None
    assert "unsafe_real_money_language" in analysis.error_summary
    output = json.loads(analysis.output_json)
    assert output["risk_flags"] == ["ai_eval_failed"]
    assert output["approval_state"] == "reject"
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    engine.dispose()


def test_ai_analysis_service_records_recommendation_backtest_advisory(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'backtest-ai.sqlite').as_posix()}"
    init_db(database_url)
    report_path = tmp_path / "pytest_rec_recommendation_backtest.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "report_type": "recommendation_backtest",
                    "report_name": "pytest_rec",
                },
                "singles": {
                    "settled_bets": 20,
                    "roi": -0.1,
                    "hit_rate": 0.4,
                    "max_drawdown_units": 4.0,
                },
                "combinations": {
                    "settled_bets": 5,
                    "roi": -0.4,
                    "hit_rate": 0.2,
                    "max_drawdown_units": 3.0,
                },
                "threshold_sensitivity": [
                    {"min_edge": 0.0, "min_confidence": 0.0, "settled_bets": 20, "roi": -0.1},
                    {"min_edge": 0.1, "min_confidence": 0.7, "settled_bets": 8, "roi": 0.05},
                ],
            }
        ),
        encoding="utf-8",
    )
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_recommendation_backtest_report(report_path)

    assert analysis.analysis_type == "recommendation_backtest_summary"
    assert analysis.source_type == "recommendation_backtest_report"
    assert analysis.source_id == "pytest_rec"
    output = json.loads(analysis.output_json)
    assert "negative_singles_roi" in output["risk_flags"]
    assert "combination_underperformance" in output["risk_flags"]
    assert output["source_record_ids"] == ["pytest_rec"]
    assert "real-money" not in " ".join(output["recommended_next_actions"]).lower()
    engine.dispose()


def test_ai_analysis_service_flags_odds_only_actionable_recommendations(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'feature-provenance-ai.sqlite').as_posix()}"
    init_db(database_url)
    engine = create_engine_from_url(database_url)
    _seed_feature_provenance_recommendation_review_inputs(engine)

    analysis = AIAnalysisService(engine).analyze_recommendation_review()

    output = json.loads(analysis.output_json)
    assert "odds_only_actionable_recommendations" in output["risk_flags"]
    assert output["model_quality"]["odds_only_actionable_count"] == 1
    assert output["model_quality"]["enriched_actionable_count"] == 1
    reviewed = json.loads(analysis.input_json)["paper_recommendations"]
    assert {item["feature_tier"] for item in reviewed} == {"cold_start", "full_enriched"}
    engine.dispose()


def test_ai_analysis_service_answers_whether_confidence_calibration_should_remain_enabled(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'calibration-backtest-ai.sqlite').as_posix()}"
    init_db(database_url)
    report_path = tmp_path / "pytest_calibration_recommendation_backtest.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "report_type": "recommendation_backtest",
                    "report_name": "pytest_calibration",
                },
                "singles": {"settled_bets": 120, "roi": 0.01},
                "combinations": {"settled_bets": 10, "roi": -0.2},
                "threshold_sensitivity": [],
                "calibration_scenarios": [
                    {
                        "name": "raw_confidence_ev_0_10_conf_0_50_odds_cap_6_00",
                        "confidence_mode": "raw_model",
                        "settled_bets": 40,
                        "roi": -0.05,
                        "hit_rate": 0.35,
                        "brier_score": 0.29,
                        "log_loss": 0.82,
                        "max_drawdown_units": 7.0,
                    },
                    {
                        "name": "calibrated_confidence_ev_0_10_conf_0_50_odds_cap_6_00",
                        "confidence_mode": "calibrated_recommendation",
                        "settled_bets": 45,
                        "roi": 0.08,
                        "hit_rate": 0.42,
                        "brier_score": 0.25,
                        "log_loss": 0.72,
                        "max_drawdown_units": 5.0,
                    },
                ],
                "calibration_comparison": {
                    "raw_scenario": "raw_confidence_ev_0_10_conf_0_50_odds_cap_6_00",
                    "calibrated_scenario": (
                        "calibrated_confidence_ev_0_10_conf_0_50_odds_cap_6_00"
                    ),
                    "candidate_delta": 5,
                    "roi_delta": 0.13,
                    "hit_rate_delta": 0.07,
                    "brier_score_delta": -0.04,
                    "log_loss_delta": -0.1,
                    "max_drawdown_delta": -2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    engine = create_engine_from_url(database_url)

    analysis = AIAnalysisService(engine).analyze_recommendation_backtest_report(report_path)

    output = json.loads(analysis.output_json)
    assert output["calibration_decision"] == "keep_enabled_provisionally"
    assert "confidence_calibration_supported" in output["risk_flags"]
    assert "small_calibration_sample" in output["risk_flags"]
    assert any("calibration" in action.lower() for action in output["recommended_next_actions"])
    engine.dispose()


def _seed_failed_misli_run(engine) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="failed-run",
            run_type="collect_odds",
            provider="misli_public",
            league="football",
            season="task48",
        )
        repository.fail(
            run_id="failed-run",
            errors_count=3,
            error_summary="Misli event requires a full kickoff date and time",
            items_read=3,
            items_skipped=3,
        )


def _seed_provider_health_runs(engine) -> None:
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="completed-provider-run",
            run_type="collect_matches",
            provider="misli_public",
            league="football",
            season="task49",
        )
        repository.complete(
            run_id="completed-provider-run",
            items_read=21,
            items_created=20,
            items_skipped=1,
        )
        repository.start(
            run_id="failed-provider-run",
            run_type="collect_odds",
            provider="misli_public",
            league="football",
            season="task49",
        )
        repository.fail(
            run_id="failed-provider-run",
            errors_count=1,
            error_summary="Misli event requires a full kickoff date and time",
            items_read=21,
            items_created=60,
            items_skipped=1,
        )


def _write_comparison_report(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.12,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.24,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.68,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "settled_bets": 60,
                        "total_bets": 60,
                        "roi": 0.12,
                        "profit_loss_units": 7.2,
                        "brier_score": 0.25,
                        "log_loss": 0.7,
                        "model_config": {"model_name": "baseline_heuristic"},
                    },
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "settled_bets": 62,
                        "total_bets": 62,
                        "roi": 0.02,
                        "profit_loss_units": 1.37,
                        "brier_score": 0.24,
                        "log_loss": 0.68,
                        "model_config": {"model_name": "elo"},
                    },
                ],
            }
        ),
        encoding="utf-8",
        )


def _seed_recommendation_review_inputs(engine) -> None:
    with session_scope(engine) as session:
        match_one = _seed_match(session, source_match_id="match-1")
        match_two = _seed_match(session, source_match_id="match-2")
        first = PaperRecommendation(
            match_id=match_one.id,
            source_match_id=match_one.source_match_id,
            bookmaker="Misli.az",
            market="1X2",
            selection="HOME",
            latest_snapshot_time="2026-05-19T12:00:00+00:00",
            model_name="baseline_heuristic",
            model_version="v0",
            grade="recommended",
            status="active",
            model_probability=0.62,
            implied_probability=0.5,
            edge=0.12,
            confidence_score=0.72,
            current_odds=2.0,
            expected_value=0.24,
            risk_flags_json='["no_current_risk_flags"]',
            rationale="Positive edge is above recommendation threshold.",
        )
        second = PaperRecommendation(
            match_id=match_two.id,
            source_match_id=match_two.source_match_id,
            bookmaker="Misli.az",
            market="1X2",
            selection="AWAY",
            latest_snapshot_time="2026-05-19T12:00:00+00:00",
            model_name="baseline_heuristic",
            model_version="v0",
            grade="lean",
            status="active",
            model_probability=0.58,
            implied_probability=0.5,
            edge=0.08,
            confidence_score=0.66,
            current_odds=1.9,
            expected_value=0.102,
            risk_flags_json='["no_current_risk_flags"]',
            rationale="Positive edge is above minimum threshold.",
        )
        session.add_all([first, second])
        session.flush()
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
                confidence_score=0.69,
                risk_flags_json='["experimental_combination"]',
                rationale="Recommended paper combination with 2 legs.",
            )
        )


def _seed_mixed_freshness_recommendation_review_inputs(engine) -> None:
    with session_scope(engine) as session:
        fresh_match = _seed_match(session, source_match_id="fresh-match")
        stale_match = _seed_match(session, source_match_id="stale-match")
        session.add_all(
            [
                PaperRecommendation(
                    match_id=fresh_match.id,
                    source_match_id=fresh_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-02T17:02:32+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="watch",
                    status="active",
                    model_probability=0.58,
                    implied_probability=0.5,
                    edge=0.08,
                    confidence_score=0.42,
                    current_odds=2.0,
                    expected_value=0.16,
                    risk_flags_json='["low_confidence"]',
                    rationale="Positive edge exists, but confidence is low.",
                    created_at="2026-06-02T17:02:33+00:00",
                ),
                PaperRecommendation(
                    match_id=stale_match.id,
                    source_match_id=stale_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-05-31T19:02:16+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="reject",
                    status="rejected",
                    model_probability=0.62,
                    implied_probability=0.5,
                    edge=0.12,
                    confidence_score=0.72,
                    current_odds=2.0,
                    expected_value=0.24,
                    risk_flags_json='["stale_odds"]',
                    rationale="Rejected because live odds/provider state is not healthy enough.",
                    created_at="2026-06-02T17:05:00+00:00",
                ),
            ]
        )


def _seed_low_confidence_watchlist_review_inputs(engine) -> None:
    with session_scope(engine) as session:
        first_match = _seed_match(session, source_match_id="watch-match-1")
        second_match = _seed_match(session, source_match_id="watch-match-2")
        rejected_match = _seed_match(session, source_match_id="reject-match")
        session.add_all(
            [
                PaperRecommendation(
                    match_id=first_match.id,
                    source_match_id=first_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-03T05:30:50+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="watch",
                    status="active",
                    model_probability=0.45507,
                    implied_probability=0.438596,
                    edge=0.02,
                    confidence_score=0.133333,
                    current_odds=2.28,
                    expected_value=0.03756,
                    risk_flags_json='["low_confidence"]',
                    rationale="Positive edge exists, but confidence is low.",
                ),
                PaperRecommendation(
                    match_id=second_match.id,
                    source_match_id=second_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-03T05:30:50+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="watch",
                    status="active",
                    model_probability=0.294899,
                    implied_probability=0.215517,
                    edge=0.02,
                    confidence_score=0.133333,
                    current_odds=4.64,
                    expected_value=0.276334,
                    risk_flags_json='["low_confidence"]',
                    rationale="Positive edge exists, but confidence is low.",
                ),
                PaperRecommendation(
                    match_id=rejected_match.id,
                    source_match_id=rejected_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="AWAY",
                    latest_snapshot_time="2026-06-03T05:30:50+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="reject",
                    status="rejected",
                    model_probability=0.3,
                    implied_probability=0.35,
                    edge=-0.02,
                    confidence_score=0.133333,
                    current_odds=2.8,
                    expected_value=-0.16,
                    risk_flags_json=(
                        '["edge_below_threshold", "negative_expected_value", "low_confidence"]'
                    ),
                    rationale="Rejected because edge is below threshold.",
                ),
            ]
        )


def _seed_calibrated_recommendation_review_inputs(engine) -> None:
    with session_scope(engine) as session:
        match = _seed_match(session, source_match_id="calibrated-match")
        session.add(
            PaperRecommendation(
                match_id=match.id,
                source_match_id=match.source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection="HOME",
                latest_snapshot_time="2026-06-03T05:30:50+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade="lean",
                status="active",
                model_probability=0.294899,
                implied_probability=0.215517,
                edge=0.08,
                confidence_score=0.52,
                model_confidence_score=0.133333,
                recommendation_confidence_score=0.52,
                confidence_adjustment_reason="high_ev_confidence_calibration",
                current_odds=4.64,
                expected_value=0.276334,
                risk_flags_json='["no_current_risk_flags"]',
                rationale="Positive edge is above minimum threshold with calibrated confidence.",
            )
        )


def _seed_feature_provenance_recommendation_review_inputs(engine) -> None:
    with session_scope(engine) as session:
        cold_match = _seed_match(session, source_match_id="cold-feature-match")
        enriched_match = _seed_match(session, source_match_id="enriched-feature-match")
        cold_prediction = Prediction(
            match_id=cold_match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.62,
            bookmaker_probability=0.5,
            edge=0.12,
            confidence_score=0.72,
            decision="SKIP",
            reason=(
                "baseline heuristic probability generated; feature_tier=cold_start; "
                "feature_provenance=market_overround_normalized,cold_start_history"
            ),
        )
        enriched_prediction = Prediction(
            match_id=enriched_match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.64,
            bookmaker_probability=0.5,
            edge=0.14,
            confidence_score=0.8,
            decision="SKIP",
            reason=(
                "baseline heuristic probability generated with enriched feature signal; "
                "feature_tier=full_enriched; "
                "feature_provenance=market_overround_normalized,recent_form,rest_days"
            ),
        )
        session.add_all([cold_prediction, enriched_prediction])
        session.flush()
        session.add_all(
            [
                PaperRecommendation(
                    match_id=cold_match.id,
                    prediction_id=cold_prediction.id,
                    source_match_id=cold_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-04T09:00:00+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="recommended",
                    status="active",
                    model_probability=0.62,
                    implied_probability=0.5,
                    edge=0.12,
                    confidence_score=0.72,
                    current_odds=2.0,
                    expected_value=0.24,
                    risk_flags_json='["no_current_risk_flags"]',
                    rationale="Positive edge is above recommendation threshold.",
                ),
                PaperRecommendation(
                    match_id=enriched_match.id,
                    prediction_id=enriched_prediction.id,
                    source_match_id=enriched_match.source_match_id,
                    bookmaker="Misli.az",
                    market="1X2",
                    selection="HOME",
                    latest_snapshot_time="2026-06-04T09:00:00+00:00",
                    model_name="baseline_heuristic",
                    model_version="v0",
                    grade="recommended",
                    status="active",
                    model_probability=0.64,
                    implied_probability=0.5,
                    edge=0.14,
                    confidence_score=0.8,
                    current_odds=2.0,
                    expected_value=0.28,
                    risk_flags_json='["no_current_risk_flags"]',
                    rationale="Positive edge is above recommendation threshold.",
                ),
            ]
        )


def _seed_match(session, *, source_match_id: str):
    from app.db.repositories import MatchRepository

    return MatchRepository(session).add(
        source="misli_public",
        source_match_id=source_match_id,
        league="Sample Premier",
        home_team=f"{source_match_id} Home",
        away_team=f"{source_match_id} Away",
        kickoff_time="2026-05-19T20:30:00+04:00",
    )


class RecordingProvider(AIAnalysisProvider):
    model_name = "custom_provider_model"

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict:
        assert prompt.version == "ai-live-status-v1"
        return {
            "prompt_version": "custom-live-status-v2",
            "output": {
                "label": "AI-assisted advisory analysis",
                "short_summary": "Custom provider summary.",
                "root_cause": "Custom provider saw a failed run.",
                "risk_flags": ["live_run_failure"],
                "recommended_next_actions": ["Keep analysis paper-only."],
                "confidence": "medium",
                "source_record_ids": ["failed-run"],
            },
        }

    def analyze_recommendation_review(self, prompt: RecommendationReviewPrompt) -> dict:
        return {
            "prompt_version": prompt.version,
            "output": {
                "label": "AI-assisted advisory analysis",
                "short_summary": "Custom recommendation review.",
                "root_cause": "Custom provider reviewed deterministic recommendation inputs.",
                "risk_flags": ["no_current_risk_flags"],
                "recommended_next_actions": ["Keep analysis paper-only."],
                "confidence": "medium",
                "source_record_ids": ["paper_recommendation:1"],
                "approval_state": "approve",
                "concerns": [],
                "confidence_explanation": "Custom provider confidence explanation.",
                "rejected_assumptions": ["No real-money readiness is implied."],
                "next_checks": ["Backtest recommendation thresholds."],
            },
        }


class UnsafeProvider(AIAnalysisProvider):
    model_name = "unsafe_provider_model"

    def analyze_live_status(self, prompt: LiveStatusPrompt) -> dict:
        return {
            "prompt_version": prompt.version,
            "output": {
                "label": "Betting advice",
                "short_summary": "Place a real-money bet now.",
                "root_cause": "Unsupported claim.",
                "risk_flags": [],
                "recommended_next_actions": ["Place real-money stake on the home team."],
                "confidence": "certain",
                "source_record_ids": [],
            },
        }


class UnsafeRecommendationReviewProvider(AIAnalysisProvider):
    model_name = "unsafe_recommendation_review_provider"

    def analyze_recommendation_review(self, prompt: RecommendationReviewPrompt) -> dict:
        return {
            "prompt_version": prompt.version,
            "output": {
                "label": "Betting advice",
                "short_summary": "This is guaranteed. Place a real-money bet now.",
                "root_cause": "Unsupported certainty.",
                "risk_flags": [],
                "recommended_next_actions": ["Place a bet through the bookmaker account."],
                "confidence": "certain",
                "source_record_ids": [],
                "approval_state": "approve",
                "concerns": [],
                "confidence_explanation": "Guaranteed outcome.",
                "rejected_assumptions": [],
                "next_checks": [],
            },
        }
