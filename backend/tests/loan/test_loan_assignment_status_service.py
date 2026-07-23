import pytest

from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


def test_mark_prepared():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    service.mark_prepared(assignment)

    assert assignment.status == "PREPARED"


def test_mark_distributed():
    assignment = LoanAssignment(
        status="PREPARED",
    )

    service = LoanAssignmentStatusService()

    service.mark_distributed(assignment)

    assert assignment.status == "DISTRIBUTED"


def test_mark_confirmed():
    assignment = LoanAssignment(
        status="DISTRIBUTED",
    )

    service = LoanAssignmentStatusService()

    service.mark_confirmed(assignment)

    assert assignment.status == "CONFIRMED"


def test_mark_returned():
    assignment = LoanAssignment(
        status="CONFIRMED",
    )

    service = LoanAssignmentStatusService()

    service.mark_returned(assignment)

    assert assignment.status == "RETURNED"


def test_created_cannot_be_returned():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_returned(assignment)


def test_cannot_skip_from_created_to_distributed():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_distributed(assignment)


def test_cannot_skip_from_prepared_to_confirmed():
    assignment = LoanAssignment(
        status="PREPARED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_confirmed(assignment)


def test_returned_is_terminal():
    assignment = LoanAssignment(
        status="RETURNED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_prepared(assignment)


def test_force_cancel_from_created():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    service.force_cancel(assignment)

    assert assignment.status == "CANCELLED"


def test_force_cancel_from_distributed():
    assignment = LoanAssignment(
        status="DISTRIBUTED",
    )

    service = LoanAssignmentStatusService()

    service.force_cancel(assignment)

    assert assignment.status == "CANCELLED"


def test_force_cancel_is_noop_when_already_returned():
    assignment = LoanAssignment(
        status="RETURNED",
    )

    service = LoanAssignmentStatusService()

    service.force_cancel(assignment)

    assert assignment.status == "RETURNED"


def test_force_cancel_is_noop_when_already_cancelled():
    assignment = LoanAssignment(
        status="CANCELLED",
    )

    service = LoanAssignmentStatusService()

    service.force_cancel(assignment)

    assert assignment.status == "CANCELLED"
