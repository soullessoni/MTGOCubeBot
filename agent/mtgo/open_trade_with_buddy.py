"""Right-click a buddy's name and select "Trade" from the context menu,
then dump the resulting UI tree — the whole sequence has to happen in one
process run since the context menu is transient.

Usage:
  .venv/Scripts/python.exe -m mtgo.open_trade_with_buddy <automation_id_or_name>
"""

import sys
import time

from mtgo.click_and_inspect import _find_mtgo_window, dump_descendants


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print(
            "Usage: python -m mtgo.open_trade_with_buddy "
            "<automation_id_or_exact_name>"
        )
        return 1

    target_identifier = sys.argv[1]

    window = _find_mtgo_window()

    if window is None:
        print("MTGO window not found.")
        return 1

    window.set_focus()

    descendants = window.descendants()
    target = None

    for element in descendants:
        info = element.element_info

        if getattr(info, "automation_id", None) == target_identifier:
            target = element
            break

    if target is None:
        for element in descendants:
            if element.window_text() == target_identifier:
                target = element
                break

    if target is None:
        print(f"No element matching {target_identifier!r} found.")
        return 1

    print(f"Right-clicking: {target.window_text()!r}")
    target.right_click_input()

    time.sleep(1.0)

    trade_item = None

    for element in window.descendants():
        info = element.element_info

        if (
            getattr(info, "control_type", None) == "MenuItem"
            and element.window_text() == "Trade"
        ):
            trade_item = element
            break

    if trade_item is None:
        print("Could not find 'Trade' menu item — menu may have closed.")
        return 1

    print("Clicking 'Trade' menu item...")
    trade_item.click_input()

    time.sleep(1.5)

    print("\n=== Descendants after opening trade ===\n")
    dump_descendants(window)

    return 0


if __name__ == "__main__":
    sys.exit(main())
