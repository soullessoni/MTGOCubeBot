"""KO-recovery script for the "to_give_back" reconciliation case: the
bot ended up holding excess copies of some card(s) after a return trade
(Import Deck grabbed more than was actually owed). This exposes those
excess cards to the player via a purpose-built binder — the player
pulls them via Search Tools/Import Deck on their own client, exactly
like the normal "give" direction (prepare_session_binders.py). These
cards are never tied to LoanAssignment rows (they were never legitimately
owed), so nothing is written back to the backend from this script — the
job's own `result` JSON is the only record of what was given back.

Usage:
  .venv/Scripts/python.exe -m mtgo.give_back_excess_cards <mtgo_username> <cards_json> <job_id>

`cards_json` is a single JSON-encoded {"Card Name": quantity, ...}
argument (not one arg per card) — this sidesteps shell-quoting issues
with apostrophes/spaces/commas in card names. `job_id` is only used to
build a readable, collision-free binder name; this script has no other
awareness of the job-tracking system.

Always prints exactly one final JSON line before exiting — see
process_session_returns.py's docstring for why.
"""

import json
import os
import sys

from dotenv import load_dotenv

from mtgo.catid_map import load_default_catid_map
from mtgo.client import create_binder_from_cards, find_mtgo_window

load_dotenv()


def expand_cards_to_names(cards: dict[str, int]) -> list[str]:
    """{"Mulldrifter": 2} -> ["Mulldrifter", "Mulldrifter"] — matches
    create_binder_from_cards' and the rest of the codebase's
    "list with repeats = quantity" convention."""
    names: list[str] = []
    for name, quantity in cards.items():
        names.extend([name] * quantity)
    return names


def _print_result(result: dict) -> None:
    print(json.dumps(result))


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 4:
        print("Usage: python -m mtgo.give_back_excess_cards <mtgo_username> <cards_json> <job_id>")
        _print_result({"ok": False, "error": "usage: <mtgo_username> <cards_json> <job_id> required"})
        return 1

    mtgo_username = sys.argv[1]
    cards = json.loads(sys.argv[2])
    job_id = sys.argv[3]

    try:
        card_names = expand_cards_to_names(cards)
        if not card_names:
            print("No cards to give back.")
            _print_result({"ok": False, "error": "cards must not be empty"})
            return 1

        window = find_mtgo_window(os.environ.get("MTGO_USERNAME"))
        if window is None:
            print("MTGO window not found.")
            _print_result({"ok": False, "error": "MTGO window not found."})
            return 1

        catid_map = load_default_catid_map()
        binder_name = f"GiveBack-Job{job_id}-{mtgo_username}"
        label = create_binder_from_cards(window, binder_name, card_names, catid_map=catid_map)
        print(f"{mtgo_username}: {label} ({len(card_names)} cards)")

        _print_result({"ok": True, "binder_label": label, "cards": cards})
        return 0
    except Exception as error:
        _print_result({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
