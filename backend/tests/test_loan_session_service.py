from app.models.card import Card
from app.services.loan_session_service import LoanSessionService
from app.services.loan_planning_service import (
    LoanPlanningResult,
    LoanRequest,
)


def test_create_loan_session(db_session):

    lotus = Card(
        name="Black Lotus",
    )

    db_session.add(lotus)
    db_session.commit()

    plan = LoanPlanningResult(
        requests=[
            LoanRequest(
                player_name="Alice",
                requested_cards=[
                    lotus,
                ],
            ),
        ],
        conflicts=[],
    )

    service = LoanSessionService(db_session)

    session = service.create_from_plan(plan)

    assert session.id is not None
    assert session.status == "CREATED"

    assignments = session.assignments

    assert len(assignments) == 1
    assert assignments[0].player_name == "Alice"
    assert assignments[0].card_id == lotus.id
    assert assignments[0].card.name == "Black Lotus"