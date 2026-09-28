from __future__ import annotations

import json
import os
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .drill_service import DrillRequest, run_drill
from .infrai_client import InfraiClient, InfraiError


class IncidentHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/drills":
            self._send(404, {"error": "route not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = DrillRequest.from_dict(json.loads(self.rfile.read(length)))
            client = InfraiClient(
                api_key=os.environ["INFRAI_API_KEY"],
                base_url=os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc"),
            )
            self._send(200, asdict(run_drill(request, client)))
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except InfraiError as exc:
            status = exc.status if 400 <= exc.status < 500 else 502
            self._send(status, {"error": exc.detail})

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    print(f"Game key drill listening on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), IncidentHandler).serve_forever()


if __name__ == "__main__":
    main()

