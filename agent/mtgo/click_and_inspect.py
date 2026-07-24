"""Click a control by automation_id on the MTGO window, wait briefly, then
dump the resulting descendants tree — for iterative UI reconnaissance.

Usage:
  .venv/Scripts/python.exe -m mtgo.click_and_inspect <automation_id>
"""

import sys
import time

from pywinauto import Desktop

MTGO_EXACT_TITLES = {
    "magic: the gathering online",
}


def _find_mtgo_window():
    desktop = Desktop(backend="uia")

    for window in desktop.windows():
        try:
            title = window.window_text()
        except Exception:
            continue

        if title.strip().lower() in MTGO_EXACT_TITLES:
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
        print(
            "Usage: python -m mtgo.click_and_inspect "
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

    print(f"Clicking element: {target.window_text()!r} ({target_identifier})")
    target.click_input()

    time.sleep(1.5)

    print("\n=== Descendants after click ===\n")
    dump_descendants(window)

    return 0


if __name__ == "__main__":
    sys.exit(main())
