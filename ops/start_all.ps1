<#
.SYNOPSIS
    One-click startup: makes sure MTGO is launched and logged in, starts
    the backend and Discord bot if they aren't already running, and
    opens the dashboard once the backend answers.

.DESCRIPTION
    Idempotent by design — safe to run again if some pieces are already
    up (e.g. the dashboard tab got closed but the backend/bot are still
    running): each step checks first and skips what's already done
    rather than restarting things that don't need it.

    This is a manual, on-demand launcher — for always-on supervision
    with auto-restart on crash, see register_scheduled_tasks.ps1 in
    this same folder. The two are independent: use this one for a
    normal "I'm sitting down to admin a session" start, use the
    scheduled tasks if you want everything running unattended all the
    time.
#>

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Write-Host "=== MTGOCubeBot - demarrage ===" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# 1. MTGO client (launch + log in, only if not already ready)
# ---------------------------------------------------------------------------
Write-Host "`n[1/4] Verification du client MTGO..." -ForegroundColor Cyan

& (Join-Path $RepoRoot 'agent\.venv\Scripts\python.exe') -m mtgo.ensure_ready
if ($LASTEXITCODE -ne 0) {
    Write-Warning "MTGO n'a pas pu etre demarre/connecte automatiquement. Verifiez manuellement avant de continuer."
}

# ---------------------------------------------------------------------------
# 2. Backend (uvicorn)
# ---------------------------------------------------------------------------
Write-Host "`n[2/4] Verification du backend..." -ForegroundColor Cyan

$backendUp = $false
try {
    Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -TimeoutSec 2 -UseBasicParsing | Out-Null
    $backendUp = $true
} catch {
    $backendUp = $false
}

if ($backendUp) {
    Write-Host "  Backend deja demarre."
} else {
    Write-Host "  Demarrage du backend..."
    Start-Process `
        -FilePath (Join-Path $RepoRoot 'backend\.venv\Scripts\python.exe') `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--app-dir', 'backend' `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Minimized
}

# ---------------------------------------------------------------------------
# 3. Discord bot
# ---------------------------------------------------------------------------
Write-Host "`n[3/4] Verification du bot Discord..." -ForegroundColor Cyan

$botRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.main*' }

if ($botRunning) {
    Write-Host "  Bot deja demarre."
} else {
    Write-Host "  Demarrage du bot..."
    Start-Process `
        -FilePath (Join-Path $RepoRoot 'agent\.venv\Scripts\python.exe') `
        -ArgumentList '-m', 'bot.main' `
        -WorkingDirectory (Join-Path $RepoRoot 'agent') `
        -WindowStyle Minimized
}

# ---------------------------------------------------------------------------
# 4. Dashboard - wait for the backend to actually answer before opening it
# ---------------------------------------------------------------------------
Write-Host "`n[4/4] Ouverture du dashboard..." -ForegroundColor Cyan

$deadline = (Get-Date).AddSeconds(30)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -TimeoutSec 2 -UseBasicParsing | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Start-Process 'http://127.0.0.1:8000/dashboard/'
} else {
    Write-Warning "Le backend ne repond pas apres 30s - dashboard non ouvert automatiquement. Verifiez la fenetre du backend."
}

Write-Host "`n=== Termine ===" -ForegroundColor Green
Write-Host "Cette fenetre peut etre fermee (le backend et le bot tournent dans leurs propres fenetres reduites)." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
