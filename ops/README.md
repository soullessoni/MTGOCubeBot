# ops/ — process supervision for MTGOCubeBot

This folder contains scripts to make the backend and Discord bot
auto-restart on failure and auto-start on machine boot/logon, using
Windows Task Scheduler.

**Nothing here has been run yet.** These scripts only *define* scheduled
tasks; a human needs to review and execute them.

## Why Task Scheduler and not a Windows Service (NSSM, etc.)

The backend is not a pure network service. When an admin triggers a
give/return/integrity-check job (via the dashboard or Discord `/mtgo-*`
commands), the backend spawns `agent/mtgo/*.py` subprocesses that use
`pywinauto` to drive a **real, already-logged-in MTGO desktop client**
through Windows UI Automation.

UI Automation requires an interactive desktop session. Windows Services
run in **Session 0**, which is isolated from the interactive desktop by
design — a service cannot see or click into GUI applications like MTGO.
If the backend were wrapped as a classic Windows Service (e.g. via NSSM),
its HTTP API would still appear to work, but every MTGO automation job
would silently fail the moment it tried to drive the client.

The fix is to supervise the backend with a **Task Scheduler task that
runs inside the logged-on user's interactive session**:

- Trigger: **At log on** (for the specific user)
- **"Run only when user is logged on"** (interactive logon type) —
  explicitly *not* "run whether user is logged on or not", which would
  run the task in a non-interactive session and reintroduce the same
  Session-0 problem as a service.
- Restart policy: Task Scheduler's own "if the task fails, restart every
  N minutes, up to M times" setting (configured here as every 1 minute,
  up to 3 times).

The Discord bot (`agent/bot/main.py`) does no GUI automation — it's pure
network I/O — so it isn't subject to this constraint and could run as a
real background service. For simplicity and consistency (one supervision
mechanism instead of two), it uses the same Task-Scheduler-at-logon
approach as the backend.

## Files

- `register_scheduled_tasks.ps1` — creates/updates two scheduled tasks:
  - `MTGOCubeBot-Backend` — runs
    `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend`
    from the repo root.
  - `MTGOCubeBot-DiscordBot` — runs
    `agent\.venv\Scripts\python.exe -m bot.main` from `agent\`.

  The repo root is resolved from `$PSScriptRoot` (parent of `ops\`), so
  the script works if the repo is cloned to a different path. Re-running
  the script is safe — it uses `Register-ScheduledTask -Force`, which
  updates the existing task definitions in place.

- `unregister_scheduled_tasks.ps1` — removes both tasks
  (`Unregister-ScheduledTask -Confirm:$false`), for rollback.

## How to run (human review required)

```powershell
powershell -ExecutionPolicy Bypass -File ops\register_scheduled_tasks.ps1
```

This registers the tasks but does not start them immediately — they will
start on the next logon. To start them right away without logging out:

```powershell
Start-ScheduledTask -TaskName "MTGOCubeBot-Backend"
Start-ScheduledTask -TaskName "MTGOCubeBot-DiscordBot"
```

To roll back:

```powershell
powershell -ExecutionPolicy Bypass -File ops\unregister_scheduled_tasks.ps1
```

## Checking status afterward

```powershell
Get-ScheduledTask -TaskName "MTGOCubeBot-Backend"
Get-ScheduledTaskInfo -TaskName "MTGOCubeBot-Backend"

Get-ScheduledTask -TaskName "MTGOCubeBot-DiscordBot"
Get-ScheduledTaskInfo -TaskName "MTGOCubeBot-DiscordBot"
```

`Get-ScheduledTaskInfo` shows `LastRunTime`, `LastTaskResult` (0 = success),
and `NumberOfMissedRuns` — useful for confirming a restart actually
happened after a crash.

You can also check the Task Scheduler UI (`taskschd.msc`) under
"Task Scheduler Library", or the History tab on each task (enable
"All Tasks History" from the Actions pane if it's disabled) for a
timeline of start/stop/restart events.

## Logging (optional, not wired up by default)

Task Scheduler actions do **not** capture a process's stdout/stderr by
default — the uvicorn/bot console output will simply go nowhere. If the
human wants persistent log files, the simplest option is to wrap the
action in `cmd /c` with redirection, e.g. by changing the action's
executable/arguments to something like:

```powershell
-Execute 'cmd.exe' `
-Argument '/c "backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend >> ops\logs\backend.log 2>&1"'
```

(and creating an `ops\logs\` folder ahead of time). This is intentionally
left out of `register_scheduled_tasks.ps1` to keep the main script simple
— add it manually if/when file-based logging is actually needed.
