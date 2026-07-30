from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_prepare_all_loan_assignments_api(
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
            status="CREATED",
            player_name="Alice",
            quantity=1,
        )
    )
    session.assignments.append(
        LoanAssignment(
            card=card,
            status="CREATED",
            player_name="Bob",
            quantity=1,
        )
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/prepare-all"
    )

    assert response.status_code == 200

    data = response.json()

    assert {a["status"] for a in data["assignments"]} == {"PREPARED"}


def test_cannot_prepare_all_when_session_not_in_progress(
        client,
        db_session,
):
    session = LoanSession(
        status="READY",
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/prepare-all"
    )

    assert response.status_code == 400


def test_prepare_all_returns_404_for_missing_session(
        client,
):
    response = client.post(
        "/loan/sessions/999/prepare-all"
    )

    assert response.status_code == 404
