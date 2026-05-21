from dataclasses import dataclass

from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.repositories import DecisionLogRepository, MatchRepository, OddsSnapshotRepository
from app.normalizers.match_normalizer import normalize_match
from app.normalizers.odds_normalizer import normalize_odds_snapshot
from app.providers.sample_provider import SampleProvider


@dataclass(frozen=True)
class ImportSummary:
    items_read: int
    items_created: int
    items_updated: int
    items_skipped: int
    errors_count: int


class CollectionService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def import_sample_data(self) -> ImportSummary:
        provider = SampleProvider()
        items_read = 0
        items_created = 0
        items_skipped = 0
        errors_count = 0

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
                if existing_match is not None:
                    items_skipped += 1
                    log_repository.add(
                        match_id=existing_match.id,
                        stage="NORMALIZE_MATCH",
                        level="INFO",
                        message="Skipped existing sample match",
                    )
                    continue

                match = match_repository.add(**normalize_match(raw_match))
                items_created += 1
                log_repository.add(
                    match_id=match.id,
                    stage="NORMALIZE_MATCH",
                    level="INFO",
                    message="Imported sample match",
                    input_json=match.raw_payload_json,
                    output_json=f'{{"match_id":{match.id}}}',
                )

            for raw_match in matches:
                if raw_match.status != "scheduled":
                    continue
                match = match_repository.get_by_source_id(
                    raw_match.source,
                    raw_match.source_match_id,
                )
                if match is None:
                    errors_count += 1
                    log_repository.add(
                        stage="COLLECT_ODDS",
                        level="ERROR",
                        message=f"Missing match for odds import: {raw_match.source_match_id}",
                    )
                    continue

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
                        log_repository.add(
                            match_id=match.id,
                            stage="NORMALIZE_ODDS",
                            level="INFO",
                            message="Skipped existing sample odds snapshot",
                        )
                        continue

                    snapshot = odds_repository.add(
                        **normalize_odds_snapshot(raw_snapshot, match_id=match.id)
                    )
                    items_created += 1
                    log_repository.add(
                        match_id=match.id,
                        stage="NORMALIZE_ODDS",
                        level="INFO",
                        message="Imported sample odds snapshot",
                        input_json=snapshot.raw_payload_json,
                        output_json=f'{{"odds_snapshot_id":{snapshot.id}}}',
                    )

        return ImportSummary(
            items_read=items_read,
            items_created=items_created,
            items_updated=0,
            items_skipped=items_skipped,
            errors_count=errors_count,
        )
