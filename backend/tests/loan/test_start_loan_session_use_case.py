from app.models.loan_session import LoanSession
from app.use_cases.loan.start_loan_session import (
    StartLoanSessionUseCase,
)


def test_start_loan_session(db_session):

    session = LoanSession(
        status="CREATED",
    )

    db_session.add(session)
    db_session.commit()

    use_case = StartLoanSessionUseCase(
        db_session,
    )

    result = use_case.execute(
        session,
    )

    assert result.status == "STARTED"


def test_cannot_start_started_session(db_session):

    session = LoanSession(
        status="STARTED",
    )

    db_session.add(session)
    db_session.commit()

    use_case = StartLoanSessionUseCase(
        db_session,
    )

    try:
        use_case.execute(session)
        assert False
    except ValueError:
        assert True