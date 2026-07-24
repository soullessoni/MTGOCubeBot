"""One-off reconnaissance script: lists top-level windows currently open,
and if the MTGO client window is found, dumps a flat list of its UI
descendants (name / control type / automation id) via pywinauto's UIA
backend, to figure out whether the client exposes accessible elements we
can drive directly instead of falling back to OCR/pixel matching.

Usage: .venv/Scripts/python.exe -m mtgo.inspect_windows
"""

import sys

from pywinauto import Desktop

MTGO_EXACT_TITLES = {
    "magic: the gathering online",
}


def _is_mtgo_window(title: str) -> bool:
    return title.strip().lower() in MTGO_EXACT_TITLES


def main():
    # The Windows console's default codepage can't encode every character
    # a window title or UI element might contain (emoji, CJK, etc.) —
    # replace instead of crashing.
    sys.stdout.reconfigure(errors="replace")

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    print(f"Found {len(windows)} top-level window(s):\n")

    target = None

    for window in windows:
        try:
            title = window.window_text()
        except Exception as error:
            title = f"<error reading title: {error}>"

        print(f"- {title!r} (class={window.class_name()!r})")

        if _is_mtgo_window(title):
            target = window

    if target is None:
        print(
            "\nNo window titled exactly 'Magic: The Gathering Online' was "
            "found. Make sure the client is open and try again."
        )
        return

    print(f"\n=== Descendants of: {target.window_text()!r} ===\n")

    try:
        descendants = target.descendants()
    except Exception as error:
        print(f"Failed to enumerate descendants: {error}")
        return

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


if __name__ == "__main__":
    sys.exit(main())
