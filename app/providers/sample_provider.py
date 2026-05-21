from collections.abc import Iterable
from datetime import datetime

from app.providers.base import MatchProvider, OddsProvider, ResultProvider
from app.schemas.match import RawMatch
from app.schemas.odds import RawOddsSnapshot
from app.schemas.result import RawResult


class SampleProvider(MatchProvider, OddsProvider, ResultProvider):
    source = "sample"
    bookmaker = "FictionalBook"
    league = "Sample Premier"
    season = "2026"

    _matches = [
        ("hist-001", "Northbridge FC", "Lakeside Town", "2026-04-01T18:00:00+00:00", 2, 1),
        ("hist-002", "Harbor Rovers", "Metro United", "2026-04-03T18:00:00+00:00", 0, 0),
        ("hist-003", "Forest City", "Eastport Athletic", "2026-04-05T18:00:00+00:00", 1, 3),
        ("hist-004", "Northbridge FC", "Harbor Rovers", "2026-04-10T18:00:00+00:00", 2, 2),
        ("hist-005", "Lakeside Town", "Forest City", "2026-04-12T18:00:00+00:00", 1, 0),
        ("hist-006", "Metro United", "Eastport Athletic", "2026-04-14T18:00:00+00:00", 3, 1),
        ("hist-007", "Harbor Rovers", "Forest City", "2026-04-18T18:00:00+00:00", 2, 0),
        ("hist-008", "Eastport Athletic", "Northbridge FC", "2026-04-20T18:00:00+00:00", 1, 1),
        ("upcoming-001", "Northbridge FC", "Metro United", "2026-05-19T18:00:00+00:00", None, None),
        ("upcoming-002", "Lakeside Town", "Harbor Rovers", "2026-05-20T18:00:00+00:00", None, None),
        (
            "upcoming-003",
            "Forest City",
            "Eastport Athletic",
            "2026-05-21T18:00:00+00:00",
            None,
            None,
        ),
    ]

    _odds = {
        "upcoming-001": {"HOME": 2.05, "DRAW": 3.25, "AWAY": 3.40},
        "upcoming-002": {"HOME": 2.45, "DRAW": 3.10, "AWAY": 2.80},
        "upcoming-003": {"HOME": 2.90, "DRAW": 3.30, "AWAY": 2.25},
    }

    def get_matches(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterable[RawMatch]:
        for (
            source_match_id,
            home_team,
            away_team,
            kickoff_time,
            home_score,
            away_score,
        ) in self._matches:
            status = (
                "completed"
                if home_score is not None and away_score is not None
                else "scheduled"
            )
            result = _result_from_score(home_score, away_score) if status == "completed" else None
            yield RawMatch(
                source=self.source,
                source_match_id=source_match_id,
                league=self.league,
                season=self.season,
                home_team=home_team,
                away_team=away_team,
                kickoff_time=kickoff_time,
                status=status,
                home_score=home_score,
                away_score=away_score,
                result=result,
                raw_payload={
                    "source_match_id": source_match_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_time": kickoff_time,
                    "home_score": home_score,
                    "away_score": away_score,
                },
            )

    def get_odds(self, match_source_id: str, market: str) -> Iterable[RawOddsSnapshot]:
        if market != "1X2":
            return

        for selection, odds_decimal in self._odds.get(match_source_id, {}).items():
            yield RawOddsSnapshot(
                source=self.source,
                source_match_id=match_source_id,
                bookmaker=self.bookmaker,
                market=market,
                selection=selection,
                odds_decimal=odds_decimal,
                snapshot_time="2026-05-18T12:00:00+00:00",
                minutes_before_kickoff=None,
                is_closing=False,
                raw_payload={
                    "source_match_id": match_source_id,
                    "bookmaker": self.bookmaker,
                    "market": market,
                    "selection": selection,
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
                raw_payload={
                    "source_match_id": match_source_id,
                    "home_score": match.home_score,
                    "away_score": match.away_score,
                    "result": match.result,
                },
            )
        return None


def _result_from_score(home_score: int | None, away_score: int | None) -> str:
    if home_score is None or away_score is None:
        return "UNKNOWN"
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"
