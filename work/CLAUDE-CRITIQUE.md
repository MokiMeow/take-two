# Claude's critique (written before reading Codex's W7)

## Honest scores today
| Criterion | Score | Why |
|---|---|---|
| Use of Switch (30%) | 6/10 | Switch carries rooms, identities, question cards and media, so it is central. But the crew side (Discord bridge) is unproven, and judges will only *see* Mattermost text and one card type. Half of what makes it "Switch" is invisible. |
| Technical execution (25%) | 7/10 | Real loop, 286 tests, four-problem day against real Switch. But the two LLM agents are **simulated** in every rehearsal so far; real Claude Code / Codex agents in Console have never answered a job. Reproducing needs Docker + Console + agents + Discord. |
| Creativity and impact (25%) | 6/10 | Strong, specific problem and good visual identity. Risk: it reads as "a scheduler with extra steps". The LLMs' contribution (story must-keep, drafting plans) is real but quiet; the checker and releases do the impressive work. |
| Presentation (20%) | 7/10 | Dashboard, set models, explainer and day replay are strong. README and final video are not written yet. |

## Weak points of the idea
1. **The people barely touch Switch.** Crew type "confirm r2" as text; reports like "I have to leave at 6" sit as pending until someone retypes them as `/change`. That is the moment where an agent + Switch should shine, and today it is a dead end.
2. **The agents don't visibly think.** In the video, plans just appear. A judge doesn't see the script supervisor reject a plan on story grounds, or the AD reason about travel. The "two agents with different jobs" story is invisible.
3. **Only one decider, one card.** The crew never gets a card. Switch question cards to each affected crew member ("Release 3: your call moves to 15:25 · Confirm / Can't make it") would make Switch obviously central and remove the most error-prone text parsing.
4. **Reproducibility.** A judge without Discord and without two agent subscriptions can't see anything happen. We have `scripts/demo_day.py` (real Switch, simulated people/workers) but it isn't packaged as "run this one command".
5. **Real-agent risk.** The first time real Claude Code / Codex agents receive a job will be on Thursday at the earliest. JSON format drift is likely; one retry exists, but no fallback.

## What I'd add (ranked by judge impact ÷ risk)
1. **Crew cards.** Each release sends affected crew a native Switch question card: Confirm / Can't make it (+ note). "Can't make it" becomes a pending change for the AD. Uses the same approval machinery as the director card. Visible, simple, very Switch.
2. **Free text → proposed change → one-tap confirm.** When Maya writes "Sorry, I have to leave at 6", the script supervisor (or a small parser agent) turns it into `/change person maya hard_stop 18:00` and the AD gets a card: "Record this? Yes / Edit / Ignore". Humans still decide; the LLM does the boring translation. This is the best single "agent + person finish a task together" moment.
3. **Show the agents' reasoning in the room.** Each agent posts a one-line, human-readable summary with its JSON ("Stairwell keeps it private; park adds passers-by"). The supervisor visibly **vetoes** one AD plan on story grounds in the demo.
4. **One-command judge demo.** `scripts/judge_demo.ps1`: checks Docker/Switch, runs the four-problem day with simulated people/workers against the local Switch, opens the dashboard and Mattermost. 15 minutes from clone, no Discord or subscriptions.
5. **"What changed for me" digest.** When a crew member asks "@take-two what's my call?", the coordinator replies with their personal call, scene list and what changed since the release they last confirmed. Cheap, delightful, Switch-native.

## Risks and cheapest mitigation
- Real agents' format: test Thursday morning with Console agents; keep one-retry + "AD agent unavailable, using last checked plan" message; never block on an agent.
- Discord bridge: configure Thursday; if it fails, the crew room is a second Mattermost channel and we say so honestly.
- Render time (~26 s preview): pre-warm at start; card waits for previews already (W4).
- Live shoot: friends' real hard stop; keep it short.

## What I'd cut
Nothing big. I would *not* build more change types; four is enough. Spend the remaining effort on people-facing Switch interactions (1–3) and on the judge path (4).
