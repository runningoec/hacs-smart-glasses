# AGENTS.md

## Cursor Cloud specific instructions

This repo is a **Home Assistant custom integration** (`custom_components/smart_glasses`),
distributed via HACS. There is no standalone app build — the "application" is
Home Assistant itself running with this integration loaded. It exposes an admin
panel at `/smart-glasses` and a 600x600 glasses Web App at `/smart-glasses-app`,
plus scope-limited proxy endpoints under `/api/smart_glasses/*`.

### Python env

Dependencies are installed into a `.venv` at the repo root by the startup update
script. Activate it before running anything: `source .venv/bin/activate`
(`hass`, `pytest`, and `ruff` all live there). Python is 3.12, matching CI.

### Lint / test (match CI in `.github/workflows/`)

- Lint: `ruff check custom_components/smart_glasses` and
  `ruff format --check custom_components/smart_glasses`.
- Tests: `pytest -q` (78 tests, ~2s). Uses `pytest-homeassistant-custom-component`,
  which pulls in Home Assistant and pins the compatible test-tooling versions —
  do not pin those yourself; let `requirements_test.txt` resolve them.
- `hassfest` and `hacs-validate` CI jobs run in upstream Docker actions and are
  not reproduced locally here.

### Running Home Assistant with the integration

1. Use a HA config dir (e.g. `/home/ubuntu/ha_config`) with the integration
   symlinked in: `ha_config/custom_components/smart_glasses -> <repo>/custom_components/smart_glasses`.
2. Start it: `hass -c /home/ubuntu/ha_config` (serves on `http://localhost:8123`).
   First boot takes ~10-15s and initializes `.storage`.
3. First run needs onboarding (create the owner user). This can be done in the
   browser, or via the `/api/onboarding/*` REST endpoints. The admin panel
   requires an **admin** login (`require_admin=True`).
4. Add the integration: Settings → Devices & Services → Add Integration →
   "Smart Glasses" (single-step flow, no inputs), or POST to
   `/api/config/config_entries/flow` with handler `smart_glasses`. The
   "Smart Glasses" sidebar panel appears once the entry is loaded.

### Non-obvious gotchas

- **Do not restart HA via the `homeassistant.restart` service.** It runs
  standalone here with no supervisor, so that service just exits the process and
  it will not come back. To restart, stop and relaunch `hass -c ...` yourself.
- On boot HA tries to build a few **optional** native deps (`netifaces` via
  `aiodiscover`, `pyspeex-noise`). These are non-fatal; installing `python3-dev`
  silences the compile errors but HA runs fine without them.
- An `aiodns`/`pycares` `Channel.getaddrinfo()` TypeError may appear on boot from
  an outbound version-check/analytics call that cannot reach the internet in the
  sandbox. It is harmless and unrelated to this integration.
- End-to-end product check (the real core flow): open `/smart-glasses-app` to get
  a 6-char pairing code, approve it in the `/smart-glasses` panel's "Glasses
  pairings" card, then tapping a card cell fires a scoped `homeassistant.toggle`
  (or pinned action) through the proxy. Card items are managed in the panel's
  Dashboard card.
