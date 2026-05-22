import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProductionSmokeError(RuntimeError):
    pass


class SmokeHttpClient(Protocol):
    def get_json(self, url: str) -> object:
        pass

    def get_text(self, url: str) -> str:
        pass


@dataclass(frozen=True)
class ProductionSmokeRequest:
    api_base_url: str
    dashboard_url: str | None = None


class UrlopenSmokeClient:
    def get_json(self, url: str) -> object:
        return json.loads(self.get_text(url))

    def get_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "paper-odds-lab-production-smoke"})
        try:
            with urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            raise ProductionSmokeError(f"http_error:{url}:{exc.code}") from exc
        except URLError as exc:
            raise ProductionSmokeError(f"url_error:{url}:{exc.reason}") from exc


class ProductionSmokeService:
    def __init__(self, client: SmokeHttpClient | None = None) -> None:
        self.client = client or UrlopenSmokeClient()

    def run(self, request: ProductionSmokeRequest) -> dict[str, Any]:
        api_base_url = _normalize_base_url(request.api_base_url)
        if not api_base_url:
            raise ProductionSmokeError("api_base_url_required")

        health_check = self._check_api_health(api_base_url)
        if not health_check["ok"]:
            raise ProductionSmokeError("production_smoke_failed:api_health")

        checks = [
            health_check,
            self._check_live_status(api_base_url),
            self._check_live_runs(api_base_url),
            self._check_worker_status(api_base_url),
            self._check_recommendations(api_base_url),
            self._check_comparison_catalog(api_base_url),
        ]
        dashboard_url = _normalize_optional_url(request.dashboard_url)
        if dashboard_url is not None:
            checks.append(self._check_dashboard_html(dashboard_url))

        failed = [check for check in checks if not check["ok"]]
        if failed:
            names = ", ".join(str(check["name"]) for check in failed)
            raise ProductionSmokeError(f"production_smoke_failed:{names}")

        return {
            "ok": True,
            "api_base_url": api_base_url,
            "dashboard_url": dashboard_url,
            "checks": checks,
        }

    def _check_api_health(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/health")
        ok = (
            isinstance(payload, dict)
            and payload.get("status") == "ok"
            and payload.get("database") == "ok"
        )
        return {
            "name": "api_health",
            "ok": ok,
            "status": _dict_value(payload, "status"),
            "database": _dict_value(payload, "database"),
        }

    def _check_live_status(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/live/status")
        required_keys = {"latest_run", "open_paper_bets", "settled_paper_bets"}
        return {
            "name": "live_status",
            "ok": isinstance(payload, dict) and required_keys.issubset(payload.keys()),
            "open_paper_bets": _dict_value(payload, "open_paper_bets"),
            "settled_paper_bets": _dict_value(payload, "settled_paper_bets"),
            "latest_run_status": _latest_run_status(payload),
        }

    def _check_live_runs(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/live/runs?limit=5")
        return {
            "name": "live_runs",
            "ok": isinstance(payload, list),
            "count": len(payload) if isinstance(payload, list) else None,
        }

    def _check_worker_status(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/live/worker-status")
        return {
            "name": "worker_status",
            "ok": isinstance(payload, dict) and payload.get("healthy") is True,
            "status": _dict_value(payload, "status"),
            "freshness_minutes": _dict_value(payload, "freshness_minutes"),
        }

    def _check_recommendations(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/live/recommendations?limit=5")
        return {
            "name": "recommendations",
            "ok": isinstance(payload, list),
            "count": len(payload) if isinstance(payload, list) else None,
        }

    def _check_comparison_catalog(self, api_base_url: str) -> dict[str, Any]:
        payload = self.client.get_json(f"{api_base_url}/api/reports/comparisons")
        return {
            "name": "comparison_catalog",
            "ok": isinstance(payload, list),
            "count": len(payload) if isinstance(payload, list) else None,
        }

    def _check_dashboard_html(self, dashboard_url: str) -> dict[str, Any]:
        html = self.client.get_text(dashboard_url)
        return {
            "name": "dashboard_html",
            "ok": "<div id=\"root\"" in html or "<div id='root'" in html,
            "bytes": len(html.encode("utf-8")),
        }


def _normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def _normalize_optional_url(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _dict_value(payload: object, key: str) -> object:
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _latest_run_status(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    latest_run = payload.get("latest_run")
    if not isinstance(latest_run, dict):
        return None
    status = latest_run.get("status")
    return str(status) if status is not None else None
