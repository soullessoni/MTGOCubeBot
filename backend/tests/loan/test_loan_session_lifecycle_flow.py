from app.models.card import Card
from app.use_cases.loan.create_loan_session_from_draft import (
    CreateLoanSessionFromDraftUseCase,
)
from app.use_cases.loan.mark_ready_loan_session import (
    MarkReadyLoanSessionUseCase,
)
from app.use_cases.loan.start_loan_session import (
    StartLoanSessionUseCase,
)
from app.use_cases.loan.complete_loan_session import (
    CompleteLoanSessionUseCase,
)
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


def test_loan_session_full_lifecycle(
    db_session,
):

    cards = [
        Card(name="Black Lotus"),
        Card(name="Mox Sapphire"),
    ]

    db_session.add_all(cards)
    db_session.commit()

    # CREATE
    create_use_case = CreateLoanSessionFromDraftUseCase(
        db_session,
    )

    session = create_use_case.execute(
        players=[
            {
                "player_name": "Alice",
                "cards": [
                    "Black Lotus",
                    "Mox Sapphire",
                ],
            }
        ],
    )

    assert session.status == "CREATED"


    # READY
    mark_ready = MarkReadyLoanSessionUseCase(
        LoanSessionStatusService(),
    )

    session = mark_ready.execute(
        session,
    )

    assert session.status == "READY"


    # START
    start = StartLoanSessionUseCase(
        LoanSessionStatusService(),
    )

    session = start.execute(
        session,
    )

    assert session.status == "IN_PROGRESS"

    # RETURN CARDS

    for assignment in session.assignments:
        assignment.status = "RETURNED"

    db_session.commit()

    # COMPLETE

    complete = CompleteLoanSessionUseCase(
        LoanSessionWorkflowService(
            db_session,
        ),
    )

    session = complete.execute(
        session,
    )

    assert session.status == "COMPLETED"