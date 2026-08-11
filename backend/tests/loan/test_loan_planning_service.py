from app.models.card import Card
from app.services.loan.loan_planning_service import LoanPlanningService


class FakeInventoryService:

    def __init__(self):
        self.calls = []

    def check_availability(self, card):
        return True

    def get_available_quantity(self, card, cube_instance_id):
        return 99



def test_generate_loan_requests(db_session, cube_instance_id):

    lotus = Card(
        name="Black Lotus",
    )

    bolt = Card(
        name="Lightning Bolt",
    )

    service = LoanPlanningService(
        inventory_service=FakeInventoryService()
    )

    result = service.generate(
        {
            "Alice": [
                lotus,
                bolt,
            ]
        },
        cube_instance_id,
    )

    assert len(result) == 2

    assert result[0].player_name == "Alice"
    assert result[0].card == lotus

    assert result[1].card == bolt



def test_generate_multiple_players_requests(db_session, cube_instance_id):

    lotus = Card(
        name="Black Lotus",
    )

    bolt = Card(
        name="Lightning Bolt",
    )

    service = LoanPlanningService(
        inventory_service=FakeInventoryService()
    )

    result = service.generate(
        {
            "Alice": [
                lotus,
            ],
            "Bob": [
                bolt,
            ],
        },
        cube_instance_id,
    )

    assert len(result) == 2

    assert result[0].player_name == "Alice"
    assert result[1].player_name == "Bob"



def test_generate_empty_player_list(db_session, cube_instance_id):

    service = LoanPlanningService(
        inventory_service=FakeInventoryService()
    )

    result = service.generate({}, cube_instance_id)

    assert result == []



def test_generate_detects_duplicate_cards_conflict(db_session, cube_instance_id):

    lotus = Card(
        name="Black Lotus",
    )

    service = LoanPlanningService(
        inventory_service=FakeInventoryService()
    )

    result = service.generate(
        {
            "Alice": [
                lotus,
            ],
            "Bob": [
                lotus,
            ],
        },
        cube_instance_id,
    )

    assert len(result) == 2
