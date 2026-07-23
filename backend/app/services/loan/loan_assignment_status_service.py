from app.models.loan_assignment import LoanAssignment


class LoanAssignmentStatusService:
    CREATED = "CREATED"
    PREPARED = "PREPARED"
    DISTRIBUTED = "DISTRIBUTED"
    CONFIRMED = "CONFIRMED"
    RETURNED = "RETURNED"

    ALLOWED_TRANSITIONS = {
        CREATED: [
            PREPARED,
        ],
        PREPARED: [
            DISTRIBUTED,
        ],
        DISTRIBUTED: [
            CONFIRMED,
        ],
        CONFIRMED: [
            RETURNED,
        ],
        RETURNED: [],
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
