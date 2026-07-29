import pytest

from app.models.loan_session import LoanSession
from app.use_cases.loan.set_session_deposit_settings import (
    SetSessionDepositSettingsUseCase,
)


def test_set_deposit_settings_enables_deposit(db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    use_case = SetSessionDepositSettingsUseCase(db_session)

    result = use_case.execute(
        session,
        deposit_required=True,
        deposit_amount=15,
    )

    assert result.deposit_required is True
    assert result.deposit_amount == 15


def test_set_deposit_settings_disables_deposit_and_clears_amount(db_session):
    session = LoanSession(
        status="CREATED",
        deposit_required=True,
        deposit_amount=15,
    )
    db_session.add(session)
    db_session.commit()

    use_case = SetSessionDepositSettingsUseCase(db_session)

    result = use_case.execute(
        session,
        deposit_required=False,
        deposit_amount=None,
    )

    assert result.deposit_required is False
    assert result.deposit_amount is None


def test_set_deposit_settings_rejects_required_without_positive_amount(db_session):
    session = LoanSession(status="CREATED")
    db_session.add(session)
    db_session.commit()

    use_case = SetSessionDepositSettingsUseCase(db_session)

    with pytest.raises(ValueError):
        use_case.execute(
            session,
            deposit_required=True,
            deposit_amount=0,
        )
