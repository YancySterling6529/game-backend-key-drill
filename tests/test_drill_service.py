from datetime import datetime, timezone

from game_key_drill.drill_service import DrillRequest, GameSurface, run_drill


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def create_drill_key(self, incident_id: str) -> dict[str, str]:
        self.calls.append(("create", incident_id))
        return {"key_id": "key_drill_42", "key": "one-time-value"}

    def report_compromise(self, key_id: str) -> dict[str, bool]:
        self.calls.append(("report", key_id))
        return {"reported": True}

    def search_logs(self, query: str, since: str) -> dict[str, list[dict[str, int]]]:
        self.calls.append(("search", query))
        return {"entries": [{"n": number} for number in range(12)]}

    def rotate_key(self, key_id: str, incident_id: str) -> dict[str, bool]:
        self.calls.append(("rotate", key_id))
        return {"rotated": True}

    def revoke_key(self, key_id: str) -> dict[str, bool]:
        self.calls.append(("revoke", key_id))
        return {"revoked": True}


def test_drill_marks_three_game_surfaces_critical_and_cleans_up() -> None:
    request = DrillRequest(
        incident_id="inc-2026-09-24",
        leaked_at=datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc),
        surfaces=tuple(GameSurface),
    )
    gateway = RecordingGateway()

    result = run_drill(request, gateway)

    assert result.severity == "critical"
    assert result.log_hits == 12
    assert result.status == "reported_rotated_confirmed"
    assert [name for name, _ in gateway.calls] == [
        "create",
        "report",
        "search",
        "rotate",
        "revoke",
    ]

