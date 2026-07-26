from mtgo.trade_reconciliation import plan_reconciliation


def test_plan_reconciliation_flags_missing_card():
    plan = plan_reconciliation(
        card_names=["Mulldrifter"],
        catid_map={"Mulldrifter": "28245"},
        actual={},
    )

    assert plan == {
        "to_remove": [],
        "to_add": ["Mulldrifter"],
        "already_correct": [],
    }


def test_plan_reconciliation_accepts_correct_edition_and_quantity():
    plan = plan_reconciliation(
        card_names=["Mulldrifter"],
        catid_map={"Mulldrifter": "28245"},
        actual={"Mulldrifter": {"28245": 1}},
    )

    assert plan == {
        "to_remove": [],
        "to_add": [],
        "already_correct": ["Mulldrifter"],
    }


def test_plan_reconciliation_flags_wrong_edition_for_removal_and_readd():
    plan = plan_reconciliation(
        card_names=["Tishana's Tidebinder"],
        catid_map={"Tishana's Tidebinder": "117962"},
        actual={"Tishana's Tidebinder": {"117678": 1}},
    )

    assert plan == {
        "to_remove": [("Tishana's Tidebinder", "117678", 1)],
        "to_add": ["Tishana's Tidebinder"],
        "already_correct": [],
    }


def test_plan_reconciliation_flags_excess_quantity_of_correct_edition():
    """The real 2026-07-26 incident: only 1 copy was lent, but the
    counterparty independently owned another and Import Deck grabbed
    both — same (correct) edition, wrong quantity."""
    plan = plan_reconciliation(
        card_names=["Mulldrifter"],
        catid_map={"Mulldrifter": "28245"},
        actual={"Mulldrifter": {"28245": 2}},
    )

    assert plan == {
        "to_remove": [("Mulldrifter", "28245", 1)],
        "to_add": [],
        "already_correct": ["Mulldrifter"],
    }


def test_plan_reconciliation_handles_two_copies_lent():
    plan = plan_reconciliation(
        card_names=["Snow-Covered Island", "Snow-Covered Island"],
        catid_map={"Snow-Covered Island": "87907"},
        actual={"Snow-Covered Island": {"87907": 1}},
    )

    assert plan == {
        "to_remove": [],
        "to_add": ["Snow-Covered Island"],
        "already_correct": ["Snow-Covered Island"],
    }


def test_plan_reconciliation_ignores_extra_cards_not_being_sought():
    plan = plan_reconciliation(
        card_names=["Mulldrifter"],
        catid_map={"Mulldrifter": "28245"},
        actual={"Mulldrifter": {"28245": 1}, "Bonus Card": {"99999": 1}},
    )

    assert plan == {
        "to_remove": [],
        "to_add": [],
        "already_correct": ["Mulldrifter"],
    }


def test_plan_reconciliation_handles_mixed_batch():
    plan = plan_reconciliation(
        card_names=["Mulldrifter", "Tishana's Tidebinder", "Scuttling Sentinel"],
        catid_map={
            "Mulldrifter": "28245",
            "Tishana's Tidebinder": "117962",
            "Scuttling Sentinel": "123392",
        },
        actual={
            "Mulldrifter": {"28245": 1},
            "Tishana's Tidebinder": {"117678": 1},
        },
    )

    assert plan["already_correct"] == ["Mulldrifter"]
    assert plan["to_remove"] == [("Tishana's Tidebinder", "117678", 1)]
    assert sorted(plan["to_add"]) == ["Scuttling Sentinel", "Tishana's Tidebinder"]
