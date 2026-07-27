from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_record_given_quantity_api(
        client,
        db_session,
):
    card = Card(name="Black Lotus")

    session = LoanSession(status="CREATED")

    assignment = LoanAssignment(
        card=card,
        player_name="Alice",
        quantity=3,
        status="PREPARED",
    )

    session.assignments.append(assignment)

    db_session.add(session)
    db_session.commit()
    db_session.refresh(assignment)

    response = client.patch(
        f"/loan/sessions/assignments/{assignment.id}/given-quantity",
        json={"given_quantity": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["given_quantity"] == 2
    assert data["status"] == "PREPARED"


def test_record_given_quantity_unknown_assignment_api(
        client,
        db_session,
):
    response = client.patch(
        "/loan/sessions/assignments/999/given-quantity",
        json={"given_quantity": 1},
    )

    assert response.status_code == 404
