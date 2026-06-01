from dataclasses import dataclass

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


class FeatureBuilder:
    def __init__(
        self,
        *,
        elo_initial_rating: float = 1500,
        elo_k_factor: float = 20,
        elo_home_advantage: float = 65,
        allow_cold_start_features: bool = False,
    ) -> None:
        self.elo_initial_rating = elo_initial_rating
        self.elo_k_factor = elo_k_factor
        self.elo_home_advantage = elo_home_advantage
        self.allow_cold_start_features = allow_cold_start_features

    def build_for_match(
        self,
        *,
        match: Match,
        completed_matches: list[Match],
        odds_snapshots: list[OddsSnapshot],
    ) -> list[BuiltFeature]:
        home_history = _team_history(match.home_team, match.kickoff_time, completed_matches)
        away_history = _team_history(match.away_team, match.kickoff_time, completed_matches)
        if (
            not self.allow_cold_start_features
            and (len(home_history) < 3 or len(away_history) < 3)
        ):
            return []
        implied_sum = sum(snapshot.implied_probability for snapshot in odds_snapshots)
        if implied_sum <= 0:
            return []

        home_stats = _team_stats_or_neutral(match.home_team, home_history)
        away_stats = _team_stats_or_neutral(match.away_team, away_history)
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
            )
            for snapshot in odds_snapshots
        ]


@dataclass(frozen=True)
class _TeamStats:
    form_points: float
    goals_for_avg: float
    goals_against_avg: float


def _team_history(team: str, kickoff_time: str, completed_matches: list[Match]) -> list[Match]:
    matches = [
        match
        for match in completed_matches
        if match.status == "completed"
        and match.kickoff_time < kickoff_time
        and (match.home_team == team or match.away_team == team)
    ]
    return sorted(matches, key=lambda match: match.kickoff_time, reverse=True)[:5]


def _team_stats(team: str, matches: list[Match]) -> _TeamStats:
    points = 0
    goals_for = 0
    goals_against = 0
    for match in matches:
        if match.home_score is None or match.away_score is None:
            continue
        if match.home_team == team:
            team_score = match.home_score
            opponent_score = match.away_score
        else:
            team_score = match.away_score
            opponent_score = match.home_score

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
    )


def _team_stats_or_neutral(team: str, matches: list[Match]) -> _TeamStats:
    if len(matches) < 3:
        return _TeamStats(
            form_points=0.0,
            goals_for_avg=0.0,
            goals_against_avg=0.0,
        )
    return _team_stats(team, matches)


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
