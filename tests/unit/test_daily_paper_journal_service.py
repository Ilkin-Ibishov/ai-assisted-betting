import json

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.migrations import init_db
from app.db.models import AIAnalysisRun, Match, PaperBet, PaperRecommendation, Prediction
from app.services.daily_paper_journal_service import DailyPaperJournalService


def test_daily_journal_reports_no_candidates(tmp_path) -> None:
    engine = _engine(tmp_path, "no-candidates.sqlite")

    entry = DailyPaperJournalService(engine).generate(journal_date="2026-06-04")

    assert entry["journal_date"] == "2026-06-04"
    assert entry["decision_state"] == "no_candidates"
    assert entry["summary"]["candidate_count"] == 0
    assert entry["summary"]["ai_approval_state"] == "missing"
    assert entry["settled_since_previous_journal"] == []
    assert entry["source_ids"] == []


def test_daily_journal_reports_candidate_ready(tmp_path) -> None:
    engine = _engine(tmp_path, "candidate-ready.sqlite")
    _seed_recommendation(engine, grade="recommended", risk_flags=["no_current_risk_flags"])
    _seed_ai_review(engine, approval_state="approve")

    entry = DailyPaperJournalService(engine).generate(journal_date="2026-06-04")

    assert entry["decision_state"] == "candidate_ready"
    assert entry["summary"]["candidate_count"] == 1
    assert entry["summary"]["blocked_count"] == 0
    assert entry["summary"]["ai_approval_state"] == "approve"
    assert "paper_recommendation:1" in entry["source_ids"]
    assert entry["quality_snapshot"]["overall_state"] == "actionable_present"


def test_daily_journal_distinguishes_ai_rejected_slate(tmp_path) -> None:
    engine = _engine(tmp_path, "ai-rejected.sqlite")
    _seed_recommendation(engine, grade="recommended", risk_flags=["no_current_risk_flags"])
    _seed_ai_review(engine, approval_state="reject", risk_flags=["low_confidence_recommendations"])

    entry = DailyPaperJournalService(engine).generate(journal_date="2026-06-04")

    assert entry["decision_state"] == "ai_rejected"
    assert entry["summary"]["candidate_count"] == 1
    assert entry["summary"]["ai_approval_state"] == "reject"
    assert entry["ai_review"]["risk_flags"] == ["low_confidence_recommendations"]


def test_daily_journal_links_settled_results_since_previous_journal(tmp_path) -> None:
    engine = _engine(tmp_path, "settled.sqlite")
    _seed_recommendation(engine, grade="recommended", risk_flags=["no_current_risk_flags"])
    _seed_ai_review(engine, approval_state="approve")
    _seed_settled_bet(engine)
    first = DailyPaperJournalService(engine).generate(journal_date="2026-06-03")
    assert first["decision_state"] == "settled_learning"
    assert first["settled_since_previous_journal"] == [
        {
            "paper_bet_id": 1,
            "prediction_id": 1,
            "match_id": 1,
            "source_match_id": "journal-match",
            "selection": "HOME",
            "status": "won",
            "profit_loss_units": 1.1,
            "settled_at": "2026-06-04T06:00:00+00:00",
        }
    ]

    second = DailyPaperJournalService(engine).generate(journal_date="2026-06-04")

    assert second["decision_state"] == "candidate_ready"
    assert second["settled_since_previous_journal"] == []


def _engine(tmp_path, filename: str):
    database_url = f"sqlite:///{(tmp_path / filename).as_posix()}"
    init_db(database_url)
    return create_engine_from_url(database_url)


def _seed_recommendation(engine, *, grade: str, risk_flags: list[str]) -> None:
    with session_scope(engine) as session:
        match = Match(
            source="misli_public",
            source_match_id="journal-match",
            league="Sample Premier",
            home_team="Home",
            away_team="Away",
            kickoff_time="2026-06-04T20:00:00+04:00",
            status="scheduled",
        )
        session.add(match)
        session.flush()
        session.add(
            PaperRecommendation(
                match_id=match.id,
                source_match_id=match.source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection="HOME",
                latest_snapshot_time="2026-06-04T09:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade=grade,
                status="active",
                model_probability=0.62,
                implied_probability=0.5,
                edge=0.12,
                confidence_score=0.72,
                current_odds=2.0,
                expected_value=0.24,
                risk_flags_json=json.dumps(risk_flags),
                rationale="Positive edge is above recommendation threshold.",
                created_at="2026-06-04T09:01:00+00:00",
            )
        )


def _seed_ai_review(
    engine,
    *,
    approval_state: str,
    risk_flags: list[str] | None = None,
) -> None:
    with session_scope(engine) as session:
        session.add(
            AIAnalysisRun(
                analysis_type="recommendation_review",
                source_type="paper_recommendations",
                source_id="latest",
                input_json="{}",
                output_json=json.dumps(
                    {
                        "approval_state": approval_state,
                        "risk_flags": risk_flags or ["no_current_risk_flags"],
                        "short_summary": "Reviewed paper slate.",
                        "concerns": [],
                        "recommended_next_actions": ["Keep all outputs paper-only."],
                    }
                ),
                model_name="deterministic_ai_fallback",
                prompt_version="ai-recommendation-review-v1",
                status="completed",
                created_at="2026-06-04T09:02:00+00:00",
            )
        )


def _seed_settled_bet(engine) -> None:
    with session_scope(engine) as session:
        match = session.scalar(select(Match))
        assert match is not None
        prediction = Prediction(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.62,
            bookmaker_probability=0.5,
            edge=0.12,
            confidence_score=0.72,
            decision="BET",
            reason="paper journal seed",
        )
        session.add(prediction)
        session.flush()
        session.add(
            PaperBet(
                prediction_id=prediction.id,
                match_id=match.id,
                market="1X2",
                selection="HOME",
                odds_taken=2.1,
                stake_units=1.0,
                expected_value=0.302,
                status="won",
                profit_loss_units=1.1,
                settled_at="2026-06-04T06:00:00+00:00",
            )
        )
