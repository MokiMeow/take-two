**Verdict: adjust Take Two; keep the production room and broaden its change-handling contract.**  
**Audience: small crews and creator teams; the short film remains the demonstration story.**  
**Evidence: disruptions are well documented, but representative frequency estimates are not verified.**  
**Critical change: distinguish creative approval, valid instructions, successful publication, and crew acknowledgment.**  
**Demo: lost location, an actor’s shortened availability, and a stale call-sheet reply—then show the real scene.**

**1. What the evidence establishes**

Claude, the rooftop example survives, but our original generalization was premature. Different disruptions share a revision-and-coordination problem; they do not all require two animatics or a director’s decision.

I read both rounds and the event rules. The baseline is the two reasoning agents and deterministic coordinator in [ROUND2-SOL.md:101](<C:/Users/Mohith S/Desktop/slop-court/debate/ROUND2-SOL.md:101>). Switch source references below concern checkout `989225d8a13f6f36359c54f52d86aec01c4e0826`. This was read-only research: no files changed, installations, Docker execution, or external posts. Runtime reliability remains **not verified**. Firecrawl lacked credits; research continued through web search and retrieval.

“How often” needs care. The sources establish routine planning concerns and firsthand incidents, not a representative denominator for small shoots. Frequency descriptions below identify that distinction; they are not estimated probabilities.

| Disruption | Evidence and what we can say about frequency |
|---|---|
| **Location lost, permission refused, noise, access** | A filmmaker describes months of verbal approval followed by a refused permit. Scouting guidance explicitly checks noise, traffic, equipment space and power; the AD checklist includes access and clearances. **Verified incidents and standard planning concerns; incidence not verified.** [Permit account](https://www.reddit.com/r/Filmmakers/comments/1ggjimb/dealing_with_dnr_filming_permit_approval/), [scouting guidance](https://www.moviemaker.com/8-keys-to-location-scouting-video/), [ScreenSkills AD checklist](https://www.screenskills.com/media/7604/final-first-assistant-director-040423.pdf). |
| **Cast sick, late, unavailable, quits** | One student reports five last-minute cancellations and says cancellations have happened repeatedly. Another describes an availability reduction, a sick lead and missing extras on the same production. Published filmmaker accounts include an AD failing to arrive and a sound operator quitting. **Repeated within some accounts; population frequency not verified.** [Cancellations](https://www.reddit.com/r/Filmmakers/comments/1roghe2/actors_keep_cancelling_on_me_last_minute_what_can/), [compound disruption](https://www.reddit.com/r/Filmmakers/comments/2pbg8k/short_film_went_to_shit_was_a_disaster_on_set_i/), [MovieMaker accounts](https://www.moviemaker.com/pots-hooky-acts-of-god-losing-cast-crew-emergency/). |
| **Rain, missed light, heat** | A wedding videographer describes hail preventing coverage and rain forcing a reduced setup. Another reports four years without encountering rain, illustrating variation. A videographer describes client availability squeezing the remaining light window. Industry guidance treats heat as a production hazard. **Exposure-dependent; no universal rate verified.** [Wedding account](https://www.reddit.com/r/videography/comments/15rnmsj/best_way_to_handle_rain_at_an_event/), [wedding community](https://www.reddit.com/r/weddingvideography/comments/1vz8gzs/rainy_elopement/), [light window](https://www.reddit.com/r/videography/comments/1wzj2qq/help_shooting_with_my_first_client_tomorrow_and/), [AICP guidance](https://aicp.com/newsletter/article/102026-extreme-heat-and-inclement-weather-on-set). |
| **Equipment failure, missing batteries/cards** | Accounts include a camera failing during a wedding, forgotten chargers and forgotten memory cards. One commenter reports two corrupted cards across 550-plus weddings: useful individual experience, not a failure-rate estimate. **Multiple firsthand reports; representative frequency not verified.** [Camera failure](https://www.reddit.com/r/canon/comments/1n0xlo8/my_r6ii_failed_during_a_wedding/), [charger](https://www.reddit.com/r/videography/comments/hnfam9), [cards](https://www.reddit.com/r/videography/comments/1e319q5), [wedding footage discussion](https://www.reddit.com/r/videography/comments/1nc2aok). |
| **Rewrites, overnight director changes, client changes** | Filming in England explicitly lists rewrites and last-minute director/producer ideas as causes of schedule changes. A commercial videographer describes one interview becoming two-to-four interviews plus expanded B-roll the day before. **Recognized recurring workflow; incidence not verified.** [Production guide, p. 6](https://www.filminginengland.co.uk/wp-content/uploads/2023/01/locationstoolkitfcv2-compressed-1.pdf), [client account](https://www.reddit.com/r/videography/comments/1kxiqbg/how_do_you_deal_with_this/). |
| **Overruns, pushed scenes, simultaneous changes** | Scheduling guidance describes changing coverage, extra takes and weather as normal reasons to revise schedules. The student account above demonstrates several interacting failures. **Schedule revision is described as normal; overtime and compound-event rates not verified.** [Scheduling guidance](https://www.studiobinder.com/blog/shooting-schedule-format/). |
| **Unconfirmed crew, old instructions, replacements** | Call-sheet guidance warns about version confusion and recipients failing to confirm. Filmmaker accounts describe emergency replacements. **Recurring coordination concern; the vendor’s frequency language is not survey evidence.** [Call-sheet guidance](https://www.studiobinder.com/blog/production-call-sheet/), [replacement accounts](https://www.moviemaker.com/pots-hooky-acts-of-god-losing-cast-crew-emergency/). |
| **Client approval and budget caps** | The commercial account includes expanded scope exceeding the client’s available budget. ScreenSkills assigns resource allocation and budget responsibility to line producers. **Concrete example plus established responsibility; approval-delay frequency not verified.** [Scope/budget account](https://www.reddit.com/r/videography/comments/1kxiqbg/how_do_you_deal_with_this/), [line-producer responsibilities](https://www.screenskills.com/skills-checklists/scripted-film-and-tv/production-department/line-producer-skills/). |

Creator work also has a different recovery cost. An r/NewTubers creator describes recording an educational episode after substantial preparation, discovering unusable audio and ultimately reshooting. That supports equipment checks and pickup planning, but does not prove demand for multi-agent coordination among solo creators. [Creator account](https://www.reddit.com/r/NewTubers/comments/1533tfu).

**2. The common room contract**

“As is” below means **specified in round two**, not implemented or tested. Value assessments are my judgment.

Retain the Script Supervisor, 1st AD and coordinator. Let smaller teams assign several human responsibilities to one person. For creator work, “script” may be a brief or shot list; for weddings, it is a coverage plan with nonrepeatable moments.

Every change follows this sequence:

1. **Record:** coordinator captures the report, reporter and affected facts in a new room-document revision. Unconfirmed information remains unknown.
2. **Delegate:** role-addressed messages send editorial consequences to the Supervisor and practical consequences to the AD.
3. **Check:** coordinator validates declared constraints. Humans verify facts the software cannot observe.
4. **Decide:** the appropriate human answers a revision-bound native question when a consequential choice remains.
5. **Release:** recheck inputs, persist the approved manifest, generate matching instructions, explicitly publish to the crew room and collect revision-specific acknowledgments.

Switch supplies [documents and creator ownership](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:555), [role-addressed delegation](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:804), [native question fields](E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:124), and [bridged attachments](E:/DevDrive/switch/console/packages/plugins/src/switch-skill/SKILL.md:360). **Validation, dependencies, business authority and release states are Take Two application behavior.**

Two changes to our contract are essential:

- A newly invalid plan triggers an immediate, clearly identified **hold/superseded notice**. Waiting for a replacement must not leave the old location apparently usable.
- **Render creative choices; publish logistical changes quickly.** A revised call time rarely benefits from an animatic.

**3. Running the disruptions through it**

| Scenario; handled as is? | What the room does, in order | Required design change; value |
|---|---|---|
| **Location lost — yes. Permit refused — partly.** | Coordinator revises location constraints → delegates through roles → AD checks supplied alternatives and travel → Supervisor explains story effects → human chooses through a question → coordinator releases matching artifacts. | Add explicit permission states: confirmed, refused, unknown. A plausible location is not an authorized one. **Very high value** across small shoots. |
| **Noise or inaccessible location — partly.** | Human reports construction noise, locked access or unusable loading route → coordinator updates documents → AD proposes another window/location → Supervisor assesses changed dialogue or staging → responsible human verifies access/sound and approves. | Represent sound suitability, access windows, setup and teardown. Never label audio “fixable in post” as a checked fact. **High value**, especially interviews and dialogue. |
| **Cast sick, late or availability changed — yes for declared windows; partly for uncertainty.** | Coordinator records revised availability → AD proposes inserts first, reordered scenes or reduced coverage → Supervisor checks story dependencies → director chooses → crew receives revised calls. | Distinguish confirmed arrival from an uncertain ETA; assign a check-in deadline. Do not schedule around an optimistic guess. **Very high value** for volunteer and student crews. |
| **Cast quits — partly.** | Coordinator marks the performer unavailable → AD identifies blocked scenes → Supervisor proposes rewriting, postponement or a supplied replacement → director/producer decides via question → coordinator revises script and schedule together. | Track completed footage and recasting continuity. The room cannot find or hire a replacement automatically. **High impact**, occurrence rate unverified. |
| **Rain — partly.** | Human supplies conditions → coordinator changes constraints → AD checks a prepared cover scene using available cast and locations → Supervisor explains continuity consequences → responsible human approves → coordinator publishes the switch. | Add weather suitability and prepared fallback scenes. Cover-set advice stresses readiness, available cast and minimal moving time. **High value for exterior work.** [AD-oriented guidance](https://www.prodslate.com/blog/cover-sets-and-weather-contingency). |
| **Golden hour missed — partly.** | Coordinator records the expired light window → AD removes impossible slots → Supervisor proposes accepting a different look, moving indoors or postponing → director selects the aesthetic compromise → matching instructions are released. | Explicit light windows and shot priorities; no automatic weather/sun API needed. A completed light window cannot be recovered by rearranging the remaining minutes. **High value where the look depends on it.** |
| **Heat — no explicit handling.** | Human flags conditions → coordinator puts affected work on hold → AD proposes a revised schedule using human-supplied restrictions → responsible on-set person confirms conditions before release. | A safety hold and human clearance field. The model must not invent safe exposure thresholds or override restrictions. **Critical consequence**, even if absent from the demo shoot. |
| **Equipment fails; batteries/cards missing — no explicit resource model.** | Operator reports the unavailable capability → coordinator revises documents → AD checks replacement arrival or remaining kit → Supervisor proposes supported coverage changes → operator verifies compatibility → director approves any creative loss. | Small capability checklist, owner and readiness status; no inventory system. **High value**, although grabbing a spare may need only a brief update. Software cannot recover unrecorded moments. |
| **Rewrite or director changes a scene overnight — yes within the supplied scene schema.** | Coordinator stores the requested script revision → Supervisor updates breakdown and story requirements → AD recalculates requirements/durations → coordinator invalidates old candidates → director approves a checked version → new call sheet and storyboard publish together. | Include props, wardrobe and already-shot material in the supplied constraints. Arbitrary screenplay ingestion remains outside scope. **Very high value** and a strong recurring use. |
| **Creator or brand client changes the brief — partly.** | Coordinator records the request without treating it as approval → Supervisor compares it with required deliverables → AD estimates extra work → producer confirms feasibility/cost → client approves the identified scope → coordinator releases instructions. | Add named client authority and required deliverables, such as a hero-product shot or vertical version. **Very high value** for commercial teams; director approval alone is insufficient. |
| **Overtime or scenes pushed to another day — partly.** | Coordinator records completed, omitted and unfinished work → AD compares remaining work with hard stop → Supervisor identifies minimum story coverage → director chooses what to drop; producer approves any permitted extension → coordinator publishes both affected days. | Actual progress, hard stops and an explicit carryover list. Use the existing [room-template primitive](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:1597). A new room does not itself reserve cast or locations. **Very high value.** |
| **Two changes at once — partly.** | Location loss and actor departure enter one serialized change queue → coordinator creates a combined constraints revision → both agents reload it → previous candidates/questions become obsolete → human chooses against the combined situation. | One active decision per shoot; input-version check at approval and publication. Existing revision binding helps, but concurrency rules were underspecified. **Essential reliability value.** |
| **Crew does not confirm or follows an old call sheet — partly.** | Coordinator publishes a numbered release through Switch → records each person’s acknowledgment → flags missing/stale replies → AD follows up with affected people → only explicit current-revision replies count. | Per-person acknowledgment state and deadline. A read receipt, emoji or delivery response is insufficient evidence of understanding. **Very high practical value.** |
| **New crew member joins mid-production — partly.** | Human adds the person to the appropriate crew room → coordinator explicitly posts the current approved snapshot, role and upcoming duties → newcomer confirms revision and availability → AD checks any new constraint. | Onboarding snapshot and roster update. Room links do not confer access or transfer documents. **Medium-to-high value**, especially replacements. [Link contract](E:/DevDrive/switch/console/packages/plugins/src/switch-skill/SKILL.md:404). |
| **Budget cap or pending permission — no explicit gate.** | Coordinator records cap/permission owner → AD supplies estimated incremental costs → deterministic checker compares known totals → producer/client decides scope or additional authorization through questions → release waits for required clearances. | Simple estimates, unknown-cost flags and named approvals. Switch’s agent-spend controls are not a shoot budget. **High value**; accounting and permit applications remain outside scope. |

For weddings and events, the room adapts **coverage**, not reality: the ceremony cannot be moved to tomorrow merely because an agent finds a convenient slot. Fixed event moments and the person authorized to alter arrangements must be declared constraints.

**4. Messy humans and system failures**

These are exact proposed behaviors, with native guarantees separated from application responsibilities.

**Director misses the deadline.**  
The question expires; silence selects nothing. Switch checks expiry when answering and has a timer-driven expiry operation. Coordinator records “decision required,” alerts the designated human and keeps affected work on hold. An earlier plan remains usable only where still valid. Any delegated fallback authority must have been explicitly recorded beforehand. [Answer/expiry enforcement](E:/DevDrive/switch/core/switch_core/session_activity/service.py:499), [expiry service](E:/DevDrive/switch/core/switch_core/session_activity/service.py:581).

**Director rejects both options.**  
Offer “Neither—revise” alongside candidates, with custom feedback enabled. Coordinator records rejection without publishing, asks which requirement failed, and delegates a bounded revision. After two unsuccessful proposal cycles, escalate to direct human planning, postponement or cancellation. Two alternatives are a presentation pattern, not a forced-choice policy. [Question options and custom answers](E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:114).

**Two humans give conflicting instructions.**  
Maintain named authority by decision: creative choice, spending, client deliverable and location permission. Conflicting instructions become a recorded conflict; affected release pauses until the relevant people resolve it. Switch restricts who may address an agent and records answerer identity, but that is not a production authority hierarchy. Even its first accepted answer cannot resolve a director–producer disagreement. [Addressing policy](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:2233), [answer recording](E:/DevDrive/switch/core/switch_core/session_activity/service.py:465).

**Someone answers an outdated question.**  
On input change, coordinator closes the pending request and opens a new one. On every outcome, compare request ID, script/constraints revisions, candidate and manifest hash with current state. A mismatched answer is retained as history and rejected for release. Switch rejects closed requests; Take Two supplies semantic revision checking. Serialize the final check and local release commitment. [Close endpoint](E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:264), [closed-request refusal](E:/DevDrive/switch/core/switch_core/session_activity/service.py:502).

**Crew replies to the old call sheet.**  
“Confirmed R2” cannot acknowledge R3. Coordinator sends the current release and specific changed instructions, then requests a new acknowledgment. If a thread reference is missing, an unqualified “yes” remains ambiguous. Switch maps external thread roots but can fall back to top-level posting when mapping fails—therefore include the release identifier in the reply itself. [Thread mapping/fallback](E:/DevDrive/switch/core/switch_core/bridges/collaboration/collaboration_core.py:1160).

**Agent proposes something impossible or unsafe.**  
Reject declared violations before presenting candidates: unavailable actor, refused location, insufficient travel/setup, missing required equipment or exceeded cap. Unsupported facts stay unknown. Human inspection remains necessary for real conditions and hazards; director preference cannot override a hard safety restriction. Log the rejection in a room document and request correction through the responsible role. Switch routes that work; the validator and safety policy are ours. [Role routing](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:828).

**Renderer fails.**  
Persist a job keyed by manifest hash; retry once, then expose the failure. Never substitute an older visual. For urgent logistics, an approved text call sheet may publish with “visual pending,” using the same manifest. For a creative comparison, offer manifest-derived static panels/text if the director accepts that review format. The promised demo still fails its visual acceptance criterion without a working render. Switch transports files; it does not guarantee rendering. [Attachment boundary](E:/DevDrive/switch/console/packages/plugins/src/switch-skill/SKILL.md:360).

**Switch, Discord or the bridge drops a message.**  
Distinguish three failures:

- **Agent delivery:** resume from the persisted event position. Switch stores agent events and reports retention gaps; on a gap, reload documents and reconcile room history.
- **Lost decision notification:** fetch unacknowledged outcomes; persist processing before marking the outcome delivered.
- **External publication or inbound crew reply:** retain pending/uncertain status, reconcile available history and retry using the same release ID. If receipt is still unknown, the AD contacts the person directly and records the result.

Discord reconnect support exists, but it does not prove every end-to-end message arrived. A repeated visible post is preferable to falsely claiming receipt; duplicate posts must identify the same logical release. [Durable events and gaps](E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/event_buffer.py:23), [outcome recovery](E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:274), [Discord reconnect](E:/DevDrive/switch/core/switch_core/bridges/collaboration/discord/gateway.py:162).

**Coordinator restarts mid-decision.**  
Restore its stable agent identity, originating session/request IDs, input revisions, event position, render jobs and publication ledger. Reconnect, reload canonical documents, fetch outstanding outcomes and reconcile unfinished releases. Reopening the same native question is idempotent only with identical content. Deduplicate release commitment locally; replay pending effects afterward. A different agent assuming a role cannot update the previous creator’s documents. [Idempotent question opening](E:/DevDrive/switch/core/switch_core/session_activity/service.py:374), [document ownership](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:563).

Crucially, the question API’s **“delivered” means the coordinator acknowledged the outcome**, not that Discord received the call sheet or a crew member understood it.

**5. Changes without building a production suite**

| Priority | Change |
|---|---|
| **Must have for the demo** | One serialized change/decision pipeline; revision-bound candidates; revalidation before publication; immediate supersession/hold notices; “neither” and expiry handling; named decision-makers. |
| **Must have for the demo** | Durable coordinator ledger and recovery; separate approved/published/acknowledged states; release IDs in artifacts and replies; reject stale acknowledgments; matching manifest hashes. |
| **Must have for the demo** | Small supplied constraint schema covering availability, permission, location windows, travel/setup, hard stops and required capabilities. Unknown facts cannot silently pass. |
| **Must have for the demo** | Creative-preview path plus fast logistical path; bounded agent/render retries; visible failure states. Keep two reasoning agents. |
| **Should have** | Completed-shot/carryover tracking, newcomer onboarding, simple incremental cost cap, client approval gate, prepared rain fallback and human-entered light windows. |
| **Later** | Forecast/calendar integrations, full inventory, rate cards/payroll, arbitrary screenplay parsing, automatic casting, permit workflows, multiple concurrent productions and additional chat platforms. |

Verification should exercise stale answers, duplicate outcomes, a restart, rejected constraints and failed publication. Acceptance is a human receiving and acknowledging the correct revision—not a green status assembled from successful API calls.

**6. The approximately 2:30 demo**

Choose **two principal scenarios**, with the acknowledgment failure connecting them.

**Scenario A: location lost.**  
Keep it because two visibly different compromises make human creative judgment legible: privacy versus openness, intimacy versus skyline. It exercises documents, role delegation, checked candidates, native questions and matching artifacts.

**Scenario B: actor must leave earlier while that decision is pending.**  
This exposes a different failure: yesterday’s valid alternative becomes impossible. It demonstrates revision invalidation, combined constraints and schedule/coverage judgment. It also makes the fast logistical path useful.

| Time | What judges see |
|---|---|
| **0:00–0:15** | Existing scene, required story beat and crew’s original call sheet. Explain the changing-plan problem. |
| **0:15–1:00** | Report the lost location; agents produce two checked, five-second previews with different creative costs. |
| **1:00–1:35** | Actor confirms an earlier departure. Old question closes; agents revise. Director chooses reduced coverage that preserves the confession. |
| **1:35–2:00** | Matching revised instructions reach the template-created Discord shoot-day room. Crew replies to the old release; coordinator requests and receives the current acknowledgment. |
| **2:00–2:30** | Show a short excerpt of the resulting real scene beside its approved plan, then the revision trail and reproduction instructions. Disclose compressed waiting/render time. |

This matches the event’s emphasis on central Switch use, execution and presentation in [EVENT.md:44](<C:/Users/Mohith S/Desktop/slop-court/debate/EVENT.md:44>).

**The real shoot should test shortened availability.** On 6 November, make a 30-second scene with two performers and one friend helping. Record actual availability and a real hard stop; choose between fuller coverage and a simpler setup. Show that the chosen plan was shootable. Any staged location withdrawal must be labeled as simulated. Do not manufacture a real permission dispute or pressure friends to remain late.

**7. Verdict**

**Adjust.** The evidence supports changing plans and inconsistent instructions as real problems. The architecture can address their shared coordination burden. It cannot replace location verification, equipment redundancy, experienced scheduling or on-set judgment. Product demand and measurable time savings remain **not verified**.

Our strongest claim is therefore narrower and more defensible: **a consequential human decision reaches everyone as one consistent, current plan, with unresolved receipt made visible.**

**Updated design:** Take Two is a Switch production room for small crews and creator teams whose shoot plans keep changing. A human lead, Script Supervisor agent and 1st AD agent work from a supplied script or brief and declared constraints. A deterministic coordinator records changes, checks proposals, routes decisions to the responsible human and invalidates obsolete questions. Creative compromises can receive short visual previews; logistical updates take a faster text path. Approved instructions and matching artifacts are explicitly published to crew rooms, with revision-specific acknowledgments, visible holds and restart recovery. The short film demonstrates the workflow; the product’s core is coordinating changes across story, feasibility and people.