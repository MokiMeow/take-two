# Coordinator operations

Run commands from the repository root with `UV_CACHE_DIR=data/uv-cache` on this restricted Windows workspace.

Stop the coordinator before `uv run python -m scripts.reset_demo`. It backs up the SQLite database to `data/backups/<timestamp>.sqlite` and clears its ledger rows. It does not alter `data/identity.json`, question identity credentials, or Switch rooms. Start the coordinator again with `uv run python -m coordinator`.

The director starts the normal-day loop in Mattermost with `/plan day-1`. The AD initial candidate uses `manifests: [<scene 1>, <scene 2>, <scene 3>]` instead of `manifest`; one director approval commits the complete release 1. The reviewed cast and required kit are in `fixtures/film/script.yaml`. Subsequent scene changes use the existing single `manifest` format, or `manifests` when several unresolved scenes must be replaced together.

`uv run python -m scripts.seed_initial_plan` posts `/plan day-1` as the configured Mattermost director account. It never edits the ledger or approves a plan. Configure its local credentials in `.env` as `TAKE_TWO_DIRECTOR_MM_USER` and `TAKE_TWO_DIRECTOR_MM_PASSWORD`; the latter is never printed. Workers must be connected with their roles. The director approves the resulting native card in Mattermost.

`uv run python -m scripts.demo_dry_run` runs the FLOW story with registered simulated worker agents and separate Mattermost test people against the real Switch server. It uses an isolated ledger and registered identities in `data/w4-demo`, plus a private Mattermost room. It performs real rendering, upload, question answering, holds and confirmations. Its local API is on port 8788 while running. Each run backs up and resets only that isolated ledger, keeps credentials, and prints a redacted final `/api/state` summary.

Publication status `sent` means **accepted by Switch for relay**. It does not prove a Discord user received or opened the attachment. The local release status `published` uses that same acceptance threshold. Observed bridge delivery errors appear in the timeline. Discord is not connected yet in this demo; `day_room_status=no_discord_bridge` is visible and no fake crew destination is created.

The browser can submit pending reports and conservative holds. Its reporter text grants no authority. Only authenticated Switch authorities can confirm facts or clear a hold; only the named director's current, checked answer can release a plan. Supervisor `must_keep` appears on the card as prose for human review and is not machine-checked.
