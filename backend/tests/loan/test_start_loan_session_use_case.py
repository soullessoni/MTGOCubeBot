from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.start_loan_session import (
    StartLoanSessionUseCase,
)


def test_start_loan_session(db_session):

    session = LoanSession(
        status="READY",
    )

    db_session.add(session)
    db_session.commit()

    workflow = LoanSessionWorkflowService(
        db_session,
    )

    service = StartLoanSessionUseCase(
        workflow,
    )

    result = service.execute(
        session,
    )

    assert result.status == "IN_PROGRESS"