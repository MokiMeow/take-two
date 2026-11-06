# Discord: steps 6 to 10 (about 5 minutes)

Do NOT send the bot token to Claude or anyone. It only goes into Switch Console (step 8).
The Application ID and Server ID are safe to share.

## 6. Add the bot to your server
Open this link in Edge. First replace APPLICATION_ID with the Application ID from step 5:

https://discord.com/oauth2/authorize?client_id=APPLICATION_ID&scope=bot%20applications.commands&permissions=310043053136

Pick **The Last Light crew**, then **Authorize**.
(Or send Claude the Application ID and Claude sends back the finished link.)

## 7. Copy the Server ID
1. Discord: **User Settings > Advanced > Developer Mode** ON.
2. Right-click your server icon, then **Copy Server ID**.

## 8. Connect Discord in Switch Console
Open Switch Console (Desktop\take-two\out\switch-console-x64.exe), your local server, then
**Home > Messaging apps > Connect > Discord**:
- Display name: `Discord crew`
- Bot Token: paste the token (only here)
- Guild Id: paste the Server ID
- Click **Connect**, then **This is me** to link your Discord account.

## 9. Wake up the rooms
In Discord, post `hello` in **#crew** and in **#day-1**. Switch creates a room for each.

## 10. Clean up
Delete the token from Notepad.

## Then tell Claude "Discord done"
Claude checks that both rooms show up in Switch and sends a test message to #crew.

---

# Part 2: the two agents (about 5 minutes)
1. Dictate with Wispr Flow a few sentences each, in your own words, into the "Who you are" section of:
   - `agents/script-supervisor.md` (keeps the story right: what each scene must keep)
   - `agents/first-ad.md` (makes practical plans: location, time, cast, kit)
2. Tell Claude. Claude builds `agents/team.template.yaml`.
3. Switch Console: **Settings > Agent providers**: check Claude Code and Codex are signed in.
4. **Templates > Import template** > `Desktop\take-two\agents\team.template.yaml` > **Use**.
5. In Mattermost **production**, check that both agents say they've taken their roles.
