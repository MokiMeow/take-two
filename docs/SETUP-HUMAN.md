# Your setup steps (about 15 minutes)

These need your accounts, so only you can do them. Do them in order and tell Claude when each part is done.

## Part 1: Discord crew server and bot (about 8 minutes)
1. **Make a test server** in Discord: **+** → **Create My Own** → "For me and my friends" → name it **The Last Light crew**.
2. Make two text channels in it: **#crew** and **#day-1**.
3. Open https://discord.com/developers/applications → **New Application** → name **Take Two** → Create.
4. Left menu **Bot**:
   - **Reset Token** → copy it into Notepad for a minute. **Don't paste it into chat or anywhere public.**
   - Scroll down and turn ON **Server Members Intent** and **Message Content Intent** → **Save Changes**.
5. Left menu **General Information** → copy the **Application ID**.
6. Open this link in Edge, after replacing `APPLICATION_ID` with yours:
   `https://discord.com/oauth2/authorize?client_id=APPLICATION_ID&scope=bot%20applications.commands&permissions=310043053136`
   → pick **The Last Light crew** → Authorize.
7. In Discord: **User Settings → Advanced → Developer Mode ON**. Then right-click your server icon → **Copy Server ID**.
8. Open **Switch Console** → your local server → **Home → Messaging apps → Connect → Discord**:
   - Display name: **Discord crew**
   - Bot Token: paste it. Guild Id: paste the server ID. Connect.
   - Then click **This is me** to link your own Discord account.
9. Post "hello" in **#crew** and in **#day-1**, so Switch creates their rooms.
10. Delete the token from Notepad.

## Part 2: two agents in Switch Console (about 5 minutes)
Before this, dictate the **"Who you are"** sections in `agents/script-supervisor.md` and `agents/first-ad.md` with **Wispr Flow**: a few sentences each, in your own words. Claude then builds the team template from those files.
1. Switch Console → **Settings → Agent providers**: check that **Claude Code** and **Codex** both show as signed in.
2. **Templates → Import template** → choose `Desktop\take-two\agents\team.template.yaml` (Claude creates this after your dictation) → Use.
3. It creates **script-supervisor** (Claude Code) and **first-ad** (Codex), each with its own folder, and adds them to the production room.
4. In Mattermost's **production** channel, check that both agents say they've taken their roles.

## Part 3: friends for the shoot (by tonight)
- Two actors and one friend on camera/sound for **6 Nov, evening**. About 1 hour.
- Ask each one for a **genuine time limit** (for example "I have to leave by 7"). That real limit is what the demo tests.
- They need Discord and need to join **The Last Light crew** to confirm the plan.

## Never
- Never paste the bot token into a chat, the repo or a screenshot.
- Never show the Mattermost passwords on screen during recording.
