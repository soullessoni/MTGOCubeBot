from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.confirm_loan_assignment import (
    ConfirmLoanAssignmentUseCase,
)


def test_confirm_loan_assignment(db_session):
    card = Card(
        name="Black Lotus",
    )

    assignment = LoanAssignment(
        card=card,
        player_name="Alice",
        quantity=1,
        status="DISTRIBUTED",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(
        session,
    )
    db_session.commit()

    workflow = LoanSessionWorkflowService(
        db_session,
    )

    use_case = ConfirmLoanAssignmentUseCase(
        workflow,
    )

    result = use_case.execute(
        assignment,
    )

    assert result.status == "CONFIRMED"
