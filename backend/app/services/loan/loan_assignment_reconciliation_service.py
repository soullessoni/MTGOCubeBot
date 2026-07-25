from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


class LoanAssignmentReconciliationService:
    """Advances only the assignments whose card actually changed hands in
    an MTGO trade, rather than assuming every planned card was taken — a
    player is never forced to pick everything offered from an exposed
    binder. `received_card_names` is expected to come from
    `mtgo.client.read_receiving_panel()`.
    """

    def __init__(self):
        self.status_service = LoanAssignmentStatusService()

    def reconcile_distributed(
            self,
            assignments: list[LoanAssignment],
            received_card_names: set[str],
    ) -> list[LoanAssignment]:
        return self._reconcile(
            assignments,
            received_card_names,
            from_status=LoanAssignmentStatusService.PREPARED,
            mark=self.status_service.mark_distributed,
        )

    def reconcile_returned(
            self,
            assignments: list[LoanAssignment],
            received_card_names: set[str],
    ) -> list[LoanAssignment]:
        return self._reconcile(
            assignments,
            received_card_names,
            from_status=LoanAssignmentStatusService.CONFIRMED,
            mark=self.status_service.mark_returned,
        )

    def _reconcile(
            self,
            assignments,
            received_card_names,
            from_status,
            mark,
    ) -> list[LoanAssignment]:
        updated = []

        for assignment in assignments:
            if assignment.status != from_status:
                continue

            mtgo_name = assignment.card.mtgo_name or assignment.card_name

            if mtgo_name in received_card_names:
                mark(assignment)
                updated.append(assignment)

        return updated
