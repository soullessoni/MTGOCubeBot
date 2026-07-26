"""Drive an ENTIRE loan session lifecycle for real, on BOTH sides of the
trade, using two MTGO accounts the same person owns (the bot account +
a personal test-player account) — the give direction AND the full
return direction, back to back.

This is a testing tool, not the production admin-trigger flow:
`prepare_session_binders.py` / `process_session_returns.py` only ever
automate the bot's own side, because a real player uses their own
hands on their own machine. Here we additionally automate the
player-side steps (accepting the trade request, picking cards, hitting
Submit) because both MTGO windows on this machine belong to the same
person for test purposes.

Usage:
  .venv/Scripts/python.exe -m mtgo.full_session_test_cycle <session_id> <mtgo_username>

Requires: the session's assignments for `mtgo_username` already PREPARED
with a binder named `Session<id>-<mtgo_username>` already created (via
`prepare_session_binders.py`), and both MTGO clients logged in
(MTGO_USERNAME env var identifies the bot account; the other account
is passed as `mtgo_username`).
"""

import os
import sys

import httpx
from dotenv import load_dotenv

from mtgo.client import (
    accept_incoming_trade_request,
    add_all_cards_from_partner_binder,
    add_card_from_partner_binder,
    confirm_trade,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    find_mtgo_window,
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


def _assignment_ids_by_card_name(session: dict, mtgo_username: str, status: str) -> dict[str, int]:
    return {
        a["card_name"]: a["id"]
        for a in session["assignments"]
        if a["status"] == status and a.get("mtgo_username") == mtgo_username
    }


def _post(path: str) -> None:
    response = httpx.post(f"{BACKEND_API_URL}{path}")
    response.raise_for_status()


def run_trade_leg(
    bot_window,
    player_window,
    bot_account: str,
    player_account: str,
    binder_to_expose: str,
    picker_is_bot: bool,
    card_names: list[str],
) -> set[str]:
    """Run one full trade negotiation (request -> accept -> pick ->
    submit both -> confirm both -> cleanup) and return the set of card
    names actually staged for pickup, as reported by `read_receiving_panel`.

    `picker_is_bot` selects which side searches the OTHER side's exposed
    binder and adds cards to their own "Will Receive" panel — True for
    the return/retrieval direction (bot picks), False for the give
    direction (player picks).
    """
    dismiss_trade_completed_popup(bot_window, timeout=3)
    dismiss_added_to_collection_popup(bot_window, timeout=3)
    dismiss_trade_completed_popup(player_window, timeout=3)
    dismiss_added_to_collection_popup(player_window, timeout=3)

    request_trade_with_binder(bot_window, player_account, binder_to_expose)
    print(f"  trade request sent to {player_account!r}, waiting for accept...")

    deadline_msg_shown = False
    accepted = False
    import time as _time
    deadline = _time.monotonic() + 60.0
    while _time.monotonic() < deadline:
        try:
            accept_incoming_trade_request(player_window, bot_account, "Full Trade List", timeout=5.0)
            accepted = True
            break
        except Exception:
            continue
    if not accepted:
        raise RuntimeError(f"{player_account!r} never accepted the trade request")
    print(f"  {player_account!r} accepted.")

    bot_trade_window = wait_for_trade_window(player_account, timeout=60.0)
    player_trade_window = wait_for_trade_window(bot_account, timeout=60.0)
    if bot_trade_window is None or player_trade_window is None:
        raise RuntimeError("trade window(s) did not appear on both sides")

    picker_window = bot_trade_window if picker_is_bot else player_trade_window
    picker_name = bot_account if picker_is_bot else player_account

    # Fast pass: whatever's already rendered without any search (works
    # well for a small binder that fits in the current viewport).
    added = add_all_cards_from_partner_binder(picker_window, card_names, timeout=8.0)
    missing = sorted(set(card_names) - set(added))
    if missing:
        print(f"  fast pass got {len(added)}/{len(card_names)}, searching {len(missing)} individually...")
    # Reliable fallback: MTGO's grid virtualizes, so cards further down
    # an unscrolled/unsearched binder don't exist as UI elements yet —
    # search finds them regardless of scroll position.
    for name in missing:
        if add_card_from_partner_binder(picker_window, name):
            added.append(name)
        else:
            print(f"    [SKIP] {name!r} not found in exposed binder")

    received = read_receiving_panel(picker_window, picker_name)
    print(f"  staged for pickup ({len(received)}): {sorted(received)[:5]}{'...' if len(received) > 5 else ''}")

    submit_trade(bot_trade_window)
    submit_trade(player_trade_window)
    print("  both sides submitted.")

    if not wait_for_confirm_trade_button(bot_trade_window, timeout=120.0):
        raise RuntimeError("Confirm Trade never appeared")

    confirm_trade(bot_trade_window)
    confirm_trade(player_trade_window)
    print("  both sides confirmed.")

    dismiss_added_to_collection_popup(bot_window, timeout=8)
    dismiss_trade_completed_popup(bot_window, timeout=5)
    dismiss_added_to_collection_popup(player_window, timeout=8)
    dismiss_trade_completed_popup(player_window, timeout=5)

    return received


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 3:
        print("Usage: python -m mtgo.full_session_test_cycle <session_id> <mtgo_username>")
        return 1

    session_id = int(sys.argv[1])
    player_account = sys.argv[2]
    bot_account = os.environ.get("MTGO_USERNAME")
    if not bot_account:
        print("MTGO_USERNAME not set.")
        return 1

    bot_window = find_mtgo_window(bot_account)
    player_window = find_mtgo_window(player_account)
    if bot_window is None or player_window is None:
        print("Could not find both MTGO windows.")
        return 1

    session = _fetch_session(session_id)
    prepared = _assignment_ids_by_card_name(session, player_account, "PREPARED")
    if not prepared:
        print(f"No PREPARED assignments for {player_account!r} in session {session_id}.")
        return 1

    binder_name = f"Session{session_id}-{player_account}"
    print(f"=== GIVE: {len(prepared)} card(s) via {binder_name!r} ===")
    given = run_trade_leg(
        bot_window, player_window, bot_account, player_account,
        binder_to_expose=binder_name, picker_is_bot=False,
        card_names=list(prepared.keys()),
    )

    distributed_ids = [prepared[name] for name in given if name in prepared]
    for aid in distributed_ids:
        _post(f"/loan/sessions/assignments/{aid}/distribute")
    print(f"Marked {len(distributed_ids)} assignment(s) DISTRIBUTED.")

    for aid in distributed_ids:
        _post(f"/loan/sessions/assignments/{aid}/confirm")
    print(f"Marked {len(distributed_ids)} assignment(s) CONFIRMED (simulated player confirmation).")

    session = _fetch_session(session_id)
    confirmed = _assignment_ids_by_card_name(session, player_account, "CONFIRMED")
    if not confirmed:
        print("Nothing CONFIRMED to return.")
        return 0

    print(f"=== RETURN: {len(confirmed)} card(s) ===")
    returned = run_trade_leg(
        bot_window, player_window, bot_account, player_account,
        binder_to_expose="Full Trade List", picker_is_bot=True,
        card_names=list(confirmed.keys()),
    )

    returned_ids = [confirmed[name] for name in returned if name in confirmed]
    for aid in returned_ids:
        _post(f"/loan/sessions/assignments/{aid}/return")
    print(f"Marked {len(returned_ids)} assignment(s) RETURNED.")

    print("=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
