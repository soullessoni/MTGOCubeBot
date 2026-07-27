from bot.cogs.session_flow import _format_assignment_line, _group_by_status


def make_assignment(id, card_name, status):
    return {"id": id, "card_id": id, "card_name": card_name, "status": status}


def test_format_assignment_line_uses_card_name_and_status():
    assignment = make_assignment(1, "Mulldrifter", "CONFIRMED")

    assert _format_assignment_line(assignment) == "- Mulldrifter (statut : CONFIRMED)"


def test_format_assignment_line_falls_back_to_card_id_when_name_missing():
    assignment = {"id": 1, "card_id": 42, "card_name": None, "status": "CONFIRMED"}

    assert _format_assignment_line(assignment) == "- Carte #42 (statut : CONFIRMED)"


def test_group_by_status_groups_assignments_sharing_a_status():
    assignments = [
        make_assignment(1, "Mulldrifter", "DISTRIBUTED"),
        make_assignment(2, "Wingcrafter", "DISTRIBUTED"),
        make_assignment(3, "Siren Stormtamer", "CONFIRMED"),
    ]

    groups = _group_by_status(assignments)

    assert [a["id"] for a in groups["DISTRIBUTED"]] == [1, 2]
    assert [a["id"] for a in groups["CONFIRMED"]] == [3]


def test_group_by_status_preserves_order_within_a_group():
    assignments = [
        make_assignment(1, "Mulldrifter", "CONFIRMED"),
        make_assignment(2, "Wingcrafter", "DISTRIBUTED"),
        make_assignment(3, "Siren Stormtamer", "CONFIRMED"),
    ]

    groups = _group_by_status(assignments)

    assert [a["id"] for a in groups["CONFIRMED"]] == [1, 3]
