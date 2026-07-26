from mtgo.stock_check import (
    compute_expected_quantities,
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
