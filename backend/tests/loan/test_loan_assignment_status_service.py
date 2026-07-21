import pytest

from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


def test_mark_borrowed():

    assignment = LoanAssignment(
        status="CREATED",
    )

    service = LoanAssignmentStatusService()

    service.mark_borrowed(assignment)

    assert assignment.status == "BORROWED"


def test_mark_returned():

    assignment = LoanAssignment(
        status="BORROWED",
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