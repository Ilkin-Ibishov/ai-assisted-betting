from typing import Any

from pydantic import BaseModel


class RawResult(BaseModel):
    source: str
    source_match_id: str
    home_score: int
    away_score: int
    result: str
    raw_payload: dict[str, Any]

