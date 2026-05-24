import hashlib
import json
from typing import Any

from sqlalchemy import Engine

from app.db.engine import session_scope
from app.db.models import LiveSnapshot
from app.db.repositories import LiveSnapshotRepository


class LiveSnapshotService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def store_latest(
        self,
        *,
        provider: str,
        payload: dict[str, Any],
        source_url: str | None = None,
    ) -> LiveSnapshot:
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        snapshot_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        event_count = _event_count(payload)
        with session_scope(self.engine) as session:
            return LiveSnapshotRepository(session).add(
                provider=normalize_snapshot_provider(provider),
                snapshot_hash=snapshot_hash,
                payload_json=json.dumps(payload, indent=2, sort_keys=True),
                source_url=source_url or _source_url(payload),
                event_count=event_count,
            )

    def latest_payload(self, provider: str) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            snapshot = LiveSnapshotRepository(session).latest(normalize_snapshot_provider(provider))
            if snapshot is None:
                return None
            loaded = json.loads(snapshot.payload_json)
            if not isinstance(loaded, dict):
                raise ValueError("stored live snapshot payload must be a JSON object")
            return loaded


def normalize_snapshot_provider(provider: str) -> str:
    return provider.replace("-", "_")


def _event_count(payload: dict[str, Any]) -> int:
    event_count = payload.get("event_count")
    if isinstance(event_count, int):
        return event_count
    events = payload.get("events")
    if isinstance(events, list):
        return len(events)
    return 0


def _source_url(payload: dict[str, Any]) -> str | None:
    page_url = payload.get("page_url")
    return page_url if isinstance(page_url, str) else None
