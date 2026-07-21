from app.models.card import Card
from app.services.loan.loan_planning_service import (
    LoanPlanningResult,
    LoanRequest,
)
from app.use_cases.loan.create_loan_session import (
    CreateLoanSessionUseCase,
)


def test_create_session_from_plan(db_session):

    lotus = Card(
        name="Black Lotus",
    )

    bolt = Card(
        name="Lightning Bolt",
    )

    plan = LoanPlanningResult(
        requests=[
            LoanRequest(
                player_name="Alice",
                requested_cards=[
                    lotus,
                    bolt,
                ],
            )
        ],
        conflicts=[],
    )

    service = CreateLoanSessionUseCase(
        db_session,
    )

    session = service.execute(
        plan,
    )

    assert session.id is not None
    assert session.status == "CREATED"

    assert len(
        session.assignments,
    ) == 2

    assert (
        session.assignments[0].player_name
        == "Alice"
    )