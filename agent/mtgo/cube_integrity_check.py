"""Standalone cube integrity check: compares the bot's live MTGO
collection against the baseline inventory minus whatever's currently
out on loan (DISTRIBUTED or CONFIRMED). Read-only — no trade, no write
to the backend. Reuses `stock_check.py`'s existing primitives entirely.

Usage:
  .venv/Scripts/python.exe -m mtgo.cube_integrity_check

Requires the backend API running (BACKEND_API_URL, default
http://localhost:8000) and MTGO_USERNAME set to the bot's own account.

Always prints exactly one final JSON line before exiting — see
process_session_returns.py's docstring for why this convention exists
(the admin-triggered job runner parses it).
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from mtgo.client import export_full_trade_list, find_mtgo_window
from mtgo.stock_check import (
    HANDED_OUT_STATUSES,
    compute_expected_quantities,
    diff_stock,
    parse_dek_quantities,
)

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def _fetch_inventory() -> list[dict]:
    response = httpx.get(f"{BACKEND_API_URL}/inventory/")
    response.raise_for_status()
    return response.json()


def _fetch_active_loan_card_names() -> list[str]:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/")
    response.raise_for_status()

    names = []
    for session in response.json():
        for assignment in session["assignments"]:
            if assignment["status"] in HANDED_OUT_STATUSES:
                names.append(assignment["card_name"])
    return names


def build_result(diff: dict, checked_at: str) -> dict:
    return {
        "ok": not diff["missing"] and not diff["extra"],
        "missing": diff["missing"],
        "extra": diff["extra"],
        "checked_at": checked_at,
    }


def _print_result(result: dict) -> None:
    print(json.dumps(result))


def main():
    sys.stdout.reconfigure(errors="replace")

    try:
        inventory = _fetch_inventory()
        active_loan_card_names = _fetch_active_loan_card_names()
        expected = compute_expected_quantities(inventory, active_loan_card_names)

        window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
        if window is None:
            print("MTGO window not found.")
            _print_result({"ok": False, "error": "MTGO window not found."})
            return 1

        export_path = export_full_trade_list(window, Path("mtgo/lists/_integrity_check.dek"))
        actual = parse_dek_quantities(export_path)

        diff = diff_stock(expected, actual)
        checked_at = datetime.now(UTC).isoformat()
        result = build_result(diff, checked_at)

        print(f"Checked {len(expected)} distinct card(s) against the live collection.")
        if diff["missing"]:
            print(f"  [ADMIN ACTION NEEDED] missing: {diff['missing']}")
        if diff["extra"]:
            print(f"  [ADMIN ACTION NEEDED] extra: {diff['extra']}")
        if not diff["missing"] and not diff["extra"]:
            print("  Cube integrity OK — no discrepancy.")

        _print_result(result)
        return 0
    except Exception as error:
        _print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
