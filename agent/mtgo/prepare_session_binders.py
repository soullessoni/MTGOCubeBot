"""Create one MTGO binder per player for a loan session, populated with
that player's PREPARED assignments — the "give" direction's first step,
driven by real backend session data instead of hand-typed card lists.

Usage:
  .venv/Scripts/python.exe -m mtgo.prepare_session_binders <session_id>

Requires the backend API running (BACKEND_API_URL, default
http://localhost:8000) and each player's assignment to already have
`mtgo_username` set (via the Discord bot's pseudo-confirmation flow) —
players without one are skipped and reported, not silently dropped.

Always prints exactly one final JSON line before exiting — this is the
structured result an admin-triggered job (see the backend's MtgoJob
runner) parses to record success/failure, so any change to this script
must keep that final line as the last thing printed.
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv

from mtgo.catid_map import load_default_catid_map
from mtgo.client import create_binder_from_cards, find_mtgo_window

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def _fetch_session(session_id: int) -> dict:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def _group_prepared_cards_by_player(session: dict) -> tuple[dict[str, list[str]], list[str]]:
    by_player: dict[str, list[str]] = {}
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

        by_player.setdefault(mtgo_username, []).append(assignment["card_name"])

    return by_player, skipped


def _print_result(result: dict) -> None:
    print(json.dumps(result))


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print("Usage: python -m mtgo.prepare_session_binders <session_id>")
        _print_result({"ok": False, "error": "usage: <session_id> required"})
        return 1

    session_id = int(sys.argv[1])

    try:
        session = _fetch_session(session_id)
        by_player, skipped = _group_prepared_cards_by_player(session)

        if not by_player:
            print(f"No PREPARED assignments with an mtgo_username found for session {session_id}.")
            _print_result({"ok": True, "created": {}, "failed": {}, "skipped_no_username": skipped})
            return 0

        # Target the bot's own account explicitly rather than "whichever
        # MTGO window comes first" — with more than one instance open (e.g.
        # a bot account plus a test-player account side by side, as used
        # during development), an unqualified lookup can silently grab the
        # wrong one.
        window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
        if window is None:
            print("MTGO window not found.")
            _print_result({"ok": False, "error": "MTGO window not found."})
            return 1

        catid_map = load_default_catid_map()
        if not catid_map:
            print(
                "  [WARN] no CatID map found — binders will use CatID=\"0\" "
                "name-only resolution, which can silently expose the wrong "
                "edition. Export the bot account's Full Trade List to "
                "mtgo/lists/full_trade_list.dek to fix this."
            )

        created: dict[str, int] = {}
        failed: dict[str, str] = {}

        for mtgo_username, card_names in by_player.items():
            binder_name = f"Session{session_id}-{mtgo_username}"
            try:
                label = create_binder_from_cards(window, binder_name, card_names, catid_map=catid_map)
                print(f"{mtgo_username}: {label} ({len(card_names)} cards)")
                created[mtgo_username] = len(card_names)
            except Exception as error:
                print(f"{mtgo_username}: FAILED — {error}")
                failed[mtgo_username] = str(error)

        _print_result({
            "ok": not failed,
            "created": created,
            "failed": failed,
            "skipped_no_username": skipped,
        })
        return 0 if not failed else 1
    except Exception as error:
        _print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
