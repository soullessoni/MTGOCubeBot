from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_full_loan_session_lifecycle_api(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="CREATED",
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
    db_session.refresh(session)
    db_session.refresh(assignment)

    #
    # READY
    #
    response = client.post(
        f"/loan/sessions/{session.id}/ready"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"

    #
    # START
    #
    response = client.post(
        f"/loan/sessions/{session.id}/start"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"

    #
    # PREPARE
    #
    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/prepare"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PREPARED"

    #
    # DISTRIBUTE
    #
    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/distribute"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "DISTRIBUTED"

    #
    # CONFIRM
    #
    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/confirm"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"

    #
    # RETURN CARD
    #
    response = client.post(
        f"/loan/sessions/assignments/{assignment.id}/return"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RETURNED"

    #
    # COMPLETE
    #
    response = client.post(
        f"/loan/sessions/{session.id}/complete"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
