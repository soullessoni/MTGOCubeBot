from mtgo.catid_map import load_default_catid_map, parse_catid_map


def test_parse_catid_map_reads_name_to_catid(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        "  <NetDeckID>0</NetDeckID>\n"
        "  <PreconstructedDeckID>0</PreconstructedDeckID>\n"
        '  <Cards CatID="28245" Quantity="1" Sideboard="false" Name="Mulldrifter" Annotation="0" />\n'
        '  <Cards CatID="87919" Quantity="50" Sideboard="false" Name="Snow-Covered Forest" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    result = parse_catid_map(dek)

    assert result == {"Mulldrifter": "28245", "Snow-Covered Forest": "87919"}


def test_parse_catid_map_handles_comma_in_name(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="116768" Quantity="1" Sideboard="false" Name="Ruby, Daring Tracker" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    result = parse_catid_map(dek)

    assert result == {"Ruby, Daring Tracker": "116768"}


def test_parse_catid_map_ignores_entries_without_catid_or_name(tmp_path):
    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="1" Quantity="1" Sideboard="false" Name="Real Card" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )

    result = parse_catid_map(dek)

    assert result == {"Real Card": "1"}


def test_load_default_catid_map_returns_empty_when_file_missing(monkeypatch, tmp_path):
    import mtgo.catid_map as catid_map_module

    monkeypatch.setattr(
        catid_map_module,
        "DEFAULT_CATID_MAP_PATH",
        tmp_path / "does_not_exist.dek",
    )

    assert load_default_catid_map() == {}


def test_load_default_catid_map_reads_existing_file(monkeypatch, tmp_path):
    import mtgo.catid_map as catid_map_module

    dek = tmp_path / "full_trade_list.dek"
    dek.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Deck xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        '  <Cards CatID="28245" Quantity="1" Sideboard="false" Name="Mulldrifter" Annotation="0" />\n'
        "</Deck>\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(catid_map_module, "DEFAULT_CATID_MAP_PATH", dek)

    assert load_default_catid_map() == {"Mulldrifter": "28245"}
