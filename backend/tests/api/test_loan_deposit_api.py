from app.models.loan_deposit import LoanDeposit
from app.models.loan_session import LoanSession


def _make_deposit_session(db_session, deposit_amount=10):
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=deposit_amount,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def test_create_deposit_api(client, db_session):
    session = _make_deposit_session(db_session)

    response = client.post(
        f"/loan/sessions/{session.id}/deposits",
        json={"mtgo_username": "FruitDuChene"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == session.id
    assert data["mtgo_username"] == "FruitDuChene"
    assert data["required_amount"] == 10
    assert data["collected_amount"] is None
    assert data["returned_amount"] is None


def test_create_deposit_rejects_session_without_deposit_required_api(client, db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    response = client.post(
        f"/loan/sessions/{session.id}/deposits",
        json={"mtgo_username": "FruitDuChene"},
    )

    assert response.status_code == 400


def test_create_deposit_unknown_session_api(client):
    response = client.post(
        "/loan/sessions/999/deposits",
        json={"mtgo_username": "FruitDuChene"},
    )

    assert response.status_code == 404


def test_list_deposits_for_session_api(client, db_session):
    session = _make_deposit_session(db_session)

    client.post(
        f"/loan/sessions/{session.id}/deposits",
        json={"mtgo_username": "Alice"},
    )
    client.post(
        f"/loan/sessions/{session.id}/deposits",
        json={"mtgo_username": "Bob"},
    )

    response = client.get(f"/loan/sessions/{session.id}/deposits")

    assert response.status_code == 200

    usernames = {item["mtgo_username"] for item in response.json()}

    assert usernames == {"Alice", "Bob"}


def test_record_deposit_collected_api(client, db_session):
    session = _make_deposit_session(db_session)
    deposit = LoanDeposit(
        session_id=session.id,
        mtgo_username="FruitDuChene",
        required_amount=10,
    )
    db_session.add(deposit)
    db_session.commit()
    db_session.refresh(deposit)

    response = client.patch(
        f"/loan/sessions/deposits/{deposit.id}/collected",
        json={"collected_amount": 10},
    )

    assert response.status_code == 200
    assert response.json()["collected_amount"] == 10


def test_record_deposit_collected_unknown_deposit_api(client):
    response = client.patch(
        "/loan/sessions/deposits/999/collected",
        json={"collected_amount": 10},
    )

    assert response.status_code == 404


def test_record_deposit_returned_api(client, db_session):
    session = _make_deposit_session(db_session)
    deposit = LoanDeposit(
        session_id=session.id,
        mtgo_username="FruitDuChene",
        required_amount=10,
        collected_amount=10,
    )
    db_session.add(deposit)
    db_session.commit()
    db_session.refresh(deposit)

    response = client.patch(
        f"/loan/sessions/deposits/{deposit.id}/returned",
        json={"returned_amount": 10},
    )

    assert response.status_code == 200
    assert response.json()["returned_amount"] == 10


def test_record_deposit_returned_unknown_deposit_api(client):
    response = client.patch(
        "/loan/sessions/deposits/999/returned",
        json={"returned_amount": 10},
    )

    assert response.status_code == 404
