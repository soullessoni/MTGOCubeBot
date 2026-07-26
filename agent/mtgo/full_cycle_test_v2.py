"""One-off validation script: run the full give+return cycle for a
40-card test pool using tonight's fixes — CatID-correct binder import
for the give direction, and the Search Tools "Import Deck" filter
combined with exact-CatID matching for the return direction.

Not meant to be a permanent production script (that's
prepare_session_binders.py / process_session_returns.py); this exists
to validate the new mechanics end to end on the live two-account setup.
"""

import sys
import time

from pywinauto import Desktop

from mtgo.catid_map import load_default_catid_map
from mtgo.client import (
    _find_visible_edit,
    accept_incoming_trade_request,
    add_all_cards_from_partner_binder,
    add_card_from_partner_binder,
    confirm_trade,
    create_binder_from_cards,
    delete_binder,
    dismiss_added_to_collection_popup,
    dismiss_trade_completed_popup,
    find_by_automation_id,
    find_mtgo_window,
    read_receiving_panel,
    request_trade_with_binder,
    submit_trade,
    wait_for_confirm_trade_button,
    wait_for_trade_window,
)

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

BINDER_NAME = "FullCycleV2-FruitDuChene"
COMPARE_DEK_NAME = "FullCycleV2Compare"


def import_deck_into_search_tools(trade_window, dek_path) -> bool:
    """Click Search Tools -> Import Deck -> fill the native file picker
    with `dek_path`. Returns True if no "missing cards" Warning dialog
    appeared (a correct-CatID .dek shouldn't trigger one)."""
    search_tools_btn = None
    for el in trade_window.descendants():
        try:
            text = el.window_text()
            cls = el.friendly_class_name()
        except Exception:
            continue
        if cls == "Button" and text.strip() == "Search Tools":
            search_tools_btn = el
            break
    if search_tools_btn is None:
        raise RuntimeError("Search Tools button not found")
    search_tools_btn.click_input()
    time.sleep(1.5)

    import_btn = None
    for el in trade_window.descendants():
        try:
            text = el.window_text()
            cls = el.friendly_class_name()
        except Exception:
            continue
        if cls == "Button" and text.strip() == "Import Deck":
            import_btn = el
            break
    if import_btn is None:
        raise RuntimeError("Import Deck button not found (Search Tools dialog didn't open)")
    import_btn.click_input()
    time.sleep(1.5)

    file_dialog = None
    for w in Desktop(backend="win32").windows():
        try:
            if w.window_text() == "Select Deck(s)":
                file_dialog = w
                break
        except Exception:
            continue
    if file_dialog is None:
        raise RuntimeError("'Select Deck(s)' file dialog not found")

    edit = _find_visible_edit(file_dialog)
    edit.set_focus()
    edit.set_edit_text(str(dek_path))
    time.sleep(0.3)
    edit.type_keys("{ENTER}")
    time.sleep(2.0)

    for el in trade_window.descendants():
        try:
            text = el.window_text()
            cls = el.friendly_class_name()
        except Exception:
            continue
        if cls == "Dialog" and text == "Warning":
            for sub in el.descendants():
                try:
                    sub_text = sub.window_text()
                    sub_cls = sub.friendly_class_name()
                except Exception:
                    continue
                if sub_cls == "Button" and sub_text.strip() == "OK":
                    sub.invoke()
                    time.sleep(1.0)
                    return False
    return True


def main():
    sys.stdout.reconfigure(errors="replace")
    catid_map = load_default_catid_map()

    bot = find_mtgo_window("TheLegionCube")
    player = find_mtgo_window("FruitDuChene")
    dismiss_trade_completed_popup(bot, timeout=3)
    dismiss_added_to_collection_popup(bot, timeout=3)

    # --- GIVE ---
    print("=== GIVE ===")
    coll = find_by_automation_id(bot, "CollectionButton")
    if coll:
        coll.click_input()
        time.sleep(2.0)
    label = create_binder_from_cards(bot, BINDER_NAME, CARDS, catid_map=catid_map)
    print(f"binder created: {label}")

    request_trade_with_binder(bot, "FruitDuChene", BINDER_NAME)
    print("trade requested, recipient verified")

    accepted = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            accept_incoming_trade_request(player, "TheLegionCube", "Full Trade List", timeout=3.0)
            accepted = True
            break
        except Exception:
            continue
    print("accepted:", accepted)

    player_tw = wait_for_trade_window("TheLegionCube", timeout=30.0)
    bot_tw = wait_for_trade_window("FruitDuChene", timeout=30.0)

    added = add_all_cards_from_partner_binder(player_tw, CARDS, timeout=8.0)
    missing = sorted(set(CARDS) - set(added))
    for name in missing:
        if add_card_from_partner_binder(player_tw, name, timeout=15.0):
            added.append(name)
        else:
            print(f"  GIVE MISSED: {name}")

    print(f"GIVE total: {len(added)} / {len(CARDS)}")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        print("Confirm Trade never appeared on GIVE leg — aborting.")
        return 1
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("GIVE confirmed both sides.")

    dismiss_added_to_collection_popup(bot, timeout=8)
    dismiss_trade_completed_popup(bot, timeout=5)
    dismiss_added_to_collection_popup(player, timeout=8)
    dismiss_trade_completed_popup(player, timeout=5)

    # --- RETURN ---
    print("=== RETURN ===")
    from mtgo.client import _write_dek_file
    compare_dek = _write_dek_file(COMPARE_DEK_NAME, CARDS, catid_map=catid_map)

    request_trade_with_binder(bot, "FruitDuChene", "Full Trade List")
    print("return trade requested, recipient verified")

    accepted = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            accept_incoming_trade_request(player, "TheLegionCube", "Full Trade List", timeout=3.0)
            accepted = True
            break
        except Exception:
            continue
    print("accepted:", accepted)

    bot_tw = wait_for_trade_window("FruitDuChene", timeout=30.0)
    player_tw = wait_for_trade_window("TheLegionCube", timeout=30.0)

    clean_import = import_deck_into_search_tools(bot_tw, compare_dek)
    print("Search Tools import triggered no missing-cards warning:", clean_import)

    added_back = add_all_cards_from_partner_binder(bot_tw, CARDS, catid_map=catid_map, timeout=10.0)
    missing_back = sorted(set(CARDS) - set(added_back))
    for name in missing_back:
        expected_catid = catid_map.get(name)
        if add_card_from_partner_binder(bot_tw, name, catid=expected_catid, timeout=15.0):
            added_back.append(name)
        else:
            print(f"  RETURN MISSED (exact CatID {expected_catid}): {name}")

    print(f"RETURN total: {len(added_back)} / {len(CARDS)}")

    submit_trade(bot_tw)
    submit_trade(player_tw)
    if not wait_for_confirm_trade_button(bot_tw, timeout=60.0):
        print("Confirm Trade never appeared on RETURN leg — aborting.")
        return 1
    confirm_trade(bot_tw)
    confirm_trade(player_tw)
    print("RETURN confirmed both sides.")

    dismiss_added_to_collection_popup(bot, timeout=8)
    dismiss_trade_completed_popup(bot, timeout=5)
    dismiss_added_to_collection_popup(player, timeout=8)
    dismiss_trade_completed_popup(player, timeout=5)

    # --- CLEANUP ---
    coll = find_by_automation_id(bot, "CollectionButton")
    if coll:
        coll.click_input()
        time.sleep(2.0)
    deleted = delete_binder(bot, BINDER_NAME)
    print("test binder deleted:", deleted)

    print("=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
