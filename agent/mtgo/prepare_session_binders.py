"""Create one MTGO binder per player for a loan session, populated with
that player's PREPARED assignments — the "give" direction's first step,
driven by real backend session data instead of hand-typed card lists.

Usage:
  .venv/Scripts/python.exe -m mtgo.prepare_session_binders <session_id>

Requires the backend API running (BACKEND_API_URL, default
http://localhost:8000) and each player's assignment to already have
`mtgo_username` set (via the Discord bot's pseudo-confirmation flow) —
players without one are skipped and reported, not silently dropped.
"""

import os
import sys

import httpx
from dotenv import load_dotenv

from mtgo.client import create_binder_from_cards, find_mtgo_window

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def _fetch_session(session_id: int) -> dict:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def _group_prepared_cards_by_player(session: dict) -> dict[str, list[str]]:
    by_player: dict[str, list[str]] = {}

    for assignment in session["assignments"]:
        if assignment["status"] != "PREPARED":
            continue

        mtgo_username = assignment.get("mtgo_username")
        if not mtgo_username:
            print(
                f"  [SKIP] assignment {assignment['id']} "
                f"({assignment['card_name']!r} for {assignment['player_name']!r}) "
                f"has no mtgo_username set"
            )
            continue

        by_player.setdefault(mtgo_username, []).append(assignment["card_name"])

    return by_player


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print("Usage: python -m mtgo.prepare_session_binders <session_id>")
        return 1

    session_id = int(sys.argv[1])

    session = _fetch_session(session_id)
    by_player = _group_prepared_cards_by_player(session)

    if not by_player:
        print(f"No PREPARED assignments with an mtgo_username found for session {session_id}.")
        return 0

    # Target the bot's own account explicitly rather than "whichever
    # MTGO window comes first" — with more than one instance open (e.g.
    # a bot account plus a test-player account side by side, as used
    # during development), an unqualified lookup can silently grab the
    # wrong one.
    window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
    if window is None:
        print("MTGO window not found.")
        return 1

    for mtgo_username, card_names in by_player.items():
        binder_name = f"Session{session_id}-{mtgo_username}"
        try:
            label = create_binder_from_cards(window, binder_name, card_names)
            print(f"{mtgo_username}: {label} ({len(card_names)} cards)")
        except Exception as error:
            print(f"{mtgo_username}: FAILED — {error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
