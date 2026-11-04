# Flip the Switch Hackathon: everything in one place

Collected 3 Nov 2026 from the WeMakeDevs pages (Overview, Rules, Schedule, Resources), the DevTools Academy page and the Switch repo on GitHub.

## The short version
- **What:** connect an AI agent you already use (Claude Code, Codex, OpenCode, Cursor, Antigravity) to a team chat (Slack, Teams, Discord, Telegram, Mattermost) using **Switch**. Build a workflow where at least one agent and at least one person finish a real task together.
- **When:** hacking runs **Wed 4 Nov, 12:01 AM IST → Sat 7 Nov, 11:59 PM IST**. The kickoff livestream already happened (Mon 2 Nov, 9 PM IST).
- **Where:** online.
- **Teams:** solo or up to 4. Teammates can be added until submissions close.
- **Cost:** free. Switch is open source; you bring your own agent subscription or API key.
- **Prize pool:** $10,000 (as advertised).
- **Must:** Switch is central (the project breaks without it), and the README shows how.

## Prizes
The two sites don't fully agree. Both versions are below.

| Prize | WeMakeDevs page | DevTools Academy page |
|---|---|---|
| Track 01: Best Business Workflow | $2,000 cash | to be announced |
| Track 02: Best Personal or Creative Workflow | $2,000 cash | to be announced |
| Track 03: Best Core Contribution | $100 × top 20 PRs | $100 × top 10 PRs |
| **Code with Wispr** (side track) | **$500, best project built by voice** | not listed |
| Best Blog (side track) | AirPods 5 | AirPods 5 for each of the top 5 posts |
| #HowISwitch social posts | Logitech mechanical keyboard, top 5 | swag, top 20 |
| Random draw | swag for 20 random projects | n/a |
| Star the Switch repo | chance at a Keychron keyboard | chance at a Keychron keyboard |
| Everyone who submits | certificate | certificate |

The listed cash adds up to about $6,500, not the advertised $10,000, so the page doesn't explain the remaining $3,500.

## Tracks
1. **Best Business Workflow:** practical people + agent work. Open to non-technical people too.
2. **Best Personal or Creative Workflow:** everyday tasks, personal projects, creative work.
3. **Best Core Contribution:** a real PR to Switch's open-source core.
   - Only issues labelled `hackathon` count, one person per issue, and you must be assigned first.
   - To claim one: comment on the issue with your plan and tag @petr-sandbox. Read CONTRIBUTING.md and sign the CLA on your first PR. Link the issue with `Closes #N`.
   - **Max 5 open PRs.** No typo or formatting fixes, and no unreviewed AI output. Issues with 48 h of no activity may be reassigned. The PR must be open by 7 Nov, 11:59 PM IST.
   - **Status on 3 Nov: all 63 open `hackathon` issues are already assigned.** Watch for new ones or reassignments.
- **Side track, Code with Wispr:** build by voice with Wispr Flow. Needs a **Wispr Flow Insights screenshot** (from the desktop app) as proof. Can be entered with any track. There's one month of Wispr Flow Pro free with code `WEMAKEDEVS`.
- **Side track, Best Blog:** a post about building with Switch: what you made, the setup, and what you learned. Can be entered alone or with a track.

You can enter more than one track.

## Judging (DevTools Academy page; the WeMakeDevs page shows the same four at 0%)
| Criterion | Weight | Question they ask |
|---|---|---|
| Use of Switch | 30% | Is Switch central? Would it break without it? |
| Technical execution | 25% | Does it run? Can someone clone and reproduce it? |
| Creativity and impact | 25% | Fresh idea, real team problem? |
| Presentation and docs | 20% | Do the demo video and README explain the build and the Switch usage? |

Process: WeMakeDevs reviews every submission and shortlists. Then a panel from Switch, DevTools Academy and WeMakeDevs picks the winners.

Blog judging looks at clarity, accuracy, and how much it helps a first-time Switch user.

## What to submit
1. A **public GitHub repo**.
2. A **short demo video** of the workflow running.
3. A **README** covering:
   - which agents are connected;
   - how the channel or room is set up;
   - how to run it;
   - clearly, how Switch is used.
4. Optional extras:
   - a blog post (enters Best Blog);
   - a Wispr Insights screenshot (Code with Wispr);
   - an #HowISwitch post on X.

The submission form is reached through the Register/Sign-in flow on wemakedevs.org. Its fields aren't shown publicly.

## Schedule (IST)
| When | What |
|---|---|
| now | register, star the repo, join the Discord; Track 03 issues can be claimed now |
| Mon 2 Nov, 9:00 PM | kickoff livestream (done) |
| Wed 4 Nov, 12:01 AM | hacking begins |
| Sat 7 Nov, 11:59 PM | submissions close (repo, video, README); Track 03 PRs must be open |
| early Nov | judging and shortlist |
| TBA | winners announced |

## Rules (legal page, condensed)
- **Age and sanctions:** 18+ (or the age of majority where you live). Not on sanctions lists, and not in a comprehensively sanctioned country.
- **One real person, one identity:**
  - no bots, multiple accounts, disposable emails, collusion or vote manipulation;
  - AI tools are allowed for building;
  - identity checks are possible, and refusing one forfeits the prize.
- **Who can't win:** sponsor staff, judges, agencies, and their families or households. If your job restricts this kind of thing, get permission.
- **Ownership:**
  - you keep your work, but grant the sponsor a broad licence to host and promote it;
  - your work must be original and follow its open-source licences, with no malicious code.
- **Disqualification:** possible for breaking rules, false information, failed verification, or tampering.
- **Prizes:** non-transferable. They can be substituted with one of equal value. You pay your own taxes (W-8BEN for India). A prize unclaimed 30 days after notice can be given to someone else.
- **Event changes:** the sponsor may change or cancel the event. US law applies.
- **Existing agents/templates:** allowed, but the **Switch setup and workflow must be built during the hackathon**. You must be able to explain everything you submit.

## What you need (setup)
- **Switch Console** plus **Docker**. Console starts a local server that bundles Mattermost, so you don't need Slack or admin access.
  - The latest Console is **0.40.1** (21 Oct 2026). **Windows is early access.**
- **An agent:** Claude Code, Codex and OpenCode work out of the box. Custom agents (LangChain, Google ADK, OpenAI…) join through the agent protocol (SSE in, HTTP out).
- **The docs as MCP**, so your agent can walk you through:
  - Claude Code: `claude mcp add switch-docs --transport http https://docs.switchagents.ai/mcp`
  - Codex: `codex mcp add switch-docs --url https://docs.switchagents.ai/mcp`
- **Quickstart** (about 10 min): https://docs.switchagents.ai/switch-rooms/getting-started

## Every link

### Event pages
- WeMakeDevs overview / register: https://www.wemakedevs.org/hackathons/switch
- Rules: https://www.wemakedevs.org/hackathons/switch/rules
- Schedule: https://www.wemakedevs.org/hackathons/switch/schedule
- Resources: https://www.wemakedevs.org/hackathons/switch/resources
- Sign in / register: https://www.wemakedevs.org/sign-in?next=%2Fhackathons%2Fswitch%3Fresume%3Dregister
- DevTools Academy page: https://www.devtoolsacademy.com/hackathons/flip-the-switch
- Book a call with Ankur Tyagi (DevTools Academy): https://cal.com/ankur-tyagi/30min

### Community
- WeMakeDevs Discord (event): https://discord.gg/E2rWw2Yhsm
- DevTools Academy Discord: https://discord.gg/E6a2Jnb6G
- WeMakeDevs Discord (general): https://discord.gg/wemakedevs
- X: https://x.com/WeMakeDevs · #HowISwitch feed: https://x.com/hashtag/HowISwitch?f=live
- Ready-made X share text: "I connected my AI agent to my team's chat with Switch for the Flip the Switch Hackathon. #HowISwitch @devtoolsacademy"
- LinkedIn: https://www.linkedin.com/company/wemakedevs · https://linkedin.com/company/devtools-academy
- YouTube: https://youtube.com/@WeMakeDevs · Switch on YouTube: https://www.youtube.com/@FlintAI-SandboxAQ
- WhatsApp: https://whatsapp.com/channel/0029Va4vHhJ5Ejxvi1qEBs1F
- Instagram: https://www.instagram.com/wemakedevs/ · Reddit: https://www.reddit.com/user/wemakedevs/
- Event calendar: https://calendar.google.com/calendar/u/3?cid=Y19lMjYzNjA1NTgyNDA5NjJhODRlMWI2ZGRkNTViZWMyNjI4YjQ1YzVlZjYxMmUzZGM0ODY4NWJhNTcxMTEyZjJjQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20
- Contact: contact@wemakedevs.org

### Switch: repo and downloads
- Repo: https://github.com/sandbox-quantum/switch (3,048 stars, Python). The star links https://devtoolsacademy.link/wemakedevs and https://devtoolsacademy.link/dta lead here.
- Hackathon issues: https://github.com/sandbox-quantum/switch/issues?q=is%3Aissue+state%3Aopen+label%3Ahackathon
- All issues: https://github.com/sandbox-quantum/switch/issues
- CONTRIBUTING + CLA: https://github.com/sandbox-quantum/switch/blob/main/CONTRIBUTING.md
- Maintainer: https://github.com/petr-sandbox
- Examples: https://github.com/sandbox-quantum/switch/tree/main/examples
- Triage template: https://github.com/sandbox-quantum/switch/blob/main/examples/agent-templates/triage-pair.template.yaml
- Console for Windows: https://github.com/sandbox-quantum/switch/releases/latest/download/switch-console-x64.exe
- Console for macOS (Apple silicon): https://github.com/sandbox-quantum/switch/releases/latest/download/switch-console-arm64.dmg
- Console for macOS (Intel): https://github.com/sandbox-quantum/switch/releases/latest/download/switch-console-x64.dmg
- Console for Linux (.deb): https://github.com/sandbox-quantum/switch/releases/latest/download/switch-console-amd64.deb
- Website: https://switchagents.ai/ · onboarding video: https://www.switchagents.ai/switch-onboarding

### Switch docs
- Home: https://docs.switchagents.ai/
- Quickstart: https://docs.switchagents.ai/switch-rooms/getting-started
- Create a room: https://docs.switchagents.ai/switch-rooms/getting-started/create-a-room
- Add a second / custom agent: https://docs.switchagents.ai/switch-rooms/getting-started/add-a-second-agent
- Meet Switch (rooms vs group chat): https://docs.switchagents.ai/switch-rooms/using/index
- Shared context: https://docs.switchagents.ai/switch-rooms/using/shared-context
- Framework (rooms, agents, roles): https://docs.switchagents.ai/switch-rooms/building/index
- Worked example, payments room: https://docs.switchagents.ai/switch-rooms/building/payments-room
- Connect Slack/Teams/Discord/Mattermost/Telegram: https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps/index
- Self-host for a team: https://docs.switchagents.ai/switch-rooms/deploy/self-host
- Agent protocol: https://docs.switchagents.ai/switch-rooms/internals/agent-protocol
- Collaboration bridge (adding a chat app): https://docs.switchagents.ai/switch-rooms/internals/collaboration-bridge
- Working safely with agents: https://docs.switchagents.ai/switch-rooms/resources/working-safely-with-agents
- Troubleshooting: https://docs.switchagents.ai/switch-rooms/resources/troubleshooting
- Docs MCP endpoint: https://docs.switchagents.ai/mcp

### Wispr (Code with Wispr side track)
- Free month of Wispr Flow Pro: https://wisprflow.ai/?promo_code=WEMAKEDEVS
