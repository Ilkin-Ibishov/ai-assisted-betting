from typing import Any

from pydantic import BaseModel


class RawOddsSnapshot(BaseModel):
    source: str
    source_match_id: str
    bookmaker: str
    market: str
    selection: str
    odds_decimal: float
    snapshot_time: str
    minutes_before_kickoff: int | None = None
    is_closing: bool = False
    raw_payload: dict[str, Any]

