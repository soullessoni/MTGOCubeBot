from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.inventory.inventory_service import InventoryService


def test_available_equals_owned_when_no_assignments(db_session):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)
    service.set_quantity(card, 2)

    assert service.get_available_quantity(card) == 2


def test_available_reduced_by_active_assignment(db_session):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)
    service.set_quantity(card, 2)

    session = LoanSession(status="IN_PROGRESS")

    session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(session)
    db_session.commit()

    assert service.get_available_quantity(card) == 1


def test_returned_assignment_does_not_reduce_availability(db_session):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)
    service.set_quantity(card, 1)

    session = LoanSession(status="COMPLETED")

    session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="RETURNED",
        )
    )

    db_session.add(session)
    db_session.commit()

    assert service.get_available_quantity(card) == 1


def test_available_reduced_across_multiple_sessions(db_session):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)
    service.set_quantity(card, 3)

    first_session = LoanSession(status="IN_PROGRESS")

    first_session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Alice",
            quantity=1,
            status="DISTRIBUTED",
        )
    )

    second_session = LoanSession(status="CREATED")

    second_session.assignments.append(
        LoanAssignment(
            card_id=card.id,
            player_name="Bob",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(first_session)
    db_session.add(second_session)
    db_session.commit()

    assert service.get_available_quantity(card) == 1


def test_available_is_zero_for_unknown_card(db_session):
    card = Card(name="Does Not Exist")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)

    assert service.get_available_quantity(card) == 0
