"""Standalone cube integrity check: compares the bot's live MTGO
collection against the baseline inventory minus whatever's currently
out on loan (DISTRIBUTED or CONFIRMED). Read-only — no trade, no write
to the backend. Reuses `stock_check.py`'s existing primitives entirely.

Usage:
  .venv/Scripts/python.exe -m mtgo.cube_integrity_check <cube_instance_id>

`cube_instance_id` identifies which account/cube-copy pool to check —
the backend now tracks inventory per instance, not as one global pool,
so this scopes both the expected-quantity baseline and the "what's
currently on loan" lookup to just that pool.

Requires the backend API running (BACKEND_API_URL, default
http://localhost:8000) and MTGO_USERNAME set to the account this
instance's job was routed to (the backend sets this automatically when
triggering the job; only matters if running by hand).

Always prints exactly one final JSON line before exiting — see
process_session_returns.py's docstring for why this convention exists
(the admin-triggered job runner parses it).
"""

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from mtgo.cli_common import BACKEND_API_URL, enable_utf8_stdout, print_result
from mtgo.client import (
    export_full_trade_list,
    find_by_automation_id,
    find_mtgo_window,
    select_cards_filter,
)
from mtgo.stock_check import (
    HANDED_OUT_STATUSES,
    compute_expected_quantities,
    diff_stock,
    parse_dek_quantities,
)


def _fetch_inventory(cube_instance_id: int) -> list[dict]:
    response = httpx.get(
        f"{BACKEND_API_URL}/inventory/",
        params={"cube_instance_id": cube_instance_id},
    )
    response.raise_for_status()
    return response.json()


def _fetch_active_loan_card_names(cube_instance_id: int) -> list[str]:
    response = httpx.get(
        f"{BACKEND_API_URL}/loan/sessions/",
        params={"cube_instance_id": cube_instance_id},
    )
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


def main():
    enable_utf8_stdout()

    if len(sys.argv) != 2:
        print("Usage: python -m mtgo.cube_integrity_check <cube_instance_id>")
        print_result({"ok": False, "error": "usage: <cube_instance_id> required"})
        return 1

    cube_instance_id = int(sys.argv[1])

    try:
        inventory = _fetch_inventory(cube_instance_id)
        active_loan_card_names = _fetch_active_loan_card_names(cube_instance_id)
        expected = compute_expected_quantities(inventory, active_loan_card_names)

        window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
        if window is None:
            print("MTGO window not found.")
            print_result({"ok": False, "error": "MTGO window not found."})
            return 1

        window.set_focus()
        collection_btn = find_by_automation_id(window, "CollectionButton")
        if collection_btn is not None:
            collection_btn.click_input()
            time.sleep(2.0)

        # Defensive: if a prior session left the "Other Products" filter
        # active on this account, the "Full Trade List" row lookup below
        # can't find it — confirmed live 2026-07-29 for the give flow,
        # same fix applies here.
        try:
            select_cards_filter(window)
        except Exception:
            pass

        export_path = export_full_trade_list(
            window, Path(f"mtgo/lists/_integrity_check_{cube_instance_id}.dek")
        )
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

        print_result(result)
        return 0
    except Exception as error:
        print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
