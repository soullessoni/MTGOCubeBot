from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_mark_ready_loan_session_api(
        client,
        db_session,
        cube_instance_id,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="CREATED",
        cube_instance_id=cube_instance_id,
    )

    session.assignments.append(
        LoanAssignment(
            card=card,
            status="CREATED",
            player_name="Alice",
            quantity=1,
        )
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/ready"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "READY"


def test_mark_ready_empty_session_fails(
        client,
        db_session,
        cube_instance_id,
):
    session = LoanSession(
        status="CREATED",
        cube_instance_id=cube_instance_id,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/ready"
    )

    assert response.status_code == 400
