import json

from sqlalchemy import select

from app.config import load_settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, Feature, LiveRun, Match, PaperBet, Prediction
from app.services.collection_service import CollectionService
from app.services.live_cycle_service import LivePaperCycleRequest, LivePaperCycleService


def test_live_paper_cycle_runs_collection_prediction_and_bet_steps_idempotently(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MIN_EDGE", "0.01")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    CollectionService(engine).import_sample_data()

    request = LivePaperCycleRequest(
        provider="misli-public",
        snapshot=snapshot_path,
        model="baseline_heuristic",
    )
    first = LivePaperCycleService(engine, settings).run(request)
    second = LivePaperCycleService(engine, settings).run(request)

    assert first.status == "completed"
    assert first.collect_matches.items_created == 1
    assert first.collect_odds.items_created == 3
    assert first.generate_features.items_created > 0
    assert first.generate_predictions.items_created > 0
    assert first.write_paper_bets.items_created > 0
    assert second.write_paper_bets.items_created == 0

    with session_scope(engine) as session:
        paper_bets = list(session.scalars(select(PaperBet)))
        cycle_runs = list(
            session.scalars(
                select(LiveRun).where(LiveRun.run_type == "run_live_paper_cycle")
            )
        )

    assert len(paper_bets) == first.write_paper_bets.items_created
    assert len(cycle_runs) == 1
    assert cycle_runs[0].status == "completed"


def test_live_paper_cycle_records_failed_run_when_collection_validation_fails(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot = _valid_snapshot()
    snapshot["events"][0]["kickoff_date"] = ""
    snapshot["events"][0]["kickoff_time"] = ""
    snapshot_path = tmp_path / "misli-invalid.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)

    result = LivePaperCycleService(engine, settings).run(
        LivePaperCycleRequest(
            provider="misli-public",
            snapshot=snapshot_path,
            model="baseline_heuristic",
        )
    )

    assert result.status == "failed"
    assert result.collect_matches.errors_count == 1
    assert result.collect_odds.errors_count == 1

    with session_scope(engine) as session:
        cycle_run = session.scalar(
            select(LiveRun).where(LiveRun.run_type == "run_live_paper_cycle")
        )

    assert cycle_run is not None
    assert cycle_run.status == "failed"
    assert "collect_matches errors=1" in (cycle_run.error_summary or "")


def test_live_paper_cycle_scopes_prediction_steps_to_snapshot_matches(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_snapshot()), encoding="utf-8")
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MIN_EDGE", "0.01")
    settings = load_settings()
    engine = create_engine_from_url(settings.database_url)
    Base.metadata.create_all(engine)
    CollectionService(engine).import_sample_data()

    result = LivePaperCycleService(engine, settings).run(
        LivePaperCycleRequest(
            provider="misli-public",
            snapshot=snapshot_path,
            model="baseline_heuristic",
        )
    )

    assert result.status == "completed"

    with session_scope(engine) as session:
        features = list(session.scalars(select(Feature)))
        predictions = list(session.scalars(select(Prediction)))
        paper_bets = list(session.scalars(select(PaperBet)))
        touched_match_ids = {
            feature.match_id for feature in features
        } | {
            prediction.match_id for prediction in predictions
        } | {
            paper_bet.match_id for paper_bet in paper_bets
        }
        touched_sources = {
            session.get(Match, match_id).source
            for match_id in touched_match_ids
            if session.get(Match, match_id) is not None
        }

    assert touched_sources == {"misli_public"}
    assert len(features) == 3
    assert len(predictions) == 3


def _valid_snapshot() -> dict:
    return {
        "source": "misli_public",
        "page_url": "https://www.misli.az/idman-novleri/futbol",
        "scraped_at": "2026-05-19T13:43:22.194Z",
        "event_count": 1,
        "events": [
            {
                "source": "misli_public",
                "sport": "football",
                "event_id": "2816300",
                "source_match_id": "misli:football:2816300",
                "home_team": "Forest City",
                "away_team": "Eastport Athletic",
                "kickoff_date": "19.05.2026",
                "kickoff_time": "20:30",
                "league": "Sample Premier",
                "odds": [
                    {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                    {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                ],
                "raw_text": "20:30 1 Forest City - Eastport Athletic 1 2.16 X 3.18 2 2.94",
            }
        ],
    }
