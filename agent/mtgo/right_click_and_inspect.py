"""Same as click_and_inspect, but right-clicks the target element (to open
a context menu), then dumps the whole desktop's top-level windows plus the
MTGO window's descendants — context menus are often separate top-level
popup windows, not nested inside the main window's tree.
"""

import sys
import time

from pywinauto import Desktop

from mtgo.click_and_inspect import _find_mtgo_window, dump_descendants


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print(
            "Usage: python -m mtgo.right_click_and_inspect "
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

    print(
        f"Right-clicking element: {target.window_text()!r} "
        f"({target_identifier})"
    )
    target.right_click_input()

    time.sleep(1.0)

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    print(f"\n=== Top-level windows after right-click ({len(windows)}) ===\n")

    popup = None

    for w in windows:
        try:
            title = w.window_text()
        except Exception:
            title = "<error>"

        print(f"- {title!r} (class={w.class_name()!r})")

        if w.class_name() in ("Popup", "#32768", "ContextMenu") or (
            not title and w.class_name() not in ("Progman",)
        ):
            popup = w

    if popup is not None:
        print(f"\n=== Descendants of likely popup: {popup.class_name()!r} ===\n")
        dump_descendants(popup)
    else:
        print("\n=== No obvious popup window found; dumping main window ===\n")
        dump_descendants(window)

    return 0


if __name__ == "__main__":
    sys.exit(main())
