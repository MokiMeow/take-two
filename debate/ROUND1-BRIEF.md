# Debate, round 1: find the idea that wins

You are Sol, debating Claude (another AI) to find **the single best idea** for one developer to build and **win** the "Flip the Switch" hackathon. This is a real debate: you will see Claude's critique of your ideas in round 2 and must respond. Push hard. Be original, be honest, use evidence.

## Everything you need
- **Event:** `debate/EVENT.md` in this folder (rules, prizes, tracks, judging, schedule, every link). Live pages:
  - https://www.wemakedevs.org/hackathons/switch
  - https://www.devtoolsacademy.com/hackathons/flip-the-switch
- **Judging:**
  - Use of Switch, 30%: is it central, would it break without Switch?
  - Technical execution, 25%: does it run, can someone clone and reproduce it?
  - Creativity and impact, 25%: a fresh idea, a real team problem.
  - Presentation and docs, 20%: video plus README.

  The finalists are judged by Switch's own team, DevTools Academy and WeMakeDevs.
- **Switch source:** shallow clone at `E:\DevDrive\switch`. Read whatever you need: `docs/TEMPLATES.md`, `docs/official/**`, `examples/**`, `console/packages/plugins/src/switch-skill/SKILL.md`, `core/switch_core/**`, and the open issues via the web (https://github.com/sandbox-quantum/switch/issues).
- **Claude's current proposal:** "Slop Court" (`README.md`, `docs/*.md`).
- **Your own earlier review of it:** `review/SOL-REVIEW.md`. You recommended "change, not replace", with a "false accusation overturned" demo.
- **Competitor repos seen so far:**
  - an incident room (er-s-an/incidentroom);
  - issue triage with approval (kamalesh404/CrewPilot);
  - a PR reviewer plus standards checker (jaysid97/pr-pilot);
  - a payments escrow room (dukemawex/clearsend-room);
  - a smart-contract auditor (majorML/flip-all-agent);
  - a demo shop with bug triage (samprati18/switch-hack-demo).

  Search GitHub and the web for more, e.g. `"Flip the Switch" hackathon`, `switchagents`, `#HowISwitch`.
- **The builder:**
  - one person on Windows 11; Docker installed; Claude Code and Codex available; about 3.5 days (build window 4 Nov 00:01 → 7 Nov 23:59 IST);
  - based in Bengaluru, India; strong at frontend and design, and ships polished demos and films;
  - can use voice (Wispr Flow) for the $500 "Code with Wispr" side track;
  - has also built: an agent-harness desktop app (Windows, orchestrates many Claude and Codex workers), a zero-knowledge auth product, and a hand-drawn train-journey portfolio site.

## Your task in this round
1. **Generate at least 8 original ideas from scratch.** Do not anchor on Slop Court. Range widely:
   - Track 01 Business;
   - Track 02 Personal or Creative, which is thin on competition;
   - non-engineering domains;
   - ideas that make Switch's *unique* properties essential: rooms as shared state between humans and many agents, roles and leases, cross-room links, templates that agents run, room documents, cross-platform bridges, native question cards, budgets, the custom agent protocol.

   For each idea, give:
   - who suffers and how badly, with evidence (URLs);
   - why it needs Switch specifically, and which primitives;
   - the demo moment a judge remembers;
   - the build risk in 3.5 days, solo, on Windows;
   - likely overlap with other entries.
2. **Score each idea 1–10** on the four judging criteria, weighted 30/25/25/20, and on solo feasibility. Show the table.
3. **Pick your champion.** It may be Slop Court revised, or something new, but you must argue *why it beats Slop Court revised* (or why nothing does). Give a 150-word pitch, the core architecture, and the exact Switch primitives with source file references from `E:\DevDrive\switch`.
4. **Pre-empt Claude's attack:** list the 3 strongest objections to your champion and your answers.

## Rules
- Read-only: do not modify files, run Docker, install anything, or post or comment anywhere.
- Cite real URLs and file paths with line numbers. Never invent evidence; say "not verified" when unsure.
- Output one Markdown report, about 2,500–4,000 words. Start with a 5-line summary naming your champion.
