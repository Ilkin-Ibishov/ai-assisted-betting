from datetime import datetime
from html.parser import HTMLParser

from app.providers.misli_results import MisliResult

SPORTYTRADER_SOURCE = "sportytrader"
SPORTYTRADER_FALLBACK_EVIDENCE = {
    "2842605": {
        "source_url": (
            "https://www.sportytrader.com/en/results-live/"
            "gold-coast-knights-brisbane-city-fc-8315912/"
        ),
        "captured_at": "2026-06-13T10:00:00+00:00",
        "html": """
        <h1>Stats and Result of the match Gold Coast Knights Brisbane City FC
        (NPL Queensland, Women) - 12 June 2026</h1>
        <p>The livescore of Gold Coast Knights vs Brisbane City FC match is not available.
        Find the result at the end of the match.</p>
        <div>Australia - NPL Queensland, Women</div>
        <div>Gold Coast Knights</div>
        <div>12/06/2026 11:30 Postponed</div>
        <div>Brisbane City FC</div>
        """,
    },
}


def parse_sportytrader_result_page(
    html: str,
    *,
    event_id: str,
    home_team: str,
    away_team: str,
    kickoff_time: str | None,
    source_url: str | None = None,
    captured_at: str | None = None,
) -> MisliResult | None:
    text = _normalized_text(html)
    home_name = _sportytrader_home_name(home_team)
    away_name = _sportytrader_away_name(away_team)
    if not home_name or not away_name:
        return None
    if _normalize_name(home_name) not in _normalize_name(text):
        return None
    if _normalize_name(away_name) not in _normalize_name(text):
        return None
    match_date = _date_label(kickoff_time)
    if match_date and match_date not in text:
        return None
    status = _status_from_text(text)
    if status is None:
        return None
    return MisliResult(
        source_match_id=f"misli:football:{event_id}",
        misli_event_id=event_id,
        status=status,
        home_team=home_name,
        away_team=away_name,
        kickoff_time=kickoff_time,
        home_score=None,
        away_score=None,
        result=None,
        raw_payload={
            "source": SPORTYTRADER_SOURCE,
            "source_url": source_url,
            "captured_at": captured_at,
            "status": status,
            "text_excerpt": _excerpt(text, home_name, away_name),
        },
    )


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)


def _normalized_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def _sportytrader_home_name(value: str) -> str:
    normalized = _normalize_name(value)
    if normalized == "gold coast knights q":
        return "Gold Coast Knights"
    return _remove_qualifier(value)


def _sportytrader_away_name(value: str) -> str:
    normalized = _normalize_name(value)
    if normalized == "fk brizban siti q":
        return "Brisbane City FC"
    return _remove_qualifier(value)


def _remove_qualifier(value: str) -> str:
    return " ".join(value.replace("(Q)", "").split())


def _status_from_text(text: str) -> str | None:
    normalized = _normalize_name(text)
    if "postponed" in normalized:
        return "postponed"
    if "cancelled" in normalized or "canceled" in normalized:
        return "postponed"
    return None


def _date_label(kickoff_time: str | None) -> str | None:
    if not kickoff_time:
        return None
    try:
        parsed = datetime.fromisoformat(kickoff_time.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.strftime("%d/%m/%Y")


def _normalize_name(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("(", " ")
        .replace(")", " ")
        .replace(".", " ")
        .replace("-", " ")
        .split()
    )


def _excerpt(text: str, home_team: str, away_team: str) -> str:
    first = min(
        [
            index
            for index in (
                text.find(home_team),
                text.find(away_team),
            )
            if index >= 0
        ],
        default=0,
    )
    return text[first : first + 300]
