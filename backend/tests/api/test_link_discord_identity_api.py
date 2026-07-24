from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_link_discord_identity_api(
        client,
        db_session,
):
    card = Card(name="Black Lotus")

    session = LoanSession(status="CREATED")

    assignment = LoanAssignment(
        card=card,
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    session.assignments.append(assignment)

    db_session.add(session)
    db_session.commit()
    db_session.refresh(assignment)

    response = client.patch(
        f"/loan/sessions/assignments/{assignment.id}/discord",
        json={
            "discord_user_id": "123456789012345678",
            "mtgo_username": "AlicePlays",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["discord_user_id"] == "123456789012345678"
    assert data["mtgo_username"] == "AlicePlays"


def test_link_discord_identity_unknown_assignment_api(
        client,
        db_session,
):
    response = client.patch(
        "/loan/sessions/assignments/999/discord",
        json={
            "discord_user_id": "1",
            "mtgo_username": "Nobody",
        },
    )

    assert response.status_code == 404
