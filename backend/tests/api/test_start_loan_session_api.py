from app.models.loan_session import LoanSession


def test_start_loan_session_api(
    client,
    db_session,
):

    session = LoanSession(
        status="READY",
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/start"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "IN_PROGRESS"

def test_cannot_start_created_session(
    client,
    db_session,
):

    session = LoanSession(
        status="CREATED",
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        f"/loan/sessions/{session.id}/start"
    )

    assert response.status_code == 400