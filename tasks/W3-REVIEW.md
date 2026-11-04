# W3: hostile review of the coordinator (read-only)

You did not write this code. Another Sol worker (W1) wrote `coordinator/`, `scripts/`, `templates/` and `fixtures/` in one session. Its report: `work/W1-REPORT.md`. Your job is to find the defects it missed, before we build on it. Claude reviews in parallel; you two will then compare.

**Read-only.** Write only `work/W3-REVIEW.md`. You may run `uv run pytest` (set `UV_CACHE_DIR=data/uv-cache`, `--basetemp=data/pytest-w3`) and read the live API at `http://127.0.0.1:8787` with GET only. Don't POST, don't call Switch, don't edit code.

## Review against
1. The spec: `docs/ARCHITECTURE.md`, `docs/FLOW.md`, `docs/AGENTS.md`, `docs/UI-CONTRACT.md`, `review/SOL-REVIEW.md` (16 fixes), and the "must never happen" list in `tasks/WORKER-STANDARD.md`.
2. The Switch source at `E:\DevDrive\switch`: every protocol call in `coordinator/switch_client.py` must match the server's real routes and payloads.
3. Demo-readiness: can the exact FLOW.md story (rooftop refused → hold → Supervisor → AD → 3 candidates, courtyard fails → two previews → question → Maya hard stop → old question closes → park fails → director picks stairwell reduced → release 2 → Dev replies to r1 → corrected → confirms r2) run end to end on this code once the agents, Discord and renderer exist? Walk it step by step through the code and name the first place it would break.

## Look especially for
- State-machine holes: a change arriving in every possible step; a worker replying twice; a reply for an old job; an outcome arriving after expiry; restart at each step.
- Authority: can anything other than the named human's authenticated Switch identity cause a release? Including `/api/changes` from the browser.
- Truthfulness of `/api/state`: does every field reflect the ledger, or are some faked or defaulted in ways the UI would show as real?
- Release publishing: what exactly is posted to Discord/Mattermost; does the call sheet come from the same manifest as the approved candidate?
- Render bridge: does it match `render/README.md` (manifest shapes = `render/src/schema.ts`)? It was written before the renderer existed. List every field mismatch.
- Over-engineering that will slow a 4-day build, and dead code.

## Output
Markdown. Start with a verdict and the 5 most important findings. Then every finding as: **severity (blocker / major / minor)**, file:line, what breaks, a concrete scenario, and the exact fix. End with "the first place the FLOW story breaks". Give it as your final message too.
