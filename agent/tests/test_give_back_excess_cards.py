from mtgo.give_back_excess_cards import expand_cards_to_names


def test_expand_cards_to_names_repeats_by_quantity():
    result = expand_cards_to_names({"Mulldrifter": 2, "Wingcrafter": 1})

    assert result.count("Mulldrifter") == 2
    assert result.count("Wingcrafter") == 1
    assert len(result) == 3


def test_expand_cards_to_names_empty_dict_gives_empty_list():
    assert expand_cards_to_names({}) == []


def test_expand_cards_to_names_zero_quantity_contributes_nothing():
    result = expand_cards_to_names({"Mulldrifter": 0, "Wingcrafter": 1})

    assert result == ["Wingcrafter"]
