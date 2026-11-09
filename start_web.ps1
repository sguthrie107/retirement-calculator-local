Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$appName = "Retirement Calculator Dashboard"
$hostAddress = "127.0.0.1"
$portNumber = if ($env:PORT) { $env:PORT } else { "8000" }
$url = "http://localhost:$portNumber"

Write-Host "Starting $appName..." -ForegroundColor Green
Write-Host ""

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install it with: winget install --id astral-sh.uv -e"
}

Write-Host "Syncing dependencies (.venv)..." -ForegroundColor Cyan
uv sync

Write-Host "Listening on ${hostAddress}:${portNumber}" -ForegroundColor Cyan
Write-Host "Opening $url" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    Start-Process $url | Out-Null
} catch {
    Write-Host "Could not auto-open the browser. Open $url manually." -ForegroundColor Yellow
}

uv run uvicorn app.main:app --reload --host $hostAddress --port $portNumber
