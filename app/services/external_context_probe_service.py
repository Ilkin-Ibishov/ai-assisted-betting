import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import Engine

from app.core.team_aliases import canonical_team_key
from app.providers.api_football_provider import ApiFootballProvider, ApiFootballTeamCandidate
from app.services.feature_enrichment_audit_service import FeatureEnrichmentAuditService


@dataclass(frozen=True)
class ExternalContextProbeRequest:
    provider: str = "api-football"
    limit: int = 20
    minimum_history: int = 3
    history_sample_size: int = 5
    max_query_variants: int = 3
    max_history_candidates_per_team: int = 2
    minimum_history_candidate_score: float = 0.72


class ExternalContextProbeService:
    def __init__(
        self,
        engine: Engine,
        *,
        api_football_provider: ApiFootballProvider | None = None,
    ) -> None:
        self.engine = engine
        self.api_football_provider = api_football_provider

    def probe(self, request: ExternalContextProbeRequest) -> dict:
        if request.provider != "api-football":
            return {
                "provider": request.provider,
                "status": "unsupported_provider",
                "teams_read": 0,
                "matched_count": 0,
                "ambiguous_count": 0,
                "unmatched_count": 0,
                "teams": [],
            }
        if self.api_football_provider is None:
            return {
                "provider": request.provider,
                "status": "missing_credentials",
                "required_env": "API_FOOTBALL_KEY",
                "teams_read": 0,
                "matched_count": 0,
                "ambiguous_count": 0,
                "unmatched_count": 0,
                "teams": [],
            }

        audit = FeatureEnrichmentAuditService(self.engine).report(
            limit=request.limit,
            minimum_history=request.minimum_history,
        )
        teams = _unique_unmatched_teams(audit["unmatched_teams"], limit=request.limit)
        probed = [self._probe_team(team, request) for team in teams]
        return {
            "provider": request.provider,
            "status": "completed",
            "audit": {
                "scheduled_matches": audit["scheduled_matches"],
                "cold_start_candidates": audit["cold_start_candidates"],
                "unmatched_team_slots": audit["team_coverage"]["unmatched_team_slots"],
            },
            "teams_read": len(teams),
            "matched_count": sum(1 for team in probed if team["match_status"] == "matched"),
            "ambiguous_count": sum(1 for team in probed if team["match_status"] == "ambiguous"),
            "unmatched_count": sum(1 for team in probed if team["match_status"] == "unmatched"),
            "teams": probed,
        }

    def _probe_team(self, team: dict, request: ExternalContextProbeRequest) -> dict:
        query_variants = _query_variants(str(team["team"]))[: request.max_query_variants]
        candidates: list[dict] = []
        for query in query_variants:
            provider_candidates = self.api_football_provider.search_teams(query)
            candidates.extend(
                self._candidate_payload(candidate, query, team)
                for candidate in provider_candidates
                if candidate.provider_team_id
            )

        deduped = _dedupe_candidates(candidates)
        self._attach_history_counts(deduped, request)
        strong = [candidate for candidate in deduped if candidate["match_score"] >= 0.82]
        if len(strong) == 1:
            match_status = "matched"
        elif len(strong) > 1:
            match_status = "ambiguous"
        else:
            match_status = "unmatched"
        return {
            "team": team["team"],
            "league": team["league"],
            "source_match_id": team["source_match_id"],
            "query_variants": query_variants,
            "match_status": match_status,
            "top_candidates": deduped[:5],
        }

    def _candidate_payload(
        self,
        candidate: ApiFootballTeamCandidate,
        query: str,
        team: dict,
    ) -> dict:
        return {
            "provider_team_id": candidate.provider_team_id,
            "name": candidate.name,
            "country": candidate.country,
            "founded": candidate.founded,
            "venue_name": candidate.venue_name,
            "query": query,
            "match_score": _name_score(str(team["team"]), candidate.name),
            "recent_fixture_count": None,
            "has_minimum_history": None,
        }

    def _attach_history_counts(
        self,
        candidates: list[dict],
        request: ExternalContextProbeRequest,
    ) -> None:
        eligible = [
            candidate
            for candidate in candidates
            if float(candidate["match_score"]) >= request.minimum_history_candidate_score
        ][: max(0, request.max_history_candidates_per_team)]
        for candidate in eligible:
            fixture_count = self.api_football_provider.recent_fixture_count(
                team_id=int(candidate["provider_team_id"]),
                last=request.history_sample_size,
            )
            candidate["recent_fixture_count"] = fixture_count
            candidate["has_minimum_history"] = fixture_count >= request.minimum_history


def _unique_unmatched_teams(items: list[dict], *, limit: int) -> list[dict]:
    seen: set[tuple[str, str | None]] = set()
    teams = []
    for item in items:
        key = (canonical_team_key(str(item["team"])), item.get("league"))
        if key in seen:
            continue
        seen.add(key)
        teams.append(item)
        if len(teams) >= max(1, min(limit, 100)):
            break
    return teams


def _query_variants(team: str) -> list[str]:
    direct = " ".join(team.split())
    lower = direct.lower()
    replacements = {
        "yunayted": "united",
        "mayami": "miami",
        "filadelfiya": "philadelphia",
        "barselona": "barcelona",
        "kolo kolo": "colo colo",
        "kobresal": "cobresal",
        "kruz": "cruz",
        "braqantino": "bragantino",
        "krisiuma": "criciuma",
        "monarxs": "monarchs",
        "tayqers": "tigers",
        "illinden": "ilinden",
    }
    variants = [direct]
    replaced = lower
    for source, target in replacements.items():
        replaced = replaced.replace(source, target)
    title_replaced = " ".join(word.capitalize() for word in replaced.split())
    if title_replaced and canonical_team_key(title_replaced) != canonical_team_key(direct):
        variants.append(title_replaced)
    variants.extend(_noise_stripped_variants(direct))
    if title_replaced:
        variants.extend(_noise_stripped_variants(title_replaced))
    tokens = direct.split()
    if len(tokens) > 2:
        variants.append(" ".join(tokens[:2]))
    return _dedupe_strings(variants)


def _name_score(left: str, right: str) -> float:
    left_key = _score_key(left)
    right_key = _score_key(right)
    if left_key == right_key:
        return 1.0
    left_tokens = set(left_key.split())
    right_tokens = set(right_key.split())
    if not left_tokens or not right_tokens:
        return 0.0
    if left_key in right_key or right_key in left_key:
        return 0.9
    overlap = len(left_tokens & right_tokens)
    token_score = (2 * overlap) / (len(left_tokens) + len(right_tokens))
    sequence_score = SequenceMatcher(None, left_key, right_key).ratio()
    return round(max(token_score, sequence_score), 6)


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    by_id: dict[int, dict] = {}
    for candidate in candidates:
        provider_team_id = int(candidate["provider_team_id"])
        existing = by_id.get(provider_team_id)
        if existing is None or candidate["match_score"] > existing["match_score"]:
            by_id[provider_team_id] = candidate
    return sorted(
        by_id.values(),
        key=lambda item: (
            float(item["match_score"]),
            int(item["recent_fixture_count"] or 0),
        ),
        reverse=True,
    )


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for value in values:
        key = canonical_team_key(value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _score_key(team: str) -> str:
    replacements = {
        "illinden": "ilinden",
        "tayqers": "tigers",
        "monarxs": "monarchs",
    }
    key = canonical_team_key(team)
    for source, target in replacements.items():
        key = key.replace(source, target)
    drop_tokens = {"fc", "cf", "ac", "sc", "fk", "sk", "ii", "b"}
    tokens = [
        token
        for token in key.split()
        if token not in drop_tokens and not re.fullmatch(r"u\d+", token)
    ]
    return " ".join(tokens)


def _noise_stripped_variants(team: str) -> list[str]:
    tokens = team.split()
    variants = []
    prefix_tokens = {"fc", "cf", "ac", "sc", "fk", "sk", "jk"}
    if len(tokens) > 2 and tokens[0].lower().strip(".") in prefix_tokens:
        variants.append(" ".join(tokens[1:]))
    if len(tokens) > 2 and _is_age_suffix(tokens[-1]):
        variants.append(" ".join(tokens[:-1]))
    if len(tokens) > 2 and len(tokens[-1].strip(".")) == 1:
        variants.append(" ".join(tokens[:-1]))
    return variants


def _is_age_suffix(token: str) -> bool:
    return re.fullmatch(r"u\d+", token.lower().strip(".")) is not None
