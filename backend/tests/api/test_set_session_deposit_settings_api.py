from app.models.loan_session import LoanSession


def test_set_deposit_settings_api(client, db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    response = client.patch(
        f"/loan/sessions/{session.id}/deposit-settings",
        json={"deposit_required": True, "deposit_amount": 20},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["deposit_required"] is True
    assert data["deposit_amount"] == 20


def test_set_deposit_settings_rejects_missing_amount_api(client, db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    response = client.patch(
        f"/loan/sessions/{session.id}/deposit-settings",
        json={"deposit_required": True, "deposit_amount": None},
    )

    assert response.status_code == 400


def test_set_deposit_settings_unknown_session_api(client):
    response = client.patch(
        "/loan/sessions/999/deposit-settings",
        json={"deposit_required": True, "deposit_amount": 5},
    )

    assert response.status_code == 404
