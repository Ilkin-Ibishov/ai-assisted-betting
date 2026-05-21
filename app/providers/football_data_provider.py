import csv
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from app.providers.base import MatchProvider, OddsProvider, ResultProvider
from app.schemas.match import RawMatch
from app.schemas.odds import RawOddsSnapshot
from app.schemas.result import RawResult

BOOKMAKER_ODDS_COLUMNS = {
    "B365": {"HOME": "B365H", "DRAW": "B365D", "AWAY": "B365A"},
    "BW": {"HOME": "BWH", "DRAW": "BWD", "AWAY": "BWA"},
    "IW": {"HOME": "IWH", "DRAW": "IWD", "AWAY": "IWA"},
    "PS": {"HOME": "PSH", "DRAW": "PSD", "AWAY": "PSA"},
    "WH": {"HOME": "WHH", "DRAW": "WHD", "AWAY": "WHA"},
    "VC": {"HOME": "VCH", "DRAW": "VCD", "AWAY": "VCA"},
    "Max": {"HOME": "MaxH", "DRAW": "MaxD", "AWAY": "MaxA"},
    "Avg": {"HOME": "AvgH", "DRAW": "AvgD", "AWAY": "AvgA"},
}


class FootballDataCsvProvider(MatchProvider, OddsProvider, ResultProvider):
    source = "football-data"
    def __init__(
        self,
        *,
        league: str,
        season: str,
        bookmaker: str = "B365",
        path: str | Path | None = None,
        url: str | None = None,
    ) -> None:
        if path is None and url is None:
            raise ValueError("Either path or url is required")
        self.league = league
        self.season = season
        self.bookmaker = bookmaker
        self.path = Path(path) if path is not None else None
        self.url = url
        self._rows: list[dict[str, str]] | None = None

    @classmethod
    def from_league_season(
        cls,
        *,
        league: str,
        season: str,
        bookmaker: str = "B365",
    ) -> "FootballDataCsvProvider":
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
        return cls(league=league, season=season, bookmaker=bookmaker, url=url)

    def get_matches(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterable[RawMatch]:
        for row in self._load_rows():
            if not row.get("HomeTeam") or not row.get("AwayTeam") or not row.get("Date"):
                continue
            kickoff_time = _parse_date(row["Date"])
            home_score = _optional_int(row.get("FTHG"))
            away_score = _optional_int(row.get("FTAG"))
            status = (
                "completed"
                if home_score is not None and away_score is not None
                else "scheduled"
            )
            result = _map_result(row.get("FTR")) if status == "completed" else None
            source_match_id = _source_match_id(
                league=self.league,
                season=self.season,
                date=kickoff_time,
                home_team=row["HomeTeam"],
                away_team=row["AwayTeam"],
            )

            yield RawMatch(
                source=self.source,
                source_match_id=source_match_id,
                league=self.league,
                season=self.season,
                home_team=row["HomeTeam"],
                away_team=row["AwayTeam"],
                kickoff_time=kickoff_time,
                status=status,
                home_score=home_score,
                away_score=away_score,
                result=result,
                raw_payload=row,
            )

    def get_odds(self, match_source_id: str, market: str) -> Iterable[RawOddsSnapshot]:
        if market != "1X2":
            return

        for row in self._load_rows():
            row_match_id = _source_match_id(
                league=self.league,
                season=self.season,
                date=_parse_date(row["Date"]),
                home_team=row["HomeTeam"],
                away_team=row["AwayTeam"],
            )
            if row_match_id != match_source_id:
                continue

            for bookmaker, odds_columns in self._selected_bookmaker_columns():
                for selection, column_name in odds_columns.items():
                    odds_decimal = _optional_float(row.get(column_name))
                    if odds_decimal is None:
                        continue
                    yield RawOddsSnapshot(
                        source=self.source,
                        source_match_id=match_source_id,
                        bookmaker=bookmaker,
                        market=market,
                        selection=selection,
                        odds_decimal=odds_decimal,
                        snapshot_time=_parse_date(row["Date"]),
                        minutes_before_kickoff=0,
                        is_closing=True,
                        raw_payload={
                            "league": self.league,
                            "season": self.season,
                            "source_match_id": match_source_id,
                            "bookmaker": bookmaker,
                            "column": column_name,
                            "odds_decimal": odds_decimal,
                        },
                    )

    def get_result(self, match_source_id: str) -> RawResult | None:
        for match in self.get_matches():
            if match.source_match_id != match_source_id or match.status != "completed":
                continue
            if match.home_score is None or match.away_score is None or match.result is None:
                return None
            return RawResult(
                source=self.source,
                source_match_id=match_source_id,
                home_score=match.home_score,
                away_score=match.away_score,
                result=match.result,
                raw_payload=match.raw_payload,
            )
        return None

    def _selected_bookmaker_columns(self) -> list[tuple[str, dict[str, str]]]:
        if self.bookmaker == "ALL":
            return list(BOOKMAKER_ODDS_COLUMNS.items())
        if self.bookmaker not in BOOKMAKER_ODDS_COLUMNS:
            supported = ", ".join([*BOOKMAKER_ODDS_COLUMNS, "ALL"])
            raise ValueError(f"Unsupported bookmaker {self.bookmaker!r}. Supported: {supported}")
        return [(self.bookmaker, BOOKMAKER_ODDS_COLUMNS[self.bookmaker])]

    def _load_rows(self) -> list[dict[str, str]]:
        if self._rows is not None:
            return self._rows

        if self.path is not None:
            csv_text = self.path.read_text(encoding="utf-8-sig")
        elif self.url is not None:
            with urlopen(self.url, timeout=30) as response:
                csv_text = response.read().decode("utf-8-sig")
        else:
            csv_text = ""

        self._rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(csv_text.splitlines())
            if row
        ]
        return self._rows


def _parse_date(value: str) -> str:
    for date_format in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value.strip(), date_format).replace(
                hour=12,
                tzinfo=UTC,
            )
            return parsed.isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported Football-Data date: {value}")


def _optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _map_result(value: str | None) -> str:
    return {"H": "HOME", "D": "DRAW", "A": "AWAY"}.get(value or "", "UNKNOWN")


def _source_match_id(
    *,
    league: str,
    season: str,
    date: str,
    home_team: str,
    away_team: str,
) -> str:
    home_slug = _slug(home_team)
    away_slug = _slug(away_team)
    return f"{league}:{season}:{date[:10]}:{home_slug}:{away_slug}"


def _slug(value: str) -> str:
    return "-".join(value.strip().lower().replace("'", "").split())
