from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.hand_out_loan_session import (
    HandOutLoanSessionUseCase,
)


def test_hand_out_loan_session(db_session):
    card = Card(
        name="Black Lotus",
    )

    assignment = LoanAssignment(
        card=card,
        player_name="Alice",
        quantity=1,
        status="CREATED",
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

    use_case = HandOutLoanSessionUseCase(
        workflow,
    )

    result = use_case.execute(
        session,
    )

    assert result.assignments[0].status == "HANDED_OUT"
