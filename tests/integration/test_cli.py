import json
from pathlib import Path

from sqlalchemy import create_engine, text
from typer.testing import CliRunner

from app.cli import app


def test_cli_help_lists_mvp_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "init-db" in result.output
    assert "import-sample-data" in result.output
    assert "settle-results" in result.output


def test_init_db_command_creates_configured_sqlite_database(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "cli.sqlite"

    result = runner.invoke(app, ["init-db"], env={"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"})

    assert result.exit_code == 0
    assert db_path.exists()
    assert "init-db: created tables" in result.output


def test_import_sample_data_command_populates_database_idempotently(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "sample.sqlite"
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    init_result = runner.invoke(app, ["init-db"], env=env)
    first_import = runner.invoke(app, ["import-sample-data"], env=env)
    second_import = runner.invoke(app, ["import-sample-data"], env=env)

    assert init_result.exit_code == 0
    assert first_import.exit_code == 0
    assert second_import.exit_code == 0
    assert "items_read=20" in first_import.output
    assert "items_created=20" in first_import.output
    assert "items_created=0" in second_import.output
    assert "items_skipped=20" in second_import.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        matches_count = connection.execute(text("SELECT count(*) FROM matches")).scalar_one()
        odds_count = connection.execute(text("SELECT count(*) FROM odds_snapshots")).scalar_one()
        logs_count = connection.execute(text("SELECT count(*) FROM decision_logs")).scalar_one()

    assert matches_count == 11
    assert odds_count == 9
    assert logs_count >= 20


def test_core_engine_commands_create_features_predictions_and_paper_bets_idempotently(
    tmp_path,
) -> None:
    runner = CliRunner()
    db_path = tmp_path / "core.sqlite"
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.02",
    }

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    assert runner.invoke(app, ["import-sample-data"], env=env).exit_code == 0
    features_result = runner.invoke(app, ["generate-features"], env=env)
    predictions_result = runner.invoke(app, ["generate-predictions"], env=env)
    first_bets_result = runner.invoke(app, ["write-paper-bets"], env=env)
    second_bets_result = runner.invoke(app, ["write-paper-bets"], env=env)

    assert features_result.exit_code == 0
    assert predictions_result.exit_code == 0
    assert first_bets_result.exit_code == 0
    assert second_bets_result.exit_code == 0
    assert "items_created=3" in features_result.output
    assert "items_created=3" in predictions_result.output
    assert "items_created=1" in first_bets_result.output
    assert "items_created=0" in second_bets_result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        features_count = connection.execute(text("SELECT count(*) FROM features")).scalar_one()
        predictions_count = connection.execute(
            text("SELECT count(*) FROM predictions")
        ).scalar_one()
        paper_bets_count = connection.execute(text("SELECT count(*) FROM paper_bets")).scalar_one()

    assert features_count == 3
    assert predictions_count == 3
    assert paper_bets_count == 1


def test_settlement_and_evaluation_commands_complete_sample_pipeline(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "full.sqlite"
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.02",
    }

    for command in [
        "init-db",
        "import-sample-data",
        "generate-features",
        "generate-predictions",
        "write-paper-bets",
    ]:
        assert runner.invoke(app, [command], env=env).exit_code == 0

    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        match_id = connection.execute(text("SELECT match_id FROM paper_bets LIMIT 1")).scalar_one()
        connection.execute(
            text(
                "UPDATE matches SET status='completed', home_score=2, away_score=1, result='HOME' "
                "WHERE id=:match_id"
            ),
            {"match_id": match_id},
        )

    settlement_result = runner.invoke(app, ["settle-results"], env=env)
    evaluation_result = runner.invoke(app, ["evaluate"], env=env)

    assert settlement_result.exit_code == 0
    assert evaluation_result.exit_code == 0
    assert "items_created=0" in settlement_result.output
    assert "items_updated=1" in settlement_result.output
    assert "Evaluation Run" in evaluation_result.output
    assert "Total bets: 1" in evaluation_result.output

    with engine.connect() as connection:
        settled_count = connection.execute(
            text("SELECT count(*) FROM paper_bets WHERE status in ('won', 'lost', 'void')")
        ).scalar_one()
        evaluation_count = connection.execute(
            text("SELECT count(*) FROM evaluation_runs")
        ).scalar_one()

    assert settled_count == 1
    assert evaluation_count == 1


def test_import_football_data_command_imports_csv_idempotently(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "football_data.sqlite"
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,15/08/25,Liverpool,Bournemouth,4,2,H,1.40,5.00,7.50",
            ]
        ),
        encoding="utf-8",
    )
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    first_result = runner.invoke(
        app,
        [
            "import-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
        ],
        env=env,
    )
    second_result = runner.invoke(
        app,
        [
            "import-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
        ],
        env=env,
    )

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "items_created=4" in first_result.output
    assert "items_created=0" in second_result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        matches_count = connection.execute(text("SELECT count(*) FROM matches")).scalar_one()
        odds_count = connection.execute(text("SELECT count(*) FROM odds_snapshots")).scalar_one()

    assert matches_count == 1
    assert odds_count == 3


def test_import_football_data_command_supports_all_bookmakers(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "football_data_all.sqlite"
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
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    result = runner.invoke(
        app,
        [
            "import-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--bookmaker",
            "ALL",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "items_created=10" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        odds_count = connection.execute(text("SELECT count(*) FROM odds_snapshots")).scalar_one()
        bookmaker_count = connection.execute(
            text("SELECT count(distinct bookmaker) FROM odds_snapshots")
        ).scalar_one()

    assert odds_count == 9
    assert bookmaker_count == 3


def test_manual_live_collection_commands_import_valid_misli_snapshot(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "live.sqlite"
    snapshot_path = tmp_path / "misli.json"
    snapshot_path.write_text(json.dumps(_valid_misli_snapshot()), encoding="utf-8")
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    matches_result = runner.invoke(
        app,
        [
            "collect-matches",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
        ],
        env=env,
    )
    odds_result = runner.invoke(
        app,
        [
            "collect-odds",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
        ],
        env=env,
    )

    assert matches_result.exit_code == 0
    assert odds_result.exit_code == 0
    assert "items_created=1" in matches_result.output
    assert "items_created=3" in odds_result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        matches_count = connection.execute(text("SELECT count(*) FROM matches")).scalar_one()
        odds_count = connection.execute(text("SELECT count(*) FROM odds_snapshots")).scalar_one()
        live_run_count = connection.execute(text("SELECT count(*) FROM live_runs")).scalar_one()

    assert matches_count == 1
    assert odds_count == 3
    assert live_run_count == 2


def test_manual_live_collection_command_records_misli_validation_errors(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "live-invalid.sqlite"
    snapshot = _valid_misli_snapshot()
    snapshot["events"][0]["kickoff_date"] = ""
    snapshot_path = tmp_path / "misli-invalid.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    result = runner.invoke(
        app,
        [
            "collect-matches",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "items_created=0" in result.output
    assert "errors_count=1" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        matches_count = connection.execute(text("SELECT count(*) FROM matches")).scalar_one()
        live_run = connection.execute(
            text("SELECT status, error_summary FROM live_runs LIMIT 1")
        ).fetchone()

    assert matches_count == 0
    assert live_run is not None
    assert live_run[0] == "failed"
    assert "full kickoff date" in live_run[1]


def test_run_live_paper_cycle_command_is_idempotent(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "live-cycle.sqlite"
    snapshot = _valid_misli_snapshot()
    snapshot["events"][0]["home_team"] = "Forest City"
    snapshot["events"][0]["away_team"] = "Eastport Athletic"
    snapshot["events"][0]["league"] = "Sample Premier"
    snapshot_path = tmp_path / "misli-cycle.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    assert runner.invoke(app, ["import-sample-data"], env=env).exit_code == 0
    first_result = runner.invoke(
        app,
        [
            "run-live-paper-cycle",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
            "--model",
            "baseline_heuristic",
        ],
        env=env,
    )
    second_result = runner.invoke(
        app,
        [
            "run-live-paper-cycle",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
            "--model",
            "baseline_heuristic",
        ],
        env=env,
    )

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "collect_matches.items_created=1" in first_result.output
    assert "collect_odds.items_created=3" in first_result.output
    assert "write_paper_bets.items_created=" in first_result.output
    assert "write_paper_bets.items_created=0" in second_result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        cycle_run_count = connection.execute(
            text("SELECT count(*) FROM live_runs WHERE run_type='run_live_paper_cycle'")
        ).scalar_one()
        paper_bets_count = connection.execute(text("SELECT count(*) FROM paper_bets")).scalar_one()

    assert cycle_run_count == 1
    assert paper_bets_count > 0


def test_run_scheduled_paper_worker_command_records_worker_run(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "scheduled-worker.sqlite"
    snapshot = _valid_misli_snapshot()
    snapshot["events"][0]["home_team"] = "Forest City"
    snapshot["events"][0]["away_team"] = "Eastport Athletic"
    snapshot["events"][0]["league"] = "Sample Premier"
    snapshot_path = tmp_path / "misli-worker.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "LIVE_COLLECTION_ENABLED": "true",
        "MIN_EDGE": "0.01",
    }

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    assert runner.invoke(app, ["import-sample-data"], env=env).exit_code == 0
    result = runner.invoke(
        app,
        [
            "run-scheduled-paper-worker",
            "--provider",
            "misli-public",
            "--snapshot",
            str(snapshot_path),
            "--model",
            "baseline_heuristic",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "run-scheduled-paper-worker: started" in result.output
    assert "status=completed" in result.output
    assert "cycle.status=completed" in result.output
    assert "run-scheduled-paper-worker: finished" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        worker_run_count = connection.execute(
            text("SELECT count(*) FROM live_runs WHERE run_type='scheduled_paper_worker'")
        ).scalar_one()
        cycle_run_count = connection.execute(
            text("SELECT count(*) FROM live_runs WHERE run_type='run_live_paper_cycle'")
        ).scalar_one()
        paper_bets_count = connection.execute(text("SELECT count(*) FROM paper_bets")).scalar_one()

    assert worker_run_count == 1
    assert cycle_run_count == 1
    assert paper_bets_count > 0


def test_collect_results_command_updates_match_and_settles_open_bet(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "live-results.sqlite"
    snapshot = _valid_misli_snapshot()
    snapshot["events"][0]["home_team"] = "Forest City"
    snapshot["events"][0]["away_team"] = "Eastport Athletic"
    snapshot["events"][0]["league"] = "Sample Premier"
    snapshot_path = tmp_path / "misli-cycle.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    results_path = tmp_path / "results.json"
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    assert runner.invoke(app, ["import-sample-data"], env=env).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "run-live-paper-cycle",
                "--provider",
                "misli-public",
                "--snapshot",
                str(snapshot_path),
                "--model",
                "baseline_heuristic",
            ],
            env=env,
        ).exit_code
        == 0
    )
    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        paper_bet_match = connection.execute(
            text(
                """
                SELECT matches.source, matches.source_match_id
                FROM paper_bets
                JOIN matches ON paper_bets.match_id = matches.id
                WHERE paper_bets.status = 'open'
                LIMIT 1
                """
            )
        ).fetchone()
    assert paper_bet_match is not None
    results_path.write_text(
        json.dumps(
            {
                "source": "manual",
                "collected_at": "2026-05-20T01:00:00+04:00",
                "results": [
                    {
                        "source": paper_bet_match[0],
                        "source_match_id": paper_bet_match[1],
                        "home_score": 2,
                        "away_score": 1,
                        "result": "HOME",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    collect_results = runner.invoke(
        app,
        ["collect-results", "--provider", "manual", "--path", str(results_path)],
        env=env,
    )
    first_settle = runner.invoke(app, ["settle-results"], env=env)
    second_settle = runner.invoke(app, ["settle-results"], env=env)

    assert collect_results.exit_code == 0
    assert "items_updated=1" in collect_results.output
    assert first_settle.exit_code == 0
    assert "items_updated=1" in first_settle.output
    assert second_settle.exit_code == 0
    assert "items_updated=0" in second_settle.output

    with engine.connect() as connection:
        completed_count = connection.execute(
            text("SELECT count(*) FROM matches WHERE status='completed'")
        ).scalar_one()
        settled_count = connection.execute(
            text("SELECT count(*) FROM paper_bets WHERE status in ('won','lost','void')")
        ).scalar_one()
        result_run_count = connection.execute(
            text("SELECT count(*) FROM live_runs WHERE run_type='collect_results'")
        ).scalar_one()

    assert completed_count >= 1
    assert settled_count >= 1
    assert result_run_count == 1


def test_replay_football_data_runs_historical_pipeline(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "replay.sqlite"
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70",
            ]
        ),
        encoding="utf-8",
    )
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    result = runner.invoke(
        app,
        [
            "replay-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "replay-football-data: finished" in result.output
    assert "Evaluation Run" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        features_count = connection.execute(text("SELECT count(*) FROM features")).scalar_one()
        predictions_count = connection.execute(
            text("SELECT count(*) FROM predictions")
        ).scalar_one()
        evaluation_count = connection.execute(
            text("SELECT count(*) FROM evaluation_runs")
        ).scalar_one()

    assert features_count > 0
    assert predictions_count > 0
    assert evaluation_count == 1


def _valid_misli_snapshot() -> dict:
    return {
        "source": "misli_public",
        "page_url": "https://www.misli.az/idman-novleri/futbol",
        "scraped_at": "2026-05-19T13:43:22.194Z",
        "event_count": 1,
        "events": [
            {
                "source": "misli_public",
                "sport": "football",
                "event_id": "2816300",
                "source_match_id": "misli:football:2816300",
                "home_team": "Rid",
                "away_team": "Volfsberq",
                "kickoff_date": "19.05.2026",
                "kickoff_time": "20:30",
                "league": "Bundesliqa, Avropa Liqasi Pley-Off",
                "odds": [
                    {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                    {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                    {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                ],
                "raw_text": "20:30 1 Rid - Volfsberq 1 2.16 X 3.18 2 2.94",
            }
        ],
    }


def test_replay_football_data_filters_candidates_and_exports_reports(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "replay_reports.sqlite"
    csv_path = tmp_path / "E0.csv"
    report_name = "pytest_replay_report"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70",
            ]
        ),
        encoding="utf-8",
    )
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    result = runner.invoke(
        app,
        [
            "replay-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--from-date",
            "2025-08-07",
            "--to-date",
            "2025-08-07",
            "--min-history",
            "3",
            "--report-name",
            report_name,
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "features_created=3" in result.output
    assert "reports/pytest_replay_report_bets.csv" in result.output
    assert "reports/pytest_replay_report_summary.json" in result.output

    bets_report = Path("reports") / f"{report_name}_bets.csv"
    summary_report = Path("reports") / f"{report_name}_summary.json"

    assert bets_report.exists()
    assert summary_report.exists()
    assert "match_id" in bets_report.read_text(encoding="utf-8").splitlines()[0]
    summary = json.loads(summary_report.read_text(encoding="utf-8"))
    assert "total_bets" in summary
    assert summary["model_config"]["model_name"] == "baseline_heuristic"
    assert summary["model_config"]["elo_home_advantage"] == 65
    assert "probability_buckets" in summary
    assert "odds_buckets" in summary
    assert "edge_buckets" in summary


def test_replay_football_data_accepts_elo_model(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "elo_replay.sqlite"
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70",
            ]
        ),
        encoding="utf-8",
    )
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    result = runner.invoke(
        app,
        [
            "replay-football-data",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--model",
            "elo",
        ],
        env=env,
    )

    assert result.exit_code == 0
    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        model_names = {
            row[0]
            for row in connection.execute(text("SELECT distinct model_name FROM predictions"))
        }

    assert model_names == {"elo"}


def test_generate_predictions_accepts_model_option(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "staged_model.sqlite"
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    for command in ["init-db", "import-sample-data", "generate-features"]:
        assert runner.invoke(app, [command], env=env).exit_code == 0

    result = runner.invoke(app, ["generate-predictions", "--model", "elo"], env=env)

    assert result.exit_code == 0
    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        model_names = {
            row[0]
            for row in connection.execute(text("SELECT distinct model_name FROM predictions"))
        }

    assert model_names == {"elo"}


def test_write_paper_bets_accepts_model_option(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "staged_bets_model.sqlite"
    env = {
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "MIN_EDGE": "0.01",
    }

    for command in ["init-db", "import-sample-data", "generate-features"]:
        assert runner.invoke(app, [command], env=env).exit_code == 0
    assert runner.invoke(app, ["generate-predictions", "--model", "elo"], env=env).exit_code == 0

    result = runner.invoke(app, ["write-paper-bets", "--model", "elo"], env=env)

    assert result.exit_code == 0
    assert "items_read=3" in result.output


def test_compare_replays_exports_side_by_side_summary(tmp_path) -> None:
    runner = CliRunner()
    csv_path = tmp_path / "E0.csv"
    report_name = "pytest_compare"
    csv_path.write_text(
        "\n".join(
            [
                (
                    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
                    "B365H,B365D,B365A,AvgH,AvgD,AvgA"
                ),
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80,2.02,3.18,3.75",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90,2.38,3.12,2.92",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20,1.92,3.35,4.10",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20,2.18,3.28,3.18",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50,2.08,3.22,3.45",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00,2.28,3.12,2.98",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70,2.55,3.18,2.72",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "compare-replays",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--models",
            "baseline_heuristic,elo",
            "--bookmakers",
            "B365,Avg",
            "--min-history",
            "3",
            "--report-name",
            report_name,
        ],
        env={"MIN_EDGE": "0.01"},
    )

    assert result.exit_code == 0
    assert "compare-replays: finished" in result.output

    comparison_csv = Path("reports") / f"{report_name}_comparison.csv"
    comparison_json = Path("reports") / f"{report_name}_comparison.json"
    assert comparison_csv.exists()
    assert comparison_json.exists()

    csv_text = comparison_csv.read_text(encoding="utf-8")
    comparison = json.loads(comparison_json.read_text(encoding="utf-8"))

    assert "baseline_heuristic" in csv_text
    assert "elo" in csv_text
    assert "roi_rank" in csv_text.splitlines()[0]
    assert "brier_score_rank" in csv_text.splitlines()[0]
    assert "log_loss_rank" in csv_text.splitlines()[0]
    assert len(comparison["runs"]) == 4
    assert comparison["rankings"]["best_roi"]["model"] in {"baseline_heuristic", "elo"}
    assert comparison["rankings"]["best_brier_score"]["bookmaker"] in {"B365", "Avg"}
    assert comparison["rankings"]["best_log_loss"]["value"] is not None
    assert all("model_config" in run for run in comparison["runs"])
    assert {
        run["model_config"]["model_name"] for run in comparison["runs"]
    } == {"baseline_heuristic", "elo"}
    assert comparison["metadata"]["models"] == ["baseline_heuristic", "elo"]
    assert comparison["metadata"]["bookmakers"] == ["B365", "Avg"]
    assert comparison["metadata"]["keep_run_dbs"] is False
    assert comparison["metadata"]["run_database_dir"] is None
    assert comparison["metadata"]["parallel_workers"] == 4
    comparison_dir = Path("data") / "comparisons" / report_name
    assert (comparison_dir / "source.csv").exists()
    assert not list(comparison_dir.glob("*.sqlite"))
    assert comparison["metadata"]["cached_source_path"].endswith(
        "data/comparisons/pytest_compare/source.csv"
    )


def test_compare_replays_can_keep_run_databases(tmp_path) -> None:
    runner = CliRunner()
    csv_path = tmp_path / "E0.csv"
    report_name = "pytest_compare_keep"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A",
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "compare-replays",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--models",
            "baseline_heuristic",
            "--bookmakers",
            "B365",
            "--min-history",
            "3",
            "--report-name",
            report_name,
            "--keep-run-dbs",
        ],
        env={"MIN_EDGE": "0.01"},
    )

    assert result.exit_code == 0
    comparison_dir = Path("data") / "comparisons" / report_name
    comparison_json = json.loads(
        (Path("reports") / f"{report_name}_comparison.json").read_text(encoding="utf-8")
    )

    assert comparison_dir.exists()
    assert list(comparison_dir.glob("*.sqlite"))
    assert comparison_json["metadata"]["keep_run_dbs"] is True
    assert comparison_json["metadata"]["run_database_dir"].endswith(
        "data/comparisons/pytest_compare_keep"
    )
    assert (comparison_dir / "source.csv").exists()
    assert comparison_json["metadata"]["cached_source_path"].endswith(
        "data/comparisons/pytest_compare_keep/source.csv"
    )


def test_compare_replays_accepts_worker_count(tmp_path) -> None:
    runner = CliRunner()
    csv_path = tmp_path / "E0.csv"
    report_name = "pytest_compare_workers"
    csv_path.write_text(
        "\n".join(
            [
                "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A,AvgH,AvgD,AvgA",
                "E0,01/08/25,Alpha FC,Beta FC,2,1,H,2.00,3.20,3.80,2.02,3.18,3.75",
                "E0,02/08/25,Gamma FC,Delta FC,0,1,A,2.40,3.10,2.90,2.38,3.12,2.92",
                "E0,03/08/25,Alpha FC,Gamma FC,1,1,D,1.90,3.40,4.20,1.92,3.35,4.10",
                "E0,04/08/25,Beta FC,Delta FC,3,1,H,2.20,3.30,3.20,2.18,3.28,3.18",
                "E0,05/08/25,Alpha FC,Delta FC,2,0,H,2.10,3.25,3.50,2.08,3.22,3.45",
                "E0,06/08/25,Beta FC,Gamma FC,1,2,A,2.30,3.15,3.00,2.28,3.12,2.98",
                "E0,07/08/25,Delta FC,Alpha FC,0,1,A,2.60,3.20,2.70,2.55,3.18,2.72",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "compare-replays",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--models",
            "baseline_heuristic,elo",
            "--bookmakers",
            "B365,Avg",
            "--min-history",
            "3",
            "--report-name",
            report_name,
            "--workers",
            "2",
        ],
        env={"MIN_EDGE": "0.01"},
    )

    assert result.exit_code == 0
    comparison_json = json.loads(
        (Path("reports") / f"{report_name}_comparison.json").read_text(encoding="utf-8")
    )
    assert comparison_json["metadata"]["parallel_workers"] == 2


def test_compare_replays_rejects_invalid_worker_count(tmp_path) -> None:
    runner = CliRunner()
    csv_path = tmp_path / "E0.csv"
    csv_path.write_text(
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "compare-replays",
            "--path",
            str(csv_path),
            "--league",
            "E0",
            "--season",
            "2526",
            "--workers",
            "0",
        ],
    )

    assert result.exit_code != 0
    assert "workers must be at least 1" in result.output


def test_analyze_comparison_command_prints_analysis(tmp_path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "comparison.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.12,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.24,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.68,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "settled_bets": 60,
                        "total_bets": 60,
                        "roi": 0.12,
                        "profit_loss_units": 7.2,
                        "brier_score": 0.25,
                        "log_loss": 0.7,
                        "roi_rank": 1,
                        "brier_score_rank": 2,
                        "log_loss_rank": 2,
                        "model_config": {"model_name": "baseline_heuristic"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-comparison", "--report", str(report_path)])

    assert result.exit_code == 0
    assert "Comparison Analysis" in result.output
    assert "Best ROI: baseline_heuristic / Avg (0.12)" in result.output
    assert "Next Experiment" in result.output


def test_analyze_comparison_command_reports_missing_file(tmp_path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "missing.json"

    result = runner.invoke(app, ["analyze-comparison", "--report", str(report_path)])

    assert result.exit_code != 0
    assert str(report_path) in result.output
    assert "does not exist" in result.output


def test_analyze_live_status_command_records_ai_advisory(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "ai-live.sqlite"
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    result = runner.invoke(app, ["analyze-live-status"], env=env)

    assert result.exit_code == 0
    assert "analyze-live-status: started" in result.output
    assert "analysis_type=live_status_summary" in result.output
    assert "model_name=deterministic_ai_fallback" in result.output
    assert "AI-assisted advisory analysis" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        analysis_count = connection.execute(
            text("SELECT count(*) FROM ai_analysis_runs")
        ).scalar_one()

    assert analysis_count == 1


def test_analyze_comparison_ai_command_records_advisory(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "ai-comparison.sqlite"
    report_path = tmp_path / "e0_compare_comparison.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.12,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.24,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.68,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "settled_bets": 60,
                        "total_bets": 60,
                        "roi": 0.12,
                        "profit_loss_units": 7.2,
                        "brier_score": 0.25,
                        "log_loss": 0.7,
                        "model_config": {"model_name": "baseline_heuristic"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    result = runner.invoke(
        app,
        ["analyze-comparison-ai", "--report", str(report_path)],
        env=env,
    )

    assert result.exit_code == 0
    assert "analyze-comparison-ai: started" in result.output
    assert "analysis_type=model_comparison_summary" in result.output
    assert "short_summary=" in result.output

    engine = create_engine(env["DATABASE_URL"])
    with engine.connect() as connection:
        stored = connection.execute(
            text("SELECT analysis_type, source_id FROM ai_analysis_runs")
        ).fetchone()

    assert stored == ("model_comparison_summary", "e0_compare")


def test_analyze_provider_health_command_records_advisory(tmp_path) -> None:
    runner = CliRunner()
    db_path = tmp_path / "ai-provider-health.sqlite"
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    assert runner.invoke(app, ["init-db"], env=env).exit_code == 0
    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO live_runs (
                    run_id, run_type, provider, status, started_at,
                    items_read, items_created, items_updated, items_skipped,
                    errors_count, error_summary, created_at
                )
                VALUES (
                    'failed-provider-run', 'collect_matches', 'misli_public', 'failed',
                    '2026-05-20T10:00:00+00:00', 21, 20, 0, 1, 1,
                    'Misli event requires a full kickoff date and time',
                    '2026-05-20T10:00:00+00:00'
                )
                """
            )
        )

    result = runner.invoke(
        app,
        ["analyze-provider-health", "--provider", "misli_public"],
        env=env,
    )

    assert result.exit_code == 0
    assert "analyze-provider-health: started" in result.output
    assert "analysis_type=provider_health_summary" in result.output
    assert "short_summary=" in result.output

    with engine.connect() as connection:
        stored = connection.execute(
            text("SELECT analysis_type, source_id FROM ai_analysis_runs")
        ).fetchone()

    assert stored == ("provider_health_summary", "misli_public")
