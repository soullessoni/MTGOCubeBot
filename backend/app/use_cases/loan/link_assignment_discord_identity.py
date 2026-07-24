from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)


class LinkAssignmentDiscordIdentityUseCase:

    def __init__(
            self,
            assignment_service: LoanAssignmentService,
    ):
        self.assignment_service = assignment_service

    def execute(
            self,
            assignment: LoanAssignment,
            discord_user_id: str,
            mtgo_username: str,
    ) -> LoanAssignment:
        return self.assignment_service.link_discord(
            assignment,
            discord_user_id,
            mtgo_username,
        )
