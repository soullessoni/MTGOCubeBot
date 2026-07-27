"""Full give+return cycle, decklist-driven ONLY — no per-card manual
search fallback anywhere. If Import Deck doesn't stage every card, this
is treated as a hard failure to report, not something to patch over
with a search. Also times each phase.

Card list is deliberately curated to exclude the known problem cases
(cards where FruitDuChene independently owns extra copies, and
non-singleton lands/basics the bot already holds copies of) — see
mtgo_automation_mechanics memory: those are a real, understood Import
Deck limitation, not something this run is trying to prove around.
"""

import sys
import time
from pathlib import Path

from mtgo.catid_map import load_default_catid_map
from mtgo.client import (
    accept_incoming_trade_request,
    confirm_trade,
    create_binder_from_cards,
    delete_binder,
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
)
from mtgo.stock_check import compute_return_reconciliation, diff_stock, parse_dek_quantities

CARDS = [
    "Harmonized Trio", "Wingcrafter", "Siren Stormtamer", "Voidmage Prodigy",
    "Floodpits Drowner", "Merfolk Trickster", "Mist-Syndicate Naga",
    "Tishana's Tidebinder", "Tireless Tracker", "Scrawling Crawler",
    "Silumgar Sorcerer", "Scuttling Sentinel", "Sea-Dasher Octopus",
    "Stunt Double", "Mystic Snake",
]

BOT = "TheLegionCube"
PLAYER = "FruitDuChene"


class CycleFailure(RuntimeError):
    pass


def goto_collection(window):
    btn = find_by_automation_id(window, "CollectionButton")
    if btn:
        window.set_focus()
        time.sleep(0.5)
        btn.click_input()
        time.sleep(2.0)


def clear_popups(window):
    for _ in range(5):
        d1 = dismiss_added_to_collection_popup(window, timeout=3)
        d2 = dismiss_trade_completed_popup(window, timeout=3)
        if not d1 and not d2:
            break


def export(window, filename) -> dict:
    path = export_full_trade_list(window, Path(f"mtgo/lists/{filename}"))
    return parse_dek_quantities(path)


def run_give_leg(bot, player, binder_name, card_names, catid_map) -> None:
    request_trade_with_binder(bot, PLAYER, binder_name)
    print(f"  give trade requested (binder {binder_name!r})")

    accepted = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            accept_incoming_trade_request(player, BOT, "Full Trade List", timeout=3.0)
            accepted = True
            break
        except Exception:
            continue
    if not accepted:
        raise CycleFailure("player did not accept the give trade request")

    player_tw = wait_for_trade_window(BOT, timeout=30.0)
    bot_tw = wait_for_trade_window(PLAYER, timeout=30.0)
    if player_tw is None or bot_tw is None:
        raise CycleFailure("trade window(s) did not open after acceptance")

    from mtgo.client import _write_dek_file
    dek = _write_dek_file(f"{binder_name}-give", card_names, catid_map=catid_map)
    clean = import_deck_for_comparison(player_tw, dek, viewer_username=PLAYER, settle_timeout=25.0)

    received = read_receiving_panel(player_tw, PLAYER)
    print(f"  Import Deck staged {len(received)}/{len(set(card_names))} unique names (clean={clean})")
    if len(received) != len(set(card_names)):
        missing = set(card_names) - received
        raise CycleFailure(f"Import Deck did not stage everything on GIVE — missing: {missing}")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        raise CycleFailure("Confirm Trade never appeared on GIVE leg")
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("  give confirmed both sides.")


def run_return_leg(bot, player, card_names, catid_map) -> None:
    request_trade_with_binder(bot, PLAYER, "Full Trade List")
    print("  return trade requested")

    accepted = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            accept_incoming_trade_request(player, BOT, "Full Trade List", timeout=3.0)
            accepted = True
            break
        except Exception:
            continue
    if not accepted:
        raise CycleFailure("player did not accept the return trade request")

    bot_tw = wait_for_trade_window(PLAYER, timeout=30.0)
    player_tw = wait_for_trade_window(BOT, timeout=30.0)
    if bot_tw is None or player_tw is None:
        raise CycleFailure("trade window(s) did not open after acceptance")

    from mtgo.client import _write_dek_file
    dek = _write_dek_file("V4ReturnCompare", card_names, catid_map=catid_map)
    clean = import_deck_for_comparison(bot_tw, dek, viewer_username=BOT, settle_timeout=25.0)

    received = read_receiving_panel(bot_tw, BOT)
    print(f"  Import Deck staged {len(received)}/{len(set(card_names))} unique names (clean={clean})")
    if len(received) != len(set(card_names)):
        missing = set(card_names) - received
        raise CycleFailure(f"Import Deck did not stage everything on RETURN — missing: {missing}")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        raise CycleFailure("Confirm Trade never appeared on RETURN leg")
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("  return confirmed both sides.")


def main():
    sys.stdout.reconfigure(errors="replace")
    catid_map = load_default_catid_map()

    bot = find_mtgo_window(BOT)
    player = find_mtgo_window(PLAYER)
    if bot is None or player is None:
        print(f"MTGO window(s) not found: bot={bot is not None} player={player is not None}")
        return 1

    clear_popups(bot)
    clear_popups(player)

    t_start = time.monotonic()

    print("=== BASELINE EXPORT ===")
    goto_collection(bot)
    before_give = export(bot, "v4_before_give.dek")
    print(f"  bot total before: {sum(before_give.values())}")

    print("=== GIVE ===")
    t_give_start = time.monotonic()
    binder_name = "V4Test-FruitDuChene"
    label = create_binder_from_cards(bot, binder_name, CARDS, catid_map=catid_map)
    print(f"  binder: {label}")

    try:
        run_give_leg(bot, player, binder_name, CARDS, catid_map)
    except CycleFailure as e:
        print(f"GIVE leg FAILED (no manual-search fallback attempted, per instructions): {e}")
        return 1
    t_give_end = time.monotonic()

    clear_popups(bot)
    clear_popups(player)

    print("=== POST-GIVE EXPORT (baseline for return reconciliation) ===")
    goto_collection(bot)
    before_return = export(bot, "v4_before_return.dek")
    print(f"  bot total after give: {sum(before_return.values())}")

    print("=== RETURN ===")
    t_return_start = time.monotonic()
    try:
        run_return_leg(bot, player, CARDS, catid_map)
    except CycleFailure as e:
        print(f"RETURN leg FAILED (no manual-search fallback attempted, per instructions): {e}")
        return 1
    t_return_end = time.monotonic()

    clear_popups(bot)
    clear_popups(player)

    print("=== FINAL EXPORT + RECONCILIATION ===")
    goto_collection(bot)
    after_return = export(bot, "v4_after_return.dek")
    print(f"  bot total after return: {sum(after_return.values())}")

    reconciliation = compute_return_reconciliation(before_return, after_return, CARDS)
    print(f"  to_give_back: {reconciliation['to_give_back']}")
    print(f"  still_owed: {reconciliation['still_owed']}")

    original_baseline = parse_dek_quantities("mtgo/lists/full_trade_list.dek")
    final_diff = diff_stock(original_baseline, after_return)
    print(f"  missing vs original 610-baseline: {final_diff['missing']}")
    print(f"  extra vs original 610-baseline: {final_diff['extra']}")

    delete_binder(bot, binder_name)

    t_end = time.monotonic()

    print("=== TIMING ===")
    print(f"  GIVE leg:   {t_give_end - t_give_start:.1f}s")
    print(f"  RETURN leg: {t_return_end - t_return_start:.1f}s")
    print(f"  total (incl. exports/reconciliation): {t_end - t_start:.1f}s")

    success = not reconciliation["to_give_back"] and not reconciliation["still_owed"]
    print("=== RESULT:", "SUCCESS — 0 manual searches used" if success else "RECONCILIATION MISMATCH", "===")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
