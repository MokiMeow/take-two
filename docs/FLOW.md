# Flow: one change, end to end

The demo story: a three-scene short. Scene 3 is a **confession**. The hard story rule is that the confession is *intelligible and confidential within the story*. A secluded look and a sunset are the director's *preferences*. Shoot day is 6 Nov; all times are IST.

## Before anything goes wrong (the normal day)
1. The director locks the script. The coordinator stores it as the `script-r1` document.
2. The Script Supervisor proposes a **scene breakdown** (people, props, hard rules and preferences per scene). The director reviews it.
3. The 1st AD proposes a schedule as full manifests (times, setup and wrap, people, kit). The checker passes it.
4. The director approves it with one question card.
5. The coordinator creates `#day-1` on Discord from the shoot-day template and uploads **release 1**: the call sheet PNG plus a text summary.
6. Crew reply "confirm r1". The AD sees 3 of 3 confirmed.

## Change 1: the rooftop is lost
| # | Where | What you see |
|---|---|---|
| 1 | `#production` | The producer (the named permission authority) types `/change location rooftop permission refused` |
| 2 | Coordinator | Records `constraints-r2`. Scene 3 in release 1 becomes **invalid immediately** |
| 3 | `#crew` | Within seconds: **"Scene 3 is ON HOLD. Don't go to the rooftop. Update coming."** Scenes 1 and 2 stay valid |
| 4 | `#production` | Coordinator → `@script-supervisor`: "s3 lost its location. What must it keep?" Reply: the hard rule plus the preferences |
| 5 | `#production` | Coordinator → `@first-ad`, with that answer: "Find options for s3." The AD proposes three manifests |
| 6 | Checker | **Courtyard: fail** (permission window ends at 17:00). **Stairwell 16:00–17:15: pass. Park bench 16:45–18:15: pass** (the light holds until 18:20) |
| 7 | Renderer | Two 5-second sketch previews: **Stairwell** (secluded, no sunset) and **Park bench** (sunset, but people in the background: less intimate, still confidential in the story) |
| 8 | `#production` | A question card for the director: A / B / "Neither, here's my note". Expires in 2 hours |

## Change 2: the actor has to leave early (while change 1 is still pending)
| # | Where | What you see |
|---|---|---|
| 9 | `#crew` | The actor: "Sorry, I have to leave at 6." A crew-side pending report is created |
| 10 | `#production` | The AD confirms it: `/change person maya hard_stop 18:00`. The coordinator records `constraints-r3` |
| 11 | Coordinator | The open question was bound to r2, so it **closes**: "This question is outdated, new options coming." Pending jobs and renders are cancelled |
| 12 | Checker | **Park now fails** (it ends at 18:15, after Maya's 18:00 hard stop). The AD offers the stairwell at full coverage (16:00–17:15) or with reduced coverage (16:30–17:15, one angle fewer, more setup buffer). Moving to day 2 isn't offered, because day-2 availability is `unknown` |
| 13 | `#production` | A new question card. The director picks **"Stairwell, reduced coverage"**, with the note "keep the confession private". The coordinator checks that the answer came from the director |

## Release
| # | Where | What you see |
|---|---|---|
| 14 | Coordinator | Re-checks that r1 and r3 are still current, commits release 2 with its outbox, renders the call sheet from the approved manifest, and checks again just before sending |
| 15 | `#day-1` (Discord) | **Release 2**: call sheet PNG, the stairwell preview MP4, a "what changed" line. Only the affected people get new call times |
| 16 | `#crew` | One crew member replies "ok see you at rooftop" to release 1. The coordinator: "That's release 1. Current plan is release 2 (stairwell). Please confirm r2." |
| 17 | `#crew` | They reply "confirm r2". The AD sees 3 of 3 on r2 (affected people re-confirmed; the others' duties carried forward) |

## When things go wrong in the system
| Problem | What happens |
|---|---|
| Director doesn't answer before expiry | Nothing is picked. The hold stays, the director gets a reminder, and the still-valid scenes stay usable |
| Director picks "Neither" | Their note becomes a hard constraint for one more round. After 2 rounds the director decides by hand |
| Someone other than the director answers | Switch accepts it, the coordinator doesn't: nothing is released, and a fresh card is posted |
| Answer to an outdated question | Rejected: the question is bound to old revisions |
| An agent misses its deadline or sends bad JSON | One retry, then "agent failed" is shown in `#production` |
| Render fails | The option is shown as text plus "preview failed". The decision can go on, but the demo needs a working render |
| Coordinator restarts mid-decision | It restores its identity, fetches undelivered outcomes from Switch, ignores duplicates and resumes |
| A Discord upload times out | The release is marked `uncertain` for that room; it reconciles, then retries with the same release ID |
