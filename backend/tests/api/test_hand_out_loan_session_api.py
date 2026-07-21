from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_hand_out_loan_session_api(
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
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(session)
    db_session.commit()

    response = client.post(
        f"/loan/sessions/{session.id}/hand-out"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["assignments"][0]["status"] == "HANDED_OUT"
