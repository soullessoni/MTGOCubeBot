import pytest

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)


def test_mark_ready():

    session = LoanSession(
        status="CREATED",
    )

    session.assignments.append(
        LoanAssignment(
            status="CREATED",
        )
    )

    service = LoanSessionStatusService()

    service.mark_ready(session)

    assert session.status == "READY"


def test_start():

    session = LoanSession(
        status="READY",
    )

    service = LoanSessionStatusService()

    service.start(session)

    assert session.status == "IN_PROGRESS"


def test_complete():

    session = LoanSession(
        status="IN_PROGRESS",
    )

    service = LoanSessionStatusService()

    service.complete(session)

    assert session.status == "COMPLETED"


def test_invalid_transition():

    session = LoanSession(
        status="CREATED",
    )

    service = LoanSessionStatusService()

    with pytest.raises(ValueError):
        service.complete(session)


def test_created_cannot_start_directly():

    session = LoanSession(
        status="CREATED",
    )

    service = LoanSessionStatusService()

    with pytest.raises(ValueError):
        service.start(session)


def test_ready_cannot_complete_directly():

    session = LoanSession(
        status="READY",
    )

    service = LoanSessionStatusService()

    with pytest.raises(ValueError):
        service.complete(session)


def test_completed_cannot_restart():

    session = LoanSession(
        status="COMPLETED",
    )

    service = LoanSessionStatusService()

    with pytest.raises(ValueError):
        service.start(session)