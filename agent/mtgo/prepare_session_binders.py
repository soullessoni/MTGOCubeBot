"""Create one MTGO binder per player for a loan session, populated with
that player's PREPARED assignments, then complete the actual give trade
so the player can pick the cards up — the "give" direction, driven by
real backend session data instead of hand-typed card lists.

Usage:
  .venv/Scripts/python.exe -m mtgo.prepare_session_binders <session_id>

Requires the backend API running (BACKEND_API_URL, default
http://localhost:8000) and each player's assignment to already have
`mtgo_username` set (via the Discord bot's pseudo-confirmation flow) —
players without one are skipped and reported, not silently dropped.

**Confirmed live 2026-07-27**: creating the binder alone doesn't expose
it to the player — MTGO's Search Tools only browses a collection
that's actually shared via an active trade. This script therefore also
requests a trade exposing that player's binder, waits for them to
accept and pick what they want, then submits/confirms the bot's own
(empty) side — `submit_trade`'s docstring confirms both sides must
submit even a giver adding nothing, or Confirm Trade never appears.

A player is never forced to take everything offered, so exactly what
left the bot's account is confirmed the same way `process_session_returns.py`
verifies returns: diffing two real "Full Trade List" exports bracketing
the trade, not by trusting the live trade window. That confirmed amount
is recorded as each assignment's `given_quantity` — the ground truth a
later return trade uses to know precisely what to retrieve, instead of
the nominal `quantity`.

Always prints exactly one final JSON line before exiting — this is the
structured result an admin-triggered job (see the backend's MtgoJob
runner) parses to record success/failure, so any change to this script
must keep that final line as the last thing printed.
"""

import os
import sys
import time
from pathlib import Path

import httpx

from mtgo.catid_map import load_default_catid_map
from mtgo.cli_common import BACKEND_API_URL, enable_utf8_stdout, fetch_session, print_result
from mtgo.client import (
    add_card_from_partner_binder,
    confirm_trade,
    create_binder_from_cards,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    export_full_trade_list,
    find_by_automation_id,
    find_mtgo_window,
    request_trade_with_binder,
    select_cards_filter,
    select_other_products_tickets_filter,
    submit_trade,
    wait_for_confirm_trade_button,
    wait_for_receiving_panel_to_settle,
    wait_for_trade_window,
)
from mtgo.stock_check import compute_give_confirmation, parse_dek_quantities


def _group_prepared_assignments_by_player(session: dict) -> tuple[dict[str, list[dict]], list[str]]:
    by_player: dict[str, list[dict]] = {}
    skipped: list[str] = []

    for assignment in session["assignments"]:
        if assignment["status"] != "PREPARED":
            continue

        mtgo_username = assignment.get("mtgo_username")
        if not mtgo_username:
            message = (
                f"assignment {assignment['id']} "
                f"({assignment['card_name']!r} for {assignment['player_name']!r}) "
                f"has no mtgo_username set"
            )
            print(f"  [SKIP] {message}")
            skipped.append(message)
            continue

        by_player.setdefault(mtgo_username, []).append(assignment)

    return by_player, skipped


def _record_given_quantity(assignment_id: int, given_quantity: int) -> None:
    response = httpx.patch(
        f"{BACKEND_API_URL}/loan/sessions/assignments/{assignment_id}/given-quantity",
        json={"given_quantity": given_quantity},
    )
    response.raise_for_status()


def _create_deposit(session_id: int, mtgo_username: str) -> dict:
    response = httpx.post(
        f"{BACKEND_API_URL}/loan/sessions/{session_id}/deposits",
        json={"mtgo_username": mtgo_username},
    )
    response.raise_for_status()
    return response.json()


def _record_deposit_collected(deposit_id: int, collected_amount: int) -> None:
    response = httpx.patch(
        f"{BACKEND_API_URL}/loan/sessions/deposits/{deposit_id}/collected",
        json={"collected_amount": collected_amount},
    )
    response.raise_for_status()


def _go_to_collection(window) -> None:
    window.set_focus()
    collection_btn = find_by_automation_id(window, "CollectionButton")
    if collection_btn is not None:
        collection_btn.click_input()
        time.sleep(2.0)


def _complete_give_trade(
        window,
        mtgo_username: str,
        binder_name: str,
        assignments: list[dict],
        deposit_amount: int | None = None,
) -> dict:
    """Expose `binder_name` to `mtgo_username` via a real trade, let
    them pick what they want, optionally pull a ticket deposit from
    their own collection, complete the trade from the bot's side, then
    confirm exactly what moved via export diff. Returns
    `{"given": {...}, "not_taken": {...}, "ticket_collected": int}`
    (see `compute_give_confirmation`).

    If `deposit_amount` is set and the full amount can't be pulled from
    the player's collection, this raises *before* submitting — MTGO
    only moves anything once both sides confirm, so leaving the trade
    unsubmitted is an all-or-nothing cancellation with no separate
    "cancel trade" click needed (none was found/verified live).

    Raises on any step that doesn't complete (acceptance timeout, no
    Confirm Trade button, insufficient deposit, or any underlying
    MtgoAutomationError)."""
    card_names = [a["card_name"] for a in assignments]

    _go_to_collection(window)
    before_qty = parse_dek_quantities(
        export_full_trade_list(window, Path(f"mtgo/lists/_give_before_{mtgo_username}.dek"))
    )

    request_trade_with_binder(window, mtgo_username, binder_name)
    print(f"Trade request sent to {mtgo_username!r}, waiting for them to accept...")

    trade_window = wait_for_trade_window(mtgo_username, timeout=300.0)
    if trade_window is None:
        raise RuntimeError(f"{mtgo_username!r} did not accept the trade request within the timeout.")

    if deposit_amount:
        # Tickets are internally an item named "Event Ticket" (CatID
        # "1") under the "Other Products" filter tab, using the exact
        # same CardQuantityControl mechanism as cards — confirmed live
        # 2026-07-29 — so the bot pulls them from the player's own
        # collection exactly like process_session_returns.py pulls
        # cards back.
        select_other_products_tickets_filter(trade_window)
        collected = 0
        for _ in range(deposit_amount):
            if add_card_from_partner_binder(trade_window, "Event Ticket", catid="1", timeout=15.0):
                collected += 1
        select_cards_filter(trade_window)

        if collected < deposit_amount:
            raise RuntimeError(
                f"Could only pull {collected}/{deposit_amount} deposit ticket(s) from "
                f"{mtgo_username!r}'s collection — leaving the trade unconfirmed, nothing transfers."
            )
        print(f"Pulled {collected}/{deposit_amount} deposit ticket(s) from {mtgo_username!r}.")

    # Confirmed live 2026-07-27: submitting immediately (before the
    # player has picked anything) risks the bot's submit being silently
    # invalidated once the player's side later changes — MTGO's Confirm
    # Trade button never appeared even though nothing raised. Wait for
    # their picks to actually settle first.
    wait_for_receiving_panel_to_settle(trade_window, mtgo_username, timeout=300.0, stable_for=3.0)

    # Both sides must submit before Confirm Trade appears, even one
    # that only added nothing or only deposit tickets on its own side
    # (see submit_trade's docstring).
    submit_trade(trade_window)
    print("Bot submitted.")

    if not wait_for_confirm_trade_button(trade_window, timeout=60.0):
        # The player may have kept adding cards after our submit,
        # invalidating it — confirmed live 2026-07-27. Re-submit once
        # before giving up.
        print("Confirm Trade not yet visible — re-submitting once in case our submit was invalidated.")
        submit_trade(trade_window)
        if not wait_for_confirm_trade_button(trade_window, timeout=240.0):
            raise RuntimeError("Confirm Trade never appeared — the other side may not have submitted yet.")

    confirm_trade(trade_window)
    print("Bot confirmed.")

    dismiss_added_to_collection_popup(window, timeout=8)
    dismiss_trade_completed_popup(window, timeout=5)

    _go_to_collection(window)
    after_qty = parse_dek_quantities(
        export_full_trade_list(window, Path(f"mtgo/lists/_give_after_{mtgo_username}.dek"))
    )

    confirmation = compute_give_confirmation(before_qty, after_qty, card_names)
    confirmation["ticket_collected"] = after_qty.get("Event Ticket", 0) - before_qty.get("Event Ticket", 0)

    return confirmation


def main():
    enable_utf8_stdout()

    if len(sys.argv) != 2:
        print("Usage: python -m mtgo.prepare_session_binders <session_id>")
        print_result({"ok": False, "error": "usage: <session_id> required"})
        return 1

    session_id = int(sys.argv[1])

    try:
        session = fetch_session(session_id)
        by_player, skipped = _group_prepared_assignments_by_player(session)

        deposit_amount = session.get("deposit_amount") if session.get("deposit_required") else None

        if not by_player:
            print(f"No PREPARED assignments with an mtgo_username found for session {session_id}.")
            print_result({
                "ok": True,
                "given": {},
                "not_taken": {},
                "deposits_collected": {},
                "failed": {},
                "skipped_no_username": skipped,
            })
            return 0

        # Target the bot's own account explicitly rather than "whichever
        # MTGO window comes first" — with more than one instance open (e.g.
        # a bot account plus a test-player account side by side, as used
        # during development), an unqualified lookup can silently grab the
        # wrong one.
        window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
        if window is None:
            print("MTGO window not found.")
            print_result({"ok": False, "error": "MTGO window not found."})
            return 1

        catid_map = load_default_catid_map()
        if not catid_map:
            print(
                "  [WARN] no CatID map found — binders will use CatID=\"0\" "
                "name-only resolution, which can silently expose the wrong "
                "edition. Export the bot account's Full Trade List to "
                "mtgo/lists/full_trade_list.dek to fix this."
            )

        given: dict[str, dict[str, int]] = {}
        not_taken: dict[str, dict[str, int]] = {}
        deposits_collected: dict[str, int] = {}
        failed: dict[str, str] = {}

        for mtgo_username, assignments in by_player.items():
            card_names = [a["card_name"] for a in assignments]
            binder_name = f"Session{session_id}-{mtgo_username}"

            try:
                label = create_binder_from_cards(window, binder_name, card_names, catid_map=catid_map)
                print(f"{mtgo_username}: {label} ({len(card_names)} cards)")

                deposit_record = None
                if deposit_amount:
                    deposit_record = _create_deposit(session_id, mtgo_username)

                confirmation = _complete_give_trade(
                    window, mtgo_username, binder_name, assignments, deposit_amount=deposit_amount,
                )

                by_name: dict[str, list[dict]] = {}
                for assignment in assignments:
                    by_name.setdefault(assignment["card_name"], []).append(assignment)

                for name, name_assignments in by_name.items():
                    remaining_given = confirmation["given"].get(name, 0)
                    for assignment in name_assignments:
                        take = min(assignment["quantity"], remaining_given)
                        _record_given_quantity(assignment["id"], take)
                        remaining_given -= take

                given[mtgo_username] = confirmation["given"]
                if confirmation["not_taken"]:
                    not_taken[mtgo_username] = confirmation["not_taken"]
                    print(f"  [INFO] {mtgo_username!r} did not pick up: {confirmation['not_taken']}")

                if deposit_record is not None:
                    _record_deposit_collected(deposit_record["id"], confirmation["ticket_collected"])
                    deposits_collected[mtgo_username] = confirmation["ticket_collected"]
            except Exception as error:
                print(f"{mtgo_username}: FAILED — {error}")
                failed[mtgo_username] = str(error)

        print_result({
            "ok": not failed and not not_taken,
            "given": given,
            "not_taken": not_taken,
            "deposits_collected": deposits_collected,
            "failed": failed,
            "skipped_no_username": skipped,
        })
        return 0 if not failed else 1
    except Exception as error:
        print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
