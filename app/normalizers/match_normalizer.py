import json

from app.schemas.match import RawMatch


def normalize_match(raw_match: RawMatch) -> dict[str, object]:
    return {
        "source": raw_match.source,
        "source_match_id": raw_match.source_match_id,
        "league": raw_match.league,
        "season": raw_match.season,
        "home_team": raw_match.home_team.strip(),
        "away_team": raw_match.away_team.strip(),
        "kickoff_time": raw_match.kickoff_time,
        "status": raw_match.status,
        "home_score": raw_match.home_score,
        "away_score": raw_match.away_score,
        "result": raw_match.result,
        "raw_payload_json": json.dumps(raw_match.raw_payload, sort_keys=True),
    }

