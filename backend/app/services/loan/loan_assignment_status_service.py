class LoanAssignmentStatusService:

    CREATED = "CREATED"
    HANDED_OUT = "HANDED_OUT"
    RETURNED = "RETURNED"

    ALLOWED_TRANSITIONS = {
        CREATED: [
            HANDED_OUT,
        ],
        HANDED_OUT: [
            RETURNED,
        ],
        RETURNED: [],
    }

    def mark_handed_out(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        return self._transition(
            assignment,
            self.HANDED_OUT,
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