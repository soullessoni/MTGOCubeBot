from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.force_cancel_loan_session import (
    ForceCancelLoanSessionUseCase,
)


def test_force_cancel_loan_session(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    session.assignments.append(
        LoanAssignment(
            card=card,
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(
        session,
    )
    db_session.commit()

    workflow = LoanSessionWorkflowService(
        db_session,
    )

    use_case = ForceCancelLoanSessionUseCase(
        workflow,
    )

    result = use_case.execute(
        session,
    )

    assert result.status == "CANCELLED"
    assert result.assignments[0].status == "CANCELLED"
