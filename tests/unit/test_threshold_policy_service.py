import json

from app.config import Settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, Base, ThresholdPolicyRun
from app.services.threshold_policy_service import ThresholdPolicyService


def test_threshold_policy_keeps_small_sample_advisory(tmp_path) -> None:
    engine = _engine(tmp_path, "small-sample.sqlite")
    review = _seed_threshold_review(
        engine,
        sample_size=42,
        overall_decision="fail_closed",
        decisions={"minimum_edge": {"decision": "keep", "rationale": "Small sample."}},
        singles={"roi": -0.2, "hit_rate": 0.3, "brier_score": 0.31, "log_loss": 0.9},
    )

    policy = ThresholdPolicyService(engine, _settings()).evaluate_latest()

    assert policy["state"] == "advisory"
    assert policy["decision"] == "fail_closed"
    assert policy["source_backtest_id"] == review.id
    assert policy["active"] is False
    assert policy["policy_values"]["min_edge"] == 0.07
    assert policy["evidence"]["sample_size"] == 42
    assert ThresholdPolicyService(engine, _settings()).active_policy() is None


def test_threshold_policy_proposes_tightening_for_supported_negative_roi(tmp_path) -> None:
    engine = _engine(tmp_path, "negative-roi.sqlite")
    _seed_threshold_review(
        engine,
        sample_size=360,
        overall_decision="tighten",
        decisions={
            "minimum_edge": {
                "decision": "tighten",
                "rationale": "Negative ROI improves under stricter edge scenarios.",
            },
            "confidence_floor": {
                "decision": "tighten",
                "rationale": "Negative ROI argues for higher confidence.",
            },
            "odds_cap": {"decision": "keep", "rationale": "Odds cap is stable."},
        },
        singles={
            "roi": -0.12,
            "hit_rate": 0.38,
            "brier_score": 0.29,
            "log_loss": 0.74,
            "max_drawdown_units": -18.0,
        },
    )

    policy = ThresholdPolicyService(engine, _settings()).evaluate_latest()

    assert policy["state"] == "proposed"
    assert policy["decision"] == "tighten"
    assert policy["active"] is False
    assert policy["policy_values"]["min_edge"] > 0.07
    assert policy["policy_values"]["min_confidence"] > 0.5
    assert policy["rollback_policy_values"]["min_edge"] == 0.07


def test_threshold_policy_does_not_loosen_on_positive_but_conflicting_metrics(tmp_path) -> None:
    engine = _engine(tmp_path, "conflicting.sqlite")
    _seed_threshold_review(
        engine,
        sample_size=340,
        overall_decision="loosen",
        risk_flags=["conflicting_threshold_metrics"],
        decisions={
            "confidence_floor": {
                "decision": "loosen",
                "rationale": "Candidate count improved.",
            }
        },
        singles={
            "roi": 0.1,
            "hit_rate": 0.5,
            "brier_score": 0.36,
            "log_loss": 0.88,
            "max_drawdown_units": -12.0,
        },
    )

    policy = ThresholdPolicyService(engine, _settings()).evaluate_latest()

    assert policy["state"] == "advisory"
    assert policy["decision"] == "keep"
    assert "loosening_requires_manual_review" in policy["risk_flags"]
    assert "conflicting_threshold_metrics" in policy["risk_flags"]


def test_threshold_policy_approval_apply_and_rollback(tmp_path) -> None:
    engine = _engine(tmp_path, "apply-rollback.sqlite")
    _seed_threshold_review(
        engine,
        sample_size=400,
        overall_decision="tighten",
        decisions={"minimum_edge": {"decision": "tighten", "rationale": "Tighten edge."}},
        singles={"roi": -0.08, "hit_rate": 0.4, "brier_score": 0.28, "log_loss": 0.72},
    )
    service = ThresholdPolicyService(engine, _settings())
    proposed = service.evaluate_latest()

    approved = service.approve(proposed["id"], reviewer="human", rationale="Use safer edge.")
    applied = service.apply(approved["id"], reviewer="human", rationale="Apply to worker.")

    assert approved["state"] == "approved"
    assert applied["state"] == "applied"
    assert applied["active"] is True
    assert service.active_policy()["id"] == applied["id"]
    assert service.effective_policy_values()["min_edge"] == applied["policy_values"]["min_edge"]

    rolled_back = service.rollback(applied["id"], reviewer="human", rationale="Undo test policy.")

    assert rolled_back["state"] == "rolled_back"
    assert rolled_back["active"] is False
    assert service.active_policy() is None
    assert service.effective_policy_values()["min_edge"] == 0.07


def test_threshold_policy_rejects_apply_without_approval(tmp_path) -> None:
    engine = _engine(tmp_path, "approval-required.sqlite")
    _seed_threshold_review(
        engine,
        sample_size=400,
        overall_decision="tighten",
        decisions={"minimum_edge": {"decision": "tighten", "rationale": "Tighten edge."}},
        singles={"roi": -0.08, "hit_rate": 0.4, "brier_score": 0.28, "log_loss": 0.72},
    )
    service = ThresholdPolicyService(engine, _settings())
    proposed = service.evaluate_latest()

    try:
        service.apply(proposed["id"], reviewer="human", rationale="Should fail.")
    except ValueError as exc:
        assert "approved" in str(exc)
    else:
        raise AssertionError("unapproved policy should not apply")


def test_threshold_policy_latest_payload_reads_existing_rows(tmp_path) -> None:
    engine = _engine(tmp_path, "latest.sqlite")
    with session_scope(engine) as session:
        session.add(
            ThresholdPolicyRun(
                state="applied",
                decision="tighten",
                active=True,
                source_backtest_id=None,
                source_backtest_name="scheduled_worker_threshold_review",
                sample_size=350,
                roi=-0.1,
                hit_rate=0.4,
                brier_score=0.3,
                log_loss=0.8,
                max_drawdown_units=-20.0,
                policy_values_json=json.dumps({"min_edge": 0.1}),
                rollback_policy_values_json=json.dumps({"min_edge": 0.07}),
                evidence_json=json.dumps({"sample_size": 350}),
                rationale="Seeded policy.",
                reviewer="human",
                reviewed_at="2026-06-07T10:00:00+00:00",
                applied_at="2026-06-07T10:01:00+00:00",
            )
        )

    latest = ThresholdPolicyService(engine, _settings()).latest()

    assert latest is not None
    assert latest["state"] == "applied"
    assert latest["active"] is True
    assert latest["policy_values"]["min_edge"] == 0.1


def _engine(tmp_path, name: str):
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / name).as_posix()}")
    Base.metadata.create_all(engine)
    return engine


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        default_sport="football",
        default_market="1X2",
        default_stake_units=1.0,
        min_edge=0.07,
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


def _seed_threshold_review(
    engine,
    *,
    sample_size: int,
    overall_decision: str,
    decisions: dict,
    singles: dict,
    risk_flags: list[str] | None = None,
) -> AIAnalysisRun:
    output = {
        "short_summary": "Threshold review available.",
        "threshold_advice": {
            "sample_size": sample_size,
            "minimum_sample_size": 300,
            "overall_decision": overall_decision,
            "risk_flags": risk_flags or ["no_current_risk_flags"],
            "decisions": decisions,
        },
        "recommendation_backtest": {
            "metadata": {"report_name": "scheduled_worker_threshold_review"},
            "singles": singles,
        },
    }
    with session_scope(engine) as session:
        review = AIAnalysisRun(
            analysis_type="recommendation_backtest_summary",
            source_type="recommendation_backtest_report",
            source_id="scheduled_worker_threshold_review",
            input_json="{}",
            output_json=json.dumps(output),
            model_name="deterministic_ai_fallback",
            prompt_version="pytest",
            status="completed",
        )
        session.add(review)
        session.flush()
        session.refresh(review)
        review_id = review.id
    with session_scope(engine) as session:
        loaded = session.get(AIAnalysisRun, review_id)
        assert loaded is not None
        return loaded
