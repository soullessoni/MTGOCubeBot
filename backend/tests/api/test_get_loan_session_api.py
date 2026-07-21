from app.models.card import Card
from app.models.loan_session import LoanSession
from app.models.loan_assignment import LoanAssignment


def test_get_loan_session_api(
    client,
    db_session,
):

    card = Card(
        name="Black Lotus",
    )

    db_session.add(card)
    db_session.flush()

    session = LoanSession(
        status="CREATED",
    )

    db_session.add(session)
    db_session.flush()

    assignment = LoanAssignment(
        session_id=session.id,
        card_id=card.id,
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    db_session.add(assignment)
    db_session.commit()

    response = client.get(
        f"/loan/sessions/{session.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == session.id
    assert data["status"] == "CREATED"
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["player_name"] == "Alice"