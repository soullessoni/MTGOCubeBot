from mtgo.cube_integrity_check import build_result
from mtgo.stock_check import compute_expected_quantities, diff_stock


def test_build_result_ok_when_no_discrepancy():
    diff = {"missing": {}, "extra": {}}

    result = build_result(diff, checked_at="2026-07-27T10:00:00+00:00")

    assert result == {
        "ok": True,
        "missing": {},
        "extra": {},
        "checked_at": "2026-07-27T10:00:00+00:00",
    }


def test_build_result_not_ok_when_missing():
    diff = {"missing": {"Mulldrifter": 1}, "extra": {}}

    result = build_result(diff, checked_at="2026-07-27T10:00:00+00:00")

    assert result["ok"] is False
    assert result["missing"] == {"Mulldrifter": 1}


def test_build_result_not_ok_when_extra():
    diff = {"missing": {}, "extra": {"Mulldrifter": 2}}

    result = build_result(diff, checked_at="2026-07-27T10:00:00+00:00")

    assert result["ok"] is False
    assert result["extra"] == {"Mulldrifter": 2}


def test_compute_expected_then_diff_stock_matches_when_collection_is_clean():
    inventory = [
        {"card_name": "Mulldrifter", "quantity": 4},
        {"card_name": "Wingcrafter", "quantity": 2},
    ]
    active_loan_card_names = ["Wingcrafter"]

    expected = compute_expected_quantities(inventory, active_loan_card_names)
    actual = {"Mulldrifter": 4, "Wingcrafter": 1}

    diff = diff_stock(expected, actual)
    result = build_result(diff, checked_at="2026-07-27T10:00:00+00:00")

    assert result["ok"] is True


def test_compute_expected_then_diff_stock_flags_a_real_discrepancy():
    inventory = [
        {"card_name": "Mulldrifter", "quantity": 4},
        {"card_name": "Wingcrafter", "quantity": 2},
    ]
    active_loan_card_names = ["Wingcrafter"]

    expected = compute_expected_quantities(inventory, active_loan_card_names)
    # Bot's live collection has one extra Mulldrifter and is missing a Wingcrafter.
    actual = {"Mulldrifter": 5, "Wingcrafter": 0}

    diff = diff_stock(expected, actual)
    result = build_result(diff, checked_at="2026-07-27T10:00:00+00:00")

    assert result["ok"] is False
    assert result["extra"] == {"Mulldrifter": 1}
    assert result["missing"] == {"Wingcrafter": 1}
