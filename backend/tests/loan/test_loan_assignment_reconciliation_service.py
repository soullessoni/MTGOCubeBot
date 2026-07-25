from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_reconciliation_service import (
    LoanAssignmentReconciliationService,
)


def _assignment(card_name, status, mtgo_name=None):
    return LoanAssignment(
        card=Card(name=card_name, mtgo_name=mtgo_name),
        status=status,
        player_name="Adrien",
    )


def test_reconcile_distributed_marks_only_received_cards():
    taken = _assignment("Agent of Atlas", "PREPARED")
    left_behind = _assignment("Depower", "PREPARED")

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_distributed(
        [taken, left_behind],
        received_card_names={"Agent of Atlas"},
    )

    assert taken.status == "DISTRIBUTED"
    assert left_behind.status == "PREPARED"
    assert updated == [taken]


def test_reconcile_distributed_ignores_assignments_not_in_prepared_status():
    already_distributed = _assignment("Agent of Atlas", "DISTRIBUTED")
    cancelled = _assignment("Depower", "CANCELLED")

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_distributed(
        [already_distributed, cancelled],
        received_card_names={"Agent of Atlas", "Depower"},
    )

    assert already_distributed.status == "DISTRIBUTED"
    assert cancelled.status == "CANCELLED"
    assert updated == []


def test_reconcile_distributed_ignores_received_names_with_no_matching_assignment():
    unrelated = _assignment("Depower", "PREPARED")

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_distributed(
        [unrelated],
        received_card_names={"Some Other Card"},
    )

    assert unrelated.status == "PREPARED"
    assert updated == []


def test_reconcile_distributed_matches_by_mtgo_name_when_set():
    assignment = _assignment(
        "Web Up",
        "PREPARED",
        mtgo_name="Web Up (Amazing Spider-Man)",
    )

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_distributed(
        [assignment],
        received_card_names={"Web Up (Amazing Spider-Man)"},
    )

    assert assignment.status == "DISTRIBUTED"
    assert updated == [assignment]


def test_reconcile_returned_marks_only_received_cards():
    returned_by_player = _assignment("Agent of Atlas", "CONFIRMED")
    kept_by_player = _assignment("Depower", "CONFIRMED")

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_returned(
        [returned_by_player, kept_by_player],
        received_card_names={"Agent of Atlas"},
    )

    assert returned_by_player.status == "RETURNED"
    assert kept_by_player.status == "CONFIRMED"
    assert updated == [returned_by_player]


def test_reconcile_returned_ignores_assignments_not_in_confirmed_status():
    still_prepared = _assignment("Agent of Atlas", "PREPARED")

    service = LoanAssignmentReconciliationService()

    updated = service.reconcile_returned(
        [still_prepared],
        received_card_names={"Agent of Atlas"},
    )

    assert still_prepared.status == "PREPARED"
    assert updated == []
