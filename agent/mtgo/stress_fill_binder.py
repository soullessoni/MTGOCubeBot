"""Populate a binder with many cards quickly, timing each add, to gauge
whether the give-direction automation (binder population) is fast enough
for several sessions to be prepared within a few minutes.

Usage:
  .venv/Scripts/python.exe -m mtgo.stress_fill_binder <binder_name> <card1> <card2> ...
"""

import sys
import time

from pywinauto import Desktop


def _find_mtgo():
    for window in Desktop(backend="uia").windows():
        try:
            if window.window_text().strip().lower() == "magic: the gathering online":
                return window
        except Exception:
            continue
    return None


def _poll_for_card_control(window, card_name, timeout=4.0, interval=0.25):
    """MTGO's search results take a variable amount of time to render —
    a fixed sleep is unreliable (silently misses the target element on a
    slow render). Poll until the element appears or the timeout elapses."""
    prefix = f"{card_name}_"
    suffix = "_CardQuantityControl"
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for element in window.descendants():
            try:
                automation_id = element.element_info.automation_id or ""
            except Exception:
                continue
            if automation_id.startswith(prefix) and automation_id.endswith(suffix):
                return element
        time.sleep(interval)

    return None


def _find_by_automation_id(window, automation_id):
    for element in window.descendants():
        try:
            if element.element_info.automation_id == automation_id:
                return element
        except Exception:
            continue
    return None


def _read_deck_total_label(window):
    for element in window.descendants():
        try:
            if element.element_info.automation_id == "DeckTotalCardsText":
                return element.window_text()
        except Exception:
            continue
    return None


def _open_binder(window, binder_name):
    """Binder tree rows all share the same window_text() (the WPF type
    name) and have no automation_id, so there's no way to target one by
    name directly. Double-click each row in turn (single click only
    highlights it — it doesn't become the active add-target) and check
    the DeckTotalCardsText label ("<name>: <count>") that appears once a
    binder is actually opened."""
    for element in window.descendants():
        try:
            if element.window_text() != "WotC.MtGO.Client.Model.Core.Collection.Binder":
                continue
        except Exception:
            continue

        element.double_click_input()
        time.sleep(1.0)

        label = _read_deck_total_label(window)
        if label is not None and label.startswith(f"{binder_name}:"):
            return True

    return False


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) < 3:
        print("Usage: python -m mtgo.stress_fill_binder <binder_name> <card1> <card2> ...")
        return 1

    binder_name = sys.argv[1]
    card_names = sys.argv[2:]

    window = _find_mtgo()
    if window is None:
        print("MTGO window not found.")
        return 1

    window.set_focus()
    time.sleep(0.3)

    collection_btn = _find_by_automation_id(window, "CollectionButton")
    if collection_btn is not None:
        collection_btn.click_input()
        time.sleep(1.5)

    if not _open_binder(window, binder_name):
        print(f"Binder {binder_name!r} not found — create it first.")
        return 1

    print(f"Opened binder {binder_name!r}")

    search_box = _find_by_automation_id(window, "searchTextBox")
    if search_box is None:
        print("Search box not found.")
        return 1

    def current_count():
        label = _read_deck_total_label(window)
        if label is None or ":" not in label:
            return None
        try:
            return int(label.rsplit(":", 1)[1].strip())
        except ValueError:
            return None

    start = time.monotonic()
    added = 0
    failed = []
    prev_count = current_count()

    for card_name in card_names:
        card_start = time.monotonic()
        succeeded = False

        for attempt in range(2):
            search_box.set_focus()
            search_box.type_keys("^a{DELETE}")
            search_box.type_keys(card_name, with_spaces=True)
            search_box.type_keys("{ENTER}")

            target = _poll_for_card_control(window, card_name)

            if target is None:
                print(f"  [attempt {attempt + 1}] {card_name!r}: element not found")
                continue

            target.double_click_input()

            new_count = None
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                new_count = current_count()
                if new_count is not None and prev_count is not None and new_count > prev_count:
                    break
                time.sleep(0.25)

            if new_count is not None and prev_count is not None and new_count > prev_count:
                succeeded = True
                prev_count = new_count
                break

            print(f"  [attempt {attempt + 1}] {card_name!r}: count did not increase "
                  f"({prev_count} -> {new_count}), retrying")

        elapsed = time.monotonic() - card_start

        if succeeded:
            added += 1
            print(f"  [{added}/{len(card_names)}] added {card_name!r} in {elapsed:.2f}s "
                  f"(binder now at {prev_count})")
        else:
            failed.append(card_name)
            print(f"  [FAILED] {card_name!r} after {elapsed:.2f}s")

    total_elapsed = time.monotonic() - start

    print()
    print(f"Added {added}/{len(card_names)} cards in {total_elapsed:.2f}s "
          f"({total_elapsed / max(len(card_names), 1):.2f}s/card avg)")
    print(f"Final binder count: {prev_count}")
    if failed:
        print(f"Failed cards: {failed}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
