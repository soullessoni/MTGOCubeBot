from sqlalchemy.orm import Session

from app.services.loan.loan_planning_service import LoanPlanningService
from app.services.inventory.inventory_service import InventoryService

from app.services.loan.loan_session_generator import (
    LoanSessionGenerator,
)


class CreateLoanSessionFromDraftUseCase:

    def __init__(
            self,
            db: Session,
    ):
        inventory_service = InventoryService(db)

        planning_service = LoanPlanningService(
            inventory_service=inventory_service
        )

        self.generator = LoanSessionGenerator(
            db,
            planning_service,
        )

    def execute(
        self,
        players: list[dict],
    ):
        return self.generator.create_from_draft(
            players,
        )