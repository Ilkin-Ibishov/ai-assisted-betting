import json

import pytest

from app.services.production_smoke_service import (
    ProductionSmokeError,
    ProductionSmokeRequest,
    ProductionSmokeService,
)


def test_production_smoke_checks_api_and_dashboard_contracts() -> None:
    client = FakeSmokeClient(
        {
            "https://api.example.test/api/health": {
                "status": "ok",
                "database": "ok",
            },
            "https://api.example.test/api/live/status": {
                "latest_run": None,
                "open_paper_bets": 0,
                "settled_paper_bets": 0,
            },
            "https://api.example.test/api/live/runs?limit=5": [],
            "https://api.example.test/api/reports/comparisons": [],
            "https://dashboard.example.test/": "<!doctype html><div id=\"root\"></div>",
        }
    )

    report = ProductionSmokeService(client=client).run(
        ProductionSmokeRequest(
            api_base_url="https://api.example.test",
            dashboard_url="https://dashboard.example.test/",
        )
    )

    assert report["ok"] is True
    assert report["api_base_url"] == "https://api.example.test"
    assert report["dashboard_url"] == "https://dashboard.example.test/"
    assert [check["name"] for check in report["checks"]] == [
        "api_health",
        "live_status",
        "live_runs",
        "comparison_catalog",
        "dashboard_html",
    ]
    assert all(check["ok"] for check in report["checks"])


def test_production_smoke_fails_when_database_health_is_not_ok() -> None:
    client = FakeSmokeClient(
        {
            "https://api.example.test/api/health": {
                "status": "ok",
                "database": "error",
            },
        }
    )

    with pytest.raises(ProductionSmokeError, match="api_health"):
        ProductionSmokeService(client=client).run(
            ProductionSmokeRequest(api_base_url="https://api.example.test")
        )


def test_production_smoke_requires_dashboard_root_when_dashboard_url_is_set() -> None:
    client = FakeSmokeClient(
        {
            "https://api.example.test/api/health": {
                "status": "ok",
                "database": "ok",
            },
            "https://api.example.test/api/live/status": {
                "latest_run": None,
                "open_paper_bets": 0,
                "settled_paper_bets": 0,
            },
            "https://api.example.test/api/live/runs?limit=5": [],
            "https://api.example.test/api/reports/comparisons": [],
            "https://dashboard.example.test/": "<!doctype html><main>missing app root</main>",
        }
    )

    with pytest.raises(ProductionSmokeError, match="dashboard_html"):
        ProductionSmokeService(client=client).run(
            ProductionSmokeRequest(
                api_base_url="https://api.example.test",
                dashboard_url="https://dashboard.example.test/",
            )
        )


class FakeSmokeClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    def get_json(self, url: str) -> object:
        return self.responses[url]

    def get_text(self, url: str) -> str:
        value = self.responses[url]
        if not isinstance(value, str):
            return json.dumps(value)
        return value
