import pytest

from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


def test_created_can_be_borrowed():

    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    service.mark_handed_out(assignment)

    assert assignment.status == "HANDED_OUT"

def test_created_cannot_be_returned():

    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_returned(assignment)


def test_handed_out_can_be_returned():

    assignment = LoanAssignment(
        status="HANDED_OUT",
    )

    service = LoanAssignmentStatusService()

    service.mark_returned(assignment)

    assert assignment.status == "RETURNED"


def test_returned_cannot_be_handed_out():

    assignment = LoanAssignment(
        status="RETURNED",
    )

    service = LoanAssignmentStatusService()

    with pytest.raises(ValueError):
        service.mark_handed_out(assignment)
