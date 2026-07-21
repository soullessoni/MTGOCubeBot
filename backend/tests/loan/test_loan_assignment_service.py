from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_assignment_service import LoanAssignmentService


def test_mark_assignment_status(db_session):

    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="CREATED",
    )

    db_session.add(card)
    db_session.add(session)
    db_session.commit()

    assignment = LoanAssignment(
        session_id=session.id,
        card_id=card.id,
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    db_session.add(assignment)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    service.mark_handed_out(
        assignment,
    )

    assert assignment.status == "HANDED_OUT"

    service.mark_returned(
        assignment,
    )

    assert assignment.status == "RETURNED"
