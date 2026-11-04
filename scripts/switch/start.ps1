$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $taskRoot
$env:UV_CACHE_DIR = Join-Path $taskRoot 'data/uv-cache'
uv run python scripts/switch/prepare.py
if ($LASTEXITCODE -ne 0) { throw 'Configuration preparation failed.' }
docker ps --format '{{.Names}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker access failed. Do not start Docker; report the blocker.' }
docker compose --project-name take-two-switch --env-file scripts/switch/.env -f 'E:/DevDrive/switch/deploy/local/standalone-docker-compose.yml' -f scripts/switch/compose.override.yml --profile collab --profile gateway --project-directory $taskRoot up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Switch compose failed.' }
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $live = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 3
        $ready = Invoke-RestMethod 'http://127.0.0.1:8000/health/ready' -TimeoutSec 3
        if ($live.status -eq 'ok') { Write-Output 'Switch health and readiness responded successfully.'; exit 0 }
    } catch { }
    Start-Sleep -Seconds 2
}
throw 'Switch did not become ready within 60 attempts.'
