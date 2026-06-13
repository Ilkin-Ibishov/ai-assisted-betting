from datetime import UTC, datetime

from sqlalchemy import select

from app.core.team_aliases import TeamAliasResolver
from app.db.engine import session_scope
from app.db.models import Match


class FeatureEnrichmentAuditService:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.alias_resolver = TeamAliasResolver.from_json_file()

    def report(
        self,
        *,
        limit: int = 100,
        minimum_history: int = 3,
        now_iso: str | None = None,
        include_past: bool = False,
    ) -> dict:
        now = _parse_datetime(now_iso) if now_iso else datetime.now(UTC)
        with session_scope(self.engine) as session:
            scheduled_matches = list(
                session.scalars(
                    select(Match)
                    .where(Match.status == "scheduled")
                    .order_by(Match.kickoff_time.asc(), Match.id.asc())
                    .limit(max(1, min(limit, 500)))
                )
            )
            completed_matches = list(
                session.scalars(select(Match).where(Match.status == "completed"))
            )
        if not include_past:
            scheduled_matches = [
                match
                for match in scheduled_matches
                if (kickoff := _parse_datetime(match.kickoff_time)) is not None
                and kickoff >= now
            ]

        match_reports = [
            self._match_report(
                match,
                completed_matches=completed_matches,
                minimum_history=minimum_history,
            )
            for match in scheduled_matches
        ]
        unmatched_teams = [
            team
            for match_report in match_reports
            for team in (match_report["home"], match_report["away"])
            if not team["has_minimum_history"]
        ]
        return {
            "scheduled_matches": len(scheduled_matches),
            "audited_matches": len(match_reports),
            "minimum_history": minimum_history,
            "include_past": include_past,
            "now": now.isoformat(),
            "full_enriched_candidates": sum(
                1
                for match_report in match_reports
                if match_report["enrichment_tier"] == "full_enriched"
            ),
            "partial_enriched_candidates": sum(
                1
                for match_report in match_reports
                if match_report["enrichment_tier"] == "partial_enriched"
            ),
            "cold_start_candidates": sum(
                1
                for match_report in match_reports
                if match_report["enrichment_tier"] == "cold_start"
            ),
            "team_coverage": {
                "total_team_slots": len(match_reports) * 2,
                "matched_team_slots": (len(match_reports) * 2) - len(unmatched_teams),
                "unmatched_team_slots": len(unmatched_teams),
            },
            "unmatched_teams": unmatched_teams[:50],
            "matches": match_reports,
        }

    def _match_report(
        self,
        match: Match,
        *,
        completed_matches: list[Match],
        minimum_history: int,
    ) -> dict:
        home = self._team_report(
            match.home_team,
            match,
            side="home",
            completed_matches=completed_matches,
            minimum_history=minimum_history,
        )
        away = self._team_report(
            match.away_team,
            match,
            side="away",
            completed_matches=completed_matches,
            minimum_history=minimum_history,
        )
        minimum_side_history = min(home["history_count"], away["history_count"])
        if minimum_side_history >= minimum_history:
            enrichment_tier = "full_enriched"
        elif minimum_side_history > 0:
            enrichment_tier = "partial_enriched"
        else:
            enrichment_tier = "cold_start"
        return {
            "match_id": match.id,
            "source_match_id": match.source_match_id,
            "league": match.league,
            "kickoff_time": match.kickoff_time,
            "match_label": f"{match.home_team} vs {match.away_team}",
            "enrichment_tier": enrichment_tier,
            "home": home,
            "away": away,
        }

    def _team_report(
        self,
        team: str,
        match: Match,
        *,
        side: str,
        completed_matches: list[Match],
        minimum_history: int,
    ) -> dict:
        team_keys = self.alias_resolver.canonical_keys(team, league=match.league)
        history = [
            completed_match
            for completed_match in completed_matches
            if completed_match.kickoff_time < match.kickoff_time
            and (
                self.alias_resolver.canonical_keys(
                    completed_match.home_team,
                    league=completed_match.league,
                )
                & team_keys
                or self.alias_resolver.canonical_keys(
                    completed_match.away_team,
                    league=completed_match.league,
                )
                & team_keys
            )
        ]
        sources = sorted({completed_match.source for completed_match in history})
        return {
            "team": team,
            "side": side,
            "league": match.league,
            "source_match_id": match.source_match_id,
            "kickoff_time": match.kickoff_time,
            "canonical_keys": sorted(team_keys),
            "history_count": len(history),
            "has_minimum_history": len(history) >= minimum_history,
            "history_sources": sources,
        }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
