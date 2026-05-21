from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel

from app.schemas.match import RawMatch
from app.schemas.odds import RawOddsSnapshot
from app.schemas.result import RawResult


class ProviderCapability(BaseModel):
    provider: str
    supports_matches: bool
    supports_odds: bool
    supports_results: bool
    supported_leagues: list[str]
    supported_markets: list[str]
    rate_limit_notes: str
    requires_full_kickoff_datetime: bool = True
    safety_boundary_notes: str


class MatchProvider(ABC):
    @abstractmethod
    def get_matches(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterable[RawMatch]:
        pass


class OddsProvider(ABC):
    @abstractmethod
    def get_odds(self, match_source_id: str, market: str) -> Iterable[RawOddsSnapshot]:
        pass


class ResultProvider(ABC):
    @abstractmethod
    def get_result(self, match_source_id: str) -> RawResult | None:
        pass
