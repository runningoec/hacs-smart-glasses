# Authentication & security model

This document is the exact token model for the Smart Glasses integration.
It exists because several glasses-facing HTTP views must set
`requires_auth = False` — Meta Ray-Ban Display Web Apps cannot complete
Home Assistant's browser login or hold a long-lived access token (LLAT)
the way a phone/desktop session can.

Using HA LLATs (`requires_auth = True` on the glasses API) would be a
**larger** blast radius: an LLAT can call any HA REST/WebSocket API. This
integration deliberately replaced that design in v0.6 with a scoped proxy.

## Why `requires_auth = False` exists

| Endpoint | Auth | Can call HA services? |
|---|---|---|
| `GET /smart-glasses-app` | none (static HTML) | no |
| `GET /smart_glasses_static/favicon-192x192.png` | none (static) | no |
| `GET /api/smart_glasses/panel.js` | none (static JS) | no |
| `POST /api/smart_glasses/pair/start` | none + per-IP rate limit | no |
| `GET /api/smart_glasses/pair/{id}/token` | knowledge of `session_id` | no |
| `GET /api/smart_glasses/glance/cards` | glasses Bearer token | no |
| `GET /api/smart_glasses/glance/states` | glasses Bearer token | no (read card entities only) |
| `POST /api/smart_glasses/glance/call_service` | glasses Bearer token | **yes, card-scoped only** |
| `WS /api/smart_glasses/glance/ws` | glasses token in first frame | no (filtered events only) |
| All `/api/smart_glasses/pairings`, `/pair/approve`, `/cards`, `/audit`, … | HA auth + admin user | n/a (panel) |

The only service-executing unauthenticated-to-HA view is
`GlanceCallServiceView`. It cannot reach `hass.services.async_call`
without passing `_require_glasses_pairing`, a per-token rate limit, type
checks, and `_service_call_allowed` (card scope + hard blocklist).

## Token lifecycle

1. Glasses call `POST /pair/start` → receive `{session_id, code}`.
2. An HA **admin** approves `(session_id, code)` from the panel
   (`requires_auth = True`).
3. Approval mints `secrets.token_urlsafe(32)` (~256 bits of entropy).
4. Server stores **only** `sha256(token)` on disk. Plaintext is kept in
   `token_pickup` until the glasses' next poll, then wiped.
5. Glasses receive the plaintext exactly once from
   `GET /pair/{session_id}/token` and keep it in their localStorage.
6. Every subsequent glasses API call sends
   `Authorization: Bearer <token>`.
7. Lookup hashes the presented token, resolves via an in-memory index,
   and confirms with `hmac.compare_digest` against the stored hash.
8. Panel **Revoke** deletes the pairing record (and hash). Next glasses
   call returns 401; Shift+Escape on the glasses clears localStorage.

Tokens are never written to the audit log or application logs.

## Scope of a valid token

A valid glasses token can **only**:

- read the current card definitions
- read states for `entity_id`s that appear on a card
- call services that match either:
  - an `entity` item's natural domain action / `homeassistant.toggle`, or
  - an exact `action` item (`domain.service` + optional target)
- receive websocket `state_changed` events filtered to card entities

It cannot:

- enumerate other entities
- call arbitrary HA services
- pass extra service data (`brightness`, alarm codes, … are dropped)
- invoke blocklisted system services (`homeassistant.restart`,
  `hassio.*`, `shell_command.*`, recorder purge, …) even if mis-added
  to a card
- exceed 30 `call_service` requests per minute per token

## Pairing bootstrap protections

- 6-char codes from an unambiguous alphabet (no `O`/`0`/`I`/`1`)
- Approval requires **both** `code` and `session_id`
- `/pair/start` rate-limited to 6 requests/min/IP
- Hard cap of 50 pending pairings; inactive pending sessions pruned
  after 30s without a token poll (5-minute hard TTL backstop)
- Token pickup is single-use (subsequent polls → 410 Gone)

## Reporting issues

Please open a private security advisory or email the maintainer listed
in `manifest.json` `codeowners` for vulnerabilities in this model.
