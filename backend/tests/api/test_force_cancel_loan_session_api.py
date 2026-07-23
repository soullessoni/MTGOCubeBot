from app.models.card import Card
from app.models.inventory_item import InventoryItem
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_force_cancel_loan_session_api(
        client,
        db_session,
):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.flush()

    db_session.add(
        InventoryItem(
            card_id=card.id,
            quantity=1,
        )
    )

    session = LoanSession(status="IN_PROGRESS")

    session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="PREPARED",
        )
    )

    db_session.add(session)
    db_session.commit()

    response = client.post(
        f"/loan/sessions/{session.id}/cancel"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CANCELLED"
    assert data["assignments"][0]["status"] == "CANCELLED"

    inventory_response = client.get("/inventory/")

    inventory_data = inventory_response.json()

    assert inventory_data[0]["available_quantity"] == 1


def test_cannot_force_cancel_completed_session_api(
        client,
        db_session,
):
    session = LoanSession(status="COMPLETED")

    db_session.add(session)
    db_session.commit()

    response = client.post(
        f"/loan/sessions/{session.id}/cancel"
    )

    assert response.status_code == 400


def test_force_cancel_unknown_session_api(
        client,
        db_session,
):
    response = client.post(
        "/loan/sessions/999/cancel"
    )

    assert response.status_code == 404
