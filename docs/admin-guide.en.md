# Admin guide — MTGOCubeBot

*[Lire en français](admin-guide.md)*

This document describes the web dashboard screens and the Discord bot
commands used to administer MTGO Cube card loan sessions.

## Overview

The system has three components:

- **The backend** (FastAPI) — source of truth for loan sessions,
  inventory, and MTGO jobs. Also serves the dashboard.
- **The dashboard** (static pages served under `/dashboard/`) — web
  interface to view and drive sessions.
- **The Discord bot** — player-facing interface (identification,
  confirming receipt/return) and admin-facing interface (triggering
  real MTGO trades).

Any action that actually touches MTGO (creating a binder, running a
trade, exporting the collection) always goes through an **MTGO job**: a
background task that drives the bot's MTGO client in real time (tens of
seconds to a few minutes, however long it takes a player to accept the
trade), tracked via its status (`PENDING` → `RUNNING` →
`SUCCEEDED` / `FAILED`).

## The dashboard

Available at `http://<server>:8000/dashboard/`.

### Sessions (`index.html`)

Lists every loan session: ID, status, card count, creation date. The
"Voir" (View) link opens a session's detail page.

### Session detail (`session.html?id=...`)

- The session's status and an action button matching the current step
  (mark ready, start, complete).
- **Forcer l'arrêt** (Force stop) — cancels the session; any
  not-yet-returned card is released back into inventory. Irreversible,
  asks for confirmation.
- The assigned-cards table, with a button per card matching its status
  (prepare, distribute, confirm, mark returned). These are manual
  tracking actions — they don't trigger any real MTGO action (see the
  MTGO Administration page for that).

### Inventory (`inventory.html`)

Lists the cube's cards with the quantity owned and the quantity
available (owned minus whatever is currently on loan). The owned
quantity can be corrected directly.

### MTGO Administration (`mtgo.html`)

The panel that triggers real actions on the bot's MTGO client.

**Trigger controls:**

| Action | What it does |
|---|---|
| Trigger give | Creates (or updates) a session's MTGO binder with each identified player's `PREPARED` cards. The player then picks the cards up themselves via Search Tools/Import Deck on their own client. |
| Trigger return | Sends a trade request to the given MTGO player, waits for them to accept, then retrieves all of their `CONFIRMED` cards for that session. |
| Check cube integrity | Compares the bot's real MTGO collection against the reference inventory (accounting for what's currently on loan) and reports any discrepancy. Read-only, no risk. |

**Recent jobs table**: refreshes automatically every 5 seconds. Each
row shows the ID, type, status, related session/player, and a
"Détails" (Details) button.

**Job detail**: shows the live log (`log_output`) while it's running,
then once finished:
- For a **return**: if cards are still missing (`still_owed`) or an
  excess was received (`to_give_back`), a corrective-action button
  appears:
  - **Relancer la récupération** (Retry the return) — reissues an
    identical return job; since only cards still `CONFIRMED` are
    picked up again, this only asks for whatever is still missing.
  - **Rendre l'excédent** (Give back the excess) — creates a binder to
    return the player's excess copies. Asks for confirmation (a real
    MTGO action).
- For an **integrity check**: simply lists what's missing or extra
  versus the reference — no automated corrective action is offered (an
  integrity discrepancy needs a human look).

## The Discord bot

### Player side

1. An admin runs `/draft-session <id>`: creates a
   `draft-session-<id>` channel in the configured category
   (`DISCORD_CATEGORY_NAME`), with a message listing the players
   involved and a dropdown for each to select their name.
2. The player picks their name → a modal asks for their exact MTGO
   username.
3. Once submitted, the bot DMs them the full list of their cards, then
   one message per status grouping the relevant cards together with a
   single action button for all of them at once (grammar adapts to
   singular/plural depending on the card count):
   - `DISTRIBUTED` → **J'ai reçu ces cartes** (I received these cards)
     (moves to `CONFIRMED`)
   - `CONFIRMED` → **J'ai rendu ces cartes** (I returned these cards)
     (moves to `RETURNED`)
4. A **Corriger mon pseudo MTGO** (Fix my MTGO username) button stays
   available if the player made a typo — resubmitting re-links their
   cards and resends a fresh list.

Session channels are automatically deleted once the session is
`COMPLETED` or `CANCELLED` (checked every `CLEANUP_INTERVAL_MINUTES`).

### Admin side

All of the following commands are restricted to members with the
Discord **Administrator** permission, or a role named exactly
**`Admin`** on the server. An unauthorized attempt gets a "Réservé aux
admins." (Admins only.) message instead of failing silently.

| Command | Effect |
|---|---|
| `/mtgo-give <session_id>` | Discord equivalent of the dashboard's "Déclencher la distribution" button. |
| `/mtgo-return <session_id> <mtgo_username>` | Equivalent of "Déclencher la récupération". |
| `/mtgo-integrity-check` | Equivalent of "Vérifier l'intégrité du cube". |
| `/mtgo-job-status <job_id>` | Checks the status and latest log lines of a running or past job — useful if the initial notification was dismissed, or if the bot restarted while waiting. |

After a trigger (`/mtgo-give`, `/mtgo-return`,
`/mtgo-integrity-check`), the bot replies immediately with the job
number, then comes back on its own with the result once the job
finishes (no need to run `/mtgo-job-status` by hand, unless checking
back later). A return that reports a discrepancy shows the same
corrective-action buttons ("Relancer la récupération" / "Rendre
l'excédent") as the dashboard.

## Required configuration

**Discord bot** (`agent/.env`):

| Variable | Role |
|---|---|
| `DISCORD_BOT_TOKEN` | Required — the bot's token. |
| `DISCORD_GUILD_ID` | Optional — restricts commands to one server (instant sync) instead of a global rollout (up to 1h). |
| `BACKEND_API_URL` | Backend URL, defaults to `http://localhost:8000`. |
| `DISCORD_CATEGORY_NAME` | Category where session channels are created, defaults to `Automated Draft on MTGO`. |
| `CLEANUP_INTERVAL_MINUTES` | How often finished channels are cleaned up, defaults to 2 minutes. |
| `MTGO_USERNAME` / `MTGO_PASSWORD` | The bot's MTGO account, used by the automation scripts. |

**Backend** (process environment variables, no `.env` file on the
backend side):

| Variable | Role |
|---|---|
| `MTGO_AGENT_DIR` | Path to the `agent/` project (holds the MTGO scripts), defaults to `<repo>/agent`. |
| `MTGO_AGENT_PYTHON` | Python interpreter used to launch MTGO jobs, defaults to `<agent>/.venv/Scripts/python.exe`. |
| `DISCORD_ADMIN_WEBHOOK_URL` | Optional — a Discord webhook URL; if set, a notification is automatically posted there whenever a job fails or reports a discrepancy (see "Production reliability" below). Without it, those events are only visible by checking the dashboard or `/mtgo-job-status`. |

**Discord**: create a role named exactly `Admin` on the server and
assign it to whoever is allowed to trigger MTGO actions — or give them
the server's "Administrator" permission.

## Populating inventory from a real MTGO export

The cube integrity check compares the real MTGO collection against the
backend's `/inventory/` table — it's only reliable if that table
reflects the full cube. To (re)populate it from a real "Full Trade
List" export:

```
.venv/Scripts/python.exe scripts/import_inventory_from_dek.py <path-to-.dek>
```

Creates any missing cards, updates owned quantities for every card
present in the export, and zeroes out any inventory card absent from
the export (stale test data, a card removed from the cube, etc.).
Re-run it whenever the cube's composition changes.

## Production reliability

### One-click startup

Double-clicking `Demarrer MTGOCubeBot.bat` (at the repo root) starts
everything in order: opens and logs into MTGO if needed (without
restarting an already-good session), starts the backend, starts the
Discord bot, then opens the dashboard once the backend is ready. Every
step checks first whether it's already running — re-running the script
while everything is already up does nothing destructive. For a nicer
desktop icon than a plain `.bat`, create a shortcut to it and assign it
a custom icon (see `ops/README.md`).

A compiled `.exe` wouldn't add anything here (there's no logic that
would benefit from compilation, just ordered process launches), and it
adds a real risk of an antivirus false positive for an unsigned
homebrew executable — the `.bat` + shortcut gives the same day-to-day
convenience.

### Process supervision (auto-start + auto-restart)

The `ops/` folder contains PowerShell scripts that register two
Windows Scheduled Tasks (backend + Discord bot), with automatic
restart on failure:

```powershell
powershell -ExecutionPolicy Bypass -File ops\register_scheduled_tasks.ps1
```

**Important**: these tasks deliberately run inside the logged-on
user's interactive session (trigger: "at log on", not "whether the
user is logged on or not"). A true Windows Service (Session 0) can't
drive the MTGO client via `pywinauto` — MTGO automation would silently
fail while the backend still looked healthy. See `ops/README.md` for
details, the rollback (`unregister_scheduled_tasks.ps1`), and how to
check task status afterward.

### Database backups

No backups were being taken until now. A script copies `cubebot.db`
into `backend/backups/` with a timestamp, and prunes old backups
beyond a configurable retention (30 by default):

```
.venv/Scripts/python.exe scripts/backup_db.py [--keep N]
```

Schedule it daily via Windows Task Scheduler: Create Basic Task →
daily trigger → action "Start a program" → program
`backend\.venv\Scripts\python.exe` → arguments
`scripts\backup_db.py` → start in `backend\`.

### Persistent Discord buttons

The entire player flow (the "J'ai reçu/rendu ces cartes" buttons, the
player-selection dropdown, the MTGO-username-correction button) now
survives a bot restart, via `discord.ui.DynamicItem` — the needed
identifiers are encoded directly in the `custom_id` rather than
captured in a Python closure that would be lost on restart.

### Proactive failure notification

If `DISCORD_ADMIN_WEBHOOK_URL` is configured on the backend, a message
is automatically posted to that webhook whenever a job:
- fails outright (`FAILED`); or
- succeeds but reports a discrepancy (an incomplete return, an excess
  received, or a cube integrity gap).

Without that variable, those events are only visible by checking the
dashboard or `/mtgo-job-status` — configuring the webhook is
recommended before letting the system run without active supervision.
