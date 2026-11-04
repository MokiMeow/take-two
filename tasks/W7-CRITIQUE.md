# W7: one-on-one critique. Is Take Two a winning hackathon entry, and what would make it one?

You are not writing code in this task. You are a sharp, honest co-founder and hackathon judge. Read the repo and argue with it. Claude (who built the UI and reviewed your earlier rounds) will read your answer and debate it.

## Read first
- `debate/EVENT.md`: the hackathon ("Flip the Switch"), its tracks, judging weights (Use of Switch 30%, Technical execution 25%, Creativity and impact 25%, Presentation and docs 20%) and submission rules. Deadline Sat 7 Nov 11:59 PM IST; we submit by 8 PM. Today is Wed 4 Nov, evening.
- `README.md`, `docs/ARCHITECTURE.md`, `docs/FLOW.md`, `docs/DEMO.md`, `docs/AGENTS.md`, `docs/SETUP-HUMAN.md`, `docs/explainer/how-it-works.html`.
- `work/W4-REPORT.md`, `work/W5-REPORT.md`, `work/W6-REPORT.md` (what is really built and proven).
- The UI in `ui/src` (React dashboard) and `render/` (Remotion previews and call sheets).
- Switch's own source at `E:/DevDrive/switch` (read-only) to see which Switch capabilities we are NOT using yet.

## What exists today (short)
A coordinator registered as a Switch agent; producer/AD/director in a Mattermost production room; crew meant to be on Discord (bridge not yet configured); two LLM agents (script supervisor on Claude Code, first AD on Codex) that propose plans; a deterministic checker; native Switch question cards for the director; versioned releases with call sheets and set-model preview videos; crew confirmations and stale-reply correction; a four-problem shoot day proven against the real Switch with simulated people and simulated workers; a dashboard that replays it.

## Answer these, bluntly
1. **Would this win?** Score it 1–10 on each judging criterion as it stands, with one sentence of evidence each. Where does a judge stop caring?
2. **The weakest points of the idea itself**, not the code. Is "re-plan a film shoot" too niche or too much like a scheduler with extra steps? Where is the LLM doing real work versus decoration? What would a skeptical Switch engineer say?
3. **Switch capabilities we are not using** that would make Switch more obviously central (look at the source: question cards for crew, room documents, media, templates, agent-to-agent, presence, threads, reactions, approvals, multiple bridges, whatever exists). Which ones fit naturally?
4. **Five bolder or more creative ideas** that could be built in ~2 days by two AI workers plus Claude, ranked by (impact on judges ÷ risk). For each: what the judge sees in the video, what it needs from Switch, what could go wrong. Think beyond scheduling: e.g. the crew's free-text message turned into a proposed change that a human confirms with one tap; a confirm/can't-make-it card sent to each crew member; the director deciding from a phone; continuity or shot-list tracking; a "what changed since you last looked" digest; voice notes; real agents disagreeing and the supervisor vetoing a plan on story grounds; anything better.
5. **Biggest demo risks** (real Claude/Codex agents not following the JSON format, Discord bridge, render time, Windows, the live shoot) and the cheapest mitigation for each.
6. **Reproducibility:** can a judge clone and run something meaningful in 15 minutes without Discord or real agents? What is the minimum path, and what is missing?
7. **If you had to cut or change one thing to make the entry clearly better, what is it?**

## Output
Write `work/W7-CRITIQUE.md`, at most ~1,500 words, plain and specific (file paths, Switch source paths). End with your recommended plan for the remaining 3 days as an ordered list with owners (Codex worker / Claude / the human). Do not edit any other file.
