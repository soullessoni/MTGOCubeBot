from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)


def test_link_discord_identity_persists(db_session):
    session = LoanSession(
        status="CREATED",
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

    result = service.link_discord(
        assignment,
        discord_user_id="123456789012345678",
        mtgo_username="AlicePlays",
    )

    assert result.discord_user_id == "123456789012345678"
    assert result.mtgo_username == "AlicePlays"


def test_discord_identity_defaults_to_none():
    assignment = LoanAssignment(
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    assert assignment.discord_user_id is None
    assert assignment.mtgo_username is None
