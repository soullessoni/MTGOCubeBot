from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_complete_loan_session_api(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    session.assignments.append(
        LoanAssignment(
            card=card,
            status="RETURNED",
            player_name="Alice",
            quantity=1,
        )
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/complete"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"


def test_cannot_complete_with_unreturned_cards(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    session.assignments.append(
        LoanAssignment(
            card=card,
            status="HANDED_OUT",
            player_name="Alice",
            quantity=1,
        )
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/complete"
    )

    assert response.status_code == 400
