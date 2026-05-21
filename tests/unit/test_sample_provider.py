from app.providers.sample_provider import SampleProvider


def test_sample_provider_returns_deterministic_matches_odds_and_results() -> None:
    provider = SampleProvider()

    matches = list(provider.get_matches())
    upcoming_matches = [match for match in matches if match.status == "scheduled"]
    completed_matches = [match for match in matches if match.status == "completed"]
    odds = [
        snapshot
        for match in upcoming_matches
        for snapshot in provider.get_odds(match.source_match_id, "1X2")
    ]
    results = [provider.get_result(match.source_match_id) for match in completed_matches]

    assert len(matches) == 11
    assert len(completed_matches) == 8
    assert len(upcoming_matches) == 3
    assert len(odds) == 9
    assert all(result is not None for result in results)
    assert {snapshot.selection for snapshot in odds} == {"HOME", "DRAW", "AWAY"}
