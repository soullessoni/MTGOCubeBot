from app.models.card import Card
from app.models.inventory_item import InventoryItem


def test_create_loan_session_api(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    db_session.add(card)
    db_session.flush()

    db_session.add(
        InventoryItem(
            card_id=card.id,
            quantity=1,
        )
    )

    db_session.commit()

    response = client.post(
        "/loan/sessions",
        json={
            "players": [
                {
                    "player_name": "Alice",
                    "cards": [
                        {
                            "card_id": card.id,
                        }
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CREATED"
    assert len(data["assignments"]) == 1
    assert (
            data["assignments"][0]["player_name"]
            == "Alice"
    )
