from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol, Sequence


class GameSurface(str, Enum):
    PLAYER_ASSET = "player_asset"
    LIVE_EVENT = "live_event"
    MODERATION_QUEUE = "moderation_queue"


@dataclass(frozen=True)
class DrillRequest:
    incident_id: str
    leaked_at: datetime
    surfaces: Sequence[GameSurface]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DrillRequest":
        incident_id = str(value["incident_id"]).strip()
        if not incident_id:
            raise ValueError("incident_id must not be empty")
        leaked_at = datetime.fromisoformat(str(value["leaked_at"]).replace("Z", "+00:00"))
        if leaked_at.tzinfo is None:
            raise ValueError("leaked_at must include a timezone")
        surfaces = tuple(GameSurface(item) for item in value["surfaces"])
        if not surfaces:
            raise ValueError("surfaces must not be empty")
        return cls(incident_id, leaked_at, surfaces)


@dataclass(frozen=True)
class DrillResult:
    incident_id: str
    temporary_key_id: str
    log_hits: int
    affected_surfaces: Sequence[GameSurface]
    severity: str
    status: str


class DrillGateway(Protocol):
    create_drill_key: Callable[[str], dict[str, Any]]
    report_compromise: Callable[[str], dict[str, Any]]
    search_logs: Callable[[str, str], dict[str, Any]]
    rotate_key: Callable[[str, str], dict[str, Any]]
    revoke_key: Callable[[str], dict[str, Any]]


def classify_blast_radius(hit_count: int, surfaces: Sequence[GameSurface]) -> str:
    if hit_count >= 10 or len(surfaces) == 3:
        return "critical"
    if hit_count or len(surfaces) == 2:
        return "elevated"
    return "contained"


def run_drill(request: DrillRequest, gateway: DrillGateway) -> DrillResult:
    created = gateway.create_drill_key(request.incident_id)
    key_id = str(created["key_id"])
    # The response may contain the one-time plaintext key; production callers store it immediately.
    try:
        gateway.report_compromise(key_id)
        terms = " OR ".join(surface.value for surface in request.surfaces)
        found = gateway.search_logs(terms, request.leaked_at.astimezone(timezone.utc).isoformat())
        entries = found.get("entries", found.get("logs", []))
        hit_count = len(entries) if isinstance(entries, list) else int(found.get("count", 0))
        gateway.rotate_key(key_id, request.incident_id)
        severity = classify_blast_radius(hit_count, request.surfaces)
        return DrillResult(
            request.incident_id,
            key_id,
            hit_count,
            request.surfaces,
            severity,
            "reported_rotated_confirmed",
        )
    finally:
        gateway.revoke_key(key_id)
