from app.services.inventory.dek_parser import parse_dek_quantities


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

    result = parse_dek_quantities(dek)

    assert result == {"Mulldrifter": 1, "Snow-Covered Forest": 50}


def test_parse_dek_quantities_sums_duplicate_names_across_printings(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="1" Quantity="1" Sideboard="false" Name="Mulldrifter" Annotation="0" />\n'
        '  <Cards CatID="2" Quantity="1" Sideboard="false" Name="Mulldrifter" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    result = parse_dek_quantities(dek)

    assert result == {"Mulldrifter": 2}


def test_parse_dek_quantities_skips_entries_missing_name_or_quantity(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="1" Sideboard="false" Name="Missing Quantity" Annotation="0" />\n'
        '  <Cards CatID="2" Quantity="1" Sideboard="false" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    result = parse_dek_quantities(dek)

    assert result == {}
