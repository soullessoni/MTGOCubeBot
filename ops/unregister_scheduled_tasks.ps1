<#
.SYNOPSIS
    Removes the MTGOCubeBot Scheduled Tasks created by
    register_scheduled_tasks.ps1 (rollback / uninstall).

.DESCRIPTION
    Inverse of ops\register_scheduled_tasks.ps1. Unregisters the
    'MTGOCubeBot-Backend' and 'MTGOCubeBot-DiscordBot' scheduled tasks.
    Safe to run even if a task is already missing (a warning is printed,
    nothing errors out).

    Usage:
        powershell -ExecutionPolicy Bypass -File ops\unregister_scheduled_tasks.ps1

.NOTES
    This only removes the scheduled task definitions. It does not stop an
    already-running backend/bot process that the task previously started;
    stop those separately (e.g. Stop-Process, or close the console window
    they are running in) if needed.
#>

[CmdletBinding()]
param(
    [string[]]$TaskNames = @('MTGOCubeBot-Backend', 'MTGOCubeBot-DiscordBot')
)

$ErrorActionPreference = 'Stop'

foreach ($name in $TaskNames) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue

    if (-not $existing) {
        Write-Warning "Task '$name' not found; nothing to remove."
        continue
    }

    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Removed scheduled task '$name'." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done." -ForegroundColor Yellow
