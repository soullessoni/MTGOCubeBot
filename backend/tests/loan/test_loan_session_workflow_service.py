import pytest

from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


def test_start_ready_session(db_session):
    session = LoanSession(
        status="READY",
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    service.start(session)

    assert session.status == "IN_PROGRESS"


def test_cannot_start_created_session(db_session):
    session = LoanSession(
        status="CREATED",
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    with pytest.raises(ValueError):
        service.start(session)


def test_hand_out_assignments(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="CREATED",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    service.hand_out(session)

    assert (
            session.assignments[0].status
            == "HANDED_OUT"
    )


def test_complete_only_when_returned(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    db_session.add(session)
    db_session.commit()

    assignment = LoanAssignment(
        status="RETURNED",
        player_name="Alice",
        quantity=1,
        card_id=1,
        session_id=session.id,
    )

    session.assignments.append(
        assignment,
    )

    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    service.complete(session)

    assert session.status == "COMPLETED"


def test_cannot_complete_with_missing_return(db_session):
    session = LoanSession(
        status="IN_PROGRESS",
    )

    db_session.add(session)
    db_session.commit()

    assignment = LoanAssignment(
        status="HANDED_OUT",
        player_name="Alice",
        quantity=1,
        card_id=1,
        session_id=session.id,
    )

    session.assignments.append(
        assignment,
    )

    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    with pytest.raises(ValueError):
        service.complete(session)


def test_hand_out_is_persisted(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    session.assignments.append(
        LoanAssignment(
            card=card,
            status="CREATED",
            player_name="Alice",
            quantity=1,
        )
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    service.hand_out(session)

    db_session.expire_all()

    refreshed = (
        db_session.query(LoanSession)
        .first()
    )

    assert (
            refreshed.assignments[0].status
            == "HANDED_OUT"
    )

    def test_return_card(db_session):
        card = Card(
            name="Black Lotus",
        )

        session = LoanSession(
            status="IN_PROGRESS",
        )

        assignment = LoanAssignment(
            card=card,
            status="HANDED_OUT",
            player_name="Alice",
            quantity=1,
        )

        session.assignments.append(
            assignment,
        )

        db_session.add(session)
        db_session.commit()

        service = LoanSessionWorkflowService(
            db_session,
        )

        service.return_card(
            assignment,
        )

        assert assignment.status == "RETURNED"

    def test_cannot_return_created_card(db_session):
        card = Card(
            name="Black Lotus",
        )

        session = LoanSession(
            status="IN_PROGRESS",
        )

        assignment = LoanAssignment(
            card=card,
            status="CREATED",
            player_name="Alice",
            quantity=1,
        )

        session.assignments.append(
            assignment,
        )

        db_session.add(session)
        db_session.commit()

        service = LoanSessionWorkflowService(
            db_session,
        )

        with pytest.raises(ValueError):
            service.return_card(
                assignment,
            )

    def test_cannot_return_twice(db_session):
        card = Card(
            name="Black Lotus",
        )

        session = LoanSession(
            status="IN_PROGRESS",
        )

        assignment = LoanAssignment(
            card=card,
            status="RETURNED",
            player_name="Alice",
            quantity=1,
        )

        session.assignments.append(
            assignment,
        )

        db_session.add(session)
        db_session.commit()

        service = LoanSessionWorkflowService(
            db_session,
        )

        with pytest.raises(ValueError):
            service.return_card(
                assignment,
            )


def test_return_card(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="HANDED_OUT",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    service.return_card(
        assignment,
    )

    assert assignment.status == "RETURNED"


def test_cannot_return_created_card(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="CREATED",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    with pytest.raises(ValueError):
        service.return_card(
            assignment,
        )


def test_cannot_return_twice(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="IN_PROGRESS",
    )

    assignment = LoanAssignment(
        card=card,
        status="RETURNED",
        player_name="Alice",
        quantity=1,
    )

    session.assignments.append(
        assignment,
    )

    db_session.add(session)
    db_session.commit()

    service = LoanSessionWorkflowService(
        db_session,
    )

    with pytest.raises(ValueError):
        service.return_card(
            assignment,
        )
