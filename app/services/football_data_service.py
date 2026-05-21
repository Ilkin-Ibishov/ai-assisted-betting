from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.repositories import DecisionLogRepository, MatchRepository, OddsSnapshotRepository
from app.normalizers.match_normalizer import normalize_match
from app.normalizers.odds_normalizer import normalize_odds_snapshot
from app.providers.football_data_provider import FootballDataCsvProvider
from app.services.prediction_service import StepSummary


@dataclass(frozen=True)
class FootballDataImportRequest:
    league: str
    season: str
    bookmaker: str = "B365"
    path: Path | None = None
    url: str | None = None


class FootballDataImportService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def import_csv(self, request: FootballDataImportRequest) -> StepSummary:
        provider = (
            FootballDataCsvProvider.from_league_season(
                league=request.league,
                season=request.season,
                bookmaker=request.bookmaker,
            )
            if request.path is None and request.url is None
            else FootballDataCsvProvider(
                league=request.league,
                season=request.season,
                bookmaker=request.bookmaker,
                path=request.path,
                url=request.url,
            )
        )
        items_read = 0
        items_created = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            match_repository = MatchRepository(session)
            odds_repository = OddsSnapshotRepository(session)
            log_repository = DecisionLogRepository(session)

            matches = list(provider.get_matches())
            for raw_match in matches:
                items_read += 1
                existing_match = match_repository.get_by_source_id(
                    raw_match.source,
                    raw_match.source_match_id,
                )
                if existing_match is None:
                    match = match_repository.add(**normalize_match(raw_match))
                    items_created += 1
                    log_repository.add(
                        match_id=match.id,
                        stage="NORMALIZE_MATCH",
                        level="INFO",
                        message="Imported Football-Data match",
                        input_json=match.raw_payload_json,
                    )
                else:
                    match = existing_match
                    items_skipped += 1

                for raw_snapshot in provider.get_odds(raw_match.source_match_id, "1X2"):
                    items_read += 1
                    if odds_repository.exists_snapshot(
                        match_id=match.id,
                        source=raw_snapshot.source,
                        bookmaker=raw_snapshot.bookmaker,
                        market=raw_snapshot.market,
                        selection=raw_snapshot.selection,
                        snapshot_time=raw_snapshot.snapshot_time,
                    ):
                        items_skipped += 1
                        continue
                    snapshot = odds_repository.add(
                        **normalize_odds_snapshot(raw_snapshot, match_id=match.id)
                    )
                    items_created += 1
                    log_repository.add(
                        match_id=match.id,
                        stage="NORMALIZE_ODDS",
                        level="INFO",
                        message="Imported Football-Data odds snapshot",
                        input_json=snapshot.raw_payload_json,
                    )

        return StepSummary(
            items_read=items_read,
            items_created=items_created,
            items_updated=0,
            items_skipped=items_skipped,
            errors_count=0,
        )
