from app.models.loan_assignment import LoanAssignment


class LoanAssignmentStatusService:
    CREATED = "CREATED"
    PREPARED = "PREPARED"
    DISTRIBUTED = "DISTRIBUTED"
    CONFIRMED = "CONFIRMED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"

    TERMINAL_STATUSES = (
        RETURNED,
        CANCELLED,
    )

    ALLOWED_TRANSITIONS = {
        CREATED: [
            PREPARED,
            CANCELLED,
        ],
        PREPARED: [
            DISTRIBUTED,
            CANCELLED,
        ],
        DISTRIBUTED: [
            CONFIRMED,
            CANCELLED,
        ],
        CONFIRMED: [
            RETURNED,
            CANCELLED,
        ],
        RETURNED: [],
        CANCELLED: [],
    }

    def mark_prepared(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self._transition(
            assignment,
            self.PREPARED,
        )

    def mark_distributed(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self._transition(
            assignment,
            self.DISTRIBUTED,
        )

    def mark_confirmed(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self._transition(
            assignment,
            self.CONFIRMED,
        )

    def mark_returned(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self._transition(
            assignment,
            self.RETURNED,
        )

    def force_cancel(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        if assignment.status in self.TERMINAL_STATUSES:
            return assignment

        assignment.status = self.CANCELLED

        return assignment

    def _transition(
            self,
            assignment: LoanAssignment,
            new_status: str,
    ) -> LoanAssignment:
        current_status = assignment.status

        allowed = self.ALLOWED_TRANSITIONS.get(
            current_status,
            [],
        )

        if new_status not in allowed:
            raise ValueError(
                f"Invalid assignment transition: "
                f"{current_status} -> {new_status}"
            )

        assignment.status = new_status

        return assignment
