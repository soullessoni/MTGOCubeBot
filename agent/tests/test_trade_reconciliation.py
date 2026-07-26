from mtgo.trade_reconciliation import plan_reconciliation


def test_plan_reconciliation_flags_missing_card():
    expected = {"Mulldrifter": "28245"}
    actual = {}

    plan = plan_reconciliation(expected, actual)

    assert plan == {
        "to_remove": [],
        "to_add": ["Mulldrifter"],
        "already_correct": [],
    }


def test_plan_reconciliation_accepts_correct_edition():
    expected = {"Mulldrifter": "28245"}
    actual = {"Mulldrifter": "28245"}

    plan = plan_reconciliation(expected, actual)

    assert plan == {
        "to_remove": [],
        "to_add": [],
        "already_correct": ["Mulldrifter"],
    }


def test_plan_reconciliation_flags_wrong_edition_for_removal_and_readd():
    expected = {"Tishana's Tidebinder": "117962"}
    actual = {"Tishana's Tidebinder": "117678"}

    plan = plan_reconciliation(expected, actual)

    assert plan == {
        "to_remove": [("Tishana's Tidebinder", "117678")],
        "to_add": ["Tishana's Tidebinder"],
        "already_correct": [],
    }


def test_plan_reconciliation_ignores_extra_cards_not_being_sought():
    expected = {"Mulldrifter": "28245"}
    actual = {"Mulldrifter": "28245", "Bonus Card": "99999"}

    plan = plan_reconciliation(expected, actual)

    assert plan == {
        "to_remove": [],
        "to_add": [],
        "already_correct": ["Mulldrifter"],
    }


def test_plan_reconciliation_handles_mixed_batch():
    expected = {
        "Mulldrifter": "28245",
        "Tishana's Tidebinder": "117962",
        "Scuttling Sentinel": "123392",
    }
    actual = {
        "Mulldrifter": "28245",
        "Tishana's Tidebinder": "117678",
    }

    plan = plan_reconciliation(expected, actual)

    assert plan["already_correct"] == ["Mulldrifter"]
    assert plan["to_remove"] == [("Tishana's Tidebinder", "117678")]
    assert set(plan["to_add"]) == {"Tishana's Tidebinder", "Scuttling Sentinel"}
