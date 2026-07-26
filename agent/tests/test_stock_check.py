from mtgo.stock_check import (
    compute_expected_quantities,
    compute_return_reconciliation,
    diff_stock,
    parse_dek_quantities,
)


def test_parse_dek_quantities_reads_name_to_quantity(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="28245" Quantity="1" Sideboard="false" Name="Mulldrifter" Annotation="0" />\n'
        '  <Cards CatID="87919" Quantity="50" Sideboard="false" Name="Snow-Covered Forest" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    assert parse_dek_quantities(dek) == {"Mulldrifter": 1, "Snow-Covered Forest": 50}


def test_parse_dek_quantities_sums_multiple_editions_of_same_name(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="117962" Quantity="1" Sideboard="false" Name="Tishana\'s Tidebinder" Annotation="0" />\n'
        '  <Cards CatID="117678" Quantity="1" Sideboard="false" Name="Tishana\'s Tidebinder" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    assert parse_dek_quantities(dek) == {"Tishana's Tidebinder": 2}


def test_compute_expected_quantities_subtracts_handed_out_cards():
    inventory = [
        {"card_name": "Mulldrifter", "quantity": 1},
        {"card_name": "Snow-Covered Forest", "quantity": 50},
    ]
    active_loans = ["Mulldrifter"]

    expected = compute_expected_quantities(inventory, active_loans)

    assert expected == {"Mulldrifter": 0, "Snow-Covered Forest": 50}


def test_compute_expected_quantities_handles_multiple_copies_out():
    inventory = [{"card_name": "Ancient Ziggurat", "quantity": 8}]
    active_loans = ["Ancient Ziggurat", "Ancient Ziggurat", "Ancient Ziggurat"]

    expected = compute_expected_quantities(inventory, active_loans)

    assert expected == {"Ancient Ziggurat": 5}


def test_diff_stock_reports_missing_cards():
    expected = {"Mulldrifter": 1}
    actual = {"Mulldrifter": 0}

    assert diff_stock(expected, actual) == {"missing": {"Mulldrifter": 1}, "extra": {}}


def test_diff_stock_reports_extra_cards():
    expected = {"Ice-Fang Coatl": 1, "Spellskite": 1}
    actual = {"Ice-Fang Coatl": 2, "Spellskite": 2}

    assert diff_stock(expected, actual) == {
        "missing": {},
        "extra": {"Ice-Fang Coatl": 1, "Spellskite": 1},
    }


def test_diff_stock_ignores_matching_cards():
    expected = {"Mulldrifter": 1, "Snow-Covered Forest": 50}
    actual = {"Mulldrifter": 1, "Snow-Covered Forest": 50}

    assert diff_stock(expected, actual) == {"missing": {}, "extra": {}}


def test_diff_stock_handles_card_present_in_actual_but_not_expected():
    expected = {}
    actual = {"Bonus Card": 1}

    assert diff_stock(expected, actual) == {"missing": {}, "extra": {"Bonus Card": 1}}


def test_compute_return_reconciliation_confirms_exact_match():
    before = {"Mulldrifter": 0}
    after = {"Mulldrifter": 1}

    result = compute_return_reconciliation(before, after, ["Mulldrifter"])

    assert result == {"to_give_back": {}, "still_owed": {}}


def test_compute_return_reconciliation_flags_excess_received():
    """The real 2026-07-26 incident: only 1 was owed, but 2 came back
    because the counterparty independently owned an extra copy."""
    before = {"Mulldrifter": 0}
    after = {"Mulldrifter": 2}

    result = compute_return_reconciliation(before, after, ["Mulldrifter"])

    assert result == {"to_give_back": {"Mulldrifter": 1}, "still_owed": {}}


def test_compute_return_reconciliation_flags_shortfall():
    before = {"Scuttling Sentinel": 0}
    after = {"Scuttling Sentinel": 0}

    result = compute_return_reconciliation(before, after, ["Scuttling Sentinel"])

    assert result == {"to_give_back": {}, "still_owed": {"Scuttling Sentinel": 1}}


def test_compute_return_reconciliation_handles_multiple_copies_owed():
    before = {"Snow-Covered Island": 0}
    after = {"Snow-Covered Island": 1}

    result = compute_return_reconciliation(
        before, after, ["Snow-Covered Island", "Snow-Covered Island"]
    )

    assert result == {"to_give_back": {}, "still_owed": {"Snow-Covered Island": 1}}


def test_compute_return_reconciliation_ignores_unrelated_baseline_changes():
    # A card neither owed nor mentioned that happens to differ between
    # exports (e.g. from an unrelated concurrent trade) shouldn't be
    # flagged as a reconciliation issue for THIS return.
    before = {"Mulldrifter": 0, "Unrelated Card": 3}
    after = {"Mulldrifter": 1, "Unrelated Card": 3}

    result = compute_return_reconciliation(before, after, ["Mulldrifter"])

    assert result == {"to_give_back": {}, "still_owed": {}}
