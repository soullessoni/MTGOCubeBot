"""One-click-launcher helper: make sure the bot's MTGO account is open
and logged in, WITHOUT unnecessarily restarting an already-good
session — unlike `restart_and_login()` (which always kills MTGO
first, meant for an explicit admin-triggered "reconnect" action), this
checks first and only launches/logs in if actually needed. Meant to be
called once at the start of a normal work session (see
ops/start_all.ps1), not as a recovery tool for a stuck client.

Usage:
  .venv/Scripts/python.exe -m mtgo.ensure_ready
"""

import os
import sys
import time

from dotenv import load_dotenv

from mtgo.client import (
    find_mtgo_window,
    is_logged_in,
    launch_mtgo,
    login,
    wait_for_logged_in,
)

load_dotenv()


def _find_window_with_retries(username: str | None, attempts: int = 3, interval: float = 3.0):
    """A single find_mtgo_window() miss can be transient window/element
    enumeration flakiness rather than "MTGO genuinely isn't running" —
    confirmed repeatedly during live testing of this codebase. A short
    retry avoids launching a redundant second MTGO instance on a false
    negative."""
    for attempt in range(attempts):
        window = find_mtgo_window(username)
        if window is not None:
            return window
        if attempt < attempts - 1:
            time.sleep(interval)
    return None


def main():
    sys.stdout.reconfigure(errors="replace")
    username = os.environ.get("MTGO_USERNAME")

    window = _find_window_with_retries(username)

    if window is not None and is_logged_in(window):
        print(f"{username!r} already logged in — nothing to do.")
        return 0

    if window is None:
        print("MTGO not running — launching...")
        window = launch_mtgo()
        if window is None:
            print("MTGO window did not appear after launch.")
            return 1
    else:
        print(f"MTGO running but {username!r} not logged in — logging in...")

    login(window)

    if not wait_for_logged_in(window):
        print("Login did not complete within the timeout.")
        return 1

    print(f"{username!r} logged in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
