# Round 1: Claude's own ideas (written before reading Sol's)

Scores are out of 10: Use of Switch (30%), Execution risk inverted (25%), Creativity and impact (25%), Presentation (20%), then the weighted total.

## 1. Slop Court, revised: "evidence before rejection"
- **What:** opt-in disputed PRs become private case rooms. A Challenger and a Defender argue, a fixed runner checks the facts, and the maintainer's verdict is bound to the head SHA.
- **Demo:** a false accusation is overturned.
- **Weakness:** a crowded category (CodeRabbit, SlopGuard, pr-pilot).
- **Scores:** 7 / 6 / 7 / 8 → **6.9**

## 2. Cross-company room: Slack ↔ Teams ↔ Discord, with agents on both sides
- **What:** an agency on Slack and its client on Teams (or Discord and Telegram) share one Switch room. Each side keeps a private room with its own agent. A "liaison" agent publishes only what each side approved into the shared room.
- **The pain:**
  - Slack Connect and Teams shared channels don't talk to each other;
  - vendor–client work is scattered across email, chat and docs;
  - agents leak context between clients.
- **Why only Switch:** collaboration bridges across apps, room boundaries, controlled publication between linked rooms, and question cards for "OK to share this with the client?".
- **Demo:** a message typed in Discord shows up in Telegram via the shared room, the agent drafts a status update, the human on one side approves, and only the approved part crosses.
- **Weakness:** it needs two chat apps set up (Discord and Telegram are easy, Teams is hard). The value can look like "a bridge bot".
- **Scores:** 9 / 5 / 7 / 7 → **7.1**

## 3. Writers' Room (Track 02, creative)
- **What:** a showrunner (human) runs a Discord writers' room with agents in roles:
  - a Story Bible keeper, who owns continuity documents;
  - a Punch-up writer;
  - a Critic;
  - a Producer, who turns the approved scene into an animated storyboard or short rendered with Remotion.

  Each episode is its own room linked to the series bible. The showrunner approves each beat with question cards.
- **Why only Switch:** exclusive roles, room documents as the series bible, episode rooms linked to the bible room, templates for each new episode, and question cards for creative decisions.
- **Demo:** the room writes and *renders* a 45-second animated short live, and the showrunner overrules the Critic and the film changes.
- **Strength:** the builder makes films, so this plays to his strengths. Track 02 is thin.
- **Weakness:** the "real team problem" evidence is weaker (creative teams, indie studios). Some judges may see it as a toy.
- **Scores:** 8 / 6 / 8 / 9 → **7.65**

## 4. Hackathon Judging Bench
- **What:** organizers have hundreds of submissions. Each submission gets a room: a Cloner agent builds and runs it with a fixed runner, a README auditor checks "can someone reproduce it", and a scorer drafts rubric scores with evidence. Human judges calibrate in a shared room and decide the shortlist.
- **Pain:** WeMakeDevs says it "reviews every submission" before shortlisting. Devpost organizers report the same load.
- **Demo:** run it on a past public hackathon's entries, and show the human panel overriding a score.
- **Weakness:**
  - it looks like judging the competitors, which is awkward;
  - same mechanics as Slop Court;
  - sounds self-serving.
- **Scores:** 7 / 6 / 6 / 7 → **6.5**

## 5. Family care room (India, Telegram)
- **What:** adult children in different cities coordinate an elderly parent's care: medicines, doctor visits, bills, reports. Agents:
  - read lab reports and prescriptions (PDF or photo) into a shared health document;
  - track refills and appointments;
  - draft questions for the doctor.

  Siblings approve decisions with question cards. A parent-facing room keeps simple Kannada or Hindi messages.
- **Why Switch:** rooms per concern (meds, money, appointments) linked to a family room, roles per sibling's agent, cross-app (siblings on Telegram, one on Discord), documents.
- **Pain:** real and emotional (remote caregiving in India), but evidence is anecdotal. Medical data needs care in the demo; use synthetic data only.
- **Scores:** 6 / 6 / 8 / 8 → **6.8**

## 6. On-call handover across time zones
Skipped: it overlaps with incident rooms.

## My current ranking
Writers' Room (7.65) > cross-company room (7.1) > Slop Court revised (6.9) > family care room (6.8) > judging bench (6.5).

I'm genuinely unsure between Writers' Room, which is less crowded, plays to the builder's strengths and has a memorable demo, and Slop Court, which has stronger evidence of pain but a crowded category.
