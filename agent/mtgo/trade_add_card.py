"""Search for a card in the trade window's "Your Collection" panel and
double-click it to add it to the trade, then dump the resulting tree.

Usage:
  .venv/Scripts/python.exe -m mtgo.trade_add_card "<card name>"
"""

import sys
import time

from pywinauto import Desktop


def _find_trade_window():
    desktop = Desktop(backend="uia")

    for window in desktop.windows():
        try:
            title = window.window_text()
        except Exception:
            continue

        if title.strip().lower().startswith("trade:"):
            return window

    return None


def dump_descendants(window):
    descendants = window.descendants()

    print(f"{len(descendants)} descendant element(s):\n")

    for element in descendants:
        try:
            info = element.element_info
            name = element.window_text()
            control_type = getattr(info, "control_type", "?")
            automation_id = getattr(info, "automation_id", "?")
            class_name = element.class_name()

            print(
                f"  name={name!r} control_type={control_type!r} "
                f"automation_id={automation_id!r} class={class_name!r}"
            )
        except Exception as error:
            print(f"  <error reading element: {error}>")


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print('Usage: python -m mtgo.trade_add_card "<card name>"')
        return 1

    card_name = sys.argv[1]

    window = _find_trade_window()

    if window is None:
        print("Trade window not found.")
        return 1

    window.set_focus()

    descendants = window.descendants()
    search_box = None

    for element in descendants:
        info = element.element_info

        if getattr(info, "automation_id", None) == "searchTextBox":
            search_box = element
            break

    if search_box is None:
        print("Search box not found.")
        return 1

    print(f"Typing {card_name!r} into search box...")
    search_box.click_input()
    search_box.type_keys(card_name, with_spaces=True)

    time.sleep(0.5)

    search_button = None

    for element in window.descendants():
        info = element.element_info

        if getattr(info, "automation_id", None) == "SearchButton":
            search_button = element
            break

    if search_button is not None:
        search_button.click_input()
    else:
        search_box.type_keys("{ENTER}")

    time.sleep(1.5)

    # The `Collection-CardStack-<name>` Image element is unreliable: MTGO's
    # virtualized card grid can leave stale "ghost" peers for a previously
    # searched card at the same screen coordinates as the currently displayed
    # one, so double-clicking it can add the wrong card. The
    # `<name>_<numericId>_CardQuantityControl` element embeds a card-specific
    # numeric id and does not exhibit this staleness — target that instead.
    prefix = f"{card_name}_"
    suffix = "_CardQuantityControl"
    card_element = None

    for element in window.descendants():
        info = element.element_info
        automation_id = getattr(info, "automation_id", "") or ""

        if automation_id.startswith(prefix) and automation_id.endswith(suffix):
            card_element = element
            break

    if card_element is None:
        print(
            f"Card {card_name!r} not found after search — dumping tree "
            f"for inspection instead.\n"
        )
        dump_descendants(window)
        return 1

    print(f"Found card element, double-clicking: {card_element.element_info.automation_id}")
    card_element.double_click_input()

    time.sleep(1.0)

    print("\n=== Descendants after adding card ===\n")
    dump_descendants(window)

    return 0


if __name__ == "__main__":
    sys.exit(main())
