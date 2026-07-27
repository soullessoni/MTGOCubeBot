<#
.SYNOPSIS
    Registers Windows Scheduled Tasks that keep the MTGOCubeBot backend and
    Discord bot running, auto-restarting them on failure and auto-starting
    them at logon.

.DESCRIPTION
    IMPORTANT: Both tasks are configured to run "at log on" for the current
    user with "run only when user is logged on" (NOT "run whether user is
    logged on or not"). This is deliberate, not an oversight.

    The backend is not a pure network service: when an admin triggers a
    give/return/integrity-check job, it spawns agent/mtgo/*.py subprocesses
    that use pywinauto to drive a real, already-logged-in MTGO desktop
    client via Windows UI Automation. UI Automation requires an interactive
    desktop session. A classic Windows Service (or a Task Scheduler task set
    to "run whether user is logged on or not") executes in Session 0, which
    is isolated from the interactive desktop and CANNOT see or control GUI
    applications like MTGO. Installing the backend as a true background
    service would leave the HTTP API looking healthy while silently
    breaking every MTGO automation job.

    The Discord bot has no such constraint (pure network I/O), but for
    consistency and to avoid introducing a second supervision mechanism
    (e.g. NSSM) for just one of the two processes, it uses the same
    Task-Scheduler-at-logon approach.

    This script only DEFINES the two scheduled tasks. It does not start
    them immediately (logon trigger only) and must be run manually by a
    human after review:

        powershell -ExecutionPolicy Bypass -File ops\register_scheduled_tasks.ps1

.NOTES
    Re-running this script is safe: Register-ScheduledTask is called with
    -Force, so existing tasks are updated in place rather than erroring.
#>

[CmdletBinding()]
param(
    # Repo root. Defaults to the parent of this script's folder (ops\..),
    # so the script is portable if the repo is cloned elsewhere.
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,

    # Restart policy shared by both tasks.
    [TimeSpan]$RestartInterval = (New-TimeSpan -Minutes 1),
    [int]$RestartCount = 3
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

$BackendPython   = Join-Path $RepoRoot 'backend\.venv\Scripts\python.exe'
$BackendWorkDir  = $RepoRoot
$BackendArgs     = '-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend'

$BotPython       = Join-Path $RepoRoot 'agent\.venv\Scripts\python.exe'
$BotWorkDir      = Join-Path $RepoRoot 'agent'
$BotArgs         = '-m bot.main'

# The account the tasks run under: the currently logged-on user. Using
# "$env:USERDOMAIN\$env:USERNAME" (rather than hardcoding a name) keeps the
# script portable across machines/users.
$RunAsUser = "$env:USERDOMAIN\$env:USERNAME"

$Tasks = @(
    [PSCustomObject]@{
        Name        = 'MTGOCubeBot-Backend'
        Description = 'MTGOCubeBot FastAPI backend (uvicorn). Runs in the interactive session because give/return/integrity-check jobs drive the MTGO desktop client via pywinauto UI Automation, which requires an interactive desktop and is unavailable to Session 0 services.'
        Executable  = $BackendPython
        Arguments   = $BackendArgs
        WorkingDir  = $BackendWorkDir
    },
    [PSCustomObject]@{
        Name        = 'MTGOCubeBot-DiscordBot'
        Description = 'MTGOCubeBot Discord bot (pure network I/O). Uses the same Task-Scheduler-at-logon approach as the backend for consistency, even though it has no interactive-desktop requirement of its own.'
        Executable  = $BotPython
        Arguments   = $BotArgs
        WorkingDir  = $BotWorkDir
    }
)

foreach ($task in $Tasks) {
    if (-not (Test-Path $task.Executable)) {
        Write-Warning "[$($task.Name)] Executable not found at '$($task.Executable)'. Registering anyway, but verify the venv path before relying on this task."
    }

    Write-Host "Preparing scheduled task '$($task.Name)'..." -ForegroundColor Cyan

    $action = New-ScheduledTaskAction `
        -Execute $task.Executable `
        -Argument $task.Arguments `
        -WorkingDirectory $task.WorkingDir

    # Fires when the target user logs on to an interactive session.
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $RunAsUser

    # "Run only when user is logged on" == LogonType Interactive.
    # (Deliberately NOT S4U / Password, which would allow "run whether
    # user is logged on or not" and land the process in Session 0.)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $RunAsUser `
        -LogonType Interactive `
        -RunLevel Limited

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount $RestartCount `
        -RestartInterval $RestartInterval `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $task.Name `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description $task.Description `
        -Force | Out-Null

    Write-Host "  Registered '$($task.Name)' -> $($task.Executable) $($task.Arguments)" -ForegroundColor Green
    Write-Host "  Working directory: $($task.WorkingDir)"
    Write-Host "  Trigger: at logon for $RunAsUser (interactive session only)"
    Write-Host "  Restart policy: every $($RestartInterval.TotalMinutes) minute(s), up to $RestartCount time(s)"
}

Write-Host ""
Write-Host "Done. Tasks are registered but will only start on the next logon trigger (or run them now with Start-ScheduledTask)." -ForegroundColor Yellow
Write-Host "See ops\README.md for status/log-checking instructions."
