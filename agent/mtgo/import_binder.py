"""Create (or replace) a binder by importing a generated .dek file, instead
of searching and double-clicking each card individually. Vastly faster and
more reliable than mtgo.stress_fill_binder: MTGO resolves cards by Name
even when CatID is 0, so no card-ID database is needed.

Usage:
  .venv/Scripts/python.exe -m mtgo.import_binder <binder_name> <card1> <card2> ...
"""

import sys
import time
from pathlib import Path
from xml.sax.saxutils import escape

from pywinauto import Desktop

LISTS_DIR = Path(__file__).parent / "lists"


def _find_mtgo():
    for window in Desktop(backend="uia").windows():
        try:
            if window.window_text().strip().lower() == "magic: the gathering online":
                return window
        except Exception:
            continue
    return None


def _find_by_automation_id(window, automation_id):
    for element in window.descendants():
        try:
            if element.element_info.automation_id == automation_id:
                return element
        except Exception:
            continue
    return None


def _write_dek_file(binder_name, card_names):
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


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) < 3:
        print("Usage: python -m mtgo.import_binder <binder_name> <card1> <card2> ...")
        return 1

    binder_name = sys.argv[1]
    card_names = sys.argv[2:]

    dek_path = _write_dek_file(binder_name, card_names)
    print(f"Wrote {dek_path} ({len(card_names)} cards)")

    window = _find_mtgo()
    if window is None:
        print("MTGO window not found.")
        return 1

    window.set_focus()
    time.sleep(0.3)

    collection_btn = _find_by_automation_id(window, "CollectionButton")
    if collection_btn is not None:
        collection_btn.click_input()
        time.sleep(1.2)

    add_btn = _find_by_automation_id(window, "AddBinderButton-Small")
    if add_btn is None:
        print("AddBinderButton-Small not found.")
        return 1
    add_btn.click_input()
    time.sleep(1.2)

    import_btn = _find_by_automation_id(window, "AddDeckDialog-ImportButton")
    if import_btn is None:
        print("Import button not found.")
        return 1
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
        print("Select Deck(s) dialog not found.")
        return 1

    filename_edit = _find_visible_edit(file_dialog)
    if filename_edit is None:
        print("Filename field not found in Select Deck(s) dialog.")
        return 1
    filename_edit.set_focus()
    filename_edit.set_edit_text(str(dek_path))
    time.sleep(0.3)
    filename_edit.type_keys("{ENTER}")
    time.sleep(1.2)

    ok_btn = None
    for element in window.descendants():
        try:
            text = element.window_text()
            cls = element.friendly_class_name()
            aid = element.element_info.automation_id
        except Exception:
            continue
        if text.strip() == "OK" and cls == "Button" and aid == "OkButton":
            ok_btn = element
            break
    if ok_btn is None:
        print("OK button not found on Add/Import Binder dialog.")
        return 1
    ok_btn.click_input()
    time.sleep(1.5)

    label = None
    for _ in range(10):
        for element in window.descendants():
            try:
                if element.window_text() != "WotC.MtGO.Client.Model.Core.Collection.Binder":
                    continue
            except Exception:
                continue
            element.double_click_input()
            time.sleep(0.6)
            found = _find_by_automation_id(window, "DeckTotalCardsText")
            if found is not None:
                try:
                    text = found.window_text()
                except Exception:
                    text = None
                if text and text.startswith(f"{binder_name}:"):
                    label = text
            break
        if label:
            break

    if label is None:
        print("Could not confirm binder contents after import.")
        return 1

    print(f"Binder ready: {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
