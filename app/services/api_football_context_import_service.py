import json
from dataclasses import dataclass

from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.repositories import DecisionLogRepository, MatchRepository
from app.providers.api_football_provider import ApiFootballFixture, ApiFootballProvider
from app.services.external_context_probe_service import (
    ExternalContextProbeRequest,
    ExternalContextProbeService,
)

API_FOOTBALL_CONTEXT_SOURCE = "api_football_context"


@dataclass(frozen=True)
class ApiFootballContextImportRequest:
    limit: int = 5
    minimum_history: int = 3
    history_sample_size: int = 5
    max_query_variants: int = 3
    dry_run: bool = True


class ApiFootballContextImportService:
    def __init__(
        self,
        engine: Engine,
        *,
        api_football_provider: ApiFootballProvider | None = None,
    ) -> None:
        self.engine = engine
        self.api_football_provider = api_football_provider

    def import_verified_history(self, request: ApiFootballContextImportRequest) -> dict:
        if self.api_football_provider is None:
            return {
                "provider": "api-football",
                "status": "missing_credentials",
                "required_env": "API_FOOTBALL_KEY",
                "dry_run": request.dry_run,
                "teams_read": 0,
                "teams_importable": 0,
                "items_read": 0,
                "items_created": 0,
                "items_skipped": 0,
                "errors_count": 0,
                "teams": [],
            }

        probe = ExternalContextProbeService(
            self.engine,
            api_football_provider=self.api_football_provider,
        ).probe(
            ExternalContextProbeRequest(
                limit=request.limit,
                minimum_history=request.minimum_history,
                history_sample_size=request.history_sample_size,
                max_query_variants=request.max_query_variants,
            )
        )
        importable_teams = [
            team for team in probe["teams"] if team["match_status"] == "matched"
        ]
        team_reports = [
            self._team_import_report(team, request)
            for team in importable_teams
        ]
        return {
            "provider": "api-football",
            "status": "completed",
            "dry_run": request.dry_run,
            "probe": {
                "teams_read": probe["teams_read"],
                "matched_count": probe["matched_count"],
                "ambiguous_count": probe["ambiguous_count"],
                "insufficient_history_count": probe["insufficient_history_count"],
                "unmatched_count": probe["unmatched_count"],
            },
            "teams_read": probe["teams_read"],
            "teams_importable": len(importable_teams),
            "items_read": sum(report["items_read"] for report in team_reports),
            "items_created": sum(report["items_created"] for report in team_reports),
            "items_skipped": sum(report["items_skipped"] for report in team_reports),
            "errors_count": 0,
            "teams": team_reports,
        }

    def _team_import_report(
        self,
        team: dict,
        request: ApiFootballContextImportRequest,
    ) -> dict:
        candidate = next(
            item
            for item in team["top_candidates"]
            if item["has_minimum_history"] is True
        )
        fixtures = self.api_football_provider.recent_completed_fixtures(
            team_id=int(candidate["provider_team_id"]),
            last=request.history_sample_size,
        )
        imported = []
        skipped = []
        if request.dry_run:
            return {
                "team": team["team"],
                "provider_team_id": candidate["provider_team_id"],
                "provider_team_name": candidate["name"],
                "items_read": len(fixtures),
                "items_created": 0,
                "items_skipped": len(fixtures),
                "fixtures": [
                    _fixture_payload(
                        fixture,
                        focal_provider_team_id=int(candidate["provider_team_id"]),
                        focal_misli_team=str(team["team"]),
                    )
                    for fixture in fixtures
                ],
            }

        with session_scope(self.engine) as session:
            match_repository = MatchRepository(session)
            log_repository = DecisionLogRepository(session)
            for fixture in fixtures:
                source_match_id = _source_match_id(fixture)
                if match_repository.get_by_source_id(
                    API_FOOTBALL_CONTEXT_SOURCE,
                    source_match_id,
                ):
                    skipped.append(source_match_id)
                    continue
                payload = _fixture_payload(
                    fixture,
                    focal_provider_team_id=int(candidate["provider_team_id"]),
                    focal_misli_team=str(team["team"]),
                )
                match = match_repository.add(
                    source=API_FOOTBALL_CONTEXT_SOURCE,
                    source_match_id=source_match_id,
                    league=fixture.league_name or str(team["league"]),
                    season=str(fixture.league_season) if fixture.league_season else None,
                    home_team=str(payload["home_team"]),
                    away_team=str(payload["away_team"]),
                    kickoff_time=fixture.kickoff_time,
                    status="completed",
                    home_score=fixture.home_score,
                    away_score=fixture.away_score,
                    result=_result_from_score(fixture.home_score, fixture.away_score),
                    raw_payload_json=json.dumps(payload, sort_keys=True),
                )
                log_repository.add(
                    match_id=match.id,
                    stage="API_FOOTBALL_CONTEXT_IMPORT",
                    level="INFO",
                    message="Imported verified API-Football context fixture",
                    input_json=match.raw_payload_json,
                )
                imported.append(source_match_id)

        return {
            "team": team["team"],
            "provider_team_id": candidate["provider_team_id"],
            "provider_team_name": candidate["name"],
            "items_read": len(fixtures),
            "items_created": len(imported),
            "items_skipped": len(skipped),
            "imported_source_match_ids": imported,
            "skipped_source_match_ids": skipped,
        }


def _fixture_payload(
    fixture: ApiFootballFixture,
    *,
    focal_provider_team_id: int,
    focal_misli_team: str,
) -> dict:
    home_team = fixture.home_team
    away_team = fixture.away_team
    if fixture.home_team_id == focal_provider_team_id:
        home_team = focal_misli_team
    elif fixture.away_team_id == focal_provider_team_id:
        away_team = focal_misli_team
    return {
        "provider": "api-football",
        "provider_fixture_id": fixture.provider_fixture_id,
        "provider_home_team_id": fixture.home_team_id,
        "provider_away_team_id": fixture.away_team_id,
        "provider_home_team": fixture.home_team,
        "provider_away_team": fixture.away_team,
        "focal_provider_team_id": focal_provider_team_id,
        "focal_misli_team": focal_misli_team,
        "home_team": home_team,
        "away_team": away_team,
        "home_score": fixture.home_score,
        "away_score": fixture.away_score,
        "status_short": fixture.status_short,
        "raw": fixture.raw_payload,
    }


def _source_match_id(fixture: ApiFootballFixture) -> str:
    return f"api-football:fixture:{fixture.provider_fixture_id}"


def _result_from_score(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"
