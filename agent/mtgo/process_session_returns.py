"""Retrieve a player's CONFIRMED cards back for a loan session — the
"return" direction's admin-triggered counterpart to
prepare_session_binders.py.

Unlike binder creation, this requires the player to actively accept the
incoming trade request on their own MTGO client, so it can't be a
pure fire-and-forget script: it waits (with a generous timeout) for
that to happen before it can pick cards.

Usage:
  .venv/Scripts/python.exe -m mtgo.process_session_returns <session_id> <mtgo_username>

Only processes the one named player per run — an admin retrieving from
several players in one session runs this once per player, since each
retrieval is a separate real-time negotiation with that specific
person.
"""

import os
import sys

import httpx
from dotenv import load_dotenv

from mtgo.client import (
    accept_incoming_trade_request,
    add_card_from_partner_binder,
    confirm_trade,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    find_mtgo_window,
    find_trade_window,
    read_receiving_panel,
    request_trade_with_binder,
    submit_trade,
    wait_for_confirm_trade_button,
    wait_for_trade_window,
)

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def _fetch_session(session_id: int) -> dict:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def _confirmed_card_names(session: dict, mtgo_username: str) -> list[str]:
    return [
        assignment["card_name"]
        for assignment in session["assignments"]
        if assignment["status"] == "CONFIRMED"
        and assignment.get("mtgo_username") == mtgo_username
    ]


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 3:
        print("Usage: python -m mtgo.process_session_returns <session_id> <mtgo_username>")
        return 1

    session_id = int(sys.argv[1])
    mtgo_username = sys.argv[2]

    session = _fetch_session(session_id)
    card_names = _confirmed_card_names(session, mtgo_username)

    if not card_names:
        print(f"No CONFIRMED cards found for {mtgo_username!r} in session {session_id}.")
        return 0

    print(f"Retrieving {len(card_names)} card(s) from {mtgo_username!r}: {card_names}")

    bot_account = os.environ.get("MTGO_USERNAME")
    bot_window = find_mtgo_window(bot_account)
    if bot_window is None:
        print("MTGO window not found.")
        return 1

    dismiss_trade_completed_popup(bot_window, timeout=3)
    dismiss_added_to_collection_popup(bot_window, timeout=3)

    request_trade_with_binder(bot_window, mtgo_username, "Full Trade List")
    print(f"Trade request sent to {mtgo_username!r}, waiting for them to accept...")

    trade_window = wait_for_trade_window(mtgo_username, timeout=300.0)
    if trade_window is None:
        print(f"{mtgo_username!r} did not accept the trade request within the timeout.")
        return 1

    added = []
    for card_name in card_names:
        if add_card_from_partner_binder(trade_window, card_name):
            added.append(card_name)
        else:
            print(f"  [SKIP] {card_name!r} not found in {mtgo_username!r}'s exposed binder")

    if not added:
        print("No cards could be added — aborting without submitting.")
        return 1

    received = read_receiving_panel(trade_window, bot_account) if bot_account else None
    if received is not None:
        print(f"Confirmed staged for pickup: {received}")

    submit_trade(trade_window)
    print("Bot submitted.")

    if not wait_for_confirm_trade_button(trade_window, timeout=120.0):
        print("Confirm Trade never appeared — the other side may not have submitted yet.")
        return 1

    confirm_trade(trade_window)
    print("Bot confirmed.")

    dismiss_added_to_collection_popup(bot_window, timeout=8)
    dismiss_trade_completed_popup(bot_window, timeout=5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
