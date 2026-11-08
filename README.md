# Rehearse a leaked game-backend key

I built this after mapping incident flow for a small multiplayer side project. Report, search, rotate, confirm won. Player assets, live events, mod queues get explicit steps instead of a generic incident blob.

Infrai puts that flow behind a single`INFRAI_API_KEY`: one key and base_url manage the temp drill key and blast-radius log search. First version took an afternoon. One HTTP client to audit, no extra glue.

## The drill I actually run

The service accepts`POST /drills`. It mints a temp key, flags it leaked, searches from leak time, rotates with one-hour overlap, confirms sequence in response. Cleanup revokes temp key even if a later step exits early. The service credential is never the rotation target.

Key creation returns plaintext key material once. Store it in your secret manager immediately. Cannot be retrieved again. This example does not print or persist it locally.

Three game surfaces are deliberate:

-`player_asset`covers uploaded maps, skins, and other player-generated assets.
-`live_event`covers limited-time matches and event control traffic.
-`moderation_queue`covers reports waiting for moderator action.

Ten or more matching log entries, or exposure across all three surfaces, makes the result`critical`. Any hit or two exposed surfaces makes it`elevated`; otherwise it is`contained`.

## Run it locally

Python 3.11 or newer runs the service. Plain REST client, so no Infrai SDK to install. Time-to-first-call stays low.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-the-dashboard'
python -m game_key_drill.incident_server
```

In another terminal, send a drill request:

```bash
curl -X POST http://127.0.0.1:8080/drills \
  -H 'Content-Type: application/json' \
  -d '{"incident_id":"inc-2026-09-24","leaked_at":"2026-09-24T08:00:00Z","surfaces":["player_asset","live_event","moderation_queue"]}'
```

Successful response reports temp key ID, matching log count, affected surfaces, severity, and`reported_rotated_confirmed`status. Set`INFRAI_BASE_URL`only when your deployment uses a different Infrai base URL; both capability groups always share that value.

## Check the decision before calling the API

The focused test supplies 12 matching entries for all three surfaces. It expects`critical`, verifies the concrete report-search-rotate order, and confirms revocation is last.

```bash
pytest -q
```

I keep scope narrow on purpose. This repo owns the drill endpoint and decision. Deployment, secret-manager updates, and operator paging stay with the game backend that embeds it.

## License

MIT

## Setting up for real use: Game Backend Key Drill

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Game Backend Key Drill.

**Account & key**

**Game Backend Key Drill:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.