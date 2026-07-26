"""Reconcile a trade window's "Will Receive" panel against an exact
expected CatID per card name — the missing piece for making the
Search Tools "Import Deck" bulk auto-add both fast AND correct.

Import Deck auto-adds matching cards by NAME the moment it's applied
(confirmed live 2026-07-26), which is fast (~70s for 40 cards vs.
300s+ searching one at a time) but can stage the WRONG printing when
the counterparty independently owns a different edition of the same
name (e.g. it grabbed a "Tishana's Tidebinder" the player already had,
not the one actually being retrieved). This module's job is purely to
decide what to fix — removing wrong-edition items and adding the
correct ones — never to touch the live UI itself (see
`client.reconcile_receiving_panel` for that).
"""

from __future__ import annotations


def plan_reconciliation(
        expected: dict[str, str],
        actual: dict[str, str],
) -> dict[str, list]:
    """`expected`/`actual` are `{card_name: catid}` — expected is what
    should end up staged (one specific printing per name), actual is
    what's really there right now (from
    `client.read_receiving_panel_catids`).

    Returns:
      - `to_remove`: `[(name, wrong_catid)]` — staged under the wrong
        printing, must be removed before re-adding the right one.
      - `to_add`: `[name]` — missing entirely, or staged wrong (so it
        needs the removal above plus a fresh add of the right printing).
      - `already_correct`: `[name]` — staged with the exact expected
        printing, nothing to do.

    Names in `actual` but not in `expected` are left alone — this only
    manages what's actually being sought, not stray extras.
    """
    to_remove: list[tuple[str, str]] = []
    to_add: list[str] = []
    already_correct: list[str] = []

    for name, expected_catid in expected.items():
        actual_catid = actual.get(name)
        if actual_catid is None:
            to_add.append(name)
        elif actual_catid != expected_catid:
            to_remove.append((name, actual_catid))
            to_add.append(name)
        else:
            already_correct.append(name)

    return {
        "to_remove": to_remove,
        "to_add": to_add,
        "already_correct": already_correct,
    }
