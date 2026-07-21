from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_validation_service import (
    LoanSessionValidationService,
)


def test_valid_session():
    session = LoanSession(
        status="CREATED",
    )

    session.assignments.append(
        LoanAssignment(
            status="CREATED",
        )
    )

    service = LoanSessionValidationService()

    result = service.validate(session)

    assert result.valid is True
    assert result.errors == []


def test_session_without_assignment():
    session = LoanSession(
        status="CREATED",
    )

    service = LoanSessionValidationService()

    result = service.validate(session)

    assert result.valid is False
    assert (
            "Loan session has no assignments"
            in result.errors
    )


def test_session_with_invalid_assignment_state():
    session = LoanSession(
        status="CREATED",
    )

    session.assignments.append(
        LoanAssignment(
            status="CREATED",
        )
    )

    session.assignments.append(
        LoanAssignment(
            status="HANDED_OUT",
        )
    )

    service = LoanSessionValidationService()

    result = service.validate(session)

    assert result.valid is False
    assert len(result.errors) == 1

    def test_validation_result_valid_is_derived():
        from app.services.loan.loan_session_validation_service import (
            LoanSessionValidationResult,
        )

        result = LoanSessionValidationResult(
            errors=[],
        )

        assert result.valid is True

    def test_validation_result_invalid_is_derived():
        from app.services.loan.loan_session_validation_service import (
            LoanSessionValidationResult,
        )

        result = LoanSessionValidationResult(
            errors=[
                "error",
            ],
        )

        assert result.valid is False
