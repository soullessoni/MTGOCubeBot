from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)


def test_mark_prepared_persists(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    result = service.mark_prepared(assignment)

    assert result.status == "PREPARED"


def test_mark_distributed_persists(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=1,
        status="PREPARED",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    result = service.mark_distributed(assignment)

    assert result.status == "DISTRIBUTED"


def test_mark_confirmed_persists(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=1,
        status="DISTRIBUTED",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    result = service.mark_confirmed(assignment)

    assert result.status == "CONFIRMED"


def test_mark_returned_persists(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=1,
        status="CONFIRMED",
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanAssignmentService(db_session)

    result = service.mark_returned(assignment)

    assert result.status == "RETURNED"
