import json

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, PaperCombination, PaperRecommendation
from app.db.repositories import MatchRepository
from app.services.combination_service import CombinationService


def test_combination_service_generates_ranked_single_and_multi_leg_sets(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'combos.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_recommendation(engine, source_match_id="match-1", selection="HOME", odds=2.0, ev=0.2)
    _seed_recommendation(engine, source_match_id="match-2", selection="AWAY", odds=1.9, ev=0.18)
    _seed_recommendation(engine, source_match_id="match-3", selection="DRAW", odds=3.2, ev=0.05)

    summary = CombinationService(engine).generate(max_legs=2, min_leg_confidence=0.6)

    assert summary.items_read == 3
    assert summary.items_created == 6
    with session_scope(engine) as session:
        combinations = list(
            session.scalars(select(PaperCombination).order_by(PaperCombination.rank.asc()))
        )

    assert combinations[0].grade == "recommended"
    assert combinations[0].leg_count == 2
    assert json.loads(combinations[0].risk_flags_json) == ["no_current_risk_flags"]
    assert combinations[0].combined_expected_value > combinations[-1].combined_expected_value


def test_combination_service_rejects_duplicate_event_exposure(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'combos.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_recommendation(engine, source_match_id="match-1", selection="HOME", odds=2.0, ev=0.2)
    _seed_recommendation(engine, source_match_id="match-1", selection="AWAY", odds=2.2, ev=0.16)

    CombinationService(engine).generate(max_legs=2, min_leg_confidence=0.6)

    with session_scope(engine) as session:
        combinations = list(session.scalars(select(PaperCombination)))

    assert len(combinations) == 2
    assert all(combination.leg_count == 1 for combination in combinations)


def test_combination_service_filters_rejected_stale_and_low_confidence_legs(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'combos.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_recommendation(engine, source_match_id="good", selection="HOME", odds=2.0, ev=0.2)
    _seed_recommendation(
        engine,
        source_match_id="rejected",
        selection="HOME",
        odds=2.0,
        ev=0.2,
        grade="reject",
        status="rejected",
    )
    _seed_recommendation(
        engine,
        source_match_id="stale",
        selection="HOME",
        odds=2.0,
        ev=0.2,
        risk_flags=["stale_odds"],
    )
    _seed_recommendation(
        engine,
        source_match_id="low-confidence",
        selection="HOME",
        odds=2.0,
        ev=0.2,
        confidence=0.4,
    )

    CombinationService(engine).generate(max_legs=2, min_leg_confidence=0.6)

    with session_scope(engine) as session:
        combinations = list(session.scalars(select(PaperCombination)))

    assert len(combinations) == 1
    assert json.loads(combinations[0].leg_recommendation_ids_json) == [1]


def test_combination_service_enforces_max_legs(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'combos.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    for index in range(4):
        _seed_recommendation(
            engine,
            source_match_id=f"match-{index}",
            selection="HOME",
            odds=2.0,
            ev=0.2,
        )

    CombinationService(engine).generate(max_legs=3, min_leg_confidence=0.6)

    with session_scope(engine) as session:
        combinations = list(session.scalars(select(PaperCombination)))

    assert combinations
    assert max(combination.leg_count for combination in combinations) == 3


def test_combination_service_enforces_max_risk_flags(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'combos.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    for index in range(3):
        _seed_recommendation(
            engine,
            source_match_id=f"match-{index}",
            selection="HOME",
            odds=2.0,
            ev=0.2,
        )

    CombinationService(engine).generate(
        max_legs=3,
        min_leg_confidence=0.6,
        max_risk_flags=0,
    )

    with session_scope(engine) as session:
        combinations = list(session.scalars(select(PaperCombination)))

    assert combinations
    assert max(combination.leg_count for combination in combinations) == 2
    assert all(
        json.loads(combination.risk_flags_json) == ["no_current_risk_flags"]
        for combination in combinations
    )


def _seed_recommendation(
    engine,
    *,
    source_match_id: str,
    selection: str,
    odds: float,
    ev: float,
    grade: str = "recommended",
    status: str = "active",
    confidence: float = 0.7,
    risk_flags: list[str] | None = None,
) -> None:
    with session_scope(engine) as session:
        matches = MatchRepository(session)
        match = matches.get_by_source_id("misli_public", source_match_id)
        if match is None:
            match = matches.add(
                source="misli_public",
                source_match_id=source_match_id,
                league="Sample Premier",
                home_team=f"{source_match_id} Home",
                away_team=f"{source_match_id} Away",
                kickoff_time="2026-05-19T20:30:00+04:00",
            )
        recommendation = PaperRecommendation(
            match_id=match.id,
            source_match_id=source_match_id,
            bookmaker="Misli.az",
            market="1X2",
            selection=selection,
            latest_snapshot_time="2026-05-19T12:00:00+00:00",
            model_name="baseline_heuristic",
            model_version="v0",
            grade=grade,
            status=status,
            model_probability=0.6,
            implied_probability=1 / odds,
            edge=0.1,
            confidence_score=confidence,
            current_odds=odds,
            expected_value=ev,
            risk_flags_json=json.dumps(risk_flags or ["no_current_risk_flags"]),
            rationale="Seed recommendation",
        )
        session.add(recommendation)
