from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_prepare_loan_assignment_api(
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
        status="CREATED",
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
        f"/loan/sessions/assignments/{assignment.id}/prepare"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "PREPARED"


def test_cannot_prepare_when_session_not_in_progress(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="READY",
    )

    assignment = LoanAssignment(
        card=card,
        status="CREATED",
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
        f"/loan/sessions/assignments/{assignment.id}/prepare"
    )

    assert response.status_code == 400
