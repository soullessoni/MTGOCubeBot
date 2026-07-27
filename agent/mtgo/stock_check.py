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

from collections import Counter
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


def compute_return_reconciliation(
        before: dict[str, int],
        after: dict[str, int],
        expected_names: list[str],
) -> dict[str, dict[str, int]]:
    """Figure out what a return trade actually accomplished by diffing
    two real "Full Trade List" exports (`before`/`after`, from
    `parse_dek_quantities` on exports bracketing the trade) — not by
    reading the live trade window, which was found unreliable for
    quantity (Search Tools' Import Deck auto-add doesn't respect "only
    1 copy needed"; it can grab however many the counterparty happens
    to own). This sidesteps that entirely: whatever the real delta in
    the account's own collection is, is the ground truth.

    `expected_names` is one entry per card that should have come back
    (matching `create_binder_from_cards`/loan-record conventions — a
    name repeated N times means N copies were owed).

    Returns `{"to_give_back": {name: excess}, "still_owed": {name: shortfall}}`
    — `to_give_back` is for a follow-up GIVE trade (received too many),
    `still_owed` is for a follow-up RETURN attempt (received too few).
    Both are meant to be resolved with another decklist-driven trade,
    never by editing the just-completed one.
    """
    expected = Counter(expected_names)
    names = set(before) | set(after) | set(expected)

    to_give_back: dict[str, int] = {}
    still_owed: dict[str, int] = {}

    for name in names:
        received = after.get(name, 0) - before.get(name, 0)
        needed = expected.get(name, 0)
        if received > needed:
            to_give_back[name] = received - needed
        elif received < needed:
            still_owed[name] = needed - received

    return {"to_give_back": to_give_back, "still_owed": still_owed}


def compute_give_confirmation(
        before: dict[str, int],
        after: dict[str, int],
        offered_names: list[str],
) -> dict[str, dict[str, int]]:
    """The give-side mirror of `compute_return_reconciliation`: figure
    out exactly which cards actually left the bot's account during a
    give trade by diffing two real "Full Trade List" exports, rather
    than trusting the live trade window — a player is never forced to
    take everything offered, and Search Tools' own auto-add behavior
    isn't something either side of a give trade drives (see
    `prepare_session_binders.py`).

    `offered_names` is one entry per card that was exposed to the
    player (matching `create_binder_from_cards`'s convention — a name
    repeated N times means N copies were offered).

    Returns `{"given": {name: quantity}, "not_taken": {name: quantity}}`
    — `given` is the confirmed ground truth to record as each
    assignment's `given_quantity`; `not_taken` is what the player left
    on the table. A stock decrease for a name that wasn't even offered
    in this give (an unrelated concurrent change) is never credited as
    "given" for this trade.
    """
    offered = Counter(offered_names)
    names = set(before) | set(after) | set(offered)

    given: dict[str, int] = {}
    not_taken: dict[str, int] = {}

    for name in names:
        left_account = before.get(name, 0) - after.get(name, 0)
        was_offered = offered.get(name, 0)
        confirmed = max(0, min(left_account, was_offered))

        if confirmed:
            given[name] = confirmed
        if was_offered > confirmed:
            not_taken[name] = was_offered - confirmed

    return {"given": given, "not_taken": not_taken}
