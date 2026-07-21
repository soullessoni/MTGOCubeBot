from app.models.loan_session import LoanSession
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)


def test_mark_ready():

    session = LoanSession(
        status="CREATED",
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

    try:
        service.complete(session)
    except ValueError:
        assert True
    else:
        assert False, "Expected ValueError"