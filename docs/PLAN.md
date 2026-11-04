# Build plan: 4–7 Nov 2026 (IST)

Rule: all Switch setup and workflow code is written during the event. `git init` at 00:01 on 4 Nov. No AI attribution lines in commits.

## Day 1, 4 Nov: prove the whole path with one scene (6 focused hours)
- Pin the Switch commit and images. Start the server: Docker Compose first. Console's native server hits the same Windows issue (#1335).
- Connect Mattermost and the Discord bridge.
- Coordinator: `POST /agents`, WebSocket with ping/pong, operations, `create_room_document`.
- One worker identity holding one role → one manifest → checker → Remotion preview → custom question card → call sheet PNG and MP4 uploaded to a **template-created** Discord room.
- Minimal revision rejection: change the location, and the old card's answer is refused.

**Exit test:** a human choice produces a matching call sheet and preview in Discord, with no manual copying, and both open from a crew account. A location change refuses the old answer and updates both. If this fails after 6 hours, see the abandonment test in RISKS.

## Day 2, 5 Nov: make it real and trustworthy
- The second worker identity and role; Supervisor-then-AD ordering.
- The full constraint schema: timezone, availability, hard stops, permission plus authority, windows, travel, setup and wrap, capabilities, `unknown`. Checker outcomes: `pass`, `fail`, `needs_verification`.
- Two checked candidates with different creative costs; "Neither + note"; the fast text path; hold notices.
- Authority check on `answered_by`; duplicate-outcome handling; restart recovery; failed and uncertain publication tests.

**Exit test:** both options pass and show different compromises. A deliberately conflicting schedule fails with a specific reason. A logistics-only change goes out with no render. The same outcome processed twice gives one release. Killing the coordinator mid-question and restarting keeps the question. An answer from the wrong person releases nothing.

## Day 3, 6 Nov: rehearse, freeze, shoot
- Morning: run demo A+B end to end three times; fix only what breaks.
- **Freeze the shoot path at noon.**
- Evening: the real 30-second shoot with friends (see DEMO).

**Exit test:** three clean A+B runs before noon, and the real scene is shot from a Take Two release.

## Day 4, 7 Nov: reproduce and submit
- Clean-checkout setup test from the README.
- Record the demo, finish the README and the video.
- **Submit by 8 PM IST** (the deadline is 11:59 PM).
- After submitting, the blog post. Wispr Flow proof is captured genuinely *while building* and added before that side track closes.

## Cut list
- **Cut first:** the client room, sun calculations, live role takeover, general script rewriting, arbitrary rescheduling.
- **Cut now:** screenplay parsing, generated images, calendars, weather APIs, equipment inventory, budgets, multiple films at once.
- **Never cut:** demo A+B, two rendered previews, holds, current-release confirmation, template-created rooms, cross-app delivery.

A text fallback keeps the system working if rendering fails, but it doesn't satisfy the visual demo.
