# Round 3: Claude's own scenario pass (written before reading Sol's)

Legend: ✅ handled by the agreed design · 🟡 handled with a small change · ❌ needs a new capability

## A. Real disruptions

| Scenario | Status | What the room does / what must change |
|---|---|---|
| Location lost | ✅ | The core demo: two alternatives, rendered, the director picks, revision released |
| Permit refused for one time slot only | 🟡 | The same flow, but the constraint is a time window, not a whole location. The checker needs per-slot location windows |
| Noisy location (construction, traffic) | 🟡 | The AD offers swapping scene order (shoot the noisy-tolerant scene first). Needs "reorder scenes" as an option type, not just "change location" |
| Actor sick | 🟡 | Options: move their scenes to another day, rewrite to remove the line (Script Supervisor), or recast a small part. Needs per-person availability edits, and options can change the script itself |
| Actor running late | 🟡 | The AD reorders the day so their scenes come later; the call sheet updates call times only for affected people. Needs **per-person call times** and **partial updates** |
| Rain | 🟡 | Swap an exterior for an interior scene, or the rain-cover plan. Needs a "cover set" per day (a standard practice) stored in the room |
| Golden hour missed | 🟡 | The sun calculator (push idea 3) flags it before the shoot; on the day, move the scene to the next day's window |
| Equipment failure | 🟡 | Mostly a human or logistics problem. The room re-checks scenes that need that kit (a crane shot, a specific lens) and offers simpler shots. Needs a light "needs" list per scene |
| Director rewrites a scene the night before | ✅🟡 | Script revision → re-breakdown → schedule check → call sheet. This is the "normal day" loop, so it must work without an emergency |
| Client asks for changes (brand or creator shoots) | 🟡 | The client is a human in a **separate client room**. Their request becomes a proposal; the director accepts or negotiates; only approved changes reach the crew. A strong Switch story: private production room, client room, crew room |
| Overtime: scenes pushed to tomorrow | ✅ | Moving scenes to the next shoot-day room (created from the template). The day rollover we planned |
| Two changes at once | 🟡 | Queue changes; each new change invalidates pending options; the director sees one combined decision, never two half-plans |

## B. Messy human and system cases

| Case | Handling |
|---|---|
| The director doesn't answer by the deadline | The card expires. The crew keeps the last *approved* plan, marked "change pending", plus a reminder to the director. **Never auto-pick a creative choice** |
| The director rejects both options | A third card option: "Neither: here's my note" (free text). Agents make a new round with the note as a hard constraint. Limit 2 rounds, then the director decides manually |
| Two humans give conflicting instructions | Only the director role can decide. A producer can propose; their message becomes input, not a decision. The decision card only accepts the director (actor check) |
| Answer to an outdated question | Rejected: the card is tied to a revision. A new card is posted |
| A crew member replies to the old call sheet | The coordinator replies: "That's revision 1. The current plan is revision 2 [link]". Unconfirmed crew get a reminder; the AD sees who hasn't confirmed |
| An agent proposes an impossible option | The checker rejects it before the director sees it. If all options fail, the director gets "no feasible option found, here's why" |
| An agent proposes an unsafe option (roof edge, road at night) | A safety note is required in the scene manifest; the checker blocks flagged hazards with no mitigation. Keep it simple: a list of banned conditions |
| The renderer fails | The option is shown without a preview (text plus a still frame), marked "preview failed"; the decision isn't blocked |
| Switch, Discord or the bridge drops a message | The coordinator keeps an outbox; each release has an ID; a crew confirmation is tied to the ID; there are re-sends for missing confirmations |
| The coordinator restarts mid-decision | State is in SQLite plus Switch; pending cards are reloaded; outcomes are deduplicated |
| A new crew member joins mid-production | They get the current revision on joining the crew room (the coordinator listens for room joins) |

## C. Design changes I'd make
**Must have for the demo:**
- per-person call times and partial updates;
- a "neither, here's my note" option;
- the director-only decision check;
- expiry that keeps the last approved plan;
- the outdated-answer guard;
- confirmations tied to the revision.

**Should have:**
- a client room for brand or creator shoots (a big Switch story);
- the sun calculator;
- option types beyond location (reorder, move to another day, cut a line).

**Later:**
- equipment lists;
- a rain-cover set;
- a safety rule list;
- multiple concurrent changes.

## D. Demo scenarios I'd pick
1. **Lost location** (the drama, two rendered options, the creative choice).
2. **A creator or brand client asks for a change** in the client room: the director negotiates, and only the approved change reaches the crew. This shows Switch room boundaries and broadens the audience to creator teams.
3. **Actor running late, on the real shoot** with friends: a live partial update, where only the affected people's call times change and they confirm on Discord.

## E. Verdict
**Keep Take Two, adjusted.** The design handles most scenarios with small, consistent changes, because every disruption is the same loop:

> change → options → checks → human picks → one approved revision → everyone confirms

That's actually a strength. The pitch becomes: "every change on a shoot, big or small, goes through one loop, and the human makes the call." The main risk is scope; the must-have list is still about 2–3 days of work.
