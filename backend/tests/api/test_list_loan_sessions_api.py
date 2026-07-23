from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


def test_list_loan_sessions_api(
        client,
        db_session,
):
    card = Card(
        name="Black Lotus",
    )

    db_session.add(card)
    db_session.flush()

    first_session = LoanSession(
        status="CREATED",
    )

    first_session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    second_session = LoanSession(
        status="READY",
    )

    db_session.add(first_session)
    db_session.add(second_session)
    db_session.commit()

    response = client.get(
        "/loan/sessions/"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    ids = {
        session["id"] for session in data
    }

    assert ids == {
        first_session.id,
        second_session.id,
    }

    session_with_assignment = next(
        session
        for session in data
        if session["id"] == first_session.id
    )

    assert (
            session_with_assignment["assignments"][0]["card_name"]
            == "Black Lotus"
    )


def test_list_loan_sessions_api_empty(
        client,
        db_session,
):
    response = client.get(
        "/loan/sessions/"
    )

    assert response.status_code == 200
    assert response.json() == []
