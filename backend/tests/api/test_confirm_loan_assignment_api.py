from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_confirm_loan_assignment_api(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="DISTRIBUTED",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(assignment)

    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/confirm"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CONFIRMED"


def test_cannot_confirm_prepared_assignment(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="PREPARED",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(assignment)

    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/confirm"
    )

    assert response.status_code == 400
