"""Full decklist-driven give+return cycle, self-correcting via
before/after export diffs rather than any per-card manual search.

- GIVE: bot's binder is purpose-built (single edition per card), so
  the player's side can safely use Search Tools' Import Deck to bulk
  auto-add everything in one shot — no edition ambiguity possible.
- RETURN: bot uses Import Deck against the player's (potentially messy,
  independently-stocked) Full Trade List, which can over/under-grab.
  Correctness is verified afterward by diffing two real "Full Trade
  List" exports against what was actually owed
  (`stock_check.compute_return_reconciliation`), and any discrepancy is
  fixed with a follow-up decklist-driven trade — never by touching the
  trade that already closed, never by searching cards one at a time.
"""

import sys
import time

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
from mtgo.stock_check import compute_return_reconciliation, parse_dek_quantities

CARDS = [
    "Harmonized Trio", "Wingcrafter", "Siren Stormtamer", "Voidmage Prodigy",
    "Floodpits Drowner", "Merfolk Trickster", "Ice-Fang Coatl", "Spellskite",
    "Mist-Syndicate Naga", "Tishana's Tidebinder", "Tireless Tracker",
    "Scrawling Crawler", "Silumgar Sorcerer", "Scuttling Sentinel",
    "Sea-Dasher Octopus", "Stunt Double", "Mystic Snake",
    "Venser, Shaper Savant", "Frilled Mystic", "Voracious Greatshark",
    "Thragtusk", "Mulldrifter", "Deadeye Navigator", "Lumbering Falls",
    "Sea Gate", "Restless Vinestalk", "Mutavault", "Snow-Covered Forest",
    "Snow-Covered Island", "Fire-Lit Thicket", "Restless Anchorage",
    "Restless Spire", "Cascade Bluffs", "Restless Vents", "Endless One",
    "Ancient Ziggurat", "Thousand-Faced Shadow", "Ruby, Daring Tracker",
    "Tetsuko Umezawa, Fugitive", "Spellstutter Sprite",
]

BOT = "TheLegionCube"
PLAYER = "FruitDuChene"


def goto_collection(window):
    btn = find_by_automation_id(window, "CollectionButton")
    if btn:
        btn.click_input()
        time.sleep(2.0)


def clear_popups(window):
    for _ in range(5):
        d1 = dismiss_added_to_collection_popup(window, timeout=3)
        d2 = dismiss_trade_completed_popup(window, timeout=3)
        if not d1 and not d2:
            break


def export(window, filename) -> dict:
    from pathlib import Path
    path = export_full_trade_list(window, Path(f"mtgo/lists/{filename}"))
    return parse_dek_quantities(path)


def run_give_leg(bot, player, binder_name, card_names, catid_map) -> bool:
    """Player uses Import Deck against the bot's purpose-built (single
    edition) binder — no edition ambiguity, so a bulk decklist import
    should get everything in one shot."""
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
    print(f"  accepted: {accepted}")
    if not accepted:
        return False

    player_tw = wait_for_trade_window(BOT, timeout=30.0)
    bot_tw = wait_for_trade_window(PLAYER, timeout=30.0)

    from mtgo.client import _write_dek_file
    dek = _write_dek_file(f"{binder_name}-give", card_names, catid_map=catid_map)
    clean = import_deck_for_comparison(player_tw, dek, viewer_username=PLAYER, settle_timeout=25.0)
    print(f"  import deck clean: {clean}")

    received = read_receiving_panel(player_tw, PLAYER)
    print(f"  player staged: {len(received)} / {len(set(card_names))} unique names")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        print("  Confirm Trade never appeared.")
        return False
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("  give confirmed both sides.")
    return True


def run_return_leg(bot, player, card_names, catid_map) -> bool:
    """Bot uses Import Deck against the player's Full Trade List —
    correctness verified afterward via export diff, not here."""
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
    print(f"  accepted: {accepted}")
    if not accepted:
        return False

    bot_tw = wait_for_trade_window(PLAYER, timeout=30.0)
    player_tw = wait_for_trade_window(BOT, timeout=30.0)

    from mtgo.client import _write_dek_file
    dek = _write_dek_file("ReturnLeg", card_names, catid_map=catid_map)
    clean = import_deck_for_comparison(bot_tw, dek, viewer_username=BOT, settle_timeout=25.0)
    print(f"  import deck clean: {clean}")

    received = read_receiving_panel(bot_tw, BOT)
    print(f"  bot staged: {len(received)} / {len(set(card_names))} unique names")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        print("  Confirm Trade never appeared.")
        return False
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("  return confirmed both sides.")
    return True


def main():
    sys.stdout.reconfigure(errors="replace")
    catid_map = load_default_catid_map()

    bot = find_mtgo_window(BOT)
    player = find_mtgo_window(PLAYER)
    clear_popups(bot)
    clear_popups(player)

    print("=== BASELINE EXPORT ===")
    goto_collection(bot)
    before_give = export(bot, "v3_before_give.dek")
    print(f"  bot total before: {sum(before_give.values())}")

    print("=== GIVE ===")
    binder_name = "V3Test-FruitDuChene"
    label = create_binder_from_cards(bot, binder_name, CARDS, catid_map=catid_map)
    print(f"  binder: {label}")

    if not run_give_leg(bot, player, binder_name, CARDS, catid_map):
        print("GIVE leg failed, aborting.")
        return 1

    clear_popups(bot)
    clear_popups(player)

    print("=== POST-GIVE EXPORT (baseline for return reconciliation) ===")
    goto_collection(bot)
    before_return = export(bot, "v3_before_return.dek")
    print(f"  bot total after give: {sum(before_return.values())}")

    print("=== RETURN ===")
    if not run_return_leg(bot, player, CARDS, catid_map):
        print("RETURN leg failed, aborting.")
        return 1

    clear_popups(bot)
    clear_popups(player)

    print("=== POST-RETURN EXPORT + RECONCILIATION ===")
    goto_collection(bot)
    after_return = export(bot, "v3_after_return.dek")
    print(f"  bot total after return: {sum(after_return.values())}")

    reconciliation = compute_return_reconciliation(before_return, after_return, CARDS)
    print(f"  to_give_back: {reconciliation['to_give_back']}")
    print(f"  still_owed: {reconciliation['still_owed']}")

    if reconciliation["to_give_back"]:
        print("=== CORRECTIVE GIVE-BACK ===")
        excess_names = []
        for name, qty in reconciliation["to_give_back"].items():
            excess_names.extend([name] * qty)
        fix_binder = "V3Fix-GiveBack"
        create_binder_from_cards(bot, fix_binder, excess_names, catid_map=catid_map)
        run_give_leg(bot, player, fix_binder, excess_names, catid_map)
        clear_popups(bot)
        clear_popups(player)
        delete_binder(bot, fix_binder)

    if reconciliation["still_owed"]:
        print("=== CORRECTIVE RE-RETURN ===")
        owed_names = []
        for name, qty in reconciliation["still_owed"].items():
            owed_names.extend([name] * qty)
        run_return_leg(bot, player, owed_names, catid_map)
        clear_popups(bot)
        clear_popups(player)

    print("=== FINAL VERIFICATION ===")
    goto_collection(bot)
    final = export(bot, "v3_final.dek")
    original_baseline = parse_dek_quantities("mtgo/lists/full_trade_list.dek")
    from mtgo.stock_check import diff_stock
    final_diff = diff_stock(original_baseline, final)
    print(f"  total: {sum(final.values())}")
    print(f"  missing vs original 610-baseline: {final_diff['missing']}")
    print(f"  extra vs original 610-baseline: {final_diff['extra']}")

    delete_binder(bot, binder_name)

    print("=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
