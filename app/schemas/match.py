from typing import Any

from pydantic import BaseModel


class RawMatch(BaseModel):
    source: str
    source_match_id: str
    league: str
    season: str | None = None
    home_team: str
    away_team: str
    kickoff_time: str
    status: str = "scheduled"
    home_score: int | None = None
    away_score: int | None = None
    result: str | None = None
    raw_payload: dict[str, Any]

