# Claude's review of W1 (coordinator)

Overall: strong. Honest state, real Switch round trip, 190 tests. The findings below are about the parts that meet the renderer, the crew and the dashboard, which W1 built before those existed.

## C1 (blocker) Render inputs don't match the renderer
`coordinator/render_bridge.py:29`, `coordinator/dispatcher.py:142`, `coordinator/dispatcher.py:199`.
The bridge passes the raw candidate manifest (preview) and `payload['snapshot']` (call sheet) straight to `render/cli.mjs`. The renderer validates input with zod (`render/src/schema.ts`), so **every render fails**:
- **Preview needs:** `letter, label, scene_number, scene_title, location, start, end, shots, people: [{id, name}], manifest_hash` (optional `sunset`, `crowd`).
- **Call sheet needs:** `production {title, day, date, timezone}, release {number, release_id, manifest_hash, summary, changes[], created_at}, general_call, sunset?, scenes [{number, title, location, start, end, cast[], changed?}], crew [{name, role, call_time, changed?}], locations [{name, note?}], confirm_hint`.

**Fix:**
- Add `coordinator/render_props.py`, with pure functions `preview_props(candidate, letter, scene, crew)` and `callsheet_props(state, release, facts)`, plus tests that validate their output against a pydantic copy of the zod schema.
- `RenderBridge.render(kind, manifest, props)` hashes the **manifest** (the identity) but writes the **props** JSON for the CLI. Today the hash is over whatever is passed, so the `result.manifest_hash != p['manifest_hash']` check at `dispatcher.py:203` would also fail once props differ.
- Letters: A, B, C in the order of passing candidates, matching what the question card shows.
- Cast numbers on the call sheet: the actor's 1-based index among crew whose role is an actor.
- `changed`: true for scenes and crew whose plan or call time differs from the previous published release.

## C2 (major) Renderer errors are thrown away
`render_bridge.py:52` sends stderr to DEVNULL. The CLI prints exactly one line, `render-error: <reason>`. Capture stderr (cap 2 KB), take the last `render-error:` line, and put it in the `RenderError` message and the timeline. Otherwise a failed preview is undiagnosable during the demo.

## C3 (major) Crew-facing text isn't readable
`dispatcher.py:_release_text` posts raw ISO times (`2026-11-06T16:30:00+05:30`), scene IDs (`s3`) and person IDs. This text is the most visible thing in the demo video. Use this format (times are HH:MM in the production timezone; names come from crew and script):
```
TAKE TWO · Release 2 (blue pages) · The Last Light, Day 1
What changed: Scene 3 moves to the stairwell, 16:30–17:15, reduced coverage.
Sc 1 · The missed call · INT. STAIRWELL · 15:00–15:15
Sc 2 · A promise · EXT. COURTYARD · 15:25–15:35
Sc 3* · The confession · INT. STAIRWELL · 16:30–17:15
Call times: Maya 16:15 · Dev 16:15 · Leela 16:15   (* = changed)
Reply "confirm r2". Replies about release 1 will be corrected.
```
The hold message follows the same style:
```
HOLD · Scene 3 (The confession). Rooftop permission refused. Do not go to the rooftop.
Scenes 1 and 2 are unchanged. An update is coming.
```
The stale-reply correction:
```
@Dev that was release 1. The current plan is release 2 (Scene 3 → stairwell, 16:30). Please reply "confirm r2".
```
Revision paper colours, in order: White, Blue, Pink, Yellow, Green, Goldenrod, Buff, Salmon, Cherry.

## C4 (minor) `production.day` is a bare date
`/api/state` returns `"day": "2026-11-06"`. The contract example is `"Day 1 - 6 November"`. Return `"Day <n> - <d Month>"`, where n is the shoot-day number from the fixtures.

## C5 (minor) Demo reset
The ledger holds W1's smoke-test changes and "message failed" events. Add `scripts/reset_demo.py`. It backs up `data/ledger.sqlite` to `data/backups/<timestamp>.sqlite`, then starts a clean ledger. It must never touch `data/identity.json` or Switch-side rooms. Document it in the README.

## C6 (question) "message failed" twice at 09:02
Explain what these were (the timeline shows "message failed; review before retrying."). If it's the smoke test posting to a room without membership, fine. Otherwise fix it.

## C7 (blocker) Worker replies will never parse
`loop.py:204` runs `json.loads(payload)` on the whole message body. Real Claude Code and Codex workers reply in the room with a mention and usually a fenced block, for example `@take-two-coordinator here is my answer:\n```json\n{...}\n```\n`. Today every such reply is rejected and retried, and then the job fails.

**Fix:** a bounded extractor:
1. Strip leading mentions.
2. If there is exactly one fenced block (```json or ```), parse it.
3. Otherwise parse the outermost `{...}` if the remaining text is only that object, plus whitespace or a short preamble of up to 300 characters.
4. Two or more JSON objects mean the reply is rejected as ambiguous. Never guess.

Add tests with realistic worker messages. The role instructions in `agents/*.md` tell workers to reply with one fenced json block and nothing else, but the parser must still tolerate the mention and a sentence.
