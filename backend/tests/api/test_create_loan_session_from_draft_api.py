from app.models.card import Card


def test_create_loan_session_from_draft_api(
    client,
    db_session,
):
    db_session.add(
        Card(name="Black Lotus")
    )

    db_session.commit()

    response = client.post(
        "/loan/sessions/from-draft",
        json={
            "players": [
                {
                    "player_name": "Alice",
                    "cards": [
                        "Black Lotus"
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CREATED"

    assert len(data["assignments"]) == 1

    assignment = data["assignments"][0]

    assert assignment["player_name"] == "Alice"
    assert assignment["quantity"] == 1
    assert assignment["status"] == "CREATED"


def test_create_loan_session_from_draft_multiple_players(
    client,
    db_session,
):
    db_session.add_all(
        [
            Card(name="Sol Ring"),
            Card(name="Lightning Bolt"),
            Card(name="Counterspell"),
        ]
    )

    db_session.commit()

    response = client.post(
        "/loan/sessions/from-draft",
        json={
            "players": [
                {
                    "player_name": "Alice",
                    "cards": [
                        "Sol Ring",
                        "Lightning Bolt",
                    ],
                },
                {
                    "player_name": "Bob",
                    "cards": [
                        "Counterspell",
                    ],
                },
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "CREATED"
    assert len(data["assignments"]) == 3

    players = {
        assignment["player_name"]
        for assignment in data["assignments"]
    }

    assert players == {
        "Alice",
        "Bob",
    }

def test_create_from_draft_unknown_card(
    client,
):
    response = client.post(
        "/loan/sessions/from-draft",
        json={
            "players": [
                {
                    "player_name": "Alice",
                    "cards": [
                        "Unknown Card"
                    ],
                }
            ]
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Card not found: Unknown Card"
    )