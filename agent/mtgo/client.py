"""Reusable MTGO desktop-client automation, consolidating the mechanics
validated by the reconnaissance scripts in this package (see README.md
and the `mtgo_automation_mechanics` memory for the full write-up).

Not a CLI tool like the other scripts here — this is the module the loan
session workflow is meant to call into. Every function takes/returns
plain pywinauto elements or simple values so callers don't need to know
about automation_ids directly.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from pywinauto import Desktop

load_dotenv()

LISTS_DIR = Path(__file__).parent / "lists"

BINDER_ROW_TEXT = "WotC.MtGO.Client.Model.Core.Collection.Binder"
MEGABINDER_ROW_TEXT = "WotC.MtGO.Client.Model.Core.Collection.MegaBinder"

MTGO_APPREF_PATH = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Daybreak Game Company LLC"
    / "Magic The Gathering Online .appref-ms"
)


class MtgoAutomationError(RuntimeError):
    """Raised when an expected MTGO UI element or state can't be found."""


def _logged_in_account(window) -> str | None:
    """The logged-in username is NOT reliably found by searching for a
    Static matching the account name anywhere in the tree — a buddy's
    name shows up the exact same way in the Buddies list, and one
    account can easily be a false-positive match for another's window
    (confirmed live: searching for "FruitDuChene" matched TheLegionCube's
    own window, because FruitDuChene is on TheLegionCube's buddy list).
    The only reliable spot is the plain Static that immediately follows
    `ChangeAvatarMainNavButton` in the nav bar — that position is
    specifically the "logged in as" label, never a buddy-list entry.
    """
    descendants = window.descendants()
    for index, element in enumerate(descendants):
        try:
            aid = element.element_info.automation_id
        except Exception:
            continue
        if aid != "ChangeAvatarMainNavButton":
            continue
        for candidate in descendants[index + 1:index + 4]:
            try:
                text = candidate.window_text()
                control = candidate.friendly_class_name()
            except Exception:
                continue
            if control == "Static" and text.strip():
                return text.strip()
    return None


def find_mtgo_window(account: str | None = None):
    """Find the MTGO main window. With two instances open (e.g. a bot
    account and a test-player account logged in side by side), both
    windows share the exact same title — pass `account` to disambiguate
    by the logged-in username (see `_logged_in_account`). With
    `account=None`, returns the first MTGO window found."""
    candidates = []
    for window in Desktop(backend="uia").windows():
        try:
            if window.window_text().strip().lower() == "magic: the gathering online":
                candidates.append(window)
        except Exception:
            continue

    if account is None:
        return candidates[0] if candidates else None

    for window in candidates:
        if _logged_in_account(window) == account:
            return window

    return None


def find_trade_window(partner_name: str | None = None):
    for window in Desktop(backend="uia").windows():
        try:
            title = window.window_text()
        except Exception:
            continue
        if not title.strip().lower().startswith("trade:"):
            continue
        if partner_name is None or partner_name in title:
            return window
    return None


def wait_for_trade_window(partner_name: str, timeout: float = 300.0, interval: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        window = find_trade_window(partner_name)
        if window is not None:
            return window
        time.sleep(interval)
    return None


def find_by_automation_id(window, automation_id: str):
    for element in window.descendants():
        try:
            if element.element_info.automation_id == automation_id:
                return element
        except Exception:
            continue
    return None


def _read_deck_total_label(window):
    element = find_by_automation_id(window, "DeckTotalCardsText")
    if element is None:
        return None
    try:
        return element.window_text()
    except Exception:
        return None


def _binder_rows(window):
    rows = []
    for element in window.descendants():
        try:
            if element.window_text() == BINDER_ROW_TEXT:
                rows.append(element)
        except Exception:
            continue
    return rows


def open_binder(window, binder_name: str, timeout: float = 15.0) -> bool:
    """Double-click binder rows in turn until the one named `binder_name`
    is the active one (a single click only highlights a row — it does
    not become the add/import target). Binder rows carry no
    automation_id and share the same window_text(), so this is the only
    reliable way to target one by name."""
    window.set_focus()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = _binder_rows(window)
        for row in rows:
            row.double_click_input()
            time.sleep(1.0)
            label = _read_deck_total_label(window)
            if label is not None and label.startswith(f"{binder_name}:"):
                return True
    return False


def binder_exists(window, binder_name: str) -> bool:
    return open_binder(window, binder_name, timeout=6.0)


def delete_binder(window, binder_name: str) -> bool:
    """Open the binder, right-click a *freshly re-fetched* reference to
    the same row (a reference captured before the tree last re-rendered
    can go stale and silently fail to open a context menu), click
    Delete, then confirm — the confirmation dialog's own button is also
    labeled "Delete", not "Yes"/"OK"."""
    if not open_binder(window, binder_name, timeout=10.0):
        return False

    rows = _binder_rows(window)
    for row in rows:
        row.right_click_input()
        time.sleep(1.2)

        delete_item = None
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "MenuItem" and text.strip() == "Delete":
                delete_item = element
                break

        if delete_item is None:
            window.type_keys("{ESC}")
            time.sleep(0.3)
            continue

        delete_item.click_input()
        time.sleep(1.2)

        confirmed = False
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Button" and text.strip() in ("Delete", "Yes", "OK"):
                element.click_input()
                time.sleep(1.2)
                confirmed = True
                break

        if not confirmed:
            continue

        label = _read_deck_total_label(window)
        return not (label and label.startswith(f"{binder_name}:"))

    return False


def export_full_trade_list(window, save_path: Path, timeout: float = 15.0) -> Path:
    """Export the account's "Full Trade List" (its entire real
    collection, quantities and CatIDs included) to a .dek file at
    `save_path` — the ground truth for post-trade stock verification
    (see `stock_check.py`).

    **Right-click gotcha confirmed live 2026-07-26**: the "Full Trade
    List" row's `right_click_input()` only opens its context menu
    reliably when called on the tree-view element (`window_text() ==
    MEGABINDER_ROW_TEXT`) directly — right-clicking via raw screen
    coordinates on the icon-gallery tile below (which visually also
    shows an "Export" hover button) was unreliable in practice."""
    window.set_focus()
    target = None
    for element in window.descendants():
        try:
            text = element.window_text()
        except Exception:
            continue
        if text == MEGABINDER_ROW_TEXT:
            target = element
            break
    if target is None:
        raise MtgoAutomationError("'Full Trade List' row not found")

    target.right_click_input()
    time.sleep(2.5)

    export_item = None
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if control == "MenuItem" and text.strip() == "Export":
            export_item = element
            break
    if export_item is None:
        raise MtgoAutomationError("'Export' context menu item not found")
    export_item.invoke()
    time.sleep(1.5)

    file_dialog = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for w in Desktop(backend="win32").windows():
            try:
                if w.window_text() == "Export Deck":
                    file_dialog = w
                    break
            except Exception:
                continue
        if file_dialog is not None:
            break
        time.sleep(0.5)
    if file_dialog is None:
        raise MtgoAutomationError("'Export Deck' file dialog not found")

    save_path = save_path.resolve()
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # This dialog has TWO Edit controls (a "search this folder" box near
    # the top, and the real filename field near the bottom) —
    # `_find_visible_edit`'s "first visible Edit" heuristic picks
    # whichever appears first in traversal order, which was confirmed
    # live 2026-07-26 to be the search box, silently leaving the
    # filename field untouched with a stale value from a previous
    # attempt. Target the one in the bottom half of the dialog instead.
    # The dialog's top-level window can exist for a moment before its
    # child controls (the filename field included) are actually attached
    # — confirmed live 2026-07-27: a one-shot descendants() walk right
    # after finding the dialog missed the field even though it was
    # visibly there a fraction of a second later. Poll instead, matching
    # every other "wait for a dialog's contents to settle" spot in this
    # module.
    dialog_rect = file_dialog.rectangle()
    edit = None
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        for element in file_dialog.descendants():
            try:
                control = element.friendly_class_name()
                visible = element.is_visible()
                rect = element.rectangle()
            except Exception:
                continue
            if control == "Edit" and visible and (rect.top - dialog_rect.top) / dialog_rect.height() > 0.5:
                edit = element
                break
        if edit is not None:
            break
        time.sleep(0.3)
    if edit is None:
        raise MtgoAutomationError("filename field not found in Export Deck dialog")

    edit.set_focus()
    edit.set_edit_text(str(save_path))
    time.sleep(0.3)
    edit.type_keys("{ENTER}")
    time.sleep(1.5)

    # Confirm overwrite if the file already exists from a previous export.
    for w in Desktop(backend="win32").windows():
        try:
            if w.window_text() != "Export Deck":
                continue
        except Exception:
            continue
        for element in w.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Button" and text.strip() == "&Oui":
                element.click()
                time.sleep(1.0)
                break

    return save_path


def _write_dek_file(
        binder_name: str,
        card_names: list[str],
        catid_map: dict[str, str] | None = None,
) -> Path:
    """Write a .dek file for import. `catid_map` (name -> CatID, e.g.
    from `catid_map.load_default_catid_map()`) lets a card reference
    the exact edition the account actually owns instead of `CatID="0"`,
    which makes MTGO resolve by name alone and silently pick the most
    recent printing — even if the account owns a different one (see
    `catid_map.py` for the full story). Falls back to "0" for any name
    not in the map."""
    LISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = LISTS_DIR / f"{binder_name}.dek"
    catid_map = catid_map or {}

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        "  <NetDeckID>0</NetDeckID>",
        "  <PreconstructedDeckID>0</PreconstructedDeckID>",
    ]
    for name in card_names:
        catid = catid_map.get(name, "0")
        lines.append(
            f'  <Cards CatID="{catid}" Quantity="1" Sideboard="false" '
            f'Name="{escape(name)}" Annotation="0" />'
        )
    lines.append("</Deck>")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _find_visible_edit(window):
    for element in window.descendants():
        try:
            if element.class_name() == "Edit" and element.is_visible():
                return element
        except Exception:
            continue
    return None


def _dialog_present(window, title: str) -> bool:
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if control == "Dialog" and text == title:
            return True
    return False


def create_binder_from_cards(
        window,
        binder_name: str,
        card_names: list[str],
        catid_map: dict[str, str] | None = None,
) -> str:
    """Create (or replace) a binder populated with exactly `card_names`,
    by importing a generated .dek file. Returns the final
    "<name>: <count>" label, or raises MtgoAutomationError if any step
    fails.

    **Pass `catid_map`** (name -> CatID, typically
    `catid_map.load_default_catid_map()`) whenever you can — without it,
    every card uses `CatID="0"` and MTGO resolves by name alone, which
    silently picks the *most recent* printing of that name rather than
    whatever edition the account actually owns. The binder then reports
    the full requested count but only actually exposes cards that
    happened to resolve to an owned edition (confirmed live 2026-07-25:
    a 58-card CatID="0" import only offered 27 cards in a real trade).

    The binder-name field auto-fills correctly from the .dek filename
    (which is `binder_name` itself) — do NOT try to overwrite that field,
    doing so was found to leave the dialog in a broken state where the
    OK button silently does nothing.
    """
    window.set_focus()
    if binder_exists(window, binder_name):
        delete_binder(window, binder_name)
        time.sleep(1.5)

    dek_path = _write_dek_file(binder_name, card_names, catid_map=catid_map)

    collection_btn = find_by_automation_id(window, "CollectionButton")
    if collection_btn is not None:
        collection_btn.click_input()
        time.sleep(2.0)

    for _ in range(3):
        if _dialog_present(window, "Add or Import Binder(s)"):
            break
        add_btn = find_by_automation_id(window, "AddBinderButton-Small")
        if add_btn is None:
            raise MtgoAutomationError("AddBinderButton-Small not found")
        add_btn.click_input()
        time.sleep(2.0)
    else:
        raise MtgoAutomationError("'Add or Import Binder(s)' dialog did not open")

    import_btn = find_by_automation_id(window, "AddDeckDialog-ImportButton")
    if import_btn is None:
        raise MtgoAutomationError("AddDeckDialog-ImportButton not found")
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
        raise MtgoAutomationError("'Select Deck(s)' file dialog not found")

    filename_edit = _find_visible_edit(file_dialog)
    if filename_edit is None:
        raise MtgoAutomationError("filename field not found in Select Deck(s) dialog")
    filename_edit.set_focus()
    filename_edit.set_edit_text(str(dek_path))
    time.sleep(0.3)
    filename_edit.type_keys("{ENTER}")
    time.sleep(1.2)

    for _ in range(3):
        dialog_present = False
        ok_btn = None
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
                aid = element.element_info.automation_id
            except Exception:
                continue
            if control == "Dialog" and text == "Add or Import Binder(s)":
                dialog_present = True
            elif text.strip() == "OK" and control == "Button" and aid == "OkButton":
                ok_btn = element
            if dialog_present and ok_btn is not None:
                break

        if not dialog_present:
            break

        if ok_btn is None:
            raise MtgoAutomationError("OK button not found on Add/Import Binder dialog")
        ok_btn.click_input()
        time.sleep(1.5)

    if not open_binder(window, binder_name, timeout=10.0):
        raise MtgoAutomationError(
            f"binder {binder_name!r} could not be confirmed after import"
        )

    return _read_deck_total_label(window)


def is_buddy(window, username: str) -> bool:
    return find_by_automation_id(window, f"MyBuddy-{username}") is not None


def _wait_until_buddy(window, username: str, timeout: float = 6.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_buddy(window, username):
            return True
        time.sleep(0.5)
    return False


def ensure_buddy(window, username: str) -> None:
    """Add `username` to the buddy list if they aren't on it already.
    Validated round-trip (remove/re-add) on 2026-07-25: `AddBuddyButton`
    opens an "Add Buddy" dialog with an `Entry` text field and an
    `Entrybutton` ("Add Buddy") to submit it.

    The buddy list widget (`AddBuddyButton`/`MyBuddy-<name>`) only
    exists on some screens (Home, Trade) — not on Collection, where a
    caller is likely to be right after populating a binder. Navigate
    Home first so this works regardless of which screen the caller left
    the window on.
    """
    window.set_focus()
    home_btn = find_by_automation_id(window, "HomeButton")
    if home_btn is not None:
        home_btn.click_input()

    # MTGO's own screen-navigation and dialog rendering is genuinely
    # slow and variable (a recurring theme throughout this module) — a
    # fixed sleep here was observed to sometimes not be enough, causing
    # a false "not a buddy" reading right after this same buddy was
    # confirmed present moments earlier. Poll instead.
    if _wait_until_buddy(window, username):
        return

    add_btn = find_by_automation_id(window, "AddBuddyButton")
    if add_btn is None:
        raise MtgoAutomationError("AddBuddyButton not found")
    add_btn.click_input()

    entry = None
    entry_btn = None
    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        for element in window.descendants():
            try:
                control = element.friendly_class_name()
                aid = element.element_info.automation_id
            except Exception:
                continue
            if aid == "Entry" and control == "Edit":
                entry = element
            if aid == "Entrybutton":
                entry_btn = element
        if entry is not None and entry_btn is not None:
            break
        time.sleep(0.5)

    if entry is None or entry_btn is None:
        raise MtgoAutomationError("Add Buddy dialog fields not found")

    entry.set_focus()
    entry.type_keys(username, with_spaces=True)
    time.sleep(0.5)
    entry_btn.click_input()

    if _wait_until_buddy(window, username):
        return

    raise MtgoAutomationError(f"buddy {username!r} was not added")


def request_trade_with_binder(window, buddy_name: str, binder_name: str) -> None:
    """Ensure `buddy_name` is on the buddy list, then right-click them
    and select "Trade", picking the named binder in the resulting
    "Trade Request" dialog before sending. The right-click + menu-item
    click must happen in the same call — MTGO's context menu is
    transient and won't survive a separate invocation.

    The buddy element is named `Buddies-<name>` under the Trade tab's
    buddy panel — a different automation_id than the `MyBuddy-<name>`
    widget `ensure_buddy`/`is_buddy` use on the Home screen — so this
    switches to the Trade tab first.
    """
    # A leftover "Trade Completed" or "Added to your Collection" popup
    # from a just-finished trade can silently eat a HomeButton click and
    # break ensure_buddy() on the very next attempt (confirmed live,
    # repeatedly) — clear both defensively before doing anything else.
    window.set_focus()
    dismiss_trade_completed_popup(window, timeout=3)
    dismiss_added_to_collection_popup(window, timeout=3)

    ensure_buddy(window, buddy_name)

    trade_tab = find_by_automation_id(window, "TradeButton")
    if trade_tab is not None:
        trade_tab.click_input()
        time.sleep(1.5)

    buddy = find_by_automation_id(window, f"Buddies-{buddy_name}")
    if buddy is None:
        # the Trade screen's "Buddies" panel section is collapsible and
        # may not be expanded, in which case Buddies-<name> elements
        # don't exist in the tree at all yet
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if text.strip() == "Buddies" and control == "Custom":
                element.click_input()
                time.sleep(1.5)
                break
        buddy = find_by_automation_id(window, f"Buddies-{buddy_name}")

    if buddy is None:
        raise MtgoAutomationError(f"buddy element 'Buddies-{buddy_name}' not found")

    buddy.right_click_input()
    time.sleep(1.5)

    # Scope strictly to MenuItem controls and stop at the first match —
    # the Trade screen's live trade-post board has its own unrelated
    # "Trade" Buttons on every row, and a text-only match without a
    # control-type filter can grab one of those instead of the actual
    # context-menu item, sending a trade request to the wrong person
    # entirely (confirmed live: this once opened a Trade Request dialog
    # targeting a random public trade-bot's post instead of the intended
    # buddy — caught and cancelled before it was sent).
    trade_item = None
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if text.strip() == "Trade" and control == "MenuItem":
            trade_item = element
            break
    if trade_item is None:
        raise MtgoAutomationError("'Trade' context menu item not found")
    trade_item.click_input()
    time.sleep(1.5)

    # Defense in depth against the same class of bug: confirm the
    # dialog that opened is actually addressed to the intended buddy
    # before doing anything that sends a real trade request.
    prompt_text = None
    for element in window.descendants():
        try:
            text = element.window_text()
        except Exception:
            continue
        if text.strip().startswith("Select trade binder to present to"):
            prompt_text = text.strip()
            break
    if prompt_text is None:
        raise MtgoAutomationError(
            "Trade Request dialog did not open as expected"
        )
    if buddy_name not in prompt_text:
        raise MtgoAutomationError(
            f"Trade Request dialog is addressed to the wrong recipient: "
            f"{prompt_text!r} (expected {buddy_name!r})"
        )

    radio = None
    ok_btn = None
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
            aid = element.element_info.automation_id
        except Exception:
            continue
        if aid == binder_name and control == "RadioButton":
            radio = element
        if text.strip() == "OK" and control == "Button" and aid == "OkButton":
            ok_btn = element

    if radio is None:
        raise MtgoAutomationError(
            f"binder {binder_name!r} not offered in Trade Request dialog"
        )
    radio.click_input()
    time.sleep(0.5)

    if ok_btn is None:
        raise MtgoAutomationError("OK button not found on Trade Request dialog")
    ok_btn.invoke()
    time.sleep(1.0)


def select_other_products_tickets_filter(window) -> None:
    """Switch the item-category filter to "Other Products" and enable
    the "Tickets" checkbox — confirmed live 2026-07-29: MTGO tickets
    are internally an item named "Event Ticket" with CatID "1", using
    the exact same CardQuantityControl mechanism as real cards, just
    filed under this separate category tab rather than "Cards". Needed
    before `add_card_from_partner_binder(window, "Event Ticket", catid="1")`
    can find anything."""
    tab = find_by_automation_id(window, "FilterTab-Other")
    if tab is None:
        raise MtgoAutomationError("'Other Products' filter tab not found")
    tab.click_input()
    time.sleep(1.0)

    checkbox = find_by_automation_id(window, "FilterCards-OptionTickets")
    if checkbox is None:
        raise MtgoAutomationError("'Tickets' filter checkbox not found")
    try:
        already_checked = checkbox.get_toggle_state() == 1
    except Exception:
        already_checked = False
    if not already_checked:
        checkbox.click_input()
        time.sleep(1.0)


def select_cards_filter(window) -> None:
    """Switch the item-category filter back to "Cards" — confirmed live
    2026-07-29: leaving "Other Products" active breaks
    `export_full_trade_list`'s "Full Trade List" binder-row lookup on
    the main Collection screen afterward (the filter tab appears to be
    shared account-wide state, not scoped to whichever window set it),
    so this must be called before relying on that lookup again."""
    tab = find_by_automation_id(window, "FilterTab-Cards")
    if tab is None:
        raise MtgoAutomationError("'Cards' filter tab not found")
    tab.click_input()
    time.sleep(1.0)


def add_card_from_partner_binder(
        trade_window,
        card_name: str,
        catid: str | None = None,
        timeout: float = 8.0,
) -> bool:
    """Search the counterparty's exposed binder inside a trade window and
    add `card_name` to "You Will Receive". Targets the
    `<name>_<numericId>_CardQuantityControl` element rather than the
    `Collection-CardStack-<name>` image — the latter can carry a stale
    "ghost" automation peer for a previously searched card at the same
    screen position, silently adding the wrong card.

    **Pass `catid`** (e.g. from `catid_map.load_default_catid_map()`)
    whenever the exact printing matters — matching by name alone can
    grab the WRONG copy when the counterparty independently owns a
    different printing of a same-named card. Confirmed live 2026-07-26:
    retrieving "Tishana's Tidebinder" back from a player who also owned
    an unrelated copy matched CatID 117678 (their own) instead of the
    cube's own CatID 117962 — same name, wrong card, silently "succeeded".
    With `catid` set, only the exact `<name>_<catid>_CardQuantityControl`
    element counts as a match; if the search doesn't surface that exact
    printing, this returns False rather than falling back to any
    same-named card, so a caller can treat it as a real failure instead
    of silently taking the wrong item.

    **Critical gotcha confirmed live**: pressing `{ENTER}` in this search
    box does NOT submit the search against a large exposed collection
    (e.g. "Full Trade List") — the browse pane just silently keeps
    showing whatever was already displayed (confirmed: searching
    "Harmonized Trio" via Enter returned an unrelated leftover card,
    "Tishana's Tidebinder"). Only clicking the actual `SearchButton`
    (magnifying glass) reliably submits the query."""
    search_box = find_by_automation_id(trade_window, "searchTextBox")
    if search_box is None:
        raise MtgoAutomationError("searchTextBox not found in trade window")
    search_btn = find_by_automation_id(trade_window, "SearchButton")
    if search_btn is None:
        raise MtgoAutomationError("SearchButton not found in trade window")

    search_box.set_focus()
    search_box.type_keys("^a{DELETE}")
    search_box.type_keys(card_name, with_spaces=True)
    search_btn.click_input()

    suffix = "_CardQuantityControl"
    exact_aid = f"{card_name}_{catid}{suffix}" if catid is not None else None
    prefix = f"{card_name}_"
    deadline = time.monotonic() + timeout
    target = None
    while time.monotonic() < deadline:
        for element in trade_window.descendants():
            try:
                aid = element.element_info.automation_id or ""
            except Exception:
                continue
            if exact_aid is not None:
                if aid == exact_aid:
                    target = element
                    break
            elif aid.startswith(prefix) and aid.endswith(suffix):
                target = element
                break
        if target is not None:
            break
        time.sleep(0.25)

    if target is None:
        return False

    target.double_click_input()
    time.sleep(0.5)
    return True


def add_all_cards_from_partner_binder(
        trade_window,
        card_names: list[str],
        catid_map: dict[str, str] | None = None,
        timeout: float = 10.0,
) -> list[str]:
    """Add several cards from the counterparty's exposed binder in one
    pass, without a separate search per card. Searching once per card
    (as `add_card_from_partner_binder` does) doesn't scale — MTGO's own
    search-result rendering is slow enough that N searches means N
    multi-second waits — and is pointless when the exposed binder is
    already small (e.g. a purpose-built `Session<id>-<player>` binder
    containing exactly the target cards): the whole thing renders in one
    pass without any search at all, so this clears the search box once
    and reads every `<name>_<id>_CardQuantityControl` element already in
    the tree, double-clicking each one whose name is in `card_names`.

    **Pass `catid_map`** (name -> CatID) whenever the exact printing
    matters — same reasoning as `add_card_from_partner_binder`: without
    it, a name match can grab a DIFFERENT printing the counterparty
    happens to own independently instead of the one actually being
    retrieved. When a name has an entry in `catid_map`, only the exact
    `<name>_<catid>_CardQuantityControl` element counts; names absent
    from the map fall back to any same-named match.

    Not suitable for narrowing down a large binder (e.g. "Full Trade
    List" with a big collection behind it) where virtualization means
    only the currently-scrolled-into-view cards actually exist as UI
    Automation elements — for that case a caller should apply a filter
    (e.g. the Wish List "Compare to wishlist" filter) before calling
    this, or fall back to `add_card_from_partner_binder` per card.

    Returns the list of card names actually found and double-clicked
    (a subset of `card_names` if some aren't in the exposed binder).
    """
    search_box = find_by_automation_id(trade_window, "searchTextBox")
    if search_box is not None:
        search_box.set_focus()
        search_box.type_keys("^a{DELETE}")
        search_box.type_keys("{ENTER}")
        time.sleep(1.0)

    catid_map = catid_map or {}
    wanted = set(card_names)
    suffix = "_CardQuantityControl"
    found: dict[str, object] = {}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and len(found) < len(wanted):
        for element in trade_window.descendants():
            try:
                aid = element.element_info.automation_id or ""
            except Exception:
                continue
            if not aid.endswith(suffix):
                continue
            body = aid[: -len(suffix)]
            name = body.rsplit("_", 1)[0]
            if name not in wanted or name in found:
                continue
            expected_catid = catid_map.get(name)
            if expected_catid is not None:
                catid = body.rsplit("_", 1)[1] if "_" in body else ""
                if catid != expected_catid:
                    continue
            found[name] = element
        if len(found) < len(wanted):
            time.sleep(0.5)

    added = []
    for name, element in found.items():
        try:
            element.double_click_input()
            time.sleep(0.3)
            added.append(name)
        except Exception:
            continue

    return added


def open_search_tools_dialog(trade_window, retries: int = 3) -> bool:
    """Click the trade window's "Search Tools" button and confirm the
    real "compare against partner's trade binder" popup opened (has an
    `Import Deck` button) — not the visually-similar Cards filter
    sidebar, which is ALSO internally labeled "Search Tools" and can be
    what a `text.strip() == "Search Tools"` match lands on if the first
    click doesn't register cleanly. Confirmed live 2026-07-26: a single
    unverified click sometimes leaves the filter sidebar open instead
    of the popup, silently breaking any caller that assumes the popup
    is there. Retries with Escape + re-click in between."""
    trade_window.set_focus()
    for _ in range(retries):
        search_tools_btn = None
        for element in trade_window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Button" and text.strip() == "Search Tools":
                search_tools_btn = element
                break
        if search_tools_btn is None:
            raise MtgoAutomationError("'Search Tools' button not found in trade window")

        search_tools_btn.click_input()
        time.sleep(1.5)

        for element in trade_window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Button" and text.strip() == "Import Deck":
                return True

        trade_window.type_keys("{ESC}")
        time.sleep(0.5)

    return False


def import_deck_for_comparison(
        trade_window,
        dek_path: Path,
        viewer_username: str | None = None,
        settle_timeout: float = 20.0,
        timeout: float = 15.0,
) -> bool:
    """Open Search Tools (via `open_search_tools_dialog`), Import Deck
    `dek_path`, and dismiss any "cards not found" Warning. Returns
    False if that warning appeared (meaning some names in `dek_path`
    didn't resolve — expected to be rare/never with a CatID-correct
    file, see `catid_map.py`), True otherwise.

    **Pass `viewer_username`** so this can wait for the auto-add to
    actually finish before returning — confirmed live 2026-07-26 that
    the "Will Receive" item count keeps climbing for several seconds
    after import (a fixed short sleep caught as few as 12/40 cards; the
    rest only appeared with more time), so reading state too early
    makes the caller think most cards need the slow per-card fallback
    when they'd have auto-added for free with a bit more patience.
    Polls the item count until it stops growing for 1.5s or
    `settle_timeout` elapses.

    This only narrows the exposed binder's browse pane to matching
    names — it does NOT guarantee the shown items are the exact
    edition being sought (confirmed live: a filtered "Tishana's
    Tidebinder" showed a different CatID than the one being compared
    against). Always follow this with an exact-CatID pick (e.g.
    `reconcile_receiving_panel`), never treat "it's in the filtered
    view" as sufficient on its own.
    """
    if not open_search_tools_dialog(trade_window):
        raise MtgoAutomationError("Search Tools popup (with Import Deck) did not open")

    import_btn = None
    for element in trade_window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if control == "Button" and text.strip() == "Import Deck":
            import_btn = element
            break
    if import_btn is None:
        raise MtgoAutomationError("Import Deck button not found")
    import_btn.click_input()
    time.sleep(1.5)

    file_dialog = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for w in Desktop(backend="win32").windows():
            try:
                if w.window_text() == "Select Deck(s)":
                    file_dialog = w
                    break
            except Exception:
                continue
        if file_dialog is not None:
            break
        time.sleep(0.5)
    if file_dialog is None:
        raise MtgoAutomationError("'Select Deck(s)' file dialog not found")

    edit = _find_visible_edit(file_dialog)
    edit.set_focus()
    edit.set_edit_text(str(dek_path))
    time.sleep(0.3)
    edit.type_keys("{ENTER}")
    time.sleep(2.0)

    for element in trade_window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if control == "Dialog" and text == "Warning":
            for sub in element.descendants():
                try:
                    sub_text = sub.window_text()
                    sub_control = sub.friendly_class_name()
                except Exception:
                    continue
                if sub_control == "Button" and sub_text.strip() == "OK":
                    sub.invoke()
                    time.sleep(1.0)
                    return False

    if viewer_username is not None:
        wait_for_receiving_panel_to_settle(trade_window, viewer_username, settle_timeout)

    return True


def wait_for_receiving_panel_to_settle(
        trade_window,
        viewer_username: str,
        timeout: float,
        stable_for: float = 1.5,
        interval: float = 0.5,
) -> int:
    """Poll `viewer_username`'s "Will Receive" item count until it stops
    increasing for `stable_for` seconds. Returns the final count."""
    last_count = -1
    stable_since = time.monotonic()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = len(read_receiving_panel_catids(trade_window, viewer_username))
        if count != last_count:
            last_count = count
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= stable_for:
            return count
        time.sleep(interval)
    return last_count


def read_receiving_panel(trade_window, viewer_username: str) -> set[str]:
    """Return the set of card names currently staged in `viewer_username`'s
    "Will Receive" panel of an open trade window (their own username for
    "You Will Receive", the counterparty's for "<Name> Will Receive").

    This is what lets the loan workflow only advance the specific cards
    a player actually picked, rather than assuming they took every card
    that was offered — a player is never forced to take everything from
    an exposed binder. Call this after the other side submits (or after
    we submit, on the retrieval direction) and before confirming, to
    reconcile against what was planned.

    Scoped to the `<viewer_username>CollectionLayoutView` container
    specifically (not the whole trade window) so it can't pick up
    unrelated `Collection-CardStack-*` elements from the browse/search
    pane above it.
    """
    container = None
    for element in trade_window.descendants():
        try:
            aid = element.element_info.automation_id
        except Exception:
            continue
        if aid == f"{viewer_username}CollectionLayoutView":
            container = element
            break

    if container is None:
        raise MtgoAutomationError(
            f"'{viewer_username}CollectionLayoutView' panel not found in trade window"
        )

    names: set[str] = set()
    prefix = "Collection-CardStack-"
    for element in container.descendants():
        try:
            aid = element.element_info.automation_id or ""
        except Exception:
            continue
        if aid.startswith(prefix):
            names.add(aid[len(prefix):])

    return names


def _receiving_panel_container(trade_window, viewer_username: str):
    for element in trade_window.descendants():
        try:
            aid = element.element_info.automation_id
        except Exception:
            continue
        if aid == f"{viewer_username}CollectionLayoutView":
            return element
    return None


def read_receiving_panel_catids(trade_window, viewer_username: str) -> dict[str, str]:
    """Like `read_receiving_panel`, but returns `{name: catid}` instead
    of just names — the CatID is what actually distinguishes "the
    printing that was lent" from "a different printing of the same
    name the counterparty happens to own", which a bare name can't
    (see `trade_reconciliation.py` for why this matters)."""
    container = _receiving_panel_container(trade_window, viewer_username)
    if container is None:
        raise MtgoAutomationError(
            f"'{viewer_username}CollectionLayoutView' panel not found in trade window"
        )

    suffix = "_CardQuantityControl"
    catids: dict[str, str] = {}
    for element in container.descendants():
        try:
            aid = element.element_info.automation_id or ""
        except Exception:
            continue
        if not aid.endswith(suffix):
            continue
        body = aid[: -len(suffix)]
        if "_" not in body:
            continue
        name, catid = body.rsplit("_", 1)
        catids[name] = catid

    return catids


def remove_card_from_receiving_panel(
        trade_window,
        viewer_username: str,
        card_name: str,
        catid: str,
        timeout: float = 8.0,
) -> bool:
    """Right-click the exact `<card_name>_<catid>_CardQuantityControl`
    element in `viewer_username`'s "Will Receive" panel and click
    "Remove All Copies from Trade" — used to undo a wrong-edition item
    that Search Tools' Import Deck auto-add staged (it matches by name
    only). Returns False if that exact printing isn't currently staged."""
    container = _receiving_panel_container(trade_window, viewer_username)
    if container is None:
        raise MtgoAutomationError(
            f"'{viewer_username}CollectionLayoutView' panel not found in trade window"
        )

    target_aid = f"{card_name}_{catid}_CardQuantityControl"
    target = None
    for element in container.descendants():
        try:
            aid = element.element_info.automation_id or ""
        except Exception:
            continue
        if aid == target_aid:
            target = element
            break
    if target is None:
        return False

    target.right_click_input()
    time.sleep(1.0)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for element in trade_window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "MenuItem" and text.strip() == "Remove All Copies from Trade":
                element.invoke()
                time.sleep(1.0)
                return True
        time.sleep(0.25)

    return False


def reconcile_receiving_panel(
        trade_window,
        viewer_username: str,
        card_names: list[str],
        catid_map: dict[str, str],
        timeout: float = 15.0,
) -> dict[str, list]:
    """The fast-and-correct pairing for Search Tools' bulk auto-add:
    read what's actually staged (by exact CatID), remove anything
    staged under the wrong printing, and add whatever's missing or was
    just removed — using `add_card_from_partner_binder`'s exact-CatID
    matching so the replacement is guaranteed right. Never blindly adds
    on top of what Import Deck already staged (that's what caused 5
    duplicate cards live 2026-07-26).

    Returns the `plan_reconciliation` dict, plus `"still_missing"` for
    any name that couldn't be found/added even after this pass.
    """
    from mtgo.trade_reconciliation import plan_reconciliation

    expected = {name: catid_map[name] for name in card_names if name in catid_map}
    actual = read_receiving_panel_catids(trade_window, viewer_username)
    plan = plan_reconciliation(expected, actual)

    for name, wrong_catid in plan["to_remove"]:
        remove_card_from_receiving_panel(trade_window, viewer_username, name, wrong_catid)

    still_missing = []
    for name in plan["to_add"]:
        ok = add_card_from_partner_binder(trade_window, name, catid=catid_map.get(name), timeout=timeout)
        if not ok:
            still_missing.append(name)

    plan["still_missing"] = still_missing
    return plan


def submit_trade(trade_window) -> None:
    """Click Submit on this side of the trade. **Both participants must
    call this, even a giver who added nothing to their own "You Will
    Receive"** — confirmed live: `Confirm Trade` never appears until
    every side has submitted, not just whoever added cards. Uses
    `invoke()` rather than a synthetic `click_input()`, since the latter
    was observed to sometimes not register on this specific button."""
    for element in trade_window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if text.strip() == "Submit" and control == "Button":
            element.invoke()
            time.sleep(1.5)
            return
    raise MtgoAutomationError("Submit button not found in trade window")


def wait_for_confirm_trade_button(trade_window, timeout: float = 300.0, interval: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for element in trade_window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if text.strip() == "Confirm Trade" and control == "Button":
                return True
        time.sleep(interval)
    return False


def confirm_trade(trade_window) -> None:
    for element in trade_window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if text.strip() == "Confirm Trade" and control == "Button":
            element.invoke()
            time.sleep(1.5)
            return
    raise MtgoAutomationError("Confirm Trade button not found in trade window")


def accept_incoming_trade_request(
        window,
        sender_name: str,
        binder_name: str = "Full Trade List",
        timeout: float = 60.0,
) -> None:
    """Accept a trade request sent by `sender_name`, exposing
    `binder_name` on this side. The receiving side's "Trade Request"
    dialog looks like the sender's (same `OkButton`/`CancelButton`
    automation_ids and binder RadioButton list) but reads "<sender> has
    sent you a trade request..." and its buttons are labeled "Accept" /
    "Reject" / "Block" rather than "OK" / "Cancel". Waits up to
    `timeout` seconds for the dialog to appear."""
    window.set_focus()
    deadline = time.monotonic() + timeout
    dialog_text = None
    while time.monotonic() < deadline:
        for element in window.descendants():
            try:
                text = element.window_text()
            except Exception:
                continue
            if text.startswith(f"{sender_name} has sent you a trade request"):
                dialog_text = text
                break
        if dialog_text is not None:
            break
        time.sleep(1.0)

    if dialog_text is None:
        raise MtgoAutomationError(
            f"no incoming trade request from {sender_name!r} appeared"
        )

    radio = None
    accept_btn = None
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
            aid = element.element_info.automation_id
        except Exception:
            continue
        if aid == binder_name and control == "RadioButton":
            radio = element
        if text.strip() == "Accept" and control == "Button" and aid == "OkButton":
            accept_btn = element

    if radio is None:
        raise MtgoAutomationError(
            f"binder {binder_name!r} not offered in incoming Trade Request dialog"
        )
    radio.click_input()
    time.sleep(0.5)

    if accept_btn is None:
        raise MtgoAutomationError("Accept button not found on incoming Trade Request dialog")
    accept_btn.invoke()
    time.sleep(1.5)


def dismiss_trade_completed_popup(window, timeout: float = 5.0) -> bool:
    """A separate "Trade Completed" dialog (distinct from "Added to your
    Collection") can also linger after a trade and block subsequent
    navigation on the main window — confirmed live: it silently ate a
    HomeButton click, which in turn made the buddy list panel
    unreachable and broke `ensure_buddy()`. Dismiss both popups after
    every completed trade, not just the collection one."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Dialog" and text == "Trade Completed":
                for sub in element.descendants():
                    try:
                        sub_text = sub.window_text()
                        sub_control = sub.friendly_class_name()
                    except Exception:
                        continue
                    if sub_text.strip() == "OK" and sub_control == "Button":
                        sub.invoke()
                        time.sleep(1.0)
                        return True
        time.sleep(0.5)
    return False


def dismiss_added_to_collection_popup(window, timeout: float = 5.0) -> bool:
    """The "Added to your Collection: N new items" popup that follows a
    completed trade must be dismissed via its `Close` button — the `OK`
    button in this specific dialog is a stale/invisible element with a
    (0,0,0,0) rectangle and clicking it silently does nothing."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Button" and text.strip() == "Close":
                rect = element.rectangle()
                if element.is_visible() and rect.width() > 0 and rect.height() > 0:
                    element.invoke()
                    time.sleep(1.0)
                    return True
        time.sleep(0.5)
    return False


def launch_mtgo(timeout: float = 60.0, interval: float = 3.0):
    """Start the MTGO client via its ClickOnce shortcut and wait for its
    window to appear. Returns the window, or None if it never showed up.
    Does nothing about logging in — see `login()`."""
    subprocess.Popen(
        ["cmd", "/c", "start", "", str(MTGO_APPREF_PATH)],
        shell=False,
    )

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        window = find_mtgo_window()
        if window is not None:
            return window
        time.sleep(interval)
    return None


def is_logged_in(window) -> bool:
    return find_by_automation_id(window, "UsernameTextBox") is None


_TYPE_KEYS_SPECIAL_CHARS = set("+^%~(){}[]")


def _escape_for_type_keys(text: str) -> str:
    """pywinauto's type_keys() treats +^%~(){}[] as modifier/grouping
    syntax, not literal characters — a password containing any of these
    would otherwise be typed wrong (or split across the wrong fields)
    with no visible error. Wrapping each one in its own braces sends it
    literally."""
    return "".join(
        f"{{{ch}}}" if ch in _TYPE_KEYS_SPECIAL_CHARS else ch for ch in text
    )


def login(window, username: str | None = None, password: str | None = None) -> None:
    """Fill the login screen and submit. Credentials default to the
    MTGO_USERNAME/MTGO_PASSWORD environment variables (see .env.example)
    so callers never need to handle the raw password themselves."""
    username = username or os.environ.get("MTGO_USERNAME")
    password = password or os.environ.get("MTGO_PASSWORD")
    if not username or not password:
        raise MtgoAutomationError(
            "MTGO_USERNAME/MTGO_PASSWORD are not set — copy .env.example to "
            ".env and fill them in"
        )

    if is_logged_in(window):
        return

    username_box = find_by_automation_id(window, "UsernameTextBox")
    password_box = find_by_automation_id(window, "PasswordBox")
    login_btn = None
    for element in window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
            aid = element.element_info.automation_id
        except Exception:
            continue
        if text.strip() == "LOG IN" and control == "Button" and aid == "LoginButton":
            login_btn = element
            break

    if username_box is None or password_box is None or login_btn is None:
        raise MtgoAutomationError("login screen fields not found")

    username_box.set_focus()
    username_box.type_keys("^a{DELETE}")
    username_box.type_keys(_escape_for_type_keys(username), with_spaces=True)
    time.sleep(0.3)

    password_box.set_focus()
    password_box.type_keys("^a{DELETE}")
    password_box.type_keys(_escape_for_type_keys(password), with_spaces=True)
    time.sleep(0.3)

    login_btn.click_input()
    time.sleep(1.0)

    # a disabled/greyed-out button (empty or rejected field) eats the
    # click silently — invoke() goes through the button's own click
    # handler instead of a synthetic mouse event, which is more likely
    # to register if the first click_input() didn't visibly do anything
    if find_by_automation_id(window, "UsernameTextBox") is not None:
        login_btn.invoke()


def wait_for_logged_in(window, timeout: float = 90.0, interval: float = 3.0) -> bool:
    """MTGO's post-login load is slow (30s+) even on a good connection —
    poll rather than assume a fixed delay."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_logged_in(window):
            return True
        time.sleep(interval)
    return False


def kill_mtgo() -> None:
    subprocess.run(
        ["taskkill", "/IM", "MTGO.exe", "/F"],
        capture_output=True,
    )
    time.sleep(2.0)


def restart_and_login(username: str | None = None, password: str | None = None):
    """Kill any running MTGO instance, relaunch it, log in, and wait for
    the post-login load to finish. Meant to be called by the bot's own
    process at its own startup (or by whatever will eventually expose a
    "reconnect" action) — never invoke this interactively on the user's
    behalf without them having explicitly triggered it themselves."""
    kill_mtgo()

    window = launch_mtgo()
    if window is None:
        raise MtgoAutomationError("MTGO window did not appear after launch")

    login(window, username=username, password=password)

    if not wait_for_logged_in(window):
        raise MtgoAutomationError("login did not complete within the timeout")

    return window
