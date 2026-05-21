from pathlib import Path

from app.providers.football_data_provider import FootballDataCsvProvider


def test_football_data_csv_provider_parses_matches_results_and_odds(tmp_path: Path) -> None:
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,15/08/25,Liverpool,Bournemouth,4,2,H,1.40,5.00,7.50",
                "E0,16/08/25,Aston Villa,Newcastle,,,,2.30,3.40,3.10",
            ]
        ),
        encoding="utf-8",
    )

    provider = FootballDataCsvProvider(path=csv_path, league="E0", season="2526")
    matches = list(provider.get_matches())
    odds = [
        snapshot
        for match in matches
        for snapshot in provider.get_odds(match.source_match_id, "1X2")
    ]
    result = provider.get_result(matches[0].source_match_id)

    assert len(matches) == 2
    assert matches[0].status == "completed"
    assert matches[0].result == "HOME"
    assert matches[1].status == "scheduled"
    assert len(odds) == 6
    assert result is not None
    assert result.home_score == 4
    assert {snapshot.bookmaker for snapshot in odds} == {"B365"}
    assert {snapshot.selection for snapshot in odds} == {"HOME", "DRAW", "AWAY"}


def test_football_data_csv_provider_can_import_all_supported_bookmakers(tmp_path: Path) -> None:
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                (
                    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
                    "B365H,B365D,B365A,BWH,BWD,BWA,AvgH,AvgD,AvgA"
                ),
                (
                    "E0,15/08/25,Liverpool,Bournemouth,4,2,H,"
                    "1.40,5.00,7.50,1.44,4.80,7.20,1.42,4.90,7.35"
                ),
            ]
        ),
        encoding="utf-8",
    )

    provider = FootballDataCsvProvider(
        path=csv_path,
        league="E0",
        season="2526",
        bookmaker="ALL",
    )
    match = next(iter(provider.get_matches()))
    odds = list(provider.get_odds(match.source_match_id, "1X2"))

    assert len(odds) == 9
    assert {snapshot.bookmaker for snapshot in odds} == {"B365", "BW", "Avg"}


def test_football_data_csv_provider_filters_selected_bookmaker(tmp_path: Path) -> None:
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A,AvgH,AvgD,AvgA",
                "E0,15/08/25,Liverpool,Bournemouth,4,2,H,1.40,5.00,7.50,1.42,4.90,7.35",
            ]
        ),
        encoding="utf-8",
    )

    provider = FootballDataCsvProvider(
        path=csv_path,
        league="E0",
        season="2526",
        bookmaker="Avg",
    )
    match = next(iter(provider.get_matches()))
    odds = list(provider.get_odds(match.source_match_id, "1X2"))

    assert len(odds) == 3
    assert {snapshot.bookmaker for snapshot in odds} == {"Avg"}
