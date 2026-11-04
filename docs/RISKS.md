# Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **The decision, render and crew plan drift onto different revisions** (the biggest risk) | Medium | Fatal to the pitch | Every artifact carries `release_id` and `manifest_hash`; the call sheet and preview come from the same manifest; re-check before release |
| Switch server won't start on Windows (#1335) | Medium | Blocks day 1 | Docker Compose first; Console second |
| Discord bridge doesn't deliver MP4 attachments | Medium | Weakens the demo | Test on day 1, hour 2, from a crew account. A GIF uses the same upload path, so it's not a fallback; the fallback is a smaller MP4, then PNG frames |
| Someone other than the director answers a card | Medium | Wrong release | Check `answered_by` against the authorised list; reject and re-ask |
| A change lands mid-render or mid-send | Medium | Crew gets a stale plan | Serialized pipeline; re-check before sending; hold if the order is uncertain |
| Day 3 mixes engineering with the friends' shoot | High | Bad shoot or broken demo | Trust features move to day 2; day 3 is rehearse, freeze at noon, shoot |
| Mattermost activity card fails on template kickoff (#1158) | Medium | Cards in odd threads | Post questions as root messages (`thread_id: null`) |
| Agents return malformed JSON | High | Slows the loop | Strict schema, one retry, then "agent failed" shown honestly |
| Renders are slow | Medium | Video drags | Fixed assets, 5 s at 540p, renders in parallel; disclose any time compression |
| Scope creep | High | Missed deadline | The cut list in PLAN.md; feature freeze at noon on 7 Nov |
| Judges see "a film toy" | Medium | Weak impact score | Frame it as creator teams and small shoots; the hold and stale-reply moments show the coordination problem, not filmmaking |
| How often this happens is unproven | Known | Weaker impact claim | Claim only what's sourced (RESEARCH.md); say "not measured" |

## Day-1 abandonment test (6 focused hours)
With one scene and fixed assets, all of these must work:
- a proposal delivered through Switch;
- a rendered preview and a native human choice;
- a matching call sheet and preview delivered to Discord;
- a location change that invalidates the old choice and visibly updates both.

If this can't work without manual copying or editing, **abandon the production-room scope** and fall back to **Writers' Room**: one approved scene rendered from one manifest, reusing the room, documents, question and renderer.
