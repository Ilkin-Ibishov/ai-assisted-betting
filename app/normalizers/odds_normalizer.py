import json

from app.schemas.odds import RawOddsSnapshot

SUPPORTED_MARKETS = {"1X2", "OVER_UNDER_2_5"}
SUPPORTED_SELECTIONS = {"HOME", "DRAW", "AWAY", "OVER_2_5", "UNDER_2_5"}


def normalize_odds_snapshot(raw_snapshot: RawOddsSnapshot, match_id: int) -> dict[str, object]:
    if raw_snapshot.odds_decimal <= 1.0:
        raise ValueError("odds_decimal must be greater than 1.0")
    if raw_snapshot.market not in SUPPORTED_MARKETS:
        raise ValueError(f"unsupported market: {raw_snapshot.market}")
    if raw_snapshot.selection not in SUPPORTED_SELECTIONS:
        raise ValueError(f"unsupported selection: {raw_snapshot.selection}")

    return {
        "match_id": match_id,
        "source": raw_snapshot.source,
        "bookmaker": raw_snapshot.bookmaker,
        "market": raw_snapshot.market,
        "selection": raw_snapshot.selection,
        "odds_decimal": raw_snapshot.odds_decimal,
        "implied_probability": 1 / raw_snapshot.odds_decimal,
        "snapshot_time": raw_snapshot.snapshot_time,
        "minutes_before_kickoff": raw_snapshot.minutes_before_kickoff,
        "is_closing": raw_snapshot.is_closing,
        "raw_payload_json": json.dumps(raw_snapshot.raw_payload, sort_keys=True),
    }

