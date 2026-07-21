from app.models.loan_assignment import LoanAssignment


class LoanAssignmentStatusService:

    CREATED = "CREATED"
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"

    ALLOWED_TRANSITIONS = {
        CREATED: [
            BORROWED,
        ],
        BORROWED: [
            RETURNED,
        ],
        RETURNED: [],
    }

    def mark_borrowed(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        return self._transition(
            assignment,
            self.BORROWED,
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
                f"Invalid transition: "
                f"{current_status} -> {new_status}"
            )

        assignment.status = new_status

        return assignment