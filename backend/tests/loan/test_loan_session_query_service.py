from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_session_query_service import (
    LoanSessionQueryService,
)


def test_get_loan_session(db_session):
    card = Card(
        name="Black Lotus",
    )

    session = LoanSession(
        status="CREATED",
    )

    db_session.add(card)
    db_session.add(session)
    db_session.commit()

    assignment = LoanAssignment(
        session_id=session.id,
        card_id=card.id,
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    db_session.add(assignment)
    db_session.commit()

    service = LoanSessionQueryService(
        db_session,
    )

    result = service.get(
        session.id,
    )

    assert result is not None
    assert result.id == session.id
    assert len(result.assignments) == 1
    assert result.assignments[0].player_name == "Alice"
    assert result.assignments[0].card.name == "Black Lotus"


def test_get_unknown_session_returns_none(db_session):
    service = LoanSessionQueryService(
        db_session,
    )

    result = service.get(
        999,
    )

    assert result is None


def test_list_all_sessions(db_session):
    first_session = LoanSession(
        status="CREATED",
    )

    second_session = LoanSession(
        status="READY",
    )

    db_session.add(first_session)
    db_session.add(second_session)
    db_session.commit()

    service = LoanSessionQueryService(
        db_session,
    )

    result = service.list_all()

    assert len(result) == 2
    assert {
        session.id for session in result
    } == {
        first_session.id,
        second_session.id,
    }


def test_list_all_sessions_when_empty(db_session):
    service = LoanSessionQueryService(
        db_session,
    )

    result = service.list_all()

    assert result == []
