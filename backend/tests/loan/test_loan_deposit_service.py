import pytest

from app.models.loan_session import LoanSession
from app.services.loan.loan_deposit_service import LoanDepositService


def test_create_deposit_uses_session_amount(db_session):
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=10,
    )
    db_session.add(session)
    db_session.commit()

    service = LoanDepositService(db_session)

    deposit = service.create(session, "FruitDuChene")

    assert deposit.session_id == session.id
    assert deposit.mtgo_username == "FruitDuChene"
    assert deposit.required_amount == 10
    assert deposit.collected_amount is None
    assert deposit.returned_amount is None


def test_create_deposit_rejects_session_without_deposit_required(db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    service = LoanDepositService(db_session)

    with pytest.raises(ValueError):
        service.create(session, "FruitDuChene")


def test_record_collected_amount(db_session):
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=10,
    )
    db_session.add(session)
    db_session.commit()

    service = LoanDepositService(db_session)
    deposit = service.create(session, "FruitDuChene")

    result = service.record_collected(deposit, 10)

    assert result.collected_amount == 10
    assert result.returned_amount is None


def test_record_returned_amount(db_session):
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=10,
    )
    db_session.add(session)
    db_session.commit()

    service = LoanDepositService(db_session)
    deposit = service.create(session, "FruitDuChene")
    service.record_collected(deposit, 10)

    result = service.record_returned(deposit, 10)

    assert result.collected_amount == 10
    assert result.returned_amount == 10


def test_list_for_session_returns_only_that_sessions_deposits(db_session):
    session_a = LoanSession(status="CREATED", deposit_required=True, deposit_amount=5)
    session_b = LoanSession(status="CREATED", deposit_required=True, deposit_amount=5)
    db_session.add_all([session_a, session_b])
    db_session.commit()

    service = LoanDepositService(db_session)
    service.create(session_a, "Alice")
    service.create(session_a, "Bob")
    service.create(session_b, "Carol")

    result = service.list_for_session(session_a.id)

    assert {deposit.mtgo_username for deposit in result} == {"Alice", "Bob"}


def test_get_returns_none_for_missing_deposit(db_session):
    service = LoanDepositService(db_session)

    assert service.get(999) is None


def test_create_is_idempotent_per_session_and_player(db_session):
    """A retried give job (e.g. after a failed trade) re-runs
    `_create_deposit` for the same player — it must reuse the existing
    row instead of creating a duplicate, or a later lookup by
    `mtgo_username` could pick the wrong (stale, uncollected) one."""
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=10,
    )
    db_session.add(session)
    db_session.commit()

    service = LoanDepositService(db_session)

    first = service.create(session, "FruitDuChene")
    service.record_collected(first, 10)

    second = service.create(session, "FruitDuChene")

    assert second.id == first.id
    assert second.collected_amount == 10
    assert len(service.list_for_session(session.id)) == 1
