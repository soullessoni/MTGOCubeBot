from app.models.loan_assignment import LoanAssignment


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

    def hand_out(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self._transition(
            assignment,
            self.HANDED_OUT,
        )

    def return_card(
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
