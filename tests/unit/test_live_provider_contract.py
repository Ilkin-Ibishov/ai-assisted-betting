import pytest
from pydantic import ValidationError

from app.providers.base import ProviderCapability
from app.providers.misli_public import MisliPublicSnapshot


def test_provider_capability_declares_live_collection_surface() -> None:
    capability = ProviderCapability(
        provider="misli_public",
        supports_matches=True,
        supports_odds=True,
        supports_results=False,
        supported_leagues=["football"],
        supported_markets=["1X2"],
        rate_limit_notes="Manual low-rate public snapshot only.",
        requires_full_kickoff_datetime=True,
        safety_boundary_notes="Public unauthenticated pages only.",
    )

    assert capability.provider == "misli_public"
    assert capability.supports_odds is True
    assert capability.supports_matches is True
    assert capability.requires_full_kickoff_datetime is True
    assert capability.supported_markets == ["1X2"]


def test_misli_public_snapshot_accepts_complete_public_1x2_event() -> None:
    snapshot = MisliPublicSnapshot.model_validate(
        {
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
                    "detail_url": "https://www.misli.az/idman-novleri-canli-merc-teferruati/futbol/2816300",
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
    )

    assert snapshot.event_count == 1
    assert snapshot.events[0].has_full_kickoff_datetime is True
    assert snapshot.events[0].has_complete_1x2 is True
    assert snapshot.events[0].odds[0].selection == "HOME"


def test_misli_public_snapshot_fails_closed_for_missing_full_kickoff_date() -> None:
    with pytest.raises(ValidationError, match="full kickoff date"):
        MisliPublicSnapshot.model_validate(
            {
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
                        "kickoff_date": "",
                        "kickoff_time": "20:30",
                        "league": "Bundesliqa, Avropa Liqasi Pley-Off",
                        "odds": [
                            {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                            {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                            {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                        ],
                        "raw_text": "20:30 1 Rid - Volfsberq",
                    }
                ],
            }
        )


def test_misli_public_snapshot_derives_today_date_from_kickoff_time_label() -> None:
    snapshot = MisliPublicSnapshot.model_validate(
        {
            "source": "misli_public",
            "page_url": "https://www.misli.az/idman-novleri/futbol",
            "scraped_at": "2026-05-20T14:58:36.426Z",
            "event_count": 1,
            "events": [
                {
                    "source": "misli_public",
                    "sport": "football",
                    "event_id": "2818392",
                    "source_match_id": "misli:football:2818392",
                    "home_team": "Ethiopia Electricity",
                    "away_team": "Dire Dawa Kenema",
                    "kickoff_date": "",
                    "kickoff_time": "Bu Gün 19:00",
                    "league": "Premyer Liqa",
                    "odds": [
                        {"market": "1X2", "selection": "HOME", "odds_decimal": 2.43},
                        {"market": "1X2", "selection": "DRAW", "odds_decimal": 2.33},
                        {"market": "1X2", "selection": "AWAY", "odds_decimal": 3.13},
                    ],
                    "raw_text": "Bu Gün 19:00 Ethiopia Electricity - Dire Dawa Kenema",
                }
            ],
        }
    )

    event = snapshot.events[0]
    assert event.kickoff_date == "20.05.2026"
    assert event.kickoff_time == "19:00"


def test_misli_public_snapshot_derives_tomorrow_date_from_kickoff_time_label() -> None:
    snapshot = MisliPublicSnapshot.model_validate(
        {
            "source": "misli_public",
            "page_url": "https://www.misli.az/idman-novleri/futbol",
            "scraped_at": "2026-05-20T22:30:00.000Z",
            "event_count": 1,
            "events": [
                {
                    "source": "misli_public",
                    "sport": "football",
                    "event_id": "2818393",
                    "source_match_id": "misli:football:2818393",
                    "home_team": "Home",
                    "away_team": "Away",
                    "kickoff_date": "",
                    "kickoff_time": "Sabah 02:00",
                    "league": "Premyer Liqa",
                    "odds": [
                        {"market": "1X2", "selection": "HOME", "odds_decimal": 2.43},
                        {"market": "1X2", "selection": "DRAW", "odds_decimal": 2.33},
                        {"market": "1X2", "selection": "AWAY", "odds_decimal": 3.13},
                    ],
                    "raw_text": "Sabah 02:00 Home - Away",
                }
            ],
        }
    )

    event = snapshot.events[0]
    assert event.kickoff_date == "22.05.2026"
    assert event.kickoff_time == "02:00"


def test_misli_public_snapshot_fails_closed_for_ambiguous_time_without_date() -> None:
    with pytest.raises(ValidationError, match="full kickoff date"):
        MisliPublicSnapshot.model_validate(
            {
                "source": "misli_public",
                "page_url": "https://www.misli.az/idman-novleri/futbol",
                "scraped_at": "2026-05-20T14:58:36.426Z",
                "event_count": 1,
                "events": [
                    {
                        "source": "misli_public",
                        "sport": "football",
                        "event_id": "2818394",
                        "source_match_id": "misli:football:2818394",
                        "home_team": "Home",
                        "away_team": "Away",
                        "kickoff_date": "",
                        "kickoff_time": "20:30",
                        "league": "Premyer Liqa",
                        "odds": [
                            {"market": "1X2", "selection": "HOME", "odds_decimal": 2.43},
                            {"market": "1X2", "selection": "DRAW", "odds_decimal": 2.33},
                            {"market": "1X2", "selection": "AWAY", "odds_decimal": 3.13},
                        ],
                        "raw_text": "20:30 Home - Away",
                    }
                ],
            }
        )


def test_misli_public_snapshot_fails_closed_for_incomplete_1x2_odds() -> None:
    with pytest.raises(ValidationError, match="complete 1X2"):
        MisliPublicSnapshot.model_validate(
            {
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
                        ],
                        "raw_text": "20:30 1 Rid - Volfsberq",
                    }
                ],
            }
        )


def test_misli_public_snapshot_normalizes_comma_decimal_odds() -> None:
    snapshot = MisliPublicSnapshot.model_validate(
        {
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
                        {"market": "1X2", "selection": "HOME", "odds_decimal": "2,16"},
                        {"market": "1X2", "selection": "DRAW", "odds_decimal": "3,18"},
                        {"market": "1X2", "selection": "AWAY", "odds_decimal": "2,94"},
                    ],
                    "raw_text": "20:30 1 Rid - Volfsberq 1 2,16 X 3,18 2 2,94",
                }
            ],
        }
    )

    assert snapshot.events[0].odds[0].odds_decimal == 2.16
    assert snapshot.events[0].odds[1].odds_decimal == 3.18
    assert snapshot.events[0].odds[2].odds_decimal == 2.94


def test_misli_public_snapshot_fails_closed_for_empty_identity_fields() -> None:
    with pytest.raises(ValidationError, match="non-empty home_team"):
        MisliPublicSnapshot.model_validate(
            {
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
                        "home_team": "",
                        "away_team": "Volfsberq",
                        "kickoff_date": "19.05.2026",
                        "kickoff_time": "20:30",
                        "league": "Bundesliqa, Avropa Liqasi Pley-Off",
                        "odds": [
                            {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
                            {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
                            {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94},
                        ],
                        "raw_text": "20:30 1 Rid - Volfsberq",
                    }
                ],
            }
        )
