import pytest

from app.models.card import Card
from app.use_cases.loan.create_loan_session import CreateLoanSessionUseCase
from app.services.loan.loan_planning_service import (
    LoanPlanningResult,
    LoanRequest,
    RequestedCard,
)


def test_create_session_from_plan(db_session):
    lotus = Card(
        name="Black Lotus",
    )

    bolt = Card(
        name="Lightning Bolt",
    )

    plan = LoanPlanningResult(
        requests=[
            LoanRequest(
                player_name="Alice",
                requested_cards=[
                    RequestedCard(
                        card=lotus,
                        quantity=1,
                    ),
                    RequestedCard(
                        card=bolt,
                        quantity=1,
                    ),
                ],
            )
        ],
        conflicts=[],
    )

    service = CreateLoanSessionUseCase(
        db_session,
    )

    session = service.execute(plan)

    assert session.status == "CREATED"
    assert len(session.assignments) == 2

    assert session.assignments[0].player_name == "Alice"
    assert session.assignments[0].card == lotus
    assert session.deposit_required is False
    assert session.deposit_amount is None


def test_create_session_with_deposit_required(db_session):
    lotus = Card(name="Black Lotus")

    plan = LoanPlanningResult(
        requests=[
            LoanRequest(
                player_name="Alice",
                requested_cards=[RequestedCard(card=lotus, quantity=1)],
            )
        ],
        conflicts=[],
    )

    service = CreateLoanSessionUseCase(db_session)

    session = service.execute(
        plan,
        deposit_required=True,
        deposit_amount=10,
    )

    assert session.deposit_required is True
    assert session.deposit_amount == 10


def test_create_session_rejects_deposit_required_without_amount(db_session):
    lotus = Card(name="Black Lotus")

    plan = LoanPlanningResult(
        requests=[
            LoanRequest(
                player_name="Alice",
                requested_cards=[RequestedCard(card=lotus, quantity=1)],
            )
        ],
        conflicts=[],
    )

    service = CreateLoanSessionUseCase(db_session)

    with pytest.raises(ValueError):
        service.execute(
            plan,
            deposit_required=True,
            deposit_amount=None,
        )