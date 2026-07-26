"""Post-trade stock verification: compare the bot's real MTGO
collection (exported as a "Full Trade List" .dek) against what it
*should* have — the account's full baseline inventory minus whatever is
currently out on loan (DISTRIBUTED or CONFIRMED, i.e. handed out and
not yet returned).

Born from a real discrepancy found live 2026-07-26: after a round of
test trades, TheLegionCube's account ended up with 2 extra copies of
cards it had already gotten back (duplicates accumulated across several
retry attempts) — something nobody noticed until manually eyeballing
the collection. This module makes that check automatic and repeatable.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

HANDED_OUT_STATUSES = ("DISTRIBUTED", "CONFIRMED")


def parse_dek_quantities(dek_path: Path) -> dict[str, int]:
    """Parse a .dek file's `<Cards Name="..." Quantity="..." />` entries
    into a `{name: total_quantity}` mapping, summing across entries for
    the same name (a name can appear more than once if the account owns
    it under more than one CatID/printing)."""
    root = ElementTree.parse(dek_path).getroot()
    totals: dict[str, int] = {}
    for card in root.findall("Cards"):
        name = card.get("Name")
        quantity = card.get("Quantity")
        if not name or quantity is None:
            continue
        totals[name] = totals.get(name, 0) + int(quantity)
    return totals


def compute_expected_quantities(
        inventory: list[dict],
        active_loan_card_names: list[str],
) -> dict[str, int]:
    """`inventory` is the baseline stock: a list of
    `{"card_name": str, "quantity": int}`. `active_loan_card_names` is
    the list of card names currently DISTRIBUTED or CONFIRMED (handed
    out, not yet returned) — one entry per assignment, so a name
    appearing twice there means 2 copies are out. Returns
    `{name: expected_quantity_still_with_the_bot}`."""
    handed_out_counts: dict[str, int] = {}
    for name in active_loan_card_names:
        handed_out_counts[name] = handed_out_counts.get(name, 0) + 1

    expected: dict[str, int] = {}
    for item in inventory:
        name = item["card_name"]
        baseline = item["quantity"]
        expected[name] = baseline - handed_out_counts.get(name, 0)
    return expected


def diff_stock(
        expected: dict[str, int],
        actual: dict[str, int],
) -> dict[str, dict[str, int]]:
    """Compare expected vs. actual quantities. Returns
    `{"missing": {name: shortfall}, "extra": {name: surplus}}` for every
    name where they disagree — cards with matching counts (including
    both-zero) are omitted."""
    missing: dict[str, int] = {}
    extra: dict[str, int] = {}

    for name in set(expected) | set(actual):
        expected_qty = expected.get(name, 0)
        actual_qty = actual.get(name, 0)
        if actual_qty < expected_qty:
            missing[name] = expected_qty - actual_qty
        elif actual_qty > expected_qty:
            extra[name] = actual_qty - expected_qty

    return {"missing": missing, "extra": extra}
