"""Retrieve a player's CONFIRMED cards back for a loan session — the
"return" direction's admin-triggered counterpart to
prepare_session_binders.py.

Unlike binder creation, this requires the player to actively accept the
incoming trade request on their own MTGO client, so it can't be a
pure fire-and-forget script: it waits (with a generous timeout) for
that to happen before it can pick cards.

**Picking strategy (validated live 2026-07-25/26)**: Search Tools'
Import Deck bulk-adds matching cards by name in one shot — much faster
than searching one card at a time (~90% of a 40-card return in one
pass) — with a per-card search as fallback for whatever it missed.
Either way, correctness is verified afterward by diffing two real
"Full Trade List" exports (before/after) against what was actually
owed, NOT by trusting the live trade window: Import Deck's auto-add
can grab extra copies of a name the player independently owns, or skip
a name the bot already holds other copies of. Only assignments the
export diff actually confirms as returned get marked RETURNED in the
backend — anything else is reported for the admin to handle (V1 is
admin-driven; this script doesn't attempt automatic correction trades).

Usage:
  .venv/Scripts/python.exe -m mtgo.process_session_returns <session_id> <mtgo_username>

Only processes the one named player per run — an admin retrieving from
several players in one session runs this once per player, since each
retrieval is a separate real-time negotiation with that specific
person.
"""

import os
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

from mtgo.catid_map import load_default_catid_map
from mtgo.client import (
    accept_incoming_trade_request,
    add_card_from_partner_binder,
    confirm_trade,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    export_full_trade_list,
    find_by_automation_id,
    find_mtgo_window,
    import_deck_for_comparison,
    read_receiving_panel,
    request_trade_with_binder,
    submit_trade,
    wait_for_confirm_trade_button,
    wait_for_trade_window,
    _write_dek_file,
)
from mtgo.stock_check import compute_return_reconciliation, parse_dek_quantities

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def _fetch_session(session_id: int) -> dict:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def _confirmed_assignments(session: dict, mtgo_username: str) -> list[dict]:
    return [
        assignment
        for assignment in session["assignments"]
        if assignment["status"] == "CONFIRMED"
        and assignment.get("mtgo_username") == mtgo_username
    ]


def _mark_returned(assignment_id: int) -> None:
    response = httpx.post(f"{BACKEND_API_URL}/loan/sessions/assignments/{assignment_id}/return")
    response.raise_for_status()


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 3:
        print("Usage: python -m mtgo.process_session_returns <session_id> <mtgo_username>")
        return 1

    session_id = int(sys.argv[1])
    mtgo_username = sys.argv[2]

    session = _fetch_session(session_id)
    assignments = _confirmed_assignments(session, mtgo_username)
    card_names = [a["card_name"] for a in assignments]

    if not card_names:
        print(f"No CONFIRMED cards found for {mtgo_username!r} in session {session_id}.")
        return 0

    print(f"Retrieving {len(card_names)} card(s) from {mtgo_username!r}: {card_names}")

    bot_account = os.environ.get("MTGO_USERNAME")
    bot_window = find_mtgo_window(bot_account)
    if bot_window is None:
        print("MTGO window not found.")
        return 1

    catid_map = load_default_catid_map()
    if not catid_map:
        print(
            "  [WARN] no CatID map found — falling back to name-only matching, "
            "which can grab the wrong printing. Export the bot account's Full "
            "Trade List to mtgo/lists/full_trade_list.dek to fix this."
        )

    dismiss_trade_completed_popup(bot_window, timeout=3)
    dismiss_added_to_collection_popup(bot_window, timeout=3)

    coll = find_by_automation_id(bot_window, "CollectionButton")
    if coll:
        coll.click_input()
    before_path = export_full_trade_list(bot_window, Path("mtgo/lists/_return_before.dek"))
    before_qty = parse_dek_quantities(before_path)

    request_trade_with_binder(bot_window, mtgo_username, "Full Trade List")
    print(f"Trade request sent to {mtgo_username!r}, waiting for them to accept...")

    trade_window = wait_for_trade_window(mtgo_username, timeout=300.0)
    if trade_window is None:
        print(f"{mtgo_username!r} did not accept the trade request within the timeout.")
        return 1

    compare_dek = _write_dek_file(f"Return-{session_id}-{mtgo_username}", card_names, catid_map=catid_map)
    clean = import_deck_for_comparison(
        trade_window, compare_dek, viewer_username=bot_account, settle_timeout=25.0,
    )
    print(f"Bulk decklist import (Search Tools): clean={clean}")

    staged = read_receiving_panel(trade_window, bot_account) if bot_account else set()
    remaining = list(card_names)
    for name in staged:
        if name in remaining:
            remaining.remove(name)

    for card_name in remaining:
        ok = add_card_from_partner_binder(trade_window, card_name, catid=catid_map.get(card_name), timeout=15.0)
        if not ok:
            print(f"  [SKIP] {card_name!r} not found in {mtgo_username!r}'s exposed binder")

    submit_trade(trade_window)
    print("Bot submitted.")

    if not wait_for_confirm_trade_button(trade_window, timeout=300.0):
        print("Confirm Trade never appeared — the other side may not have submitted yet.")
        return 1

    confirm_trade(trade_window)
    print("Bot confirmed.")

    dismiss_added_to_collection_popup(bot_window, timeout=8)
    dismiss_trade_completed_popup(bot_window, timeout=5)

    coll = find_by_automation_id(bot_window, "CollectionButton")
    if coll:
        coll.click_input()
    after_path = export_full_trade_list(bot_window, Path("mtgo/lists/_return_after.dek"))
    after_qty = parse_dek_quantities(after_path)

    reconciliation = compute_return_reconciliation(before_qty, after_qty, card_names)
    still_owed = Counter(reconciliation["still_owed"])
    to_give_back = reconciliation["to_give_back"]

    # Mark RETURNED exactly as many of this player's CONFIRMED assignments
    # per card name as the export diff actually confirms came back.
    by_name: dict[str, list[int]] = {}
    for assignment in assignments:
        by_name.setdefault(assignment["card_name"], []).append(assignment["id"])

    returned_count = 0
    for name, assignment_ids in by_name.items():
        owed_here = still_owed.get(name, 0)
        confirmed_returned = len(assignment_ids) - owed_here
        for assignment_id in assignment_ids[:confirmed_returned]:
            _mark_returned(assignment_id)
            returned_count += 1

    print(f"Marked {returned_count}/{len(card_names)} assignment(s) RETURNED "
          f"(confirmed by real export diff, not just the trade window).")

    if still_owed:
        print(f"  [ADMIN ACTION NEEDED] still owed, never came back: {dict(still_owed)}")
    if to_give_back:
        print(f"  [ADMIN ACTION NEEDED] received extra copies not owed — give back: {to_give_back}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
