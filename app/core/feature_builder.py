from dataclasses import dataclass
from datetime import datetime

from app.core.team_aliases import TeamAliasResolver
from app.db.models import Match, OddsSnapshot


@dataclass(frozen=True)
class BuiltFeature:
    match_id: int
    market: str
    selection: str
    home_form_points_5: float
    away_form_points_5: float
    home_goals_for_avg_5: float
    away_goals_for_avg_5: float
    home_goals_against_avg_5: float
    away_goals_against_avg_5: float
    home_advantage_flag: int
    bookmaker_probability: float
    bookmaker_margin_estimate: float
    home_elo_rating: float
    away_elo_rating: float
    enrichment_tier: str
    feature_provenance: tuple[str, ...]
    home_rest_days: float | None
    away_rest_days: float | None
    home_goal_difference_trend_5: float
    away_goal_difference_trend_5: float
    odds_movement_velocity: float


class FeatureBuilder:
    def __init__(
        self,
        *,
        elo_initial_rating: float = 1500,
        elo_k_factor: float = 20,
        elo_home_advantage: float = 65,
        allow_cold_start_features: bool = False,
        team_alias_resolver: TeamAliasResolver | None = None,
    ) -> None:
        self.elo_initial_rating = elo_initial_rating
        self.elo_k_factor = elo_k_factor
        self.elo_home_advantage = elo_home_advantage
        self.allow_cold_start_features = allow_cold_start_features
        self.team_alias_resolver = team_alias_resolver or TeamAliasResolver.from_json_file()

    def build_for_match(
        self,
        *,
        match: Match,
        completed_matches: list[Match],
        odds_snapshots: list[OddsSnapshot],
    ) -> list[BuiltFeature]:
        home_history = _team_history(
            match.home_team,
            match.kickoff_time,
            completed_matches,
            league=match.league,
            alias_resolver=self.team_alias_resolver,
        )
        away_history = _team_history(
            match.away_team,
            match.kickoff_time,
            completed_matches,
            league=match.league,
            alias_resolver=self.team_alias_resolver,
        )
        if (
            not self.allow_cold_start_features
            and (len(home_history) < 3 or len(away_history) < 3)
        ):
            return []
        implied_sum = sum(snapshot.implied_probability for snapshot in odds_snapshots)
        if implied_sum <= 0:
            return []

        home_stats = _team_stats_or_neutral(
            match.home_team,
            home_history,
            league=match.league,
            alias_resolver=self.team_alias_resolver,
        )
        away_stats = _team_stats_or_neutral(
            match.away_team,
            away_history,
            league=match.league,
            alias_resolver=self.team_alias_resolver,
        )
        enrichment_tier = _enrichment_tier(home_history, away_history)
        feature_provenance = _feature_provenance(
            enrichment_tier,
            has_odds_movement=_has_odds_movement(odds_snapshots),
            has_external_football_data_context=_has_external_football_data_context(
                home_history,
                away_history,
            ),
        )
        ratings = _elo_ratings_before(
            match.kickoff_time,
            completed_matches,
            initial_rating=self.elo_initial_rating,
            k_factor=self.elo_k_factor,
            home_advantage=self.elo_home_advantage,
        )
        margin = implied_sum - 1

        return [
            BuiltFeature(
                match_id=match.id,
                market=snapshot.market,
                selection=snapshot.selection,
                home_form_points_5=home_stats.form_points,
                away_form_points_5=away_stats.form_points,
                home_goals_for_avg_5=home_stats.goals_for_avg,
                away_goals_for_avg_5=away_stats.goals_for_avg,
                home_goals_against_avg_5=home_stats.goals_against_avg,
                away_goals_against_avg_5=away_stats.goals_against_avg,
                home_advantage_flag=1,
                bookmaker_probability=round(snapshot.implied_probability / implied_sum, 6),
                bookmaker_margin_estimate=round(margin, 6),
                home_elo_rating=round(ratings.get(match.home_team, self.elo_initial_rating), 6),
                away_elo_rating=round(ratings.get(match.away_team, self.elo_initial_rating), 6),
                enrichment_tier=enrichment_tier,
                feature_provenance=feature_provenance,
                home_rest_days=_rest_days(match.kickoff_time, home_history),
                away_rest_days=_rest_days(match.kickoff_time, away_history),
                home_goal_difference_trend_5=home_stats.goal_difference_trend,
                away_goal_difference_trend_5=away_stats.goal_difference_trend,
                odds_movement_velocity=_odds_movement_velocity(snapshot, odds_snapshots),
            )
            for snapshot in odds_snapshots
        ]


@dataclass(frozen=True)
class _TeamStats:
    form_points: float
    goals_for_avg: float
    goals_against_avg: float
    goal_difference_trend: float


def _team_history(
    team: str,
    kickoff_time: str,
    completed_matches: list[Match],
    *,
    league: str | None,
    alias_resolver: TeamAliasResolver,
) -> list[Match]:
    team_keys = alias_resolver.canonical_keys(team, league=league)
    matches = [
        match
        for match in completed_matches
        if match.status == "completed"
        and match.kickoff_time < kickoff_time
        and (
            alias_resolver.canonical_keys(match.home_team, league=match.league) & team_keys
            or alias_resolver.canonical_keys(match.away_team, league=match.league) & team_keys
        )
    ]
    return sorted(matches, key=lambda match: match.kickoff_time, reverse=True)[:5]


def _team_stats(
    team: str,
    matches: list[Match],
    *,
    league: str | None,
    alias_resolver: TeamAliasResolver,
) -> _TeamStats:
    points = 0
    goals_for = 0
    goals_against = 0
    team_keys = alias_resolver.canonical_keys(team, league=league)
    for match in matches:
        if match.home_score is None or match.away_score is None:
            continue
        if alias_resolver.canonical_keys(match.home_team, league=match.league) & team_keys:
            team_score = match.home_score
            opponent_score = match.away_score
        elif alias_resolver.canonical_keys(match.away_team, league=match.league) & team_keys:
            team_score = match.away_score
            opponent_score = match.home_score
        else:
            continue

        goals_for += team_score
        goals_against += opponent_score
        if team_score > opponent_score:
            points += 3
        elif team_score == opponent_score:
            points += 1

    count = len(matches)
    return _TeamStats(
        form_points=round(points / count, 6),
        goals_for_avg=round(goals_for / count, 6),
        goals_against_avg=round(goals_against / count, 6),
        goal_difference_trend=round((goals_for - goals_against) / count, 6),
    )


def _team_stats_or_neutral(
    team: str,
    matches: list[Match],
    *,
    league: str | None,
    alias_resolver: TeamAliasResolver,
) -> _TeamStats:
    if len(matches) < 3:
        return _TeamStats(
            form_points=0.0,
            goals_for_avg=0.0,
            goals_against_avg=0.0,
            goal_difference_trend=0.0,
        )
    return _team_stats(team, matches, league=league, alias_resolver=alias_resolver)


def _enrichment_tier(home_history: list[Match], away_history: list[Match]) -> str:
    minimum_history = min(len(home_history), len(away_history))
    if minimum_history >= 3:
        return "full_enriched"
    if minimum_history > 0:
        return "partial_enriched"
    return "cold_start"


def _feature_provenance(
    enrichment_tier: str,
    *,
    has_odds_movement: bool,
    has_external_football_data_context: bool,
) -> tuple[str, ...]:
    labels = ["market_overround_normalized"]
    if enrichment_tier == "cold_start":
        labels.append("cold_start_history")
    else:
        labels.extend(["recent_form", "home_away_split", "rest_days", "goal_difference_trend"])
    if has_external_football_data_context:
        labels.append("external_context:football_data_csv")
    if has_odds_movement:
        labels.append("odds_movement_velocity")
    if enrichment_tier == "full_enriched":
        labels.append("elo_rating")
    return tuple(labels)


def _has_external_football_data_context(
    home_history: list[Match],
    away_history: list[Match],
) -> bool:
    return any(
        match.source == "football_data" for match in [*home_history, *away_history]
    )


def _rest_days(kickoff_time: str, history: list[Match]) -> float | None:
    if not history:
        return None
    kickoff = _parse_datetime(kickoff_time)
    previous = _parse_datetime(history[0].kickoff_time)
    return round((kickoff - previous).total_seconds() / 86400, 6)


def _has_odds_movement(odds_snapshots: list[OddsSnapshot]) -> bool:
    selections = {snapshot.selection for snapshot in odds_snapshots}
    return any(
        len([snapshot for snapshot in odds_snapshots if snapshot.selection == selection]) > 1
        for selection in selections
    )


def _odds_movement_velocity(
    current_snapshot: OddsSnapshot,
    odds_snapshots: list[OddsSnapshot],
) -> float:
    selection_snapshots = sorted(
        [
            snapshot
            for snapshot in odds_snapshots
            if snapshot.selection == current_snapshot.selection
        ],
        key=lambda snapshot: snapshot.snapshot_time,
    )
    if len(selection_snapshots) < 2:
        return 0.0
    first = selection_snapshots[0]
    last = selection_snapshots[-1]
    elapsed_hours = (
        _parse_datetime(last.snapshot_time) - _parse_datetime(first.snapshot_time)
    ).total_seconds() / 3600
    if elapsed_hours <= 0:
        return 0.0
    return round((last.odds_decimal - first.odds_decimal) / elapsed_hours, 6)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _elo_ratings_before(
    kickoff_time: str,
    completed_matches: list[Match],
    *,
    initial_rating: float,
    k_factor: float,
    home_advantage: float,
) -> dict[str, float]:
    ratings: dict[str, float] = {}
    prior_matches = sorted(
        [
            match
            for match in completed_matches
            if match.status == "completed"
            and match.kickoff_time < kickoff_time
            and match.home_score is not None
            and match.away_score is not None
        ],
        key=lambda match: match.kickoff_time,
    )
    for match in prior_matches:
        home_rating = ratings.get(match.home_team, initial_rating)
        away_rating = ratings.get(match.away_team, initial_rating)
        expected_home = 1 / (
            1 + 10 ** (-((home_rating + home_advantage) - away_rating) / 400)
        )
        actual_home = _actual_home_score(match.home_score, match.away_score)
        change = k_factor * (actual_home - expected_home)
        ratings[match.home_team] = home_rating + change
        ratings[match.away_team] = away_rating - change
    return ratings


def _actual_home_score(home_score: int, away_score: int) -> float:
    if home_score > away_score:
        return 1.0
    if home_score == away_score:
        return 0.5
    return 0.0
