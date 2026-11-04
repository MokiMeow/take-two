**My final champion is a scoped merge: Take Two — the production room.** I would bet my own money on it, conditional on a hard day-one integration test. Claude, your critique improves the idea: the recurring workflow should be pre-production, and the disruption should demonstrate why it matters.

Research remained read-only. I checked Switch at commit `989225d8a13f6f36359c54f52d86aec01c4e0826` and refreshed public sources. Runtime reliability and demand from the proposed users remain **not verified**.

**1. Your five attacks**

**Attack 1: “Your scores don’t discriminate.” Conceded.**

My round-one table was inflated. Giving nearly everything an 8 or 9 concealed meaningful differences in delivery risk, evidence and Switch dependence.

The revised Slop Court score was particularly weak. My review said its integration needed architectural changes; the subsequent table effectively awarded those changes before implementation. The stronger design deserves consideration, but a feature list does not earn a 9.

The new scores below assess plausible hackathon deliverables. Feasibility is a separate gate: a beautiful proposal that cannot ship is a poor bet.

**Attack 2: “Is the pain real, and will judges understand it?” Partly conceded; better evidence exists.**

ScreenSkills establishes the assistant director’s responsibilities, not demand for Take Two.

StudioBinder’s production guidance supplies more concrete evidence: shooting plans change, multiple call-sheet versions cause confusion, departmental checks reveal dependencies, and confirming receipt matters. That supports **revision coordination as a recurring problem**. It remains vendor-authored guidance, not independent evidence that Indian student crews want our product. [StudioBinder’s production-call-sheet guide](https://www.studiobinder.com/blog/production-call-sheet/).

I cannot substantiate adoption among WhatsApp-first crews. The initial audience should therefore be **small filmmaking or creator teams already using a supported chat platform**. Bengaluru is the builder’s context, not a validated market segment.

For judges, open with an observable failure:

> “The director changed the scene. The crew still has yesterday’s location.”

Show the old call sheet and revised scene together. Within twenty seconds, establish that Take Two keeps the artistic decision, schedule and crew instructions consistent. The animatic makes the decision understandable; the coordinated release makes it useful.

**Attack 3: “It’s a one-off event.” Conceded on my original scope.**

The room should support:

**script lock → reviewed breakdown → schedule → approved call sheet → crew acknowledgment → next-day rollover.**

Script changes and departmental dependencies enter that loop between disruptions. StudioBinder describes preliminary schedules, departmental distribution, breakdowns and successive approvals as normal production work. [Call-sheet approval workflow](https://www.studiobinder.com/blog/how-call-sheets-are-approved-on-features-and-television/).

However, “useful throughout pre-production” must not become “build a production suite.” Our submission handles one supplied three-scene film and creates successive shoot-day rooms. No screenplay parser, equipment inventory or calendar synchronization.

I withdraw any implied promise of thirty days of daily engagement. A project-based workflow can still recur meaningfully.

**Attack 4: “The validator is trivial; who actually renders the artifact?” Conceded on the missing implementation contract.**

Availability checking is ordinary constraint validation. Continuity analysis is editorial judgment. Neither deserves inflated claims of algorithmic novelty.

The technical depth should come from a complete, inspectable chain:

1. Agents produce structured scene and schedule proposals.
2. A deterministic checker rejects declared constraint violations.
3. A fixed Remotion composition renders each valid alternative from its shot manifest.
4. The director selects a specific candidate revision.
5. The approved manifest produces both the final storyboard and call sheet.
6. The publisher releases that revision to the crew.

Remotion supports parameterized compositions and programmatic rendering; it does not supply our scene schema or guarantee artistic quality. [Parameterized videos](https://www.remotion.dev/docs/parameterized-rendering), [renderMedia](https://www.remotion.dev/docs/renderer/render-media).

Use existing hand-drawn assets and fixed camera/layout presets. Agents select supported shots and write dialogue; they do not generate arbitrary React code.

Each artifact records its source revision and manifest hash. Changing the selected location must change the visible background and call-sheet location together. That is a stronger execution demonstration than a detached storyboard appended to agent conversation.

**Attack 5: “Switch depth is thin.” Mostly conceded, with a limit on feature accumulation.**

Documents, agent-run templates, a meaningful cross-app handoff and native human decisions should become essential.

I would retain role-addressed delegation, but make the live scheduler takeover optional. Four days do not justify manufacturing a failure merely to exhibit another primitive.

Two source constraints change your merge:

- **Document ownership follows agent identity.** Assuming the Script Supervisor role does not grant permission to update another agent’s document. The deterministic coordinator should create canonical documents; the supervisor proposes editorial changes. [Document ownership contract](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:555).
- **Links are navigation pointers.** They do not grant membership or automatically deliver documents and messages. Publication must explicitly cross the room boundary. [Linked-room contract](E:/DevDrive/switch/console/packages/plugins/src/switch-skill/SKILL.md:404).

Your merge wins architecturally after those corrections and scope cuts.

**2. Re-scoring**

The official weights remain **Switch 30%, execution 25%, creativity/impact 25%, presentation/docs 20%**. [Judging criteria](https://www.devtoolsacademy.com/hackathons/flip-the-switch).

These are forecasts, not measured results. The scale is unrestricted: **1 means effectively undeliverable or absent; 5 means credible but ordinary; 10 means exceptional potential.** Feasibility measures delivering the stated scope, solo, within this window.

| Proposal | Switch | Execution | Creativity / impact | Presentation | Weighted /10 | Solo feasibility |
|---|---:|---:|---:|---:|---:|---:|
| Original Take Two | 5 | 6 | 6 | 8 | **6.10** | 8 |
| Heirloom | 6 | 7 | 7 | 8 | **6.90** | 7 |
| Open Doors | 7 | 4 | 6 | 5 | **5.60** | 4 |
| Claude’s Writers’ Room | 6 | 6 | 5 | 10 | **6.55** | 7 |
| Claude’s merge, uncut | 9 | 3 | 8 | 9 | **7.25** | 1 |
| **Scoped production-room merge** | **9** | **7** | **8** | **10** | **8.45** | **6** |
| Revised Slop Court | 7 | 5 | 4 | 8 | **5.95** | 5 |

The uncut merge’s feasibility score is deliberately severe: three specialist agent workflows, rendering, cross-app delivery, recurring rooms and takeover have no measured integration baseline. Scope reduction is a prerequisite.

Heirloom remains strong but depends on narrator participation and publication decisions that are harder to stage convincingly. Open Doors needs reliable venue facts and attendee involvement. Writers’ Room has excellent visual potential, but “agents write a film” leaves the collaboration problem less distinctive.

The scoped merge earns its advantage through **a consequential human choice propagated into matching deliverables**. Its presentation score assumes the builder executes that visual explanation exceptionally well.

**3. The champion**

**Pitch — 100 words**

Take Two is a production room for small film teams whose creative decisions keep changing the plan. A director and specialist agents turn a locked script into a scene breakdown, shooting schedule, and call sheet. When a location disappears, the room produces two feasible alternatives and renders each as a short animatic. The director chooses which artistic compromise preserves the story. That decision updates the canonical revision, generates the matching storyboard, and sends the approved changes to the crew's Discord. Switch carries the documents, role assignments, decision, and handoff, keeping yesterday's plan from quietly becoming tomorrow's expensive mistake on set.

**Build two reasoning agents and one deterministic coordinator.**

The Script Supervisor proposes breakdowns, preserves declared story requirements and explains creative consequences. The 1st AD proposes schedules against supplied availability, location and travel constraints.

The coordinator owns document publication, validation, rendering jobs, question handling and delivery recovery. **Storyboard is a deterministic capability, not a third reasoning agent.**

Use a private production room in Mattermost, a crew room in Discord, and shoot-day rooms created on Discord from a reusable template. The split has a purpose: private alternatives remain with production; approved instructions reach crew members, whose acknowledgments return through Switch.

This deployment scenario is a demo fixture until a real team validates the platform split.

**The essential Switch primitives**

| Primitive | Essential responsibility | What breaks without it |
|---|---|---|
| **Room documents** | Store script, constraints, candidate manifests and approved release records. Workers explicitly load them. | Agents and renderer lose their shared, inspectable input. |
| **Agent-run templates** | Coordinator creates each shoot-day room with instructions, participants and an explicit approved snapshot. | The repeatable day rollover requires manual provisioning. |
| **Exclusive roles and role-addressed messages** | Send work to the current `script-supervisor` or `first-ad`, rather than hard-coded provider names. | Role-based delegation and replacement stop working. |
| **Native questions** | Director chooses an identified candidate against identified source revisions. | The system cannot record the required creative authorization. |
| **Separate rooms, bridges and attachments** | Explicitly publish the approved call sheet and storyboard to Discord; receive crew replies. | The director’s decision never completes the crew handoff. |
| **Custom protocol participant** | Coordinator receives Switch events and enforces the release sequence. | Validation, decision processing and publication cannot advance. |

Source contracts: [template operation](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:1597), [room bridge and participant fields](E:/DevDrive/switch/docs/TEMPLATES.md:428), [role routing](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:804), [exclusive leases](E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:1131), [question schema](E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:124), [custom-agent registration](E:/DevDrive/switch/core/switch_core/bridges/agent/api/handlers.py:206).

Switch also documents native file delivery across bridges. Test actual MP4 delivery early; a local filesystem link is insufficient. [Attachment contract](E:/DevDrive/switch/console/packages/plugins/src/switch-skill/SKILL.md:360).

Create separate `script-r1`, `script-r2` and release documents, plus a current-release pointer. That revision scheme is application behavior, not a claim of native document version control.

Every proposal carries `{script_revision, constraints_revision, candidate_id, manifest_hash}`. Recheck those inputs when the human answers. Persist the outcome before acknowledging delivery. SQLite may hold recovery bookkeeping; workers obtain assignments and canonical inputs through Switch.

**The demo, approximately two minutes**

Use an explicitly fictional short: a promise, a private confession and a reconciliation.

| Time | Beat |
|---|---|
| **0:00–0:15** | Show script revision one, its breakdown, and the crew’s existing call sheet. Establish the private confession as the director’s requirement. |
| **0:15–0:30** | “Rooftop permission withdrawn.” The production room identifies the affected scene and invalidates the old location plan. |
| **0:30–0:55** | Two checked alternatives appear: a courtyard changes the intimacy; a stairwell preserves privacy but loses the sunset silhouette. Play each five-second animatic. |
| **0:55–1:10** | The director chooses the stairwell through a native question: “Keep the confession private; sacrifice the skyline.” |
| **1:10–1:35** | Revalidate current inputs. Publish revision two and generate the complete fifteen-second storyboard from the approved manifest. Show matching scene identifiers. |
| **1:35–1:55** | Coordinator creates the shoot-day Discord room from its template and sends the revised call sheet, change summary and storyboard. A human crew member acknowledges revision two. |
| **1:55–2:10** | Show the revision trail and repository instructions. State actual render latency; disclose any recording time compression. |

The two alternatives must remain meaningfully different. If the validator simply identifies a uniquely correct answer, the director has no artistic work left to do.

**4. The 4–7 November plan**

These are future exit tests, not checks already passed.

| Day | Work | Exit test |
|---|---|---|
| **4 Nov — prove the complete path** | Pin Switch and renderer versions. Connect both apps. Register the coordinator, create documents and a template room, obtain one structured worker proposal, render it, collect a native answer and deliver files. | A human choice produces a matching call sheet and animatic in Discord without manual transfer. Change the location once and repeat successfully. Apply the abandonment test below. |
| **5 Nov — make the choices useful** | Add the second worker, reviewed breakdown, two candidate previews and deterministic checks for availability, location windows, overlaps and declared travel. | Both alternatives satisfy declared constraints and show different compromises. An intentionally conflicting schedule is rejected with a specific explanation. |
| **6 Nov — make release trustworthy** | Complete revision invalidation, actor checks, expiry, restart recovery and retry handling. Demonstrate a second shoot-day template run. | An old answer cannot release changed inputs; processing the same outcome twice produces one logical release; restart preserves the pending decision. Crew receives only approved artifacts. |
| **7 Nov — reproduce and submit** | Freeze features. Test documented setup from a clean checkout with prerequisites available. Record the real workflow; finish README, video and submission. Target **8 PM IST**. | Setup produces the documented result; files open from Discord; README explains every essential Switch dependency. Submit before the official **11:59 PM IST** deadline. |

The deadline and required repository, video and README are confirmed on the [event page](https://www.devtoolsacademy.com/hackathons/flip-the-switch).

**The cut list**

Cut immediately: arbitrary screenplay ingestion, generated imagery, new voice infrastructure, autonomous filmmaking, calendars, weather feeds, equipment inventory, budgeting and concurrent films.

Cut next: a dedicated Storyboard agent, live lease-expiry theatrics, elaborate timeline UI and extra notification channels. Keep role routing; demonstrate takeover separately only if the core passes.

Preserve: two rendered compromises, revision-bound human choice, matching final artifacts, recurring day-room creation and real cross-app delivery. Removing these requires revising the pitch and scores.

Wispr proof and the blog come after the submission works. Existing assets and libraries are allowed; the Switch setup and workflow must be built during the event. [Official FAQ and side-track requirements](https://www.wemakedevs.org/hackathons/switch).

**5. The single biggest risk and abandonment test**

The biggest risk is **failing to keep the approved creative choice, rendered scene and published crew plan on the same revision**. That would reduce the submission to an attractive demonstration with disconnected outputs.

Time-box the day-one test to **six focused hours**. With one scene and fixed assets, require:

- A proposal delivered through Switch.
- A rendered preview and native human selection.
- A matching call sheet and storyboard delivered to Discord.
- A location change that invalidates the old choice and visibly updates both artifacts.

If this cannot work without manual editing or copying, abandon the production-room scope.

Switch to **Writers’ Room, narrowed to one approved scene rendered from one manifest**. That reuses the room, documents, question and renderer while removing scheduling and synchronized production releases. It is the cheapest credible fallback from the work already completed, even though Heirloom ranks higher as a fresh starting point.