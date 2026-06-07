import json

from fastapi.testclient import TestClient

from app.api import create_api
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, ThresholdPolicyRun


def test_latest_threshold_policy_endpoint_returns_policy_state(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'threshold-policy-api.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    with session_scope(engine) as session:
        session.add(
            ThresholdPolicyRun(
                state="applied",
                decision="tighten",
                active=True,
                source_backtest_id=None,
                source_backtest_name="scheduled_worker_threshold_review",
                sample_size=360,
                roi=-0.08,
                hit_rate=0.39,
                brier_score=0.3,
                log_loss=0.82,
                max_drawdown_units=-16.0,
                policy_values_json=json.dumps({"min_edge": 0.1, "max_odds": 3.5}),
                rollback_policy_values_json=json.dumps({"min_edge": 0.07, "max_odds": 3.5}),
                evidence_json=json.dumps({"sample_size": 360}),
                rationale="Applied safer threshold.",
                reviewer="human",
                reviewed_at="2026-06-07T10:00:00+00:00",
                applied_at="2026-06-07T10:01:00+00:00",
            )
        )
    client = TestClient(create_api(database_url=database_url))

    response = client.get("/api/live/threshold-policy/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "applied"
    assert payload["active"] is True
    assert payload["policy_values"]["min_edge"] == 0.1


def test_latest_threshold_policy_endpoint_404s_without_policy(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'threshold-policy-empty.sqlite').as_posix()}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    client = TestClient(create_api(database_url=database_url))

    response = client.get("/api/live/threshold-policy/latest")

    assert response.status_code == 404
