from app.core.evaluator import Evaluator, SettledBetForEvaluation
from app.core.result_settler import ResultSettler


def test_result_settler_settles_1x2_and_over_under_markets() -> None:
    settler = ResultSettler()

    home_win = settler.settle(
        market="1X2",
        selection="HOME",
        odds_taken=2.2,
        stake_units=1.0,
        home_score=2,
        away_score=1,
    )
    draw_loss = settler.settle(
        market="1X2",
        selection="DRAW",
        odds_taken=3.1,
        stake_units=1.0,
        home_score=2,
        away_score=1,
    )
    over_win = settler.settle(
        market="OVER_UNDER_2_5",
        selection="OVER_2_5",
        odds_taken=1.9,
        stake_units=1.0,
        home_score=2,
        away_score=1,
    )

    assert home_win.status == "won"
    assert home_win.profit_loss_units == 1.2
    assert draw_loss.status == "lost"
    assert draw_loss.profit_loss_units == -1.0
    assert over_win.status == "won"
    assert over_win.profit_loss_units == 0.9


def test_evaluator_calculates_core_metrics_for_settled_bets() -> None:
    report = Evaluator().evaluate(
        [
            SettledBetForEvaluation(
                status="won",
                stake_units=1.0,
                odds_taken=2.2,
                profit_loss_units=1.2,
                edge=0.08,
                model_probability=0.55,
            ),
            SettledBetForEvaluation(
                status="lost",
                stake_units=1.0,
                odds_taken=2.0,
                profit_loss_units=-1.0,
                edge=0.04,
                model_probability=0.48,
            ),
        ]
    )

    assert report.total_bets == 2
    assert report.settled_bets == 2
    assert report.wins == 1
    assert report.losses == 1
    assert report.profit_loss_units == 0.2
    assert report.roi == 0.1
    assert report.hit_rate == 0.5
    assert report.average_odds == 2.1
    assert report.average_edge == 0.06


def test_evaluator_includes_probability_odds_and_edge_buckets() -> None:
    report = Evaluator().evaluate(
        [
            SettledBetForEvaluation(
                status="won",
                stake_units=1.0,
                odds_taken=2.2,
                profit_loss_units=1.2,
                edge=0.08,
                model_probability=0.55,
            ),
            SettledBetForEvaluation(
                status="lost",
                stake_units=1.0,
                odds_taken=3.2,
                profit_loss_units=-1.0,
                edge=0.03,
                model_probability=0.35,
            ),
        ]
    )

    assert report.probability_buckets["0.50-0.60"]["bets"] == 1
    assert report.probability_buckets["0.30-0.40"]["losses"] == 1
    assert report.odds_buckets["2.01-2.50"]["wins"] == 1
    assert report.odds_buckets["3.01-3.50"]["losses"] == 1
    assert report.edge_buckets["0.08+"]["wins"] == 1
    assert report.edge_buckets["0.02-0.04"]["losses"] == 1
