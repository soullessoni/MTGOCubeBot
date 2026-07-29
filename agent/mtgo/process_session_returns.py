"""Retrieve a player's CONFIRMED cards back for a loan session — the
"return" direction's admin-triggered counterpart to
prepare_session_binders.py.

Unlike binder creation, this requires the player to actively accept the
incoming trade request on their own MTGO client, so it can't be a
pure fire-and-forget script: it waits (with a generous timeout) for
that to happen before it can pick cards.

**Picking strategy (revised 2026-07-27)**: the bot selects every card
itself via `add_card_from_partner_binder`'s exact-CatID matching,
against exactly what `prepare_session_binders.py` recorded as actually
given (`given_quantity`, falling back to the nominal `quantity` for
assignments never run through that flow) — not Search Tools' bulk
Import Deck, which matches by name only and can grab extra copies the
player independently owns or skip ones the bot already holds. Trusting
the bot's own precise selection over a bulk name-match is slower but
correct by construction. Correctness is still verified afterward by
diffing two real "Full Trade List" exports (before/after) against what
was actually owed, NOT by trusting the live trade window's contents.
Only assignments the export diff actually confirms as returned get
marked RETURNED in the backend — anything else is reported for the
admin to handle (V1 is admin-driven; this script doesn't attempt
automatic correction trades).

Usage:
  .venv/Scripts/python.exe -m mtgo.process_session_returns <session_id> <mtgo_username>

Only processes the one named player per run — an admin retrieving from
several players in one session runs this once per player, since each
retrieval is a separate real-time negotiation with that specific
person.

Always prints exactly one final JSON line before exiting — this is the
structured result an admin-triggered job (see the backend's MtgoJob
runner) parses to record success/failure and surface the
still_owed/to_give_back reconciliation for follow-up recovery actions,
so any change to this script must keep that final line as the last
thing printed. A RETURN job with `"ok": false` here means the trade
completed but reconciliation found a discrepancy — it is NOT a process
failure (that's the early `return 1` paths below, which still print
their own `"ok": false` + `"error"` line).
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

from mtgo.catid_map import load_default_catid_map
from mtgo.cli_common import BACKEND_API_URL, enable_utf8_stdout, fetch_session, print_result
from mtgo.client import (
    add_card_from_partner_binder,
    confirm_trade,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    export_full_trade_list,
    find_by_automation_id,
    find_mtgo_window,
    request_trade_with_binder,
    submit_trade,
    wait_for_confirm_trade_button,
    wait_for_trade_window,
)
from mtgo.stock_check import compute_return_reconciliation, parse_dek_quantities


def _confirmed_assignments(session: dict, mtgo_username: str) -> list[dict]:
    return [
        assignment
        for assignment in session["assignments"]
        if assignment["status"] == "CONFIRMED"
        and assignment.get("mtgo_username") == mtgo_username
    ]


def _expected_card_names(assignments: list[dict]) -> list[str]:
    """One entry per card actually owed back — `given_quantity` (what
    the give trade's export diff confirmed actually left the account)
    when known, falling back to 1 per assignment (the existing
    convention) for assignments never run through that flow."""
    names: list[str] = []
    for assignment in assignments:
        count = assignment.get("given_quantity")
        if count is None:
            count = 1
        names.extend([assignment["card_name"]] * count)
    return names


def _mark_returned(assignment_id: int) -> None:
    response = httpx.post(f"{BACKEND_API_URL}/loan/sessions/assignments/{assignment_id}/return")
    response.raise_for_status()


def _fetch_deposit_for_player(session_id: int, mtgo_username: str) -> dict | None:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}/deposits")
    response.raise_for_status()
    for deposit in response.json():
        if deposit["mtgo_username"] == mtgo_username:
            return deposit
    return None


def _record_deposit_returned(deposit_id: int, returned_amount: int) -> None:
    response = httpx.patch(
        f"{BACKEND_API_URL}/loan/sessions/deposits/{deposit_id}/returned",
        json={"returned_amount": returned_amount},
    )
    response.raise_for_status()


def main():
    enable_utf8_stdout()

    if len(sys.argv) != 3:
        print("Usage: python -m mtgo.process_session_returns <session_id> <mtgo_username>")
        print_result({"ok": False, "error": "usage: <session_id> <mtgo_username> required"})
        return 1

    session_id = int(sys.argv[1])
    mtgo_username = sys.argv[2]

    try:
        session = fetch_session(session_id)
        assignments = _confirmed_assignments(session, mtgo_username)
        card_names = _expected_card_names(assignments)

        if not card_names:
            print(f"No CONFIRMED cards found for {mtgo_username!r} in session {session_id}.")
            print_result({
                "ok": True,
                "returned_count": 0,
                "reconciliation": {"still_owed": {}, "to_give_back": {}},
                "assignment_ids_returned": [],
            })
            return 0

        print(f"Retrieving {len(card_names)} card(s) from {mtgo_username!r}: {card_names}")

        bot_account = os.environ.get("MTGO_USERNAME")
        bot_window = find_mtgo_window(bot_account)
        if bot_window is None:
            print("MTGO window not found.")
            print_result({"ok": False, "error": "MTGO window not found."})
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

        bot_window.set_focus()
        coll = find_by_automation_id(bot_window, "CollectionButton")
        if coll:
            coll.click_input()
            time.sleep(2.0)
        before_path = export_full_trade_list(bot_window, Path("mtgo/lists/_return_before.dek"))
        before_qty = parse_dek_quantities(before_path)

        request_trade_with_binder(bot_window, mtgo_username, "Full Trade List")
        print(f"Trade request sent to {mtgo_username!r}, waiting for them to accept...")

        trade_window = wait_for_trade_window(mtgo_username, timeout=300.0)
        if trade_window is None:
            print(f"{mtgo_username!r} did not accept the trade request within the timeout.")
            print_result({"ok": False, "error": f"{mtgo_username!r} did not accept the trade request."})
            return 1

        # The bot picks every card itself, exact CatID first — it knows
        # precisely what was given (given_quantity), so there's no
        # reason to trust a bulk name-only match over its own selection.
        for card_name in card_names:
            ok = add_card_from_partner_binder(trade_window, card_name, catid=catid_map.get(card_name), timeout=15.0)
            if not ok:
                print(f"  [SKIP] {card_name!r} not found in {mtgo_username!r}'s exposed binder")

        submit_trade(trade_window)
        print("Bot submitted.")

        if not wait_for_confirm_trade_button(trade_window, timeout=300.0):
            print("Confirm Trade never appeared — the other side may not have submitted yet.")
            print_result({"ok": False, "error": "Confirm Trade never appeared."})
            return 1

        confirm_trade(trade_window)
        print("Bot confirmed.")

        dismiss_added_to_collection_popup(bot_window, timeout=8)
        dismiss_trade_completed_popup(bot_window, timeout=5)

        bot_window.set_focus()
        coll = find_by_automation_id(bot_window, "CollectionButton")
        if coll:
            coll.click_input()
            time.sleep(2.0)
        after_path = export_full_trade_list(bot_window, Path("mtgo/lists/_return_after.dek"))
        after_qty = parse_dek_quantities(after_path)

        reconciliation = compute_return_reconciliation(before_qty, after_qty, card_names)
        still_owed = Counter(reconciliation["still_owed"])
        to_give_back = reconciliation["to_give_back"]

        # Mark RETURNED exactly as many of this player's CONFIRMED assignments
        # per card name as the export diff actually confirms came back. An
        # assignment's status is all-or-nothing, so one whose given_quantity
        # is > 1 only gets marked once every one of its copies is accounted
        # for — a partial shortfall on it surfaces via still_owed instead.
        by_name: dict[str, list[dict]] = {}
        for assignment in assignments:
            by_name.setdefault(assignment["card_name"], []).append(assignment)

        returned_count = 0
        returned_assignment_ids: list[int] = []
        for name, name_assignments in by_name.items():
            total_expected = sum(a.get("given_quantity") or 1 for a in name_assignments)
            confirmed_returned = total_expected - still_owed.get(name, 0)

            for assignment in name_assignments:
                needed = assignment.get("given_quantity") or 1
                if confirmed_returned < needed:
                    continue
                _mark_returned(assignment["id"])
                returned_count += needed
                returned_assignment_ids.append(assignment["id"])
                confirmed_returned -= needed

        print(f"Marked {returned_count}/{len(card_names)} card(s) RETURNED "
              f"(confirmed by real export diff, not just the trade window).")

        if still_owed:
            print(f"  [ADMIN ACTION NEEDED] still owed, never came back: {dict(still_owed)}")
        if to_give_back:
            print(f"  [ADMIN ACTION NEEDED] received extra copies not owed — give back: {to_give_back}")

        # The deposit (if any) travels back in this same trade — the
        # player picks their tickets back from the bot's exposed Full
        # Trade List exactly like they picked cards at give time, so no
        # extra automation is needed here beyond confirming via the same
        # before/after diff already taken for the cards.
        deposit_result = None
        deposit = _fetch_deposit_for_player(session_id, mtgo_username)
        if deposit is not None and deposit.get("collected_amount") is not None:
            ticket_change = after_qty.get("Event Ticket", 0) - before_qty.get("Event Ticket", 0)
            deposit_returned = max(0, -ticket_change)
            _record_deposit_returned(deposit["id"], deposit_returned)

            deposit_still_owed = max(0, deposit["collected_amount"] - deposit_returned)
            deposit_result = {
                "collected_amount": deposit["collected_amount"],
                "returned_amount": deposit_returned,
                "still_owed": deposit_still_owed,
            }
            if deposit_still_owed:
                print(
                    f"  [ADMIN ACTION NEEDED] deposit not fully returned: "
                    f"{deposit_returned}/{deposit['collected_amount']} ticket(s)"
                )

        print_result({
            "ok": not still_owed and not to_give_back and (deposit_result is None or not deposit_result["still_owed"]),
            "returned_count": returned_count,
            "reconciliation": {"still_owed": dict(still_owed), "to_give_back": to_give_back},
            "assignment_ids_returned": returned_assignment_ids,
            "deposit": deposit_result,
        })
        return 0
    except Exception as error:
        print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
