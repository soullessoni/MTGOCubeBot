from app.models.card import Card
from app.models.inventory_item import InventoryItem
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_list_inventory_api(
        client,
        db_session,
):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.flush()

    db_session.add(
        InventoryItem(
            card_id=card.id,
            quantity=2,
        )
    )

    session = LoanSession(status="IN_PROGRESS")

    session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(session)
    db_session.commit()

    response = client.get("/inventory/")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["card_id"] == card.id
    assert data[0]["card_name"] == "Black Lotus"
    assert data[0]["quantity"] == 2
    assert data[0]["available_quantity"] == 1


def test_list_inventory_api_empty(
        client,
        db_session,
):
    response = client.get("/inventory/")

    assert response.status_code == 200
    assert response.json() == []


def test_update_inventory_quantity_api(
        client,
        db_session,
):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    response = client.put(
        f"/inventory/{card.id}",
        json={"quantity": 3},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["card_id"] == card.id
    assert data["quantity"] == 3
    assert data["available_quantity"] == 3


def test_update_inventory_quantity_overwrites_existing(
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

    db_session.commit()

    response = client.put(
        f"/inventory/{card.id}",
        json={"quantity": 5},
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 5


def test_update_inventory_quantity_unknown_card(
        client,
        db_session,
):
    response = client.put(
        "/inventory/999",
        json={"quantity": 1},
    )

    assert response.status_code == 404
