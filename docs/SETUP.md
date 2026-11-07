# Setup: Discord crew room and the two Console agents

The replay and the real loop in [QUICKSTART.md](../QUICKSTART.md) need neither of these. Do them to put the crew on Discord and to run Claude Code and Codex in the two roles.

## Part 1: the Discord crew room (about 8 minutes)

1. **Create a server** in Discord (for example *The Last Light crew*) with a text channel **#day-1** (and **#crew** if you want a standing crew room).
2. Open the [Discord developer portal](https://discord.com/developers/applications), **New Application** (name it *Take Two*).
3. **Bot** page:
   - **Reset Token** and keep it somewhere private for a minute. Never paste it into a chat, the repo or a screenshot.
   - Turn on **Server Members Intent** and **Message Content Intent**, then **Save Changes**.
4. **General Information** page: copy the **Application ID**.
5. Invite the bot. Replace `APPLICATION_ID` in this link and open it:
   `https://discord.com/oauth2/authorize?client_id=APPLICATION_ID&scope=bot%20applications.commands&permissions=310043053136`
6. In Discord turn on **User Settings > Advanced > Developer Mode**, then right-click the server icon and **Copy Server ID**.
7. In **Switch Console**, open your local server, then **Home > Messaging apps > Connect > Discord**:
   - Display name: `Discord crew` (the shoot-day template refers to the bridge by this name).
   - Paste the bot token and the server ID, then **Connect**.
   - Click **This is me** to link your own Discord account.
8. Post `hello` in **#day-1** so Switch creates its room. Delete the token from wherever you kept it.

`uv run python -m scripts.discord_probe crew` checks the bridge: it creates a private room through Switch and posts a message and an image.

## Part 2: the two agents in Switch Console (about 5 minutes)

1. **Settings > Agent providers**: check that **Claude Code** and **Codex** both show as signed in.
2. Create the production room first (`templates/production.yaml`), so the coordinator is already in it.
3. **Templates > Import template** and choose [`agents/team.template.yaml`](../agents/team.template.yaml). Pick the production room and **Use**.
4. It creates `script-supervisor` (Claude Code) and `first-ad` (Codex), each in its own folder, with the briefs from [`agents/`](../agents), and adds them to the room.
5. In the production room, check that both agents have taken their roles. The coordinator reports a missing role holder in the room instead of skipping it.

Set `TAKE_TWO_SUPERVISOR_AGENT_NAME`, `TAKE_TWO_AD_AGENT_NAME`, `TAKE_TWO_SUPERVISOR_SENDER_ID` and `TAKE_TWO_AD_SENDER_ID` in `.env` to the two agents' names and Switch sender ids, so the coordinator addresses them and accepts only their replies (see [`.env.example`](../.env.example) and [`coordinator/config.py`](../coordinator/config.py)).

## Never

- Never commit `.env`, `scripts/switch/.env` or `data/judge.env`. All three are ignored.
- Never show the Discord bot token or Mattermost passwords on screen while recording.
