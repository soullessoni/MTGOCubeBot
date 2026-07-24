"""Same as click_and_inspect, but double-clicks the target element."""

import sys
import time

from mtgo.click_and_inspect import _find_mtgo_window, dump_descendants


def main():
    sys.stdout.reconfigure(errors="replace")

    if len(sys.argv) != 2:
        print(
            "Usage: python -m mtgo.double_click_and_inspect "
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
        f"Double-clicking element: {target.window_text()!r} "
        f"({target_identifier})"
    )
    target.double_click_input()

    time.sleep(1.5)

    print("\n=== Descendants after double-click ===\n")
    dump_descendants(window)

    return 0


if __name__ == "__main__":
    sys.exit(main())
