from dataclasses import dataclass


@dataclass(frozen=True)
class SettlementResult:
    status: str
    profit_loss_units: float


class ResultSettler:
    def settle(
        self,
        *,
        market: str,
        selection: str,
        odds_taken: float,
        stake_units: float,
        home_score: int,
        away_score: int,
    ) -> SettlementResult:
        won = self._is_winning_selection(
            market=market,
            selection=selection,
            home_score=home_score,
            away_score=away_score,
        )
        if won:
            profit_loss_units = stake_units * (odds_taken - 1)
            return SettlementResult("won", round(profit_loss_units, 6))
        return SettlementResult("lost", -stake_units)

    def _is_winning_selection(
        self,
        *,
        market: str,
        selection: str,
        home_score: int,
        away_score: int,
    ) -> bool:
        if market == "1X2":
            if selection == "HOME":
                return home_score > away_score
            if selection == "DRAW":
                return home_score == away_score
            if selection == "AWAY":
                return away_score > home_score
        if market == "OVER_UNDER_2_5":
            total_goals = home_score + away_score
            if selection == "OVER_2_5":
                return total_goals > 2.5
            if selection == "UNDER_2_5":
                return total_goals < 2.5
        raise ValueError(f"unsupported market/selection: {market}/{selection}")

