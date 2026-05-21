import re
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.providers.base import ProviderCapability

MISLI_PUBLIC_CAPABILITY = ProviderCapability(
    provider="misli_public",
    supports_matches=True,
    supports_odds=True,
    supports_results=False,
    supported_leagues=["football"],
    supported_markets=["1X2"],
    rate_limit_notes="Manual low-rate public snapshot only; incomplete dates fail closed.",
    requires_full_kickoff_datetime=True,
    safety_boundary_notes="Public unauthenticated Misli.az sports pages only.",
)


class MisliPublicOdd(BaseModel):
    model_config = ConfigDict(extra="allow")

    market: str
    selection: str
    odds_decimal: float = Field(gt=1.0)
    label: str | None = None
    previous_odds_decimal: float | None = None
    final_odds_decimal: float | None = None
    raw_text: str | None = None


class MisliPublicEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    sport: str
    event_id: str
    source_match_id: str
    detail_url: str | None = None
    home_team: str
    away_team: str
    kickoff_date_label: str | None = None
    kickoff_date: str
    kickoff_time: str
    league: str
    odds: list[MisliPublicOdd]
    raw_text: str

    @property
    def has_full_kickoff_datetime(self) -> bool:
        return bool(self.kickoff_date.strip() and self.kickoff_time.strip())

    @property
    def has_complete_1x2(self) -> bool:
        selections = {
            odd.selection
            for odd in self.odds
            if odd.market == "1X2" and odd.odds_decimal > 1.0
        }
        return {"HOME", "DRAW", "AWAY"}.issubset(selections)

    @model_validator(mode="after")
    def validate_public_event(self) -> "MisliPublicEvent":
        if self.source != "misli_public":
            raise ValueError("Misli event source must be misli_public")
        if not self.has_full_kickoff_datetime:
            raise ValueError("Misli event requires a full kickoff date and time")
        if not self.has_complete_1x2:
            raise ValueError("Misli event requires complete 1X2 HOME, DRAW, and AWAY odds")
        return self


class MisliPublicSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    page_url: str
    scraped_at: str
    title: str | None = None
    event_count: int
    events: list[MisliPublicEvent]

    @model_validator(mode="before")
    @classmethod
    def derive_missing_event_dates(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        scraped_at = str(data.get("scraped_at") or "")
        events = data.get("events")
        if not isinstance(events, list):
            return data
        enriched = {
            **data,
            "events": [resolve_misli_public_event_date(event, scraped_at) for event in events],
        }
        return enriched

    @model_validator(mode="after")
    def validate_public_snapshot(self) -> "MisliPublicSnapshot":
        if self.source != "misli_public":
            raise ValueError("Misli snapshot source must be misli_public")
        if self.event_count != len(self.events):
            raise ValueError("Misli snapshot event_count must match events length")
        return self


def resolve_misli_public_event_date(raw_event: Any, scraped_at: str) -> Any:
    if not isinstance(raw_event, dict):
        return raw_event
    if str(raw_event.get("kickoff_date") or "").strip():
        return raw_event
    kickoff_time = str(raw_event.get("kickoff_time") or "").strip()
    resolved = _resolve_relative_kickoff(kickoff_time, scraped_at)
    if resolved is None:
        return raw_event
    kickoff_date, normalized_time = resolved
    return {
        **raw_event,
        "kickoff_date": kickoff_date,
        "kickoff_time": normalized_time,
        "kickoff_date_resolution": "relative_label_from_snapshot_scraped_at",
    }


def _resolve_relative_kickoff(kickoff_time: str, scraped_at: str) -> tuple[str, str] | None:
    match = re.match(
        r"^(?P<label>bu\s+gün|bu\s+gun|bu\s+gã¼n|sabah)\s+(?P<time>\d{1,2}:\d{2})$",
        kickoff_time,
        re.IGNORECASE,
    )
    if match is None:
        return None
    scraped_local = _scraped_at_local(scraped_at)
    if scraped_local is None:
        return None
    label = match.group("label").casefold()
    day_offset = 1 if label == "sabah" else 0
    kickoff_date = scraped_local.date() + timedelta(days=day_offset)
    return kickoff_date.strftime("%d.%m.%Y"), match.group("time")


def _scraped_at_local(scraped_at: str) -> datetime | None:
    if not scraped_at:
        return None
    try:
        parsed = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(ZoneInfo("Asia/Baku"))
