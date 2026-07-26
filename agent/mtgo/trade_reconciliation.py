"""Reconcile a trade window's "Will Receive" panel against exactly what
was actually handed out to the player — the missing piece for making
Search Tools' "Import Deck" bulk auto-add both fast AND correct.

**Why compare against handed-out records, not MTGO's own state**:
Import Deck auto-adds matching cards by NAME the moment it's applied
(confirmed live 2026-07-26), which is fast (~70s for 40 cards vs.
300s+ searching one at a time), but its notion of "how many to add" is
MTGO's own opaque "cards from this list not in your collection" logic
— confirmed live to sometimes grab 0, 1, or 2 copies of the same name
depending on state we don't control (e.g. it grabbed 2 copies of 5
different cards when the counterparty happened to independently own
an extra one). The only reliable source of "how many should come
back" is our own loan records, never MTGO's internal comparison.

This module's job is purely to decide what to fix; it never touches
the live UI itself (see `client.py` for that). The corrective actions
are also decklist-driven (a follow-up Import Deck pass for anything
still missing) rather than per-card manual search, per explicit
project direction 2026-07-26.
"""

from __future__ import annotations

from collections import Counter


def plan_reconciliation(
        card_names: list[str],
        catid_map: dict[str, str],
        actual: dict[str, dict[str, int]],
) -> dict[str, list]:
    """`card_names` is one entry per physical card actually handed out
    to this player (a name repeated N times means N copies were lent —
    this is what our own loan records say should come back). `catid_map`
    is `{name: catid}` for the correct printing. `actual` is
    `{name: {catid: quantity}}` — what's really staged right now (from
    `client.read_receiving_panel_quantities`).

    Returns:
      - `to_remove`: `[(name, catid, quantity)]` — staged copies that
        must go: any wrong-edition copies (all of them), plus any
        surplus of the correct edition beyond what was actually lent.
      - `to_add`: `[name, ...]` — one entry per copy still needed,
        repeated per copy (missing entirely, or removed above for
        being the wrong edition and needing a correct replacement).
      - `already_correct`: `[name, ...]` — one entry per copy already
        staged under the right printing, in the right amount.
    """
    expected_counts = Counter(card_names)

    to_remove: list[tuple[str, str, int]] = []
    to_add: list[str] = []
    already_correct: list[str] = []

    for name, expected_qty in expected_counts.items():
        expected_catid = catid_map.get(name)
        staged = actual.get(name, {})

        for catid, qty in staged.items():
            if catid != expected_catid and qty > 0:
                to_remove.append((name, catid, qty))

        correct_qty = staged.get(expected_catid, 0) if expected_catid is not None else 0

        if correct_qty > expected_qty:
            to_remove.append((name, expected_catid, correct_qty - expected_qty))
            already_correct.extend([name] * expected_qty)
        elif correct_qty < expected_qty:
            already_correct.extend([name] * correct_qty)
            to_add.extend([name] * (expected_qty - correct_qty))
        else:
            already_correct.extend([name] * expected_qty)

    return {
        "to_remove": to_remove,
        "to_add": to_add,
        "already_correct": already_correct,
    }
