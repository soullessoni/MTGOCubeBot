from types import SimpleNamespace

import pytest

from app.services.loan.loan_session_readiness_service import (
    LoanSessionReadinessService,
)


def test_session_is_ready():

    session = SimpleNamespace(
        status="CREATED",
        assignments=[
            SimpleNamespace(
                status="CREATED",
            ),
        ],
    )

    service = LoanSessionReadinessService()

    assert service.validate(session) is True


def test_session_without_assignment_is_not_ready():

    session = SimpleNamespace(
        status="CREATED",
        assignments=[],
    )

    service = LoanSessionReadinessService()

    with pytest.raises(ValueError):
        service.validate(session)


def test_completed_session_is_not_ready():

    session = SimpleNamespace(
        status="COMPLETED",
        assignments=[
            SimpleNamespace(
                status="CREATED",
            ),
        ],
    )

    service = LoanSessionReadinessService()

    with pytest.raises(ValueError):
        service.validate(session)


def test_invalid_assignment_status():

    session = SimpleNamespace(
        status="CREATED",
        assignments=[
            SimpleNamespace(
                status="RETURNED",
            ),
        ],
    )

    service = LoanSessionReadinessService()

    with pytest.raises(ValueError):
        service.validate(session)