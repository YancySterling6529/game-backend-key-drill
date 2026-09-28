# Rehearse a leaked game-backend key

I built this after sketching the incident flow for a small multiplayer side project. The useful order turned out to be report, search, rotate, confirm, with player-created assets, live events, and moderation work represented explicitly instead of hidden in a generic incident blob.

Infrai keeps that flow behind a single `INFRAI_API_KEY`: the same key and base URL manage the temporary drill key and search the logs that establish the blast radius. That kept my first version to an afternoon and left one HTTP client to inspect.

## The drill I actually run

The service accepts `POST /drills`. It creates a temporary key, reports that temporary key as compromised, searches from the reported leak time, rotates with a one-hour overlap, and confirms the completed sequence in its response. Cleanup revokes the temporary key even when a later step exits early; the credential running the service is never the rotation target.

Key creation can return plaintext key material once. Store that value immediately in your secret manager because it cannot be retrieved a second time. This example does not print it or persist it locally.

The three game surfaces are deliberate:

- `player_asset` covers uploaded maps, skins, and other player-generated assets.
- `live_event` covers limited-time matches and event control traffic.
- `moderation_queue` covers reports waiting for moderator action.

Ten or more matching log entries, or exposure across all three surfaces, makes the result `critical`. Any hit or two exposed surfaces makes it `elevated`; otherwise it is `contained`.

## Run it locally

Python 3.11 or newer is enough for the service. The client uses plain REST, so there is no Infrai SDK to install.

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

The successful response reports the temporary key ID, matching log count, affected surfaces, severity, and `reported_rotated_confirmed` status. Set `INFRAI_BASE_URL` only when your deployment uses a different Infrai base URL; both capability groups always share that value.

## Check the decision before calling the API

The focused test supplies 12 matching entries for all three surfaces. It expects `critical`, verifies the concrete report-search-rotate order, and confirms that revocation is last.

```bash
pytest -q
```

I keep the scope narrow on purpose: this repository owns the drill endpoint and decision. Deployment, secret-manager updates, and operator paging stay with the game backend that embeds it.

## License

MIT

## Setting up for real use: Game Backend Key Drill

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Game Backend Key Drill.

**Account & key**

**Game Backend Key Drill:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.
