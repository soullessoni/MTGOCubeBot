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


def find_mtgo_window(account: str | None = None):
    """Find the MTGO main window. With two instances open (e.g. a bot
    account and a test-player account logged in side by side), both
    windows share the exact same title — pass `account` to disambiguate
    by the logged-in username, which shows up as a plain `Static` text
    element matching the account name exactly. With `account=None`,
    returns the first MTGO window found, same as before."""
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
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
            except Exception:
                continue
            if control == "Static" and text.strip() == account:
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


def _write_dek_file(binder_name: str, card_names: list[str]) -> Path:
    LISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = LISTS_DIR / f"{binder_name}.dek"

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        "  <NetDeckID>0</NetDeckID>",
        "  <PreconstructedDeckID>0</PreconstructedDeckID>",
    ]
    for name in card_names:
        lines.append(
            f'  <Cards CatID="0" Quantity="1" Sideboard="false" '
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


def create_binder_from_cards(window, binder_name: str, card_names: list[str]) -> str:
    """Create (or replace) a binder populated with exactly `card_names`,
    by importing a generated .dek file. Vastly faster and more reliable
    than searching and double-clicking each card: MTGO resolves cards by
    their `Name` attribute even with `CatID="0"`, so no card-ID database
    is needed. Returns the final "<name>: <count>" label, or raises
    MtgoAutomationError if any step fails.

    The binder-name field auto-fills correctly from the .dek filename
    (which is `binder_name` itself) — do NOT try to overwrite that field,
    doing so was found to leave the dialog in a broken state where the
    OK button silently does nothing.
    """
    if binder_exists(window, binder_name):
        delete_binder(window, binder_name)
        time.sleep(1.5)

    dek_path = _write_dek_file(binder_name, card_names)

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
        if not _dialog_present(window, "Add or Import Binder(s)"):
            break
        ok_btn = None
        for element in window.descendants():
            try:
                text = element.window_text()
                control = element.friendly_class_name()
                aid = element.element_info.automation_id
            except Exception:
                continue
            if text.strip() == "OK" and control == "Button" and aid == "OkButton":
                ok_btn = element
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


def ensure_buddy(window, username: str) -> None:
    """Add `username` to the buddy list if they aren't on it already.
    Validated round-trip (remove/re-add) on 2026-07-25: `AddBuddyButton`
    opens an "Add Buddy" dialog with an `Entry` text field and an
    `Entrybutton` ("Add Buddy") to submit it."""
    if is_buddy(window, username):
        return

    add_btn = find_by_automation_id(window, "AddBuddyButton")
    if add_btn is None:
        raise MtgoAutomationError("AddBuddyButton not found")
    add_btn.click_input()
    time.sleep(1.5)

    entry = None
    entry_btn = None
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

    if entry is None or entry_btn is None:
        raise MtgoAutomationError("Add Buddy dialog fields not found")

    entry.set_focus()
    entry.type_keys(username, with_spaces=True)
    time.sleep(0.5)
    entry_btn.click_input()
    time.sleep(1.5)

    if not is_buddy(window, username):
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
    ensure_buddy(window, buddy_name)

    trade_tab = find_by_automation_id(window, "TradeButton")
    if trade_tab is not None:
        trade_tab.click_input()
        time.sleep(1.5)

    buddy = find_by_automation_id(window, f"Buddies-{buddy_name}")
    if buddy is None:
        raise MtgoAutomationError(f"buddy element 'Buddies-{buddy_name}' not found")

    buddy.right_click_input()
    time.sleep(1.5)

    trade_item = None
    for element in window.descendants():
        try:
            text = element.window_text()
        except Exception:
            continue
        if text.strip() == "Trade":
            trade_item = element
    if trade_item is None:
        raise MtgoAutomationError("'Trade' context menu item not found")
    trade_item.click_input()
    time.sleep(1.5)

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


def add_card_from_partner_binder(trade_window, card_name: str, timeout: float = 8.0) -> bool:
    """Search the counterparty's exposed binder inside a trade window and
    add `card_name` to "You Will Receive". Targets the
    `<name>_<numericId>_CardQuantityControl` element rather than the
    `Collection-CardStack-<name>` image — the latter can carry a stale
    "ghost" automation peer for a previously searched card at the same
    screen position, silently adding the wrong card."""
    search_box = find_by_automation_id(trade_window, "searchTextBox")
    if search_box is None:
        raise MtgoAutomationError("searchTextBox not found in trade window")

    search_box.set_focus()
    search_box.type_keys("^a{DELETE}")
    search_box.type_keys(card_name, with_spaces=True)
    search_box.type_keys("{ENTER}")

    prefix = f"{card_name}_"
    suffix = "_CardQuantityControl"
    deadline = time.monotonic() + timeout
    target = None
    while time.monotonic() < deadline:
        for element in trade_window.descendants():
            try:
                aid = element.element_info.automation_id or ""
            except Exception:
                continue
            if aid.startswith(prefix) and aid.endswith(suffix):
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


def submit_trade(trade_window) -> None:
    for element in trade_window.descendants():
        try:
            text = element.window_text()
            control = element.friendly_class_name()
        except Exception:
            continue
        if text.strip() == "Submit" and control == "Button":
            element.click_input()
            time.sleep(1.0)
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
            element.click_input()
            time.sleep(1.5)
            return
    raise MtgoAutomationError("Confirm Trade button not found in trade window")


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
                    element.click_input()
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
