from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)


def test_record_given_quantity_persists(db_session):
    session = LoanSession(
        status="CREATED",
    )

    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=3,
        status="PREPARED",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    result = service.record_given_quantity(
        assignment,
        given_quantity=2,
    )

    assert result.given_quantity == 2
    # Recording what was actually given is orthogonal to the manual
    # DISTRIBUTED/CONFIRMED tracking flow — it must not change status.
    assert result.status == "PREPARED"


def test_given_quantity_defaults_to_none():
    assignment = LoanAssignment(
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    assert assignment.given_quantity is None
