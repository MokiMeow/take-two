# Live Switch server (started by Claude, 4 Nov 09:0x IST)

Running with Docker Compose, project name `taketwo`, profiles `collab,gateway`:
- Switch API: http://localhost:8000 (`/health` → ok)
- Mattermost: http://localhost:8065 (admin user and passwords in `scripts/switch/.env`: MATTERMOST_ADMIN_USER / MATTERMOST_ADMIN_PASSWORD, MATTERMOST_USER / MATTERMOST_USER_PASSWORD)
- Gateway dashboard: http://localhost:3000 (GATEWAY_ADMIN_PASSWORD)
- Registration token: `AGENT_REGISTRATION_TOKEN` in `scripts/switch/.env` (bootstrap token; see SWITCH-NOTES about owner attribution)
- Image: switch-core:latest, digest in `scripts/switch/core-digest.txt`

W1: you can't run Docker from your sandbox, and you don't need to. Use this server over HTTP. Read secrets from `scripts/switch/.env` into your `.env`; never print them.
Start/stop is Claude's job: `docker compose --env-file .env -p taketwo -f E:/DevDrive/switch/deploy/local/standalone-docker-compose.yml up -d` from `scripts/switch/`.
