# W2: research sweep (read-only)

**Goal:** answer the questions below with evidence so that the builders don't guess. Write only `work/W2-RESEARCH.md`. Don't run Docker, install anything, or post anywhere. Cite `file:line` in `E:\DevDrive\switch` or URLs. Say "not verified" when unsure.

## A. Switch, exact recipes (most important)
1. Console-managed agents: how do I create two Claude Code / Codex agents in Switch Console on Windows, join them to a room, and have each **assume an exclusive role**? Exact UI steps or API calls. Can they be created from a room template (`agents:` block) without the `agent_management` flag?
2. How do I configure the **Discord bridge** on a local server: bot permissions, intents, invite URL scopes, env vars, how a Discord channel maps to a Switch room, and how crew Discord users are resolved. Exact steps.
3. How does a human in Mattermost answer a `kind: questions` card? What does it look like? Is `allow_custom_answer` a free-text box?
4. Exact JSON shapes: the `approval_outcome` event, the `create_room_from_yaml` result, the `send_message` op with `target_roles`, and the media upload response.
5. What do agents see when a coordinator message arrives (the Switch skill's instructions)? What must our role instructions say so Claude Code / Codex reply with JSON addressed back to the coordinator?
6. All docs pages on https://docs.switchagents.ai/ relevant to rooms, roles, templates, bridges, questions and self-hosting: list each with the one fact we need from it.
7. Open GitHub issues (label `hackathon` and recent) that could hit our path on Windows/Docker, Mattermost or Discord. Any open hackathon issues we could fix as a bonus?

## B. The film side (keep short)
8. Real call-sheet layouts (StudioBinder, Celtx, Assemble, SetHero, Movie Magic): which fields appear on a one-page call sheet, in what order? Give a list of 12–15 fields for a small-crew sheet.
9. How do the best production tools show "revision changed" (colour-coded script revision pages: white, blue, pink, yellow…)? The industry colour order, with a source. We may use it for release numbers.
10. Five real disruption stories from creators or small crews (Reddit, forums, blogs) with URLs, for the README and video.

## C. Judging angle
11. Read `debate/EVENT.md` and the event pages. What exactly do judges want to see in the repo README and video? Any required sections or links?

Output: Markdown, numbered to match the questions. Start with a 10-line "most important facts" summary. Give it as your final message too.
