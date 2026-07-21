import pytest

from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


def test_mark_handed_out():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    service.mark_handed_out(assignment)

    assert assignment.status == "HANDED_OUT"


def test_mark_returned():
    assignment = LoanAssignment(
        status="HANDED_OUT",
    )

    service = LoanAssignmentStatusService()

    service.mark_returned(assignment)

    assert assignment.status == "RETURNED"


def test_invalid_transition():
    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_returned(assignment)
